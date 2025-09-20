from collections.abc import Mapping
from typing import Any, cast

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import selector

from homeassistant.const import (
    CONF_NAME,
    CONF_ICON,
    CONF_DEVICE_ID,
)

from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowError,
)

from .constants import *

import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)

async def _create_config_schema(user_input: dict):
    return vol.Schema({
        vol.Required(CONF_NAME, default=user_input.get(CONF_NAME)): selector({"text": {}}),
    }).extend((await _create_options_schema(user_input)).schema)

SIZE_SELECTOR = {"number": {"min": 0, "max": 9999, "mode": "box"}}
FADE_SELECTOR = {"number": {"min": 0, "max": 3600, "unit_of_measurement": "seconds"}}

async def _create_options_schema(user_input: dict):
    return vol.Schema({
        vol.Required(CONF_DEVICE_ID, default=user_input.get(CONF_DEVICE_ID)): selector({"device": {"integration": "esphome"}}),        
        vol.Required(CONF_W, default=user_input.get(CONF_W, 300)): selector(SIZE_SELECTOR),
        vol.Required(CONF_H, default=user_input.get(CONF_H, 300)): selector(SIZE_SELECTOR),
        vol.Required(CONF_X, default=user_input.get(CONF_X, 0)): selector(SIZE_SELECTOR),
        vol.Required(CONF_Y, default=user_input.get(CONF_Y, 0)): selector(SIZE_SELECTOR),
        vol.Required(CONF_ANGLE, default=user_input.get(CONF_ANGLE, 0)): selector({"number": {"min": 0, "max": 360, "unit_of_measurement": "degrees"}}),
        vol.Required(CONF_OCCUPANCY_FADE, default=user_input.get(CONF_OCCUPANCY_FADE, CONF_OCCUPANCY_FADE_DEF)): selector(FADE_SELECTOR),
    })

async def _create_zone_config_schema(user_input: dict, zone_type: str):
    return vol.Schema({
        vol.Required(CONF_NAME, default=user_input.get(CONF_NAME)): selector({"text": {}}),
    }).extend((await _create_zone_options_schema(user_input, zone_type)).schema)

async def _create_zone_options_schema(user_input: dict, zone_type: str):
    return vol.Schema({
        vol.Required(CONF_ICON, default=user_input.get(CONF_ICON, CONF_ICON_DEF)): selector({"icon": {}}),
        vol.Required(CONF_ZONE_TYPE, default=user_input.get(CONF_ZONE_TYPE, CONF_ZONE_TYPE_DEF)): selector({
            "select": {"options": [{
                "value": "normal", "label": "Normal",
            }, {
                "value": "exit", "label": "Exit",
            }, {
                "value": "ignore", "label": "Ignore",
            }], "mode": "dropdown"}
        }),
        vol.Optional(CONF_ZONE_ID, default=user_input.get(CONF_ZONE_ID)): selector({"text": {}}),
        vol.Required(CONF_X, default=user_input.get(CONF_X, 0)): selector(SIZE_SELECTOR),
        vol.Required(CONF_Y, default=user_input.get(CONF_Y, 0)): selector(SIZE_SELECTOR),
        vol.Required(CONF_W, default=user_input.get(CONF_W, 300)): selector(SIZE_SELECTOR),
        vol.Required(CONF_H, default=user_input.get(CONF_H, 300)): selector(SIZE_SELECTOR),
        vol.Required(CONF_OCCUPANCY_FADE, default=user_input.get(CONF_OCCUPANCY_FADE, CONF_OCCUPANCY_FADE_DEF)): selector(FADE_SELECTOR),
    })

class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input = None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], options=user_input, data={ "type": "room" })
        return self.async_show_form(step_id="user", data_schema=await _create_config_schema({}))
    
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler()
    
    def async_get_supported_subentry_types(config_entry: config_entries.ConfigEntry):
        _LOGGER.debug(f"async_get_supported_subentry_types: {config_entry}")
        return {"zone": ZoneConfigFlowHandler}
    
class OptionsFlowHandler(config_entries.OptionsFlow):

    async def async_step_init(self, user_input = None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(step_id="init", data_schema=await _create_options_schema(self.config_entry.as_dict()["options"]))

class ZoneConfigFlowHandler(config_entries.ConfigSubentryFlow):

    async def async_step_user(self, user_input = None):
        _LOGGER.debug(f"async_step_user: {user_input}, {self._entry_id}, {self._subentry_type}")
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=await _create_zone_config_schema({}, self._subentry_type))
    
    async def async_step_reconfigure(self, user_input = None):
        _LOGGER.debug(f"async_step_reconfigure: {user_input}, {self._entry_id}, {self._subentry_type}, {self._get_reconfigure_subentry()}")
        if user_input is not None:
            return self.async_update_and_abort(self._get_entry(), self._get_reconfigure_subentry(), data=user_input)
        return self.async_show_form(step_id="reconfigure", data_schema=await _create_zone_options_schema(self._get_reconfigure_subentry().as_dict()["data"], self._subentry_type))
