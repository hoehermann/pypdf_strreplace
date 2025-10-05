# PyPDF Text Search and Replace

This tool searches and replaces text in PDF files using [PyPDF](https://github.com/py-pdf/pypdf).

Some alternative approaches are discussed [here](https://stackoverflow.com/questions/41769120/search-and-replace-for-text-within-a-pdf-in-python/) and 
[here](https://stackoverflow.com/questions/31703037/how-can-i-change-modify-replace-text-in-a-pdf-using-python).

**Needs pypdf 5 or newer.** pypdf 4.x.x will not suffice. This tool is known to work with pypdf 5.1.0 as well as 6.1.1.

### Caveats

Since PDF is a fairly complex and convoluted file format, searching and replacing text can only work in very specific circumstances. These are the things to consider:

* PDF files may contain no text at all but instead images (raster or vector graphics) of text. This tool will not work.
* PDF files can contain fonts. Fonts may be "subset". This means glyphs ("characters") which are not used in the document are stripped from the font. As a result, you cannot use glyphs which are not used elsewhere in the document.
* Some sequences of letters can be combined into single glyphs. This is called "ligature". This tool does not care about ligatures. Sometimes, it works.
* In case a glyph is not available in one font, the PDF generator may switch to a different font spontaneously. This can happen even for single glyphs. This tool will use only the font which is selected at the beginning of the needle.
* In PDF, you can adjust the position of individual letters in detail. This may be called "kerning". This tool can only work with text with letters not affected by this technique.

This list is not exhaustive.

#### Visual Explanation of Limitations

Consider the text "this is fine":

<img src="subsetting.svg?raw=true" />

You cannot replace "fine" with "not" since the "o" has been stripped from the font. The "n" and the "t" are available (since they are being used in "fine" and "this").

What happens with missing glyphs depends on the PDV viewer. Some draw a "glyph not found symbol" similar to ⌧. Others insert a blank space. Others crash.

With ligatures, the issue becomes even less obvious. You cannot replace "ﬁne" with "fine", since there is no "f" in the font either. Instead, a fi-ligature like "ﬁ" has been supplied (take a close look at the first two lines).

<img src="ligature.svg?raw=true" />

Overcoming this limitation would not only take substantial development effort, but also require the user to have a copy of the original font as well as the license to embed it in a document.

### Usage

First, get a list of all the lines in the PDF:

    pypdf_strreplace.py --input pdfs/Inkscape.pdf

This tool cannot do search and replace across multiple lines.

Then specify search text and replacement text:

    pypdf_strreplace.py --input pdfs/Inkscape.pdf --search "Inkscape 1.1.2" --replace "pleasure" --output out.pdf 
    pypdf_strreplace.py --input pdfs/LibreOffice.pdf --search "7.3.2" --replace "infinite" --output out.pdf

With `--debug-ui`, a GUI is shown which helps understanding the content stream structure. Completely optional. Needs wxPython.

### License

Since some parts of the code are modified variants of PyPDF, the license is copied from PyPDF.
