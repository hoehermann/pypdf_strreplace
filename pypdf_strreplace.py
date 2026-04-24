#!/usr/bin/env python3
try:
    import pypdf
except ModuleNotFoundError:
    print("pypdf not found. pypdf 6.6.x is needed. A newer version might work, too.")
    raise
pypdf_version = tuple([int(x) for x in pypdf.__version__.split(".")[0:2]])
if (pypdf_version < (6,6)):
    raise ModuleNotFoundError(f"pypdf 6.6.x is needed. A newer version might work, too. You have {pypdf.__version__}.")
import argparse
from typing import Any, Dict, Tuple, Union, List, cast
from pypdf.generic import DictionaryObject, NameObject, ArrayObject, ContentStream
from pypdf.generic._base import TextStringObject, ByteStringObject, NumberObject, FloatObject
from pypdf.constants import PageAttributes as PG
from pypdf._font import Font
import re

class MissingGlyphError(KeyError):
    pass

class ExceptionalTranslator:
    def __init__(self, map, font_name):
        self.trans = str.maketrans(map)
        self.font_name = font_name
    def __getitem__(self, key):
        if key not in self.trans.keys():
            if (key == 32):
                print("WARNING: Missing space glyph.")
            else:
                error_message = f"Replacement glyph »{chr(key)}« (ordinal {key}) is not available in this document for font {self.font_name}." # error message on separate line to avoid confusion with the acutal string „key“
                raise MissingGlyphError(error_message)
        return self.trans.__getitem__(key)

class FontCodec:
    def __init__(self, font: Font):
        self.font = font
    @classmethod
    def from_font(cls, font: Font):
        return cls(font)
    def decode(self, text:Union[TextStringObject,ByteStringObject]):
        #print(f"Decoding „{text.get_original_bytes()}“ with this map:")
        #pprint.pprint(self.font.character_map)
        if (isinstance(self.font.encoding, dict)):
            return str(text) # it looks like pypdf applies the encoding dict automatically
        elif (isinstance(text, TextStringObject) and self.font.encoding == "charmap"):
            # decoding with ascii is a wild guess
            return "".join(text.get_original_bytes().decode('ascii').translate(str.maketrans(self.font.character_map)))
        elif (isinstance(text, TextStringObject) and isinstance(self.font.encoding, str) and self.font.character_map):
            return "".join(text.get_original_bytes().decode(self.font.encoding).translate(str.maketrans(self.font.character_map))).lstrip("\ufeff") # strip BOM
        elif (isinstance(text, ByteStringObject)):
            return "".join(text.decode(self.font.encoding).translate(str.maketrans(self.font.character_map)))
        else:
            raise NotImplementedError(f"Cannot decode {type(text)} „{text}“ with this {type(self.font.encoding)} encoding: {self.font.encoding}")
    def encode(self, text, reference, inject_truetype):
        #print(f"Encoding „{text}“ to conform to", type(reference))
        font_key = None
        if (self.font.character_map != {}):
            # check glyph availability for all text with fonts subject to mapping
            available_glyphs = self.font.character_map.values()
            for glyph in text:
                if (glyph not in available_glyphs):
                    # ignore missing spaces for now since most PDF viewers render unknown glyphs as space
                    # TODO: do not try to add a missing space glyph, inject PDFOperationTd instead
                    if (glyph == " "):
                        print("WARNING: Missing space glyph.")
                    else:
                        error_message = f"Replacement glyph »{glyph}« is not available in this document for font {self.font.name}."
                        raise MissingGlyphError(error_message) 
        if (isinstance(self.font.encoding, dict)):
            for c in text:
                if (self.font.character_widths[c] == 0):
                    print(f"Replacement glyph »{c}« is not available in this document for font {self.font.name}.")
                    # TODO: inject font iff is truetype and needs no translation
                    font_name = self.font.name.split('+')[-1]
                    font_key = inject_truetype(font_name)
                    print(f"Injected reference to font {font_name} as {font_key}.")
            return TextStringObject(text), font_key
        elif (self.font.encoding == "charmap"):
            map = {v:k for k,v in self.font.character_map.items()}
            return ByteStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode('ascii')), font_key # encoding with ascii is a wild guess
        elif (isinstance(reference, TextStringObject) and isinstance(self.font.encoding, str) and self.font.character_map):
            map = {v:k for k,v in self.font.character_map.items() if not isinstance(v,str) or len(v) == 1}
            # TODO: find out if BOM needs to be added in case it was stripped (see decode)
            return TextStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode(self.font.encoding)), font_key
        elif (isinstance(reference, ByteStringObject)):
            map = {v:k for k,v in self.font.character_map.items() if not isinstance(v,str) or len(v) == 1}
            return ByteStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode(self.font.encoding)), font_key
        else:
            raise NotImplementedError(f"Cannot encode this {type(self.font.encoding)} encoding: {self.font.encoding}")

