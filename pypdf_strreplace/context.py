from pypdf.generic import DictionaryObject, NameObject
from typing import Dict, cast
from .codec import FontCodec
from pypdf._font import Font

class Context:
    def __init__(self, font_codecs:Dict[str,FontCodec], fonts_dict):
        self.font = None
        self.font_size = None
        self.font_codecs = font_codecs
        self.fonts_dict = fonts_dict
    def clone_shared_font_codecs(self):
        obj = type(self)(self.font_codecs, self.fonts_dict)
        obj.font = self.font
        obj.font_size = self.font_size
        return obj
    def inject_truetype(self, postscript_name):
        font_name = "/"+postscript_name
        for key, font in self.fonts_dict.items():
            if (font["/BaseFont"] == font_name):
                return (key, self.font_size)
        prefix = "/F"
        def int_or_zero(s):
            try:
                return int(s.lstrip("/F"))
            except ValueError:
                return 0
        max_font_number = max([int_or_zero(key) for key in self.fonts_dict.keys()])
        dictionary_key = prefix+str(max_font_number+1)
        font_dict = DictionaryObject()
        font_dict[NameObject("/Type")] = NameObject("/Font")
        font_dict[NameObject("/Subtype")] = NameObject("/TrueType")
        font_dict[NameObject("/BaseFont")] = NameObject(font_name)
        self.fonts_dict[NameObject(dictionary_key)] = font_dict
        return (dictionary_key, self.font_size)

def get_fonts_dict(page):
    object_with_resources = page
    while NameObject("/Resources") not in object_with_resources:
        object_with_resources = object_with_resources["/Parent"].get_object()
    resources_dict = cast(DictionaryObject, object_with_resources["/Resources"])
    if "/Font" in resources_dict:
        return cast(DictionaryObject, resources_dict["/Font"])
    raise RuntimeError("This tool was not tested on PDF documents without any fonts.")

def get_font_codecs(fonts_dict) -> Dict[str, FontCodec]:
    font_codecs = {}
    for font_id in fonts_dict:
        font_dict = cast(DictionaryObject, fonts_dict[font_id].get_object())
        font_codecs[font_id] = FontCodec.from_font(Font.from_font_resource(font_dict))
    return font_codecs