import argparse
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ContentStream
from .context import Context, get_fonts_dict, get_font_codecs
from .codec import MissingGlyphError
from .content import replace_text

def main():
    parser = argparse.ArgumentParser(description="Replace text in a PDF file.")
    parser.add_argument("--input", type=str, required=True, help="Path to the input PDF file.")
    parser.add_argument("--output", type=str, help="Path to the output PDF file.")
    parser.add_argument("--search", type=str, help="Regular expression to search for.")
    parser.add_argument("--replace", type=str, help="Replacement text.")
    parser.add_argument("--delete", action="store_true", help="Do not search. Delete all text.")
    parser.add_argument('--compress', action='store_true', help='Compress output.')
    parser.add_argument("--debug-ui", action="store_true", help="Show debug interface.")
    parser.add_argument("--indexes", type=int, action="extend", nargs="+", help="Indexes of matches for replacement.")
    parser.add_argument('--fonts', type=str, nargs='*', help="Font file(s) to load to embed in case of missing glyphs.")
    args = parser.parse_args()

    append_to_tree_list = None
    if (args.debug_ui):
        from .debug import initialize as initialize_debug_ui
        from .debug import append_to_tree_list as _append_to_tree_list
        app, frame, gui_treeList = initialize_debug_ui()
        append_to_tree_list = lambda operations: _append_to_tree_list(operations, gui_treeList)

    font_repository = None
    if (args.fonts):
        from .font import FontRepository
        font_repository = FontRepository()
        for font_filename in args.fonts:
            postscript_name, _ = font_repository.load(font_filename)
            print(f"Loaded font „{postscript_name}“.")

    total_replacements = 0
    reader = PdfReader(args.input)
    writer = PdfWriter(clone_from=reader)
    try:
        for page_index, page in enumerate(writer.pages):
            fonts_dict = get_fonts_dict(page)
            font_codecs = get_font_codecs(fonts_dict)
            if (args.search is None):
                print(f"# These fonts are referenced on page {page_index+1}: {', '.join([fc.font.name for fc in font_codecs.values()])}")
            context = Context(font_codecs, fonts_dict, font_repository, writer)
            contents = page.get_contents()
            if (isinstance(contents, ArrayObject)):
                for content in contents:
                    total_replacements += replace_text(content, context, args.search, args.replace, args.delete, args.indexes, append_to_tree_list)
            elif (isinstance(contents, ContentStream)):
                total_replacements += replace_text(contents, context, args.search, args.replace, args.delete, args.indexes, append_to_tree_list)
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

if __name__ == "__main__":
    main()