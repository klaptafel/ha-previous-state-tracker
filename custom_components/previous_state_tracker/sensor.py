from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import re

class PreviousStateSensor(SensorEntity):
    def __init__(self, hass, entity_id):
        self._hass = hass
        self._entity_id = entity_id
        self._entity_domain, self._entity_object_id = entity_id.split(".", 1)
        self._attr_name = "Previous State"
        self._attr_unique_id = f"{entity_id}_previous_state"
        self._attr_icon = "mdi:history"
        self._state = None
        self._device_info = None

    async def async_added_to_hass(self):
        registry = async_get_entity_registry(self._hass)
        original_entry = registry.async_get(self._entity_id)

        if original_entry and original_entry.device_id:
            self._device_info = DeviceInfo(identifiers={("homeassistant", original_entry.device_id)})

        # Haal device_class, unit_of_measurement en state_class op van originele entiteit
        orig_entity = self._hass.states.get(self._entity_id)
        if orig_entity:
            attrs = orig_entity.attributes
            self._attr_device_class = attrs.get("device_class")
            self._attr_unit_of_measurement = attrs.get("unit_of_measurement")
            self._attr_state_class = attrs.get("state_class")

        @callback
        def state_change_listener(event):
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            if (
                old_state
                and old_state.state not in ("unknown", "unavailable")
                and new_state
                and new_state.state not in ("unknown", "unavailable")
            ):
                self._state = old_state.state
                self.async_write_ha_state()

        async_track_state_change_event(self._hass, [self._entity_id], state_change_listener)

    @property
    def state(self):
        return self._state

    @property
    def device_info(self):
        return self._device_info


async def async_setup_entry(hass, entry, async_add_entities):
    entities = entry.data.get("entities")
    if not entities:
        return
    sensors = [PreviousStateSensor(hass, entity_id) for entity_id in entities]
    async_add_entities(sensors)
