import json, pathlib, logging
from PIL import ImageFont, ImageDraw
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

def locate_dir():
    return __path__[0]

class GlyphProvider:

    def __init__(self) -> None:
        self._font_cache = {}

    def init(self):
        self._glyph_map = self._load_meta_json()

    def _load_meta_json(self) -> dict:
        path = pathlib.Path(locate_dir()).joinpath("meta.json")
        data = json.loads(path.read_text())
        result = {}
        aliases = {}
        for item in data:
            codepoint = chr(int(item["codepoint"], 16))
            result[item["name"]] = codepoint
            for a in item.get("aliases", []):
                aliases[a] = codepoint
        for a, codepoint in aliases.items():
            if a not in result:
                result[a] = codepoint
        return result
    
    def _load_ttf_font(self, size: int):
        if size not in self._font_cache:
            path = pathlib.Path(locate_dir()).joinpath("mdi-webfont.ttf")
            ttf_font = ImageFont.truetype(path, size)
            self._font_cache[size] = ttf_font
        return self._font_cache[size]
    
    def draw_icon(self, draw: ImageDraw.ImageDraw, icon: str, size: int, x: int, y: int, color: tuple) -> bool:
        if not icon:
            return False
        glyph = self._glyph_map.get(icon[4:])
        if not glyph:
            return False
        font = self._load_ttf_font(size)
        draw.text((x, y), glyph, font=font, anchor="mm", fill=color)
        return True
