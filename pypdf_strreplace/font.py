from fontTools.ttLib import TTFont

class FontRepository():
    def __init__(self):
        self.fonts = {}
    def load(self, ttf_filename):
        font = TTFont(ttf_filename)
        postscript_name = next((name for name in font['name'].names if name.nameID == 6)).toUnicode()
        self.fonts[postscript_name] = font
        return postscript_name, font
    def get_widths(self, postscript_name):
        if (postscript_name not in self.fonts):
            return None
        font = self.fonts[postscript_name]
        units_per_em = font['head'].unitsPerEm
        horizontal_metrics_table = font['hmtx']
        character_map = font.getBestCmap()
        glyph_widths = [0]*256
        for index in range(256):
            try:
                # we are going for the PDF WinAnsiEncoding which is not a direct 1:1 mapping
                unicode_point = ord(bytes([index]).decode('cp1252'))
            except UnicodeDecodeError:
                continue
            if (unicode_point in character_map):
                advance_width, left_side_bearing = horizontal_metrics_table[character_map[unicode_point]]
                pdf_width = int(round(advance_width * 1000 / units_per_em))
                glyph_widths[index] = pdf_width
        return glyph_widths

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Read font metrics for PDF dictionary.')
    parser.add_argument('--input', type=str, help='Input TrueType file.')
    args = parser.parse_args()
    font_repository = FontRepository()
    postscript_name, font = font_repository.load(args.input)
    print(postscript_name)
    print(font_repository.get_widths(postscript_name))