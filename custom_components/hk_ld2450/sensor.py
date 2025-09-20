from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    EntityCategory,
    STATE_ON,
    STATE_OFF,
    CONF_ICON,
)

import logging

from .coordinator import Coordinator, BaseEntity, BaseSubEntity
from .constants import *

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, add_entities):
    coordinator = entry.runtime_data
    add_entities([_RoomTargets(coordinator), _RoomZone(coordinator)])
    coordinator.create_zone_sensor(_ZoneTargets, add_entities)
    return True


class _RoomTargets(BaseEntity, SensorEntity):

    def __init__(self, coordinator: Coordinator):
        super().__init__(coordinator)
        self.with_name("targets", "Targets")
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return len(self.coordinator.data["targets"])

class _ZoneTargets(BaseSubEntity, SensorEntity):

    def __init__(self, coordinator: Coordinator, subentry_id: str):
        super().__init__(coordinator, subentry_id)
        self.with_name("targets", "Targets")
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        zones = 0
        for t in self.coordinator.data["targets"]:
            if t[0] == self.config["index"]:
                zones += 1
        return zones

class _RoomZone(BaseEntity, SensorEntity):

    def __init__(self, coordinator: Coordinator):
        super().__init__(coordinator)
        self.with_name("zone", "Zone")
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def normal_zones(self):
        return filter(lambda x: x.get(CONF_ZONE_ID) and x.get(CONF_ZONE_TYPE, CONF_ZONE_TYPE_DEF) == "normal", self.coordinator._subentries.values())

    @property
    def find_zone(self):
        counts = {}
        for zone in self.normal_zones:
            counts[zone["index"]] = 0
        no_zone = 0
        for t in self.coordinator.data["targets"]:
            if t[0] in counts:
                counts[t[0]] = counts[t[0]] + 1
            else:
                no_zone += 1
        if len(counts) > 0:
            pairs = list(sorted(counts.items(), key=lambda x: x[1], reverse=True))
            if pairs[0][1] > 0:
                return pairs[0][0] # index
        if no_zone > 0:
            return True
        return False

    @property
    def options(self):
        result = [STATE_ON, STATE_OFF]
        for zone in self.normal_zones:
            result.append(zone[CONF_ZONE_ID])
        _LOGGER.debug(f"_RoomZone::options: {result}")
        return result
    
    @property
    def native_value(self):
        zone = self.find_zone
        _LOGGER.debug(f"_RoomZone::native_value: {zone}")
        if zone is True:
            return STATE_ON
        elif zone is False:
            return STATE_OFF
        else:
            return self.coordinator.subentry_config_by_index(zone).get(CONF_ZONE_ID)
    
    @property
    def icon(self):
        zone = self.find_zone
        if zone is True:
            return "mdi:home"
        elif zone is False:
            return "mdi:home-outline"
        else:
            return self.coordinator.subentry_config_by_index(zone).get(CONF_ICON)