def get_fonts_dict(page):
    object_with_resources = page
    while NameObject(PG.RESOURCES) not in object_with_resources:
        # /Resources can be inherited sometimes so we look to parents
        object_with_resources = object_with_resources["/Parent"].get_object()
    resources_dict = cast(DictionaryObject, object_with_resources[PG.RESOURCES])
    if "/Font" in resources_dict:
        return cast(DictionaryObject, resources_dict["/Font"])
    raise RuntimeError("This tool was not tested on PDF documents without any fonts.")

# from https://github.com/py-pdf/pypdf/blob/27d0e99/pypdf/_page.py#L1546
def get_font_codecs(fonts_dict) -> Dict[str, FontCodec]:
    font_codecs = {}
    for font_id in fonts_dict:
        font_dict = cast(DictionaryObject, fonts_dict[font_id].get_object())
        font_codecs[font_id] = FontCodec.from_font(Font.from_font_resource(font_dict))
    return font_codecs

class Context:
    def __init__(self, font_codecs:Dict[str,FontCodec], fonts_dict):
        self.font = None
        self.font_codecs = font_codecs
        self.fonts_dict = fonts_dict
    def clone_shared_font_codecs(self):
        obj = type(self)(self.font_codecs, self.fonts_dict)
        obj.font = self.font
        return obj
    def inject_truetype(self, postscript_name):
        prefix = "/F" # not all PDF generators use this prefix, but I am only interested in the first non-clashing index
        def int_or_zero(s):
            try:
                return int(s.lstrip("/F"))
            except ValueError:
                return 0
        max_font_number = max([int_or_zero(key) for key in self.fonts_dict.keys()])
        dictionary_key = prefix+str(max_font_number+1)
        font_dict = DictionaryObject()
        font_dict[NameObject("/Type")] = NameObject("/Font")
        font_dict[NameObject("/Subtype")] = NameObject("/TrueType")
        font_dict[NameObject("/BaseFont")] = NameObject("/"+postscript_name)
        # TODO: do not inject the same font more than once
        self.fonts_dict[NameObject(dictionary_key)] = font_dict
        return dictionary_key
class PDFOperation:
    def __init__(self, operands, operator, context:Context):
        self.operands = operands
        self.operator = operator
        self.context = context
    @classmethod
    def from_tuple(cls, operands, operator, context:Context):
        operator = operator.decode('ascii') # PDF operators are indeed ascii encoded
        classname = f"PDFOperation{operator}"
        if (classname in globals()):
            # create object of specific class
            return globals()[classname](operands, context)
        else:
            # create object of passthrough-class
            return cls(operands, operator, None)
    # ~ def __repr__(self):
        # ~ return self.operator
    def get_relevant_operands(self):
        return self.operands
    def write_to_stream(self, stream):
        for op in self.operands:
            op.write_to_stream(stream)
            stream.write(b" ")
        stream.write(self.operator.encode("ascii")) # PDF operators are indeed ascii encoded
        stream.write(b"\n")
class PDFOperationTf(PDFOperation):
    def __init__(self, operands, context:Context):
        super().__init__(operands, "Tf", None)
        context.font = operands[0]
class PDFOperationTd(PDFOperation):
    def __init__(self, operands, context:Context):
        super().__init__(operands, "Td", None)
        self._infer_plain_text()
    def __str__(self):
        return f"{self.operands} {self.operator}"
    def _infer_plain_text(self):
        tx, ty = self.operands
        if (ty != 0):
            # consider a vertical adjustment starting a new line
            ty.plain_text = "\n"
        elif (tx != 0):
            # interpret horizontal adjustment as space. total guess. works for the xelatex sample.
            tx.plain_text = " "
        return map
