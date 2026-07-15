"""Small helpers shared across previous_state_tracker's config flow, sensor, and diagnostics.

Kept free of a runtime `homeassistant` import (the ConfigEntry reference
below is TYPE_CHECKING-only) so this whole module -- including
IgnoredStates -- can be unit tested with plain pytest, without needing
pytest-homeassistant-custom-component installed.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


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
