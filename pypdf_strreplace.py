#!/usr/bin/env python3
import argparse
import pypdf
from typing import Any, Callable, Dict, Tuple, Union, cast
from pypdf.generic import DictionaryObject, NameObject, RectangleObject, EncodedStreamObject, DecodedStreamObject
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
    return {cmap[4]["/BaseFont"]:cmap[3] for cmap in cmaps.values()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Replace text in a PDF file.')
    parser.add_argument('--input')
    parser.add_argument('--output')
    parser.add_argument('--papersize', default="A4")
    parser.add_argument('--font', required=False)
    parser.add_argument('--search', required=False)
    parser.add_argument('--replace', required=False)
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
        if (not args.font):
            continue

        charmap = cmaps[args.font]
        reverse_charmap = {v:k for k,v in charmap.items()}
        def full_to_subsetted(full):
            subsetted = ''.join([reverse_charmap[c] for c in full])
            subsetted = subsetted.replace(r'(',r'\(').replace(r')',r'\)') # TODO: which other characters must be escaped?
            return subsetted.encode('ascii') # TODO: use original cmap[2] here
        search = full_to_subsetted(args.search)
        replace = full_to_subsetted(args.replace)

        page_replacements = 0
        # based on https://stackoverflow.com/questions/41769120/search-and-replace-for-text-within-a-pdf-in-python#69276885
        contents = page.get_contents()
        for index, content in enumerate(contents):
            obj = content.get_object()
            data = obj.get_data()
            while (search in data):
                data = data.replace(search, replace, 1)
                page_replacements += 1
            if (isinstance(obj, EncodedStreamObject)):
                raise NotImplementedError("Modifying encoded (compressed) data streams is not supported. Uncompress input with qpdf's --qdf option should help.")
                obj = DecodedStreamObject() # TODO: find out how to add this to output
            obj.set_data(data)
            contents[index] = obj

        if (page_replacements > 0):
            total_replacements += page_replacements
            print(f"Replaced {page_replacements} occurrences on this page.")
        papersize = getattr(pypdf.PaperSize, args.papersize)
        # TODO: find out how to preserve original mediabox
        page.mediabox = RectangleObject((0, 0, papersize.width, papersize.height))
        writer.add_page(page)
    if (args.output):
        writer.write(args.output)
        print(f"Replaced {total_replacements} occurrences in document.")
