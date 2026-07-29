from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import async_entity_id_to_device_id
from homeassistant.helpers.helper_integration import async_remove_helper_devices

from .const import CONF_ENTITY_ID, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry.

    Same one-time cleanup HA core's own threshold/derivative run for HA
    2026.8's single-config-entry-per-device model (confirmed against their
    real source, home-assistant/core): before this version, sensor.py merged
    onto the tracked entity's own device by reusing its identifiers, which
    made this entry's own device a co-owner. async_remove_helper_devices is
    the first-party migration for exactly that -- it finds the resulting
    duplicate/split device (however HA 2026.8 itself already reshaped it, if
    the user upgraded before this fix ever ran) and relinks this entry's own
    entities back onto the real, single tracked-entity device."""
    _LOGGER.debug("Migrating from version %s.%s", entry.version, entry.minor_version)

    if entry.version == 1:
        if entry.minor_version < 2:
            entity_id = entry.data.get(CONF_ENTITY_ID)
            if entity_id and (source_device_id := async_entity_id_to_device_id(hass, entity_id)):
                async_remove_helper_devices(
                    hass,
                    helper_config_entry_id=entry.entry_id,
                    source_device_id=source_device_id,
                )
        hass.config_entries.async_update_entry(entry, minor_version=2)

    _LOGGER.debug(
        "Migration to version %s.%s successful", entry.version, entry.minor_version
    )
    return True