class PDFOperationTJ(PDFOperation):
    def __init__(self, operands:list[list[Union[TextStringObject,ByteStringObject,NumberObject]]], context:Context):
        if (len(operands) != 1):
            raise ValueError(f"PDFOperationTJ expects one non-empty Array of Array")
        super().__init__(operands, "TJ", context.clone_shared_font_codecs())
        self._infer_plain_text()
        object_types = set([operand.__class__ for operand in operands])-set([NumberObject.__class__])
        if (len(object_types) > 1):
            raise NotImplementedError(f"Cannot handle Operations with mixed string object types {str(object_types)}.")
    def __str__(self):
        return f"„{self.get_relevant_operands()}“ {self.operator}"
    def _infer_plain_text(self):
        for operand in self.get_relevant_operands():
            if (isinstance(operand, NumberObject) or isinstance(operand, FloatObject)):
                space_width = self.context.font_codecs[self.context.font].font.space_width
                if (operand < -space_width):
                    operand.plain_text = " "
                pass
            else:
                operand.plain_text = self.context.font_codecs[self.context.font].decode(operand)
    def get_relevant_operands(self):
        return self.operands[0]
    def set_operand_text(self, text, index):
        sample = self.operands[0][index] # use the operand which is going to be replaced as a sample
        # it is possible that the operand we are going to replace is a space produced by horizontal adjustment
        if (not isinstance(sample, TextStringObject) and not isinstance(sample, ByteStringObject)):
            # in this case, just select any text operand
            sample = next((op for op in self.operands[0] if isinstance(op, TextStringObject) or isinstance(op, ByteStringObject)))
        self.operands[0][index], font_key = font_codecs[self.context.font].encode(text, sample, self.context.inject_truetype)
        return font_key
class PDFOperationTj(PDFOperation):
    def __init__(self, operands:list[Union[TextStringObject,ByteStringObject]], context:Context):
        if (len(operands) != 1):
            raise ValueError(f"PDFOperationTj expects one non-empty Array of TextStringObject")
        super().__init__(operands, "Tj", context.clone_shared_font_codecs())
        self._infer_plain_text()
    def __str__(self):
        return f"„{self.get_relevant_operands()}“ {self.operator}"
    def _infer_plain_text(self):
        self.operands[0].plain_text = self.context.font_codecs[self.context.font].decode(self.operands[0])
    def get_relevant_operands(self):
        return self.operands
    def set_operand_text(self, text, index):
        sample = self.operands[0] # Tj has only one operand
        self.operands[0], font_key = font_codecs[self.context.font].encode(text, sample, self.context.inject_truetype)
        return font_key

def append_to_tree_list(operations, tree_list):
    root = tree_list.GetRootItem()
    for operation in operations:
        if (operation.__class__ == PDFOperation):
            continue # only show operations relevant to text processing
        operation_node = tree_list.AppendItem(root, operation.operator)
        tree_list.SetItemText(operation_node, 3, str(getattr(operation, "scheduled_change", "")))
        for operand in operation.get_relevant_operands():
            operand_node = tree_list.AppendItem(operation_node, str(operand))
            tree_list.SetItemText(operand_node, 1, str(type(operand).__name__))
            tree_list.SetItemText(operand_node, 2, getattr(operand, "plain_text", "").replace(" ","␣").replace("\n","↲")) # might also consider ␊ for visualising line breaks
            tree_list.SetItemText(operand_node, 3, str(getattr(operand, "scheduled_change", "")))
        if (operation.operator in ["Td", "Tj", "TJ"]): # only expand operators relevant to text
            tree_list.Expand(operation_node)
            tree_list.Expand(operand_node)

def extract_text(operations: List[PDFOperation]):
    text = ""
    for operation in operations:
        text += "".join([getattr(operand, "plain_text", "") for operand in operation.get_relevant_operands()])
    return text

class Change:
    def __str__(self):
        return self.__class__.__name__
    def apply(self, element=None, index=None, collection=None):
        pass
class Delete(Change):
    def apply(self, element=None, index:int=None, collection:List[Tuple]=None):
        collection.pop(index)
class Cluster(Change):
    # this Change moves the element (operand) directly in front of the next operand of the same type, creating a cluster
    def apply(self, element:Tuple=None, index:int=None, collection:List[Tuple]=None):
        element = collection.pop(index)
        target_index = next((i for i,e in enumerate(collection) if i >=index and e[1] == element[1]), None)
        if (target_index is not None):
            collection.insert(target_index, element)
class Text(Change):
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return f"Set text to „{self.text}“"
    def apply(self, element=None, index=None, collection=None):
        return element.set_operand_text(self.text, index)
