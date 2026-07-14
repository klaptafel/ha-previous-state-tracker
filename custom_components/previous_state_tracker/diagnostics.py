"""Diagnostics support for Previous State Tracker."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENTITY_ID,
    CONF_IGNORE_UNAVAILABLE,
    CONF_IGNORE_UNKNOWN,
    CONF_IGNORE_EXTRA_STATES,
    DEFAULT_IGNORE_UNAVAILABLE,
    DEFAULT_IGNORE_UNKNOWN,
)
from .util import merged_config


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Nothing here needs redaction -- the config is just an entity reference,
    two booleans, and a user-typed list of state names to ignore, and the
    tracked entity's state is already exactly as visible to the user as the
    sensor itself.
    """
    config = merged_config(entry)
    tracked_entity_id = config[CONF_ENTITY_ID]
    tracked_state = hass.states.get(tracked_entity_id)

    return {
        "entry_data": dict(entry.data),
        "entry_options": dict(entry.options),
        "config": {
            CONF_ENTITY_ID: tracked_entity_id,
            CONF_IGNORE_UNKNOWN: config.get(CONF_IGNORE_UNKNOWN, DEFAULT_IGNORE_UNKNOWN),
            CONF_IGNORE_UNAVAILABLE: config.get(CONF_IGNORE_UNAVAILABLE, DEFAULT_IGNORE_UNAVAILABLE),
            CONF_IGNORE_EXTRA_STATES: config.get(CONF_IGNORE_EXTRA_STATES, []),
        },
        "tracked_entity_found": tracked_state is not None,
        "tracked_entity_state": tracked_state.state if tracked_state else None,
    }
