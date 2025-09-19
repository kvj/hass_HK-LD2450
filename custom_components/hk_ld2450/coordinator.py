from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from homeassistant.config_entries import (
    SIGNAL_CONFIG_ENTRY_CHANGED,
    ConfigEntryChange,
    ConfigEntryState,
    ConfigEntry
)

from homeassistant.helpers import (
    dispatcher,
    event,
    template,
    device_registry,
)

from homeassistant.core import (
    callback,
    HomeAssistant,
)
# from homeassistant.components import camera, image, light
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
)


from .constants import *
from .mdi_font import GlyphProvider

import collections.abc
import logging
import json, copy
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

class Coordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            setup_method=self._async_setup,
            update_method=self._async_update,
        )
        self._entry = entry
        self._entry_id = entry.entry_id
        self._subentries = {}
        self._subentries_map = {}

        self._on_config_entry_handler = None
        self._on_device_updated_handler = None
        self._entry_data = None
        self._on_event_handler = None

    async def _async_setup(self):
        self._mdi_font = GlyphProvider()
        self._mdi_font.init()

    async def _async_update(self):
        return {
            "connected": False,
            "targets": [],
        }

    async def _async_update_state(self, data: dict):
        _LOGGER.debug(f"_async_update_state: {data}, {self.data}")
        new_state = {
            **self.data,
            **data,
        }
        if json.dumps(new_state) != json.dumps(self.data):
            new_state["ts"] = datetime.now().timestamp()
        self.async_set_updated_data(new_state)

    def call_device_service(self, name: str, data: dict) -> bool:
        if not self.is_device_connected():
            _LOGGER.warning(f"call_device_service: not connected")
            return False
        for _, service in self._entry_data.services.items():
            if service.name == name:
                _LOGGER.debug(f"call_device_service: call service {name} with {data}, spec: {service}")
                self._entry_data.client.execute_service(service, data)
                return True
        _LOGGER.warning(f"call_device_service: service not found: {name}")
        return False
    
    def _dimension_to_mm(self, value: float) -> int:
        return int(value * 10)
    
    def _platform_config(self):
        return self.hass.data[DOMAIN]

    async def async_send_configuration(self):
        self.call_device_service("set_layout", {
            "x": self._dimension_to_mm(self._config.get(CONF_X, 0)),
            "y": self._dimension_to_mm(self._config.get(CONF_Y, 0)),
            "w": self._dimension_to_mm(self._config.get(CONF_W, 0)),
            "h": self._dimension_to_mm(self._config.get(CONF_H, 0)),
            "a": int(self._config.get(CONF_ANGLE, 0)),
        })
        for index, id in self._subentries_map.items():
            conf = self._subentries[id]
            self.call_device_service("add_zone", {
                "x": self._dimension_to_mm(conf.get(CONF_X, 0)),
                "y": self._dimension_to_mm(conf.get(CONF_Y, 0)),
                "w": self._dimension_to_mm(conf.get(CONF_W, 0)),
                "h": self._dimension_to_mm(conf.get(CONF_H, 0)),
                "f": 0,
                "id": index,
            })
    
    async def async_handle_event(self, type_: str, event: dict):
        _LOGGER.debug(f"async_handle_event: event = {event}")
        targets = int(event.get("t", 1))
        targets_ = []
        for i in range(targets):
            zone = int(event.get(f"z_{i}", -1))
            x = int(event.get(f"x_{i}", 0))
            y = int(event.get(f"y_{i}", 0))
            sp = int(event.get(f"sp_{i}", 0))
            targets_.append((zone, x, y, sp))
        await self._async_process_targets(targets_)

    def _connect_to_esphome_device(self, entry_data):
        def _on_device_update():
            _LOGGER.debug(f"_on_device_update: {entry_data.available}")
            if entry_data.available:
                self.hass.async_create_task(self.async_send_configuration())
            self.hass.async_create_task(self._async_update_state({"connected": self.is_device_connected()}))            

        self._on_device_updated_handler = entry_data.async_subscribe_device_updated(_on_device_update)
        self._entry_data = entry_data
        _LOGGER.debug(f"_connect_to_esphome_device: {entry_data.available}")
        if entry_data.available:
            _on_device_update()

    def _disconnect_from_esphome(self):
        if self._entry_data:
            _LOGGER.debug(f"_disconnect_from_esphome: {self._on_device_updated_handler}")
            self._on_device_updated_handler = self._disable_listener(self._on_device_updated_handler)
        self._entry_data = None

    def subentry_config(self, id: str) -> dict:
        return self._subentries.get(id, {})

    def load_options(self):
        self._config = {
            **self._entry.as_dict()["options"],
            "title": self._entry.title,
        }
        self._subentries = {}
        self._subentries_map = {}
        index = 1
        for id, entry in self._entry.subentries.items():
            self._subentries[id] = {
                **entry.as_dict()["data"],
                "title": entry.title,
                "type": entry.subentry_type,
                "index": index,
            }
            self._subentries_map[index] = id
            index += 1
        self._targets = []
        for i in range(3):
            self._targets.append((-1, 0, 0, 0, None))

    async def _async_process_targets(self, targets):
        changed = False
        for i in range(len(targets)):
            t = targets[i]
            p = self._targets[i]
            if t[0] != -1:
                # Real coordinates
                if p[1] != t[1] or p[2] != t[2] or t[3] != p[3]:
                    # Target moved
                    self._targets[i] = (t[0], t[1], t[2], t[3], datetime.now())
                    changed = True
                    continue
            # No change in coordinates
            if p[0] != -1:
                # Something was there
                fade = self._config.get(CONF_OCCUPANCY_FADE) if p[0] == 0 else self._subentries[self._subentries_map[p[0]]][CONF_OCCUPANCY_FADE]
                if datetime.now() - p[4] > timedelta(seconds=fade):
                    # Faded
                    self._targets[i] = (-1, 0, 0, 0, None)
                    changed = True
        if changed:
            state = []
            for t in self._targets:
                if t[0] != -1:
                    state.append((t[0], t[1], t[2], t[3]))
            await self._async_update_state({
                "targets": state
            })


    def _config_entry_by_device_id(self, device_id: str):
        if device := device_registry.async_get(self.hass).async_get(device_id):
            _LOGGER.debug(f"_config_entry_by_device_id: device = {device}")
            for entry_id in device.config_entries:
                if entry := self.hass.config_entries.async_get_entry(entry_id):
                    _LOGGER.debug(f"_config_entry_by_device_id: entry: {entry}")
                    if entry.domain == "esphome":
                        return entry
        return None
    
    async def _async_on_device_event(self, event):
        type_ = event.data.get("type")
        await self.async_handle_event(type_, event.data)

    def is_device_connected(self) -> bool:
        return True if self._entry_data and self._entry_data.available else False

    @callback
    def _device_event_filter(self, event_data) -> bool:
        return self.is_device_connected() and event_data.get("device_id") == self._config[CONF_DEVICE_ID]

    async def async_load(self):
        self.load_options()
        conf_entry = self._config_entry_by_device_id(self._config[CONF_DEVICE_ID])
        _LOGGER.debug(f"async_load: {self._config}, {self._subentries}, {conf_entry}")
        if not conf_entry:
            return
        
        self._on_event_handler = self.hass.bus.async_listen("esphome.hkld2450_data", self._async_on_device_event, self._device_event_filter)

        def _on_config_entry(state, entry):
            if entry == conf_entry:
                _LOGGER.debug(f"_on_config_entry: {state}, {entry}")
                if entry.state == ConfigEntryState.LOADED:
                    self._connect_to_esphome_device(entry.runtime_data)
                if entry.state == ConfigEntryState.NOT_LOADED:
                    self._disconnect_from_esphome()
        self._on_config_entry_handler = dispatcher.async_dispatcher_connect(self.hass, SIGNAL_CONFIG_ENTRY_CHANGED, _on_config_entry)
        if conf_entry.state == ConfigEntryState.LOADED:
            _on_config_entry(ConfigEntryChange.UPDATED, conf_entry)
        

    async def async_unload(self):
        _LOGGER.debug(f"async_unload:")
        self._on_config_entry_handler = self._disable_listener(self._on_config_entry_handler)
        self._on_event_handler = self._disable_listener(self._on_event_handler)
        self._disconnect_from_esphome()

    def _disable_listener(self, listener):
        if listener:
            listener()
        return None
    
    def create_zone_sensor(self, sensor_cls, add_entities):
        for id in self._subentries:
            add_entities([sensor_cls(self, id)], config_subentry_id=id)

