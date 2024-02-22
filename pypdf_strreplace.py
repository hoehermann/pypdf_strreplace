#!/usr/bin/env python3
import argparse
import sys
import io
import pypdf
from typing import Any, Callable, Dict, Tuple, Union, cast
from pypdf.generic import DictionaryObject, NameObject, RectangleObject, ContentStream
from pypdf.constants import PageAttributes as PG
from pypdf._cmap import build_char_map

# TODO: does something like this exist somewhere in PyPDF already?
# TODO: find out if ascii is an appropriate output encoding
def operations_to_bytes(operations):
    data = b""
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
    for operands, operation in operations:
        if (operands):
            operands = [operand_to_bytes(o, operation) for o in operands]
            data += b" ".join(operands)+b" "
        data += operation+b"\n"
    return data

def squash_TJs(operations):
    for operands, operation in operations:
        if (operation == b"TJ"):
            operands[0] = pypdf.generic._base.ByteStringObject(b''.join([o.original_bytes for o in operands[0] if isinstance(o, pypdf.generic._base.ByteStringObject)]))
            operation = b"Tj"
        yield (operands, operation)

def squash_TdTjs(operations, collapsible_width):
    def _squash_TdTjs(operations, collapsible_width):
        vertical_offset = 0
        horizontal_offset = 0
        previous_Tj_operands = None
        for operands, operation in operations:
            if (operation == b"Td"):
                horizontal_offset = int(operands[0])
                vertical_offset = int(operands[1])
            elif (operation == b"Tj"):
                if (vertical_offset == 0 and previous_Tj_operands and  horizontal_offset >= 0 and horizontal_offset < collapsible_width):
                    # found a Tj with no vertical adjustment
                    # → character is on same line
                    # → append character to previous Tj, ignore this Tj
                    previous_Tj_operands[0] = pypdf.generic._base.ByteStringObject(previous_Tj_operands[0] + operands[0])
                    continue
                else:
                    previous_Tj_operands = operands
            yield (operands, operation)
    # _squash_TdTjs modifies operators by reference retroactively.
    # _squash_TdTjs must iterate over the entire list to be effective.
    return list(_squash_TdTjs(operations, collapsible_width))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Replace text in a PDF file.')
    parser.add_argument('--input')
    parser.add_argument('--output', required=False)
    parser.add_argument('--collapsible_width', default=25)
    parser.add_argument('--papersize', default="A4")
    args = parser.parse_args()
    reader = pypdf.PdfReader(args.input)
    writer = pypdf.PdfWriter()
    
    for page_index, page in enumerate(reader.pages):
        print(f"Processing page {page_index+1}…")
        #page.extract_text()
        contents = page.get_contents()
        if (not isinstance(contents, pypdf.generic._data_structures.ArrayObject)):
            # sometimes, there is only one content object
            contents = [contents]
        for content in contents:
            obj = content.get_object()
            if (not isinstance(obj, pypdf.generic._data_structures.DecodedStreamObject)):
                raise NotImplementedError("Modifying encoded (compressed) data streams is not supported. Uncompress input with qpdf's --qdf option should help.")
            content_stream = ContentStream(obj, reader, "bytes")
            operations = content_stream.operations
            operations = squash_TJs(operations)
            operations = squash_TdTjs(operations, args.collapsible_width)
            obj.set_data(operations_to_bytes(operations))
            
        papersize = getattr(pypdf.PaperSize, args.papersize)
        page.mediabox = RectangleObject((0, 0, papersize.width, papersize.height))
        writer.add_page(page)
    if (args.output):
        writer.write(args.output)
