from __future__ import annotations
from .constants import *
from .coordinator import Coordinator

from homeassistant.core import (
    HomeAssistant,
    SupportsResponse,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers import service, reload
from homeassistant.const import SERVICE_RELOAD


import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_ROUND_SIZE): cv.positive_int,
        vol.Optional(CONF_BORDER_SIZE): cv.positive_int,
        vol.Optional(CONF_OPACITY): cv.small_float,
        vol.Optional(CONF_ROOM_SIZE): cv.positive_int,
        vol.Optional(CONF_ROOM_COLOR): cv.color_hex,
        vol.Optional(CONF_ZONE_COLOR): cv.color_hex,
        vol.Optional(CONF_ICON_SIZE): cv.positive_int,
        vol.Optional(CONF_ICON_COLOR): cv.color_hex,
        vol.Optional(CONF_SENSOR_SIZE): cv.positive_int,
        vol.Optional(CONF_SENSOR_COLOR): cv.color_hex,
        vol.Optional(CONF_PERSON_SIZE): cv.positive_int,
        vol.Optional(CONF_PERSON_ACTIVE_SIZE): cv.positive_int,
        vol.Optional(CONF_PERSON_COLOR): cv.color_hex,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

async def _async_update_entry(hass, entry: ConfigEntry):
    _LOGGER.debug(f"_async_update_entry: {entry}, {entry.subentries}")
    coordinator = entry.runtime_data
    entry.subentries
    await coordinator.async_unload()
    await coordinator.async_load()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    _LOGGER.debug(f"async_setup_entry: {entry}, {entry.subentries}")
    entry.runtime_data = Coordinator(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_update_entry))
    await entry.runtime_data.async_config_entry_first_refresh()
    await entry.runtime_data.async_load()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await entry.runtime_data.async_unload()
    entry.runtime_data = None
    return True

# def _register_service(hass: HomeAssistant,  name: str, handler, resp: SupportsResponse = SupportsResponse.NONE):
#     async def handler_(call):
#         await handler(_manager(hass), call.data)
#     hass.services.async_register(DOMAIN, name, handler_, supports_response=resp)
# 
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    conf = config.get(DOMAIN, {})
    _LOGGER.debug(f"async_setup: {conf}")
    hass.data[DOMAIN] = conf
    async def _async_reload_yaml(call):
        config = await reload.async_integration_yaml_config(hass, DOMAIN)
        conf = config.get(DOMAIN, {})
        _LOGGER.debug(f"_async_reload_yaml: {conf}")
        hass.data[DOMAIN] = conf
    service.async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, _async_reload_yaml)
    return True
