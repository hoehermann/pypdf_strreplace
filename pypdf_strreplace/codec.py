from pypdf.generic._base import TextStringObject, ByteStringObject
from pypdf._font import Font
from typing import Union

class MissingGlyphError(KeyError):
    pass

class ExceptionalTranslator:
    def __init__(self, map, font_name):
        self.trans = str.maketrans(map)
        self.font_name = font_name
    def __getitem__(self, key):
        if key not in self.trans.keys():
            if (key == 32):
                print("WARNING: Missing space glyph.")
            else:
                error_message = f"Replacement glyph »{chr(key)}« (ordinal {key}) is not available on this page for font {self.font_name}."
                raise MissingGlyphError(error_message)
        return self.trans.__getitem__(key)

class FontCodec:
    def __init__(self, font: Font):
        self.font = font
    @classmethod
    def from_font(cls, font: Font):
        return cls(font)
    def decode(self, text:Union[TextStringObject,ByteStringObject]):
        if (isinstance(self.font.encoding, dict)):
            return str(text)
        elif (isinstance(text, TextStringObject) and self.font.encoding == "charmap"):
            return "".join(text.get_original_bytes().decode('ascii').translate(str.maketrans(self.font.character_map)))
        elif (isinstance(text, TextStringObject) and isinstance(self.font.encoding, str) and self.font.character_map):
            return "".join(text.get_original_bytes().decode(self.font.encoding).translate(str.maketrans(self.font.character_map))).lstrip("\ufeff")
        elif (isinstance(text, ByteStringObject)):
            return "".join(text.decode(self.font.encoding).translate(str.maketrans(self.font.character_map)))
        else:
            raise NotImplementedError(f"Cannot decode {type(text)} with this {type(self.font.encoding)} encoding: {self.font.encoding}")
    def inject_font_or_raise(self, text, missing_glyphs, inject_truetype):
        error_message = f"Replacement glyphs {missing_glyphs} are not available on this page for font {self.font.name}."
        if (inject_truetype is None):
            error_message += " Font injection disabled for explicitly kerned text."
            raise MissingGlyphError(error_message)
        try:
            windows_1252_bytes = text.encode("Windows-1252")
        except UnicodeEncodeError:
            error_message += " At last one glyph is not available in Windows-1252 encoding."
            raise MissingGlyphError(error_message)
        font_name = self.font.name.split('+')[-1]
        font_tuple = inject_truetype(font_name)
        print(f"Preparing to inject reference to font {font_name} and use as {font_tuple[0]}.")
        return ByteStringObject(windows_1252_bytes), font_tuple
    def encode(self, text, reference, inject_truetype):
        if (self.font.character_map != {}):
            available_glyphs = self.font.character_map.values()
            missing_glyphs = [glyph for glyph in text if glyph not in available_glyphs]
            if (" " in missing_glyphs):
                print("WARNING: Missing space glyph.")
                missing_glyphs.remove(" ")
            if (missing_glyphs):
                inject_truetype = None
                return self.inject_font_or_raise(text, missing_glyphs, inject_truetype)
        if (isinstance(self.font.encoding, dict)):
            missing_glyphs = [glyph for glyph in text if glyph not in self.font.character_widths or self.font.character_widths[glyph] == 0]
            if (missing_glyphs):
                return self.inject_font_or_raise(text, missing_glyphs, inject_truetype)
            return TextStringObject(text), None
        elif (self.font.encoding == "charmap"):
            map = {v:k for k,v in self.font.character_map.items()}
            return ByteStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode('ascii')), None
        elif (isinstance(reference, TextStringObject) and isinstance(self.font.encoding, str) and self.font.character_map):
            map = {v:k for k,v in self.font.character_map.items() if not isinstance(v,str) or len(v) == 1}
            return TextStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode(self.font.encoding)), None
        elif (isinstance(reference, ByteStringObject)):
            map = {v:k for k,v in self.font.character_map.items() if not isinstance(v,str) or len(v) == 1}
            return ByteStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode(self.font.encoding)), None
        else:
            raise NotImplementedError(f"Cannot encode this {type(self.font.encoding)} encoding: {self.font.encoding}")