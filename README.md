# PyPDF Text Search and Replace

This tool searches and replaces text in PDF files using [PyPDF](https://github.com/py-pdf/pypdf).

Some alternative approaches are discussed [here](https://stackoverflow.com/questions/41769120/search-and-replace-for-text-within-a-pdf-in-python/) and 
[here](https://stackoverflow.com/questions/31703037/how-can-i-change-modify-replace-text-in-a-pdf-using-python).

**Requires pypdf version starting with 6.6.x.** Newer may work, too. This tool is known to work with pypdf 6.10.2.

### Usage

First, get a list of all the lines in the PDF:

    python3 -m pypdf_strreplace.main --input pdfs/Inkscape.pdf

This tool cannot do search and replace across multiple lines.

Then specify search text and replacement text:

    python3 -m pypdf_strreplace.main --input pdfs/Inkscape.pdf --search "Inkscape 1.1.2" --replace "pleasure" --output out.pdf 
    python3 -m pypdf_strreplace.main --input pdfs/LibreOffice.pdf --search "7.3.2" --replace "infinite" --output out.pdf

With `--debug-ui`, a GUI is shown which helps understanding the content stream structure. Completely optional. Needs wxPython.

### Caveats

Since PDF is a fairly complex and convoluted file format, searching and replacing text can only work in very specific circumstances. These are the things to consider:

* PDF files may contain no text at all but instead images (raster or vector graphics) of text. This tool will not work.
* PDF files can contain fonts. Fonts may be "subset". This means glyphs ("characters") which are not used in the document are stripped from the font. As a result, you cannot use glyphs which are not used elsewhere in the document.
* Some sequences of letters can be combined into single glyphs. This is called "ligature". This tool does not care about ligatures. Sometimes it works.
* In case a glyph is not available in one font, the PDF generator may switch to a different font spontaneously. This can happen even for single glyphs. This tool will use only the font which is selected at the beginning of the needle.
* In PDF, you can adjust the position of individual letters in detail. This may be called "kerning". Support for replacing text with letters affected by this technique is hit or miss.

This list is not exhaustive.

#### Visual Explanation of Limitations

Consider the text "this is fine":

<img src="subsetting.svg?raw=true" />

You cannot replace "fine" with "not" since the "o" has been stripped from the font. The "n" and the "t" are available (since they are being used in "fine" and "this").

What happens with missing glyphs depends on the PDF viewer. Some draw a "glyph not found symbol" similar to ⌧. Others insert a blank space. Others crash.

With ligatures, the issue becomes even less obvious. You cannot replace "ﬁne" with "fine", since there is no "f" in the font either. Instead, a fi-ligature like "ﬁ" has been supplied (take a close look at the first two lines).

<img src="ligature.svg?raw=true" />

#### Overcoming Limitations by Providing the Font

This tool can, under some circumstances, insert missing glyphs iff the user can provide the font. The provided font must match the required font exactly. Criterion is the font's postscript name. This feature has only been tested for TrueType fonts using the Windows 1252 encoding. Support for Unicode is much harder to achieve.

**WARNING:** The font will be referenced – *not* embedded! Text sections containing inserted glyphs will only be displayed correctly if the PDF renderer has access to the font, too. On another computer, the modified text might be displayed incorrectly or not displayed at all.

    python3 -m pypdf_strreplace.main --input pdfs/Inkscape.pdf --search i --replace ö --font DejaVuSans.ttf --output out.pdf

Using this feature requires [fonttools](https://pypi.org/project/fonttools/). Version 4.46.0 is known to work.

### License

Since some parts of the code are modified variants of PyPDF, the license is copied from PyPDF.
