# PyPDF Text Search and Replace

This tool searches and replaces text in PDF files using [PyPDF](https://github.com/py-pdf/pypdf).

Some alternative approaches are discussed [here](https://stackoverflow.com/questions/41769120/search-and-replace-for-text-within-a-pdf-in-python/) and 
[here](https://stackoverflow.com/questions/31703037/how-can-i-change-modify-replace-text-in-a-pdf-using-python).

Last known to work with pypdf 4.0.2.

### Caveats

Since PDF is a fairly complex and convoluted file format, searching and replacing text can only work in very specific circumstances. These are the things to consider:

* PDF files may contain no text at all but instead images (raster or vector graphics) of text.
* PDF files can contain fonts. Fonts may be "subset". This means glyphs ("characters") which are not used in the document are stripped from the font. As a result, you cannot use glyphs which are not used elsewhere in the document.
* Some sequences of letters can be combined into single glyphs. This is called "ligature". This tool does not handle ligatures.
* In PDF, you can adjust the position of individual letters in detail. This may be called "kerning". This tool can only work with text with letters not affected by this technique.

This list is not exhaustive.

### Usage

First, get a list of all the fonts included in the PDF:

    pypdf_strreplace.py --input pdfs/Inkscape.pdf

Then select the font, search text and replacement text:

    pypdf_strreplace.py --input pdfs/Inkscape.pdf --font '/ZXOQQB+DejaVuSans' --search 'Inkscape 1.1.2' --replace 'pleasure' --output out.pdf 

    pypdf_strreplace.py --input pdfs/LibreOffice.pdf --font '/BAAAAA+LiberationSerif' --search "7.3.2" --replace "infinite" --output out.pdf

You need to guess which of the fonts may be correct. Or rely on your typography experience.

For most of your documents, this will probably not work right away. You can use `--debug-subsetting` to see how the strings look after they have been translated due to subsetting:

    pypdf_strreplace.py --input pdfs/Inkscape.pdf --font '/ZXOQQB+DejaVuSans' --search 'Inkscape 1.1.2' --replace 'pleasure' --debug-subsetting

With `--debug-data`, you can take a look at the raw data:

    pypdf_strreplace.py --input pdfs/Inkscape.pdf --debug-data

Your translated string might be interrupted by commands. In any case… good luck.

### License

Since some parts of the code are modified variants of PyPDF, the license is copied from PyPDF.
