from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory
)

import logging

from .coordinator import Coordinator, BaseEntity, BaseSubEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, add_entities):
    coordinator = entry.runtime_data
    add_entities([_RoomTargets(coordinator)])
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
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        zones = 0
        for t in self.coordinator.data["targets"]:
            if t[0] == self.config["index"]:
                zones += 1
        return zones
