import pypdf
from pypdf.generic import NameObject, DictionaryObject, ContentStream, ArrayObject, NumberObject, TextStringObject, ByteStringObject
writer = pypdf.PdfWriter()
page = pypdf.PageObject.create_blank_page(writer, 50, 20)
page[NameObject('/Resources')] = DictionaryObject()
page['/Resources'][NameObject('/Font')] = DictionaryObject()
font_dict = DictionaryObject()
font_dict[NameObject('/Type')] = NameObject('/Font')
font_dict[NameObject('/Subtype')] = NameObject('/TrueType')
font_dict[NameObject('/BaseFont')] = NameObject('/FreeSans')
font_dict[NameObject('/Encoding')] = NameObject('/WinAnsiEncoding')
page['/Resources']['/Font'][NameObject('/F1')] = font_dict
content = ContentStream(None, page.pdf)
content.operations = [
    (ArrayObject(), b'BT'),
    (ArrayObject([NumberObject(12), NumberObject(5)]), b'Td'),
    ([NameObject('/F1'), NumberObject(12)], b'Tf'),
    (ArrayObject([ByteStringObject('ÄB€'.encode("cp1252"))]), b'Tj'),
    (ArrayObject(), b'ET'),
    (ArrayObject(), b'Q'),
]
print(content.operations)
page.replace_contents(content)
writer.add_page(page)
writer.write("test.pdf")