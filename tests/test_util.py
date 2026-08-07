"""Tests for util.py's pure helpers (merged_config/humanize_entity_id/IgnoredStates).

Loaded directly from its file path via importlib, bypassing
custom_components/previous_state_tracker/__init__.py (which imports
homeassistant at module level -- unavailable in this environment). util.py
itself keeps its one homeassistant reference (ConfigEntry) TYPE_CHECKING-only
specifically so this works, sidestepping a local
pytest-homeassistant-custom-component install constraint;
this covers the pure logic only, not entity/config-flow behavior.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_UTIL_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components" / "previous_state_tracker" / "util.py"
)
_spec = importlib.util.spec_from_file_location("previous_state_tracker_util", _UTIL_PATH)
util = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(util)


class TestHumanizeEntityId:
    def test_basic(self):
        assert util.humanize_entity_id("sensor.front_door_battery") == "Front Door Battery"

    def test_no_domain_separator(self):
        assert util.humanize_entity_id("weirdvalue") == "Weirdvalue"


class TestMergedConfig:
    def test_options_override_data(self):
        class FakeEntry:
            data = {"a": 1, "b": 2}
            options = {"b": 3}

        assert util.merged_config(FakeEntry()) == {"a": 1, "b": 3}


class TestIgnoredStatesExactMatch:
    def test_empty_is_falsy(self):
        assert not util.IgnoredStates([])

    def test_nonempty_is_truthy(self):
        assert util.IgnoredStates(["unknown"])

    def test_exact_match_case_insensitive(self):
        matcher = util.IgnoredStates(["Unknown", "UNAVAILABLE"])
        assert matcher.matches("unknown")
        assert matcher.matches("Unknown")
        assert matcher.matches("unavailable")
        assert not matcher.matches("on")

    def test_no_accidental_substring_match(self):
        matcher = util.IgnoredStates(["on"])
        assert not matcher.matches("online")
        assert not matcher.matches("front_on")


class TestIgnoredStatesWildcard:
    def test_prefix_wildcard(self):
        matcher = util.IgnoredStates(["Error: *"])
        assert matcher.matches("Error: dustbin full")
        assert matcher.matches("error: dustbin full")
        assert not matcher.matches("Cleared: dustbin full")

    def test_wildcard_matches_empty_remainder(self):
        # '*' matches "any run of characters, including none".
        matcher = util.IgnoredStates(["Error: *"])
        assert matcher.matches("Error: ")

    def test_suffix_wildcard(self):
        matcher = util.IgnoredStates(["* dustbin full"])
        assert matcher.matches("error: dustbin full")
        assert not matcher.matches("error: stuck")

    def test_multiple_wildcards_in_one_pattern(self):
        matcher = util.IgnoredStates(["Error: * (code *)"])
        assert matcher.matches("Error: dustbin full (code 12)")
        assert not matcher.matches("Error: dustbin full")

    def test_wildcard_treats_question_mark_and_brackets_literally(self):
        # Only '*' is special here -- unlike Python's fnmatch, '?' and
        # '[...]' must NOT get glob meaning, since a real state value could
        # plausibly contain them literally (e.g. "50% [charging]").
        matcher = util.IgnoredStates(["50% [charging]*"])
        assert matcher.matches("50% [charging] soon")
        assert not matcher.matches("50% xcharging soon")

    def test_mix_of_exact_and_wildcard_entries(self):
        matcher = util.IgnoredStates(["unknown", "unavailable", "Error: *"])
        assert matcher.matches("unknown")
        assert matcher.matches("Error: anything")
        assert not matcher.matches("on")