def schedule_replacements(operations, matches, args_replace):
    text = ""
    match = None
    matches = matches[:]
    first_operation = None
    first_operand = None
    for operation in operations:
        for operand in operation.get_relevant_operands():
            if (hasattr(operand, "plain_text")):
                previous_length = len(text)
                text += operand.plain_text
                while (matches or match):
                    if (match):
                        if (len(text) >= match.end(0)):
                            # we have enough text to cover the end of the current match
                            postfix = operand.plain_text[match.end(0)-previous_length:].strip("\n") # see prefix
                            postfix = match.re.sub(args_replace, postfix) if args_replace is not None else postfix # see prefix
                            new_text = prefix+match.expand(args_replace)+postfix if args_replace is not None else prefix+match.group(0)+postfix
                            first_operand.scheduled_change = Text(new_text)
                            if (operand != first_operand):
                                # the match spans multiple operands
                                # the first operand receives the replacement text in its entirety (with postfix)
                                # we do not need the current operand anymore. mark current operand for deletion
                                operand.scheduled_change = Delete()
                            # we changed an operand in the operation the match begun in
                            # this might be the current operation or a previous one
                            first_operation.scheduled_change = Change()
                            if (operation != first_operation):
                                # the match spans multiple operations
                                # the first operations receives the replacement text in its entirety (with postfix)
                                # we do not need the current operations anymore. mark current operations for deletion
                                operation.scheduled_change = Delete()
                                if (operation.operator in ["TJ"]):
                                    operand_changes = set([c.__class__.__name__ if c else c for c in [getattr(op, "scheduled_change", None) for op in operation.get_relevant_operands()]])
                                    if (operand_changes-set([Delete.__name__])):
                                        #print(f"But wait: Not all the operation's operands are going to be deleted! The operation must be changed, not deleted.")
                                        operation.scheduled_change = Change()
                            # reset text gathering metadata for next match
                            match = None
                            first_operation = None
                            first_operand = None
                        else:
                            # match exists, but the current text does not reach the end
                            # quit looking here and get more text
                            break
                    if (matches):
                        if (len(text) > matches[0].start(0)):
                            match = matches[0]
                            matches.pop(0)
                            # newlines do not actually occur in the PDF. they have been added by us for visual representation. they must be removed here
                            prefix = operand.plain_text[:match.start(0)-previous_length].strip("\n")
                            # one operand might contain multiple matches. since we are focussing on the current match, we must re-do the search and replace in the prefix
                            prefix = match.re.sub(args_replace, prefix) if args_replace is not None else prefix
                            first_operation = operation
                            first_operand = operand
                        else:
                            # match exists, but the current text does not reach the start
                            # quit looking here and get more text
                            break
            if (operation.operator in ["TJ", "Tj"] and first_operand is not None and not hasattr(operand, "scheduled_change")):
                # delete operands containing replaced text
                operand.scheduled_change = Delete()
        if (first_operation is not None and not hasattr(operation, "scheduled_change")):
            # the match spans multiple operations
            # the current operation (might be Tf or something else entirely) did not contain any text and must be removed to avoid confusion
            operation.scheduled_change = Delete()
        if (isinstance(getattr(operation, "scheduled_change", None), Delete) and operation.operator == "Td"):
            # Td movement operations should not be deleted, but rather grouped together and moved behind the replacement
            operation.scheduled_change = Cluster()
def schedule_deletion(operations):
    """Schedule deletion of all text-related operations.
    
    Useful for redacting a document entirely while maintaining design."""
    for operation in operations:
        if (operation.operator in ["TJ", "Tj", "Td", "Tf"]):
            operation.scheduled_change = Delete()

