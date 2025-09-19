from PIL import Image, ImageDraw, ImageColor
import io

from homeassistant.components.image import ImageEntity
from homeassistant.const import (
    CONF_ICON
)

from .coordinator import Coordinator, BaseEntity
from .constants import *

import logging, datetime


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, add_entities):
    coordinator = entry.runtime_data
    add_entities([_Entity(coordinator)])
    return True


class _Entity(BaseEntity, ImageEntity):

    def __init__(self, coordinator: Coordinator):
        super().__init__(coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        self._attr_content_type = "image/png"
        self.with_name("plan", "Plan")

    @property
    def image_last_updated(self):
        return datetime.datetime.fromtimestamp(self.coordinator.data.get("ts"))

    async def async_image(self) -> bytes | None:

        x = self.coordinator._dimension_to_mm(self.coordinator._config.get(CONF_X, 0))
        y = self.coordinator._dimension_to_mm(self.coordinator._config.get(CONF_Y, 0))
        w = self.coordinator._dimension_to_mm(self.coordinator._config.get(CONF_W, 0))
        h = self.coordinator._dimension_to_mm(self.coordinator._config.get(CONF_H, 0))
        a = self.coordinator._config.get(CONF_ANGLE, 0)

        im_size = self.coordinator._platform_config().get(CONF_ROOM_SIZE, CONF_ROOM_SIZE_DEF)
        r_size = self.coordinator._platform_config().get(CONF_ROUND_SIZE, CONF_ROUND_SIZE_DEF)
        b_size = self.coordinator._platform_config().get(CONF_BORDER_SIZE, CONF_BORDER_SIZE_DEF)
        opa = self.coordinator._platform_config().get(CONF_OPACITY, CONF_OPACITY_DEF)

        def opa_color(color: tuple) -> tuple:
            return tuple(color + (int(255.0 * opa),))

        p_size = self.coordinator._platform_config().get(CONF_PERSON_SIZE, CONF_PERSON_SIZE_DEF)
        pa_size = self.coordinator._platform_config().get(CONF_PERSON_ACTIVE_SIZE, CONF_PERSON_ACTIVE_SIZE_DEF)

        wh = max(w, h)
        scale = float(im_size - 2 * pa_size) / float(wh)

        im_size = (int(scale * w + 2 * pa_size), int(scale * h + 2 * pa_size))
        base_img = Image.new("RGBA", im_size, (0, 0, 0, 0))
        draw_img = Image.new("RGBA", im_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(draw_img)

        room_col = ImageColor.getrgb(self.coordinator._platform_config().get(CONF_ROOM_COLOR, CONF_ROOM_COLOR_DEF))        
        draw.rounded_rectangle((
            int(pa_size), 
            int(pa_size), 
            int(pa_size + w * scale), 
            int(pa_size + h * scale),
        ), r_size, room_col)

        sensor_col = ImageColor.getrgb(self.coordinator._platform_config().get(CONF_SENSOR_COLOR, CONF_SENSOR_COLOR_DEF))
        s_size = self.coordinator._platform_config().get(CONF_SENSOR_SIZE, CONF_SENSOR_SIZE_DEF)
        draw.pieslice((
            int(pa_size + (x * scale) - s_size), 
            int(pa_size + ((h - y) * scale) - s_size),
            int(pa_size + (x * scale) + s_size), 
            int(pa_size + ((h - y) * scale) + s_size),
        ), 180 + a - 60, 180 + a + 60, opa_color(sensor_col), sensor_col, b_size)

        zone_col = ImageColor.getrgb(self.coordinator._platform_config().get(CONF_ZONE_COLOR, CONF_ZONE_COLOR_DEF))        
        icon_col = ImageColor.getrgb(self.coordinator._platform_config().get(CONF_ICON_COLOR, CONF_ICON_COLOR_DEF))        
        icon_size = self.coordinator._platform_config().get(CONF_ICON_SIZE, CONF_ICON_SIZE_DEF)
        for id, zone in self.coordinator._subentries.items():
            zx  = self.coordinator._dimension_to_mm(zone.get(CONF_X, 0))
            zy  = self.coordinator._dimension_to_mm(zone.get(CONF_Y, 0))
            zw  = self.coordinator._dimension_to_mm(zone.get(CONF_W, 0))
            zh  = self.coordinator._dimension_to_mm(zone.get(CONF_H, 0))
            icon = zone.get(CONF_ICON, CONF_ICON_DEF)

            draw.rounded_rectangle((
                int(pa_size + zx * scale), 
                int(pa_size + (h - zy - zh) * scale), 
                int(pa_size + (zx + zw) * scale), 
                int(pa_size + (h - zy) * scale), 
            ), r_size, zone_col, None)

            self.coordinator._mdi_font.draw_icon(
                draw, icon, icon_size, 
                int(pa_size + (zx + zw / 2) * scale),
                int(pa_size + (h - zy - zh / 2) * scale),
                icon_col,
            )

        p_col = ImageColor.getrgb(self.coordinator._platform_config().get(CONF_PERSON_COLOR, CONF_PERSON_COLOR_DEF))        
        for t in self.coordinator.data["targets"]:
            if t[0] != -1:
                r = pa_size if t[3] != 0 else p_size
                draw.circle((
                    int(pa_size + t[1] * scale),
                    int(pa_size + (h - t[2]) * scale),
                ), r, opa_color(p_col), p_col, b_size)

        img_bytes = io.BytesIO()
        Image.alpha_composite(base_img, draw_img).save(img_bytes, format="png")
        return img_bytes.getvalue()
