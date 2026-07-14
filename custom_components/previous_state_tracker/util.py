"""Small helpers shared across previous_state_tracker's config flow, sensor, and diagnostics."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry


def merged_config(entry: ConfigEntry) -> dict[str, Any]:
    """Options override data, the same precedence used everywhere a
    tracker's effective settings are read."""
    return {**entry.data, **entry.options}


def humanize_entity_id(entity_id: str) -> str:
    """Fallback display name when neither the entity registry nor its
    current state has one: "sensor.front_door_battery" -> "Front Door
    Battery"."""
    return entity_id.split(".", 1)[-1].replace("_", " ").title()
