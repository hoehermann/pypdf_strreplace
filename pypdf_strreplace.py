#!/usr/bin/env python3
import argparse
import sys
import io
import pypdf
from typing import Any, Callable, Dict, Tuple, Union, cast
from pypdf.generic import DictionaryObject, NameObject, RectangleObject, ContentStream
from pypdf.constants import PageAttributes as PG
from pypdf._cmap import build_char_map

# from https://github.com/py-pdf/pypdf/blob/27d0e99/pypdf/_page.py#L1546
def get_char_maps(obj: Any, space_width: float = 200.0):
    cmaps: Dict[
        str,
        Tuple[
            str, float, Union[str, Dict[int, str]], Dict[str, str], DictionaryObject
        ],
    ] = {}
    objr = obj
    while NameObject(PG.RESOURCES) not in objr:
        # /Resources can be inherited sometimes so we look to parents
        objr = objr["/Parent"].get_object()
    resources_dict = cast(DictionaryObject, objr[PG.RESOURCES])
    if "/Font" in resources_dict:
        for f in cast(DictionaryObject, resources_dict["/Font"]):
            cmaps[f] = build_char_map(f, space_width, obj)
    return cmaps

        
def full_to_subsetted(full, cmap):
    reverse_charmap = {v:k for k,v in cmap[3].items()}
    subsetted = ''.join([reverse_charmap[c] for c in full])
    #subsetted = subsetted.replace(r'(',r'\(').replace(r')',r'\)') # TODO: which other characters must be escaped?
    return subsetted.encode(cmap[2])

# TODO: does something like this exist somewhere in PyPDF already?
#       → looks like obj.write_to_stream
# TODO: find out if ascii is an appropriate output encoding
def operation_tuple_to_bytes(operands, operation):
    def operand_to_bytes(operand, operation):
        #print(f"{operand} is of type {type(operand)}")
        if (isinstance(operand, pypdf.generic._data_structures.ArrayObject)):
            return b"["+b"".join([operand_to_bytes(o, operation) for o in operand])+b"]"
        elif (isinstance(operand, pypdf.generic._base.ByteStringObject)):
            return b"("+operand.original_bytes.replace(b"(",br"\(").replace(b")",br"\)")+b")"
        elif (isinstance(operand, pypdf.generic._base.FloatObject)):
            return f"{operand:.2f}".encode("ascii")
        else:
            return str(operand).encode("ascii")
    data = b""
    if (operands):
        operands = [operand_to_bytes(o, operation) for o in operands]
        data += b" ".join(operands)+b" "
    data += operation
    return data
def operations_to_bytes(operations):
    return b"\n".join([operation_tuple_to_bytes(*opt) for opt in operations])

class Operation:
    def __init__(self, operation):
        self.original = operation
        self.squashed = operation
        self.modified = operation
        self.text = None
        self.font = None
    def __str__(self):
        return self.original[1].decode("ascii")+"\t"+(self.squashed[1].decode("ascii") if self.squashed else "")+"\t"+(self.text if self.text else "")

def map_text(operations, cmaps):
    global font
    for ooperation in operations:
        if (ooperation.squashed is None):
            continue
        operands, operation = ooperation.squashed
        if (operation == b"Tf"):
            font = operands[0]
        if (operation == b"Tj"):
            ooperation.font = font
            cmap = cmaps[font]
            if (isinstance(cmap[2], str)):
                decoded_operand = operands[0].decode(cmap[2], "surrogatepass")
                ooperation.text = "".join([cmap[3][c] for c in decoded_operand])
            else:
                ooperation.text = operands[0].decode("charmap", "surrogatepass")
def squash_TJs(operations):
    for ooperation in operations:
        operands, operation = ooperation.squashed
        if (operation == b"TJ" and operands):
            operands[0] = pypdf.generic._base.ByteStringObject(b''.join([o.original_bytes for o in operands[0] if isinstance(o, pypdf.generic._base.ByteStringObject)]))
            operation = b"Tj"
        ooperation.squashed = (operands, operation)

