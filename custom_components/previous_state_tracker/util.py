"""Small helpers shared across previous_state_tracker's config flow, sensor, and diagnostics.

Kept free of a runtime `homeassistant` import (the ConfigEntry reference
below is TYPE_CHECKING-only) so this whole module -- including
IgnoredStates -- can be unit tested with plain pytest, without needing
pytest-homeassistant-custom-component installed.
"""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_NON_NUMERIC_DEVICE_CLASSES = {"date", "enum", "timestamp", "uptime"}


def merged_config(entry: "ConfigEntry") -> dict[str, Any]:
    """Options override data, the same precedence used everywhere a
    tracker's effective settings are read."""
    return {**entry.data, **entry.options}


def humanize_entity_id(entity_id: str) -> str:
    """Fallback display name when neither the entity registry nor its
    current state has one: "sensor.front_door_battery" -> "Front Door
    Battery"."""
    return entity_id.split(".", 1)[-1].replace("_", " ").title()


def _compile_wildcard(pattern: str) -> re.Pattern[str]:
    """Turn a pattern where only '*' is special (matches any run of
    characters, including none) into a regex. Every other character is
    matched literally -- unlike fnmatch, '?' and '[...]' are NOT given
    special meaning, since a real state value could plausibly contain
    those literally (e.g. "50% [charging]") and silently misbehave."""
    segments = pattern.split("*")
    escaped = ".*".join(re.escape(segment) for segment in segments)
    return re.compile(f"^{escaped}$", re.DOTALL)


class IgnoredStates:
    """Matches a state value against a set of ignored values, case
    insensitively. An entry containing '*' is treated as a wildcard
    (see _compile_wildcard); everything else is an exact match.

    Splitting the two apart once at construction time keeps the common
    case (no wildcards configured) a plain O(1) set lookup -- the
    wildcard list is only ever consulted as a fallback, and is empty for
    most trackers.
    """

    def __init__(self, values: Iterable[str]) -> None:
        exact: set[str] = set()
        patterns: list[re.Pattern[str]] = []
        for value in values:
            lowered = value.lower()
            if "*" in lowered:
                patterns.append(_compile_wildcard(lowered))
            else:
                exact.add(lowered)
        self._exact = exact
        self._patterns = patterns

    def __bool__(self) -> bool:
        return bool(self._exact) or bool(self._patterns)

    def matches(self, value: str) -> bool:
        lowered = value.lower()
        if lowered in self._exact:
            return True
        return any(pattern.match(lowered) for pattern in self._patterns)


def sanitize_copied_metadata(
    device_class: str | None,
    unit_of_measurement: str | None,
    state_class: str | None,
    value: Any,
) -> tuple[str | None, str | None, str | None]:
    """Decide which of the device_class/unit/state_class copied from a
    tracked entity survive, given the value about to be written as the
    previous-state sensor's own state. SensorEntity raises ValueError (and
    the write is lost) when they disagree with the value, e.g. a leftover
    unit on a non-numeric device class, or a unit/state_class implying a
    numeric value that the previous state can't satisfy (including a
    non-finite float, which HA rejects just like a non-numeric one).

    For "date", "timestamp", and "uptime", the value must already be
    parsed into a date/datetime by the caller (None if parsing failed) --
    this module stays free of a homeassistant import so it can run under
    plain pytest.
    """
    if device_class in _NON_NUMERIC_DEVICE_CLASSES:
        if device_class == "enum":
            # ENUM needs an options list this sensor never sets.
            return None, None, None
        if value is None:
            return None, None, None
        return device_class, None, None

    if value is None or not (device_class or unit_of_measurement or state_class):
        return device_class, unit_of_measurement, state_class
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = None
    if numeric_value is None or not math.isfinite(numeric_value):
        return None, None, None
    return device_class, unit_of_measurement, state_class
