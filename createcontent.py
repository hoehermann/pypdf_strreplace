import pypdf
from pypdf.generic import NameObject, DictionaryObject

writer = pypdf.PdfWriter()
page = pypdf.PageObject.create_blank_page(writer, 612, 792)

# Add font resource to the page
if '/Resources' not in page:
    page[NameObject('/Resources')] = DictionaryObject()
if '/Font' not in page['/Resources']:
    page['/Resources'][NameObject('/Font')] = DictionaryObject()

font_dict = DictionaryObject()
font_dict[NameObject('/Type')] = NameObject('/Font')
font_dict[NameObject('/Subtype')] = NameObject('/TrueType')
font_dict[NameObject('/BaseFont')] = NameObject('/Calibri-Bold')

page['/Resources']['/Font'][NameObject('/F1')] = font_dict

writer.add_page(page)
writer.write("test.pdf")