def squash_TdTjs(operations, collapsible_width):
    vertical_offset = 0
    horizontal_offset = 0
    previous_Tj_operands = None
    for ooperation in operations:
        operands, operation = ooperation.squashed
        if (operation == b"Td"):
            horizontal_offset = int(operands[0])
            vertical_offset = int(operands[1])
        elif (operation == b"Tj"):
            if (vertical_offset == 0 and previous_Tj_operands and  horizontal_offset >= 0 and horizontal_offset < collapsible_width):
                # found a Tj with no vertical adjustment
                # → character is on same line
                # → append character to previous Tj, ignore this Tj
                previous_Tj_operands[0] = pypdf.generic._base.ByteStringObject(previous_Tj_operands[0] + operands[0])
                ooperation.squashed = None
                continue
            else:
                previous_Tj_operands = operands
        ooperation.squashed = (operands, operation)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Replace text in a PDF file.')
    parser.add_argument('--input')
    parser.add_argument('--output', required=False)
    parser.add_argument('--remove_spacing', action='store_true')
    parser.add_argument('--collapse_lines', action='store_true')
    parser.add_argument('--collapsible_width', type=int, default=25)
    parser.add_argument('--operations', action='store_true')
    parser.add_argument('--papersize', type=str, default="A4")
    parser.add_argument('--search', type=str, required=False)
    parser.add_argument('--replace', type=str, default="")
    args = parser.parse_args()
    reader = pypdf.PdfReader(args.input)
    writer = pypdf.PdfWriter()
    
    for page_index, page in enumerate(reader.pages):
        print(f"Processing page {page_index+1}…")
        cmaps = get_char_maps(page)
        contents = page.get_contents()
        if (not isinstance(contents, pypdf.generic._data_structures.ArrayObject)):
            # sometimes, there is only one content object
            contents = [contents]
        for content in contents:
            obj = content.get_object()
            if (not isinstance(obj, pypdf.generic._data_structures.DecodedStreamObject)):
                raise NotImplementedError("Modifying encoded (compressed) data streams is not supported. Uncompress input with qpdf's --qdf option should help.")
            content_stream = ContentStream(obj, reader, "bytes")
            if (args.operations):
                for operation in content_stream.operations:
                    print(operation)
            operations = [Operation(o) for o in content_stream.operations]
            if (args.remove_spacing):
                squash_TJs(operations)
            if (args.collapse_lines):
                squash_TdTjs(operations, args.collapsible_width)
            map_text(operations, cmaps)
            for ooperation in operations:
                if (ooperation.text):
                    if (not args.output):
                        print(ooperation.text)
                    if (args.search): 
                        while (args.search in ooperation.text):
                            search_subsetted = full_to_subsetted(args.search, cmaps[ooperation.font])
                            replace_subsetted = full_to_subsetted(args.replace, cmaps[ooperation.font])
                            ooperation.text = ooperation.text.replace(args.search, args.replace, 1)
                            if (search_subsetted in ooperation.original[0][0]):
                                ooperation.modified = ooperation.original
                                ooperation.modified[0][0] = ooperation.original[0][0].replace(search_subsetted, replace_subsetted, 1)
                            elif (search_subsetted in ooperation.squashed[0][0]):
                                ooperation.modified = ooperation.squashed
                                ooperation.modified[0][0] = ooperation.squashed[0][0].replace(search_subsetted, replace_subsetted, 1)
                            else:
                                raise ValueError("Unable to confirm match.")
            obj.set_data(operations_to_bytes([oop.modified for oop in operations if oop.modified is not None]))
            
        papersize = getattr(pypdf.PaperSize, args.papersize)
        page.mediabox = RectangleObject((0, 0, papersize.width, papersize.height))
        writer.add_page(page)
    if (args.output):
        writer.write(args.output)
