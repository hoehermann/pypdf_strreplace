import pypdf
from pypdf.generic import NameObject, DictionaryObject, ContentStream, ArrayObject, NumberObject, TextStringObject, ByteStringObject
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a PDF document with one line of text.')
    parser.add_argument('--width', type=int, default=100, help='Width (pt) of the blank page.')
    parser.add_argument('--height', type=int, default=20, help='Height (pt) of the blank page.')
    parser.add_argument('--x', type=int, default=18, help='X-coordinate (pt) for text placement.')
    parser.add_argument('--y', type=int, default=5, help='Y-coordinate (pt) for text placement.')
    parser.add_argument('--font_name', type=str, default='Helvetica', help='Font to use.')
    parser.add_argument('--font_size', type=int, default=12, help='Font size (units).')
    parser.add_argument('--font_type', default='Type1', const='Type1', nargs='?', choices=['Type1', 'TrueType'])
    parser.add_argument('--text', type=str, default='Hellø Wörld', help='Text to encode and place.')
    parser.add_argument('--output', type=str, default='output.pdf', help='Output PDF file name.')
    args = parser.parse_args()

    standard_14_fonts = ['Times-Roman', 'Helvetica', ' Courier', ' Symbol', ' Times-Bold', ' Helvetica-Bold', ' Courier-Bold', ' ZapfDingbats', ' Times-Italic', ' Helvetica-Oblique', ' Courier-Oblique', ' Times-BoldItalic', ' Helvetica-BoldOblique', ' Courier-BoldOblique']
    if (args.font_name not in standard_14_fonts):
        print(f'''Warning: "{args.font_name}" is not one of the PDF standard 14 fonts {", ".join(standard_14_fonts)}.
This example does not embed the font. For truthful representation, the font must be available to the PDF viewer.''')

    writer = pypdf.PdfWriter()
    page = pypdf.PageObject.create_blank_page(writer, args.width, args.height)
    page[NameObject('/Resources')] = DictionaryObject()
    page['/Resources'][NameObject('/Font')] = DictionaryObject()
    font_dict = DictionaryObject()
    font_dict[NameObject('/Type')] = NameObject('/Font')
    font_dict[NameObject('/Subtype')] = NameObject('/'+args.font_type)
    font_dict[NameObject('/BaseFont')] = NameObject('/'+args.font_name)
    font_dict[NameObject('/Encoding')] = NameObject('/WinAnsiEncoding')
    # Windows-1252 encoding is the most reasonable choice since
    # ASCII is more limited, and while
    # Unicode is possible, it is much more cumbersome.
    page['/Resources']['/Font'][NameObject('/F1')] = font_dict
    content = ContentStream(None, page.pdf)
    content.operations = [
        (ArrayObject(), b'BT'),
        (ArrayObject([NumberObject(args.x), NumberObject(args.y)]), b'Td'),
        ([NameObject('/F1'), NumberObject(args.font_size)], b'Tf'),
        (ArrayObject([ByteStringObject(args.text.encode('Windows-1252'))]), b'Tj'),
        (ArrayObject(), b'ET')
    ]
    page.replace_contents(content)
    writer.add_page(page)
    writer.write(args.output)
