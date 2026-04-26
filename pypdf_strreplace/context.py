from pypdf.generic import DictionaryObject, NameObject, NumberObject, ArrayObject
from typing import Dict, cast
from .codec import FontCodec, WinAnsiFontCodec
from pypdf._font import Font
from pypdf.constants import PageAttributes, Resources

class Context:
    def __init__(self, font_codecs:Dict[str,FontCodec], fonts_dict, font_repository):
        self.font_key = None
        self.font_size = None
        self.font_codecs = font_codecs
        self.fonts_dict = fonts_dict
        self.font_repository = font_repository
    def get_font_codec(self) -> FontCodec:
        return self.font_codecs[self.font_key]
    def clone_shared_font_codecs(self):
        obj = type(self)(self.font_codecs, self.fonts_dict, self.font_repository)
        obj.font_key = self.font_key
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
        font_key = NameObject(prefix+str(max_font_number+1))
        font_dict = DictionaryObject()
        font_dict[NameObject("/Type")] = NameObject("/Font")
        font_dict[NameObject("/Subtype")] = NameObject("/TrueType")
        font_dict[NameObject("/BaseFont")] = NameObject(font_name)
        font_dict[NameObject('/Encoding')] = NameObject('/WinAnsiEncoding')
        widths = None
        if (self.font_repository):
            widths = self.font_repository.get_widths(postscript_name)
        if (widths):
            font_dict[NameObject('/Widths')] = ArrayObject([NumberObject(width) for width in widths])
            # these describe the range of the Widths array in respect to the entire WinAnsiEncoding
            font_dict[NameObject('/FirstChar')] = NumberObject(0)
            font_dict[NameObject('/LastChar')] = NumberObject(255)
        else:
            print(f"WARNING: Font „{postscript_name}“ has not been loaded. Horizontal spacing is likely to be inaccurate.")
        self.fonts_dict[font_key] = font_dict
        self.font_codecs[font_key] = WinAnsiFontCodec(None)
        print(f"WARNING: Font „{postscript_name}“ must be available to the renderer for truthful presentation.")
        return (font_key, self.font_size)

def get_fonts_dict(page) -> DictionaryObject:
    object_with_resources = page
    while NameObject(PageAttributes.RESOURCES) not in object_with_resources:
        # /Resources can be inherited so we look to parents
        object_with_resources = object_with_resources[PageAttributes.PARENT].get_object()
    resources_dict = cast(DictionaryObject, object_with_resources[PageAttributes.RESOURCES])
    if Resources.FONT in resources_dict:
        return cast(DictionaryObject, resources_dict[Resources.FONT])
    raise RuntimeError("This tool was not tested on PDF documents without any fonts.")

def get_font_codecs(fonts_dict) -> Dict[str, FontCodec]:
    font_codecs = {}
    for font_id in fonts_dict:
        font_dict = cast(DictionaryObject, fonts_dict[font_id].get_object())
        font_codecs[font_id] = FontCodec.from_font(Font.from_font_resource(font_dict))
    return font_codecs