def replace_text(content, context, args_search, args_replace, args_delete, args_indexes, gui_treeList):
    # transform plain operations to high-level objects
    operations = [PDFOperation.from_tuple(operands, operator, context) for operands, operator in content.operations]
    
    # flatten mappings into one plain text string
    text = extract_text(operations)

    matches = []
    if (args_search is None and not args_delete):
        # just print
        print("# These are the lines this tool might be able to handle:")
        print(text)
    if (args_search):
        # search in text
        matcher = re.compile(args_search)
        matches = list(matcher.finditer(text))

    if args_indexes is not None:
        matches = [m for i,m in enumerate(matches) if i in args_indexes]

    if (args_search is not None and args_delete is False):
        # look up which operations contributed to each match and schedule to replace them
        schedule_replacements(operations, matches, args_replace)
    if (args_delete):
        schedule_deletion(operations)
    
    # visualize content stream structure and scheduled changes
    if (gui_treeList):
        append_to_tree_list(operations, gui_treeList)

    if (args_replace is not None or args_delete is True):
        # do the replacements, but working backwards – else the indices would no longer match
        # we iterate over the list of high-level operations, but we modify the pypdf low-level operations
        for operation_index, operation in reversed(list(enumerate(operations))):
            operation_change = getattr(operation, "scheduled_change", None)
            if (operation_change):
                operation_change.apply(index=operation_index, collection=content.operations)
                if (isinstance(operation_change, Delete)):
                    #print(f"Deleted: {operation}")
                    pass
                elif (isinstance(operation_change, Cluster)):
                    #print(f"Moving together: {operation}")
                    pass
                else:
                    #print(f"Before replacements: {operation}")
                    for operand_index, operand in reversed(list(enumerate(operation.get_relevant_operands()))):
                        operand_change = getattr(operand, "scheduled_change", None)
                        if (operand_change):
                            font_key = operand_change.apply(operation, operand_index, operation.get_relevant_operands())
                            if (font_key is not None):
                                # TODO: keep track of font size, too
                                # insert font-selection operation right in front of the current operation which probably is a text output operation
                                # this should be okay since we touch each operation only once and changes to later operations have already been applied
                                content.operations[operation_index:operation_index] = [([NameObject(font_key), NumberObject(12)], b'Tf')]
                    #print(f"After replacements:  {operation}")
    print(content.operations)
    return len(matches) # return amount of matches – which is hopefully the amount of replacements (mind the postfixes!)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replace text in a PDF file.")
    parser.add_argument("--input", type=str, required=True, help="Path to the input PDF file.")
    parser.add_argument("--output", type=str, help="Path to the output PDF file.")
    parser.add_argument("--search", type=str, help="Regular expression to search for.")
    parser.add_argument("--replace", type=str, help="Replacement text.")
    parser.add_argument("--delete", action="store_true", help="Do not search. Delete all text.")
    parser.add_argument('--compress', action='store_true', help='Compress output.')
    parser.add_argument("--debug-ui", action="store_true", help="Show debug interface.")
    parser.add_argument("--indexes", type=int, action="extend", nargs="+", help="Indexes of matches for replacement.")
    args = parser.parse_args()
    
    gui_treeList = None
    if (args.debug_ui):
        import wx
        from gui import Main
        app = wx.App(False)
        frame = Main(parent=None)
        frame.m_treeList.AppendColumn("Operation")
        frame.m_treeList.AppendColumn("Type")
        frame.m_treeList.AppendColumn("Text")
        frame.m_treeList.AppendColumn("Changes")
        font_size = frame.m_treeList.GetFont().GetPixelSize()
        frame.m_treeList.SetColumnWidth(col=0, width=30 * font_size[0])
        gui_treeList = frame.m_treeList

    total_replacements = 0
    reader = pypdf.PdfReader(args.input)
    writer = pypdf.PdfWriter(clone_from=reader)
    try:
        for page_index, page in enumerate(writer.pages):
            fonts_dict = get_fonts_dict(page)
            font_codecs = get_font_codecs(fonts_dict)
            if (args.search is None):
                print(f"# These fonts are referenced on page {page_index+1}: {', '.join([fc.font.name for fc in font_codecs.values()])}")
            context = Context(font_codecs, fonts_dict)
            contents = page.get_contents()
            # NOTE: contents may be None, ContentStream, EncodedStreamObject, ArrayObject
            if (isinstance(contents, ArrayObject)):
                for content in contents:
                    total_replacements += replace_text(content, context, args.search, args.replace, args.delete, args.indexes, gui_treeList)
            elif (isinstance(contents, ContentStream)):
                total_replacements += replace_text(contents, context, args.search, args.replace, args.delete, args.indexes, gui_treeList)
            else:
                raise NotImplementedError(f"Handling content of type {type(contents)} is not implemented.")
            page.replace_contents(contents)

        if (args.output):
            if (args.compress):
                for page in writer.pages:
                    page.compress_content_streams()
            writer.write(args.output)

        if (args.search):
            print(f"There are {total_replacements} occurrences.")
    except MissingGlyphError as mge:
        print(mge.args[0])

    if (args.debug_ui):
        frame.Show()
        app.MainLoop()
