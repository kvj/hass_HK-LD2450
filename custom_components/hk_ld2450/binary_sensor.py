from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass
)

import logging

from .coordinator import Coordinator, BaseEntity, BaseSubEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, add_entities):
    coordinator = entry.runtime_data
    add_entities([_RoomOccupancy(coordinator), _RoomMotion(coordinator)])
    coordinator.create_zone_sensor(_ZoneOccupancy, add_entities)
    coordinator.create_zone_sensor(_ZoneMotion, add_entities)
    return True


class _RoomOccupancy(BaseEntity, BinarySensorEntity):

    def __init__(self, coordinator: Coordinator):
        super().__init__(coordinator)
        self.with_name("occupancy", "Occupancy")
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self):
        return len(self.coordinator.data["targets"]) > 0

class _RoomMotion(BaseEntity, BinarySensorEntity):

    def __init__(self, coordinator: Coordinator):
        super().__init__(coordinator)
        self.with_name("motion", "Motion")
        self._attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def is_on(self):
        zones = 0
        for t in self.coordinator.data["targets"]:
            if t[3] != 0:
                zones += 1
        return zones > 0

class _ZoneOccupancy(BaseSubEntity, BinarySensorEntity):

    def __init__(self, coordinator: Coordinator, subentry_id: str):
        super().__init__(coordinator, subentry_id)
        self.with_name("occupancy", "Occupancy")
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self):
        zones = 0
        for t in self.coordinator.data["targets"]:
            if t[0] == self.config["index"]:
                zones += 1
        return zones > 0

class _ZoneMotion(BaseSubEntity, BinarySensorEntity):

    def __init__(self, coordinator: Coordinator, subentry_id: str):
        super().__init__(coordinator, subentry_id)
        self.with_name("motion", "Motion")
        self._attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def is_on(self):
        zones = 0
        for t in self.coordinator.data["targets"]:
            if t[0] == self.config["index"] and t[3] != 0:
                zones += 1
        return zones > 0
