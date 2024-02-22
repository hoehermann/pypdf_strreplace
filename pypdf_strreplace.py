#!/usr/bin/env python3
import argparse
import binascii
import pypdf
from typing import Any, Callable, Dict, Tuple, Union, cast
from pypdf.generic import DictionaryObject, NameObject, RectangleObject
from pypdf.constants import PageAttributes as PG
from pypdf._cmap import build_char_map

class CharMap:
    def __init__(self, subtype, encoding, map, ft):
        [setattr(self, k, v) for k,v in locals().items()]
    @classmethod
    def from_char_map(cls, subtype:str, halfspace:float, encoding:Union[str, Dict[int, str]], map:Dict[str, str], ft:DictionaryObject):
        return cls(subtype, encoding, map, ft)

# from https://github.com/py-pdf/pypdf/blob/27d0e99/pypdf/_page.py#L1546
def get_char_maps(obj: Any, space_width: float = 200.0):
    cmaps = {}
    objr = obj
    while NameObject(PG.RESOURCES) not in objr:
        # /Resources can be inherited sometimes so we look to parents
        objr = objr["/Parent"].get_object()
    resources_dict = cast(DictionaryObject, objr[PG.RESOURCES])
    if "/Font" in resources_dict:
        for f in cast(DictionaryObject, resources_dict["/Font"]):
            cmaps[f] = CharMap.from_char_map(*build_char_map(f, space_width, obj))
    for cmap in cmaps.values():
        if (
            ("/Encoding" in cmap.ft and cmap.ft["/Encoding"] == "/WinAnsiEncoding") or
            (cmap.encoding == "charmap") # NOTE: can also be a table byte → character
        ):
            print("WARNING: This tool assumes subsetting with a charmap or WinAnsiEncoding (cp1252).")
    return {cmap.ft["/BaseFont"]:cmap for cmap in cmaps.values()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Replace text in a PDF file.')
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str)
    parser.add_argument('--papersize', type=str, default="A4")
    parser.add_argument('--font', type=str)
    parser.add_argument('--search', type=str)
    parser.add_argument('--replace', type=str)
    parser.add_argument('--debug-subsetting', action='store_true')
    parser.add_argument('--debug-data', action='store_true')
    args = parser.parse_args()
    total_replacements = 0
    reader = pypdf.PdfReader(args.input)
    writer = pypdf.PdfWriter()

    for page_index, page in enumerate(reader.pages):
        print(f"Processing page {page_index+1}…")

        cmaps = get_char_maps(page)
        for fontname in cmaps.keys():
            if (not args.font):
                print(fontname)
            elif (fontname.endswith(args.font)):
                args.font = fontname

        # have these set to None for runs with only --debug-data
        search = None
        replace = None
        if (args.font and args.search and args.replace):
            charmap = cmaps[args.font]
            if (charmap.map):
                # Subsetting is active. Prepare lookup function.
                reverse_charmap = {v:k for k,v in charmap.map.items()}
                def full_to_subsetted(full):
                    missing = set([c for c in full if c not in reverse_charmap])
                    if (missing):
                        raise KeyError(f'These characters are not available in the selected font and cannot be used in replacements: {"".join(missing)}')
                    subsetted = ''.join([reverse_charmap[c] for c in full])
                    subsetted = subsetted.replace(r'(',r'\(').replace(r')',r'\)') # TODO: which other characters must be escaped? probably < and >
                    return subsetted.encode('cp1252') # TODO: use charmap.encoding here?
            else:
                # Subsetting is not active. Just encode the string.
                full_to_subsetted = lambda full: full.encode('cp1252') # TODO: use charmap.encoding here?
            search = full_to_subsetted(args.search)
            replace = full_to_subsetted(args.replace)
            if (args.debug_subsetting):
                print(f"After subsetting, „{args.search}“ looks like {search} or {binascii.hexlify(search).upper()}.")

        # based on https://stackoverflow.com/questions/41769120/search-and-replace-for-text-within-a-pdf-in-python#69276885
        def replace_in_content(content, search, replace):
            content_replacements = 0
            data = content.get_data()
            if (args.debug_data):
                print(data)
            if (search and replace):
                while (search in data):
                    data = data.replace(search, replace, 1)
                    content_replacements += 1
                # brute-forcefully retry with hexlified variant (PDF can have both ascii and binary representations)
                search = binascii.hexlify(search).upper() # TODO: research if binary representations are really always uppercase
                replace = binascii.hexlify(replace).upper()
                while (search in data):
                    data = data.replace(search, replace, 1)
                    content_replacements += 1
                content.set_data(data)
            return content_replacements
            
        page_replacements = 0
        contents = page.get_contents()
        # NOTE: contents may be None, ContentStream, EncodedStreamObject, ArrayObject
        if (isinstance(contents, pypdf.generic._data_structures.ArrayObject)):
            for content in contents:
                page_replacements += replace_in_content(content, search, replace)
        elif (isinstance(contents, pypdf.generic._data_structures.ContentStream)):
            page_replacements += replace_in_content(contents, search, replace)
        else:
            raise NotImplementedError(f"Cannot modify {type(contents)}.")
        page.replace_contents(contents)
        if (page_replacements > 0):
            print(f"Replaced {page_replacements} occurrences on this page.")
            total_replacements += page_replacements
        papersize = getattr(pypdf.PaperSize, args.papersize)
        # TODO: find out how to preserve original mediabox
        page.mediabox = RectangleObject((0, 0, papersize.width, papersize.height))
        writer.add_page(page)
    if (args.output):
        writer.write(args.output)
        print(f"Replaced {total_replacements} occurrences in document {args.output}.")
