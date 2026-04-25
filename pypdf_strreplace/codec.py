from pypdf.generic._base import TextStringObject, ByteStringObject
from pypdf._font import Font
from typing import Set, Union

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
    def space_glyph_available(self):
        if (self.font.character_map != {}):
            available_glyphs = self.font.character_map.values()
            return " " in available_glyphs
        return True # blindly assume all other fonts and situations come with a space glyph
    def check_glyph_availability(self, text) -> Set[str]:
        if (self.font.character_map != {}):
            available_glyphs = self.font.character_map.values()
            return set([glyph for glyph in text if glyph not in available_glyphs and glyph != " "]) # missing space should be handled in set_operand_text()
        if (isinstance(self.font.encoding, dict)):
            # no idea if this check is actually correct or reliable
            # font.encoding seems to be handled by pypdf internally – no translation needs to happen here
            return set([glyph for glyph in text if glyph not in self.font.encoding.values() or glyph not in self.font.character_widths or self.font.character_widths[glyph] == 0])
    def encode(self, text, reference):
        #print(f"Encoding „{text}“ to conform to", type(reference))
        missing_glyphs = self.check_glyph_availability(text)
        if (missing_glyphs):
            error_message = f"Replacement glyphs {missing_glyphs} are not available on this page for font {self.font.name}."
            raise MissingGlyphError(error_message)
        if (isinstance(self.font.encoding, dict)):
            return TextStringObject(text)
        elif (self.font.encoding == "charmap"):
            map = {v:k for k,v in self.font.character_map.items()}
            return ByteStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode('ascii'))
        elif (isinstance(reference, TextStringObject) and isinstance(self.font.encoding, str) and self.font.character_map):
            map = {v:k for k,v in self.font.character_map.items() if not isinstance(v,str) or len(v) == 1}
            return TextStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode(self.font.encoding))
        elif (isinstance(reference, ByteStringObject)):
            map = {v:k for k,v in self.font.character_map.items() if not isinstance(v,str) or len(v) == 1}
            return ByteStringObject(text.translate(ExceptionalTranslator(map, self.font.name)).encode(self.font.encoding))
        else:
            raise NotImplementedError(f"Cannot encode this {type(self.font.encoding)} encoding: {self.font.encoding}")

class WinAnsiFontCodec(FontCodec):
    def space_glyph_available(self):
        return True
    def check_glyph_availability(self, text):
        def is_windows_1252(glyph):
            try:
                glyph.encode("Windows-1252")
                return True
            except UnicodeEncodeError:
                return False
        return [glyph for glyph in text if not is_windows_1252(glyph)]
    def decode(self, text):
        raise NotImplementedError("This should never be called.")
    def encode(self, text, reference):
        #print(f"Encoding „{text}“")
        try:
            return ByteStringObject(text.encode("Windows-1252"))
        except UnicodeEncodeError as ue:
            glyph = ue.args[1][ue.args[2]]
            error_message = f"Glyph »{glyph}« is not available in Windows-1252."
            raise MissingGlyphError(error_message)