class BaseEntity(CoordinatorEntity):

    def __init__(self, coordinator: Coordinator):
        super().__init__(coordinator)

    def with_name(self, suffix: str, name: str):
        self._attr_has_entity_name = True
        entry_id = self.coordinator._entry_id
        self._attr_unique_id = f"_{entry_id}_{suffix}"
        self._attr_name = name
        return self

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("config_entry", self.coordinator._entry_id)
            },
            "name": self.coordinator._config["title"],
        }

    @property
    def available(self):
        return self.coordinator.is_device_connected()

class BaseSubEntity(CoordinatorEntity):

    def __init__(self, coordinator: Coordinator, subentry_id: str):
        super().__init__(coordinator)
        self._subentry_id = subentry_id

    def with_name(self, suffix: str, name: str):
        self._attr_has_entity_name = True
        entry_id = self._subentry_id
        self._attr_unique_id = f"_{entry_id}_{suffix}"
        self._attr_name = name
        return self
    
    @property
    def config(self):
        return self.coordinator.subentry_config(self._subentry_id)
    
    @property
    def device_info(self):
        return {
            "identifiers": {
                ("config_entry", self._subentry_id)
            },
            "name": self.config["title"],
        }

    @property
    def available(self):
        return self.coordinator.is_device_connected()
