from __future__ import annotations
from typing import Set, Tuple

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, EntityCategory # <-- NIEUWE IMPORT
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, EventStateChangedData
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import EventType

from .const import (
    DOMAIN,
    CONF_ENTITY_ID,
    CONF_IGNORE_UNKNOWN,
    CONF_IGNORE_UNAVAILABLE,
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**config_entry.data, **config_entry.options}
    
    entity_id = config[CONF_ENTITY_ID]
    name = config["name"]
    ignore_unknown = config.get(CONF_IGNORE_UNKNOWN, True)
    ignore_unavailable = config.get(CONF_IGNORE_UNAVAILABLE, True)
    device_id = config.get("device_id")

    device_identifiers: Set[Tuple[str, str]] | None = None
    if device_id:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device:
            device_identifiers = device.identifiers

    sensor = PreviousStateSensor(
        hass=hass,
        entity_id=entity_id,
        name=name,
        ignore_unknown=ignore_unknown,
        ignore_unavailable=ignore_unavailable,
        unique_id=config_entry.entry_id,
        device_identifiers=device_identifiers
    )
    async_add_entities([sensor])


class PreviousStateSensor(SensorEntity, RestoreEntity):
    _attr_should_poll = False
    _attr_icon = "mdi:history"
    _attr_translation_key = "previous_state"
    _attr_entity_category = EntityCategory.DIAGNOSTIC # <-- TOEGEVOEGDE REGEL

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        name: str,
        ignore_unknown: bool,
        ignore_unavailable: bool,
        unique_id: str,
        device_identifiers: Set[Tuple[str, str]] | None
    ) -> None:
        self.hass = hass
        self._tracked_entity_id = entity_id
        self._ignore_unknown = ignore_unknown
        self._ignore_unavailable = ignore_unavailable
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_native_value = None
        self._attr_extra_state_attributes = {
            "tracked_entity_id": entity_id,
            "last_changed": None,
        }

        if device_identifiers:
            self._attr_device_info = DeviceInfo(
                identifiers=device_identifiers
            )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        
        last_state = await self.async_get_last_state()
        if last_state:
            self._attr_native_value = last_state.state
            if "last_changed" in last_state.attributes:
                self._attr_extra_state_attributes["last_changed"] = last_state.attributes["last_changed"]

        self._attr_available = self.hass.states.get(self._tracked_entity_id) is not None

        @callback
        def state_change_listener(
            event: EventType[EventStateChangedData],
        ) -> None:
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")

            self._attr_available = new_state is not None
            
            if old_state is None:
                self.async_write_ha_state()
                return

            if self._ignore_unknown and old_state.state == "unknown":
                return
            if self._ignore_unavailable and old_state.state == "unavailable":
                return

            self._attr_native_value = old_state.state
            self._attr_extra_state_attributes["last_changed"] = event.time_fired.isoformat()
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._tracked_entity_id], state_change_listener
            )
        )
