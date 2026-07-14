# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Versions before 1.0.5 are not retroactively documented; see git history / GitHub releases for those.

## [Unreleased]

No user-facing changes. Some internal code cleanup.

### Changed
- Duplicated logic moved into a new shared `util.py`: `merged_config()` (combining a config entry's data+options, previously repeated in `sensor.py`/`diagnostics.py`) and `humanize_entity_id()` (the fallback display-name formatting, previously repeated in `config_flow.py`/`sensor.py`).
- `config_flow.py`'s repeated "look up the device_id for an entity, or None" logic consolidated into a shared `_device_id_for()` helper.
- `config_flow.py`'s shared `_extra_states_label_to_raw` state (previously accessed via an untyped `getattr(flow, ..., {})`) now declared properly through a small `_ExtraStatesLabelMapMixin` base class.
- `sensor.py`'s disabled/removed repair-issue logic (previously two near-duplicate blocks) consolidated into one shared code path.
- `sensor.py`'s tracked-entity unit/device-class/state-class sync now always applies the current values instead of first checking whether they changed; same end result, just simpler.
- The hardcoded `True` default for `ignore_unknown`/`ignore_unavailable`, repeated across `config_flow.py`/`sensor.py`/`diagnostics.py`, replaced with shared `DEFAULT_IGNORE_UNKNOWN`/`DEFAULT_IGNORE_UNAVAILABLE` constants in `const.py`.

## [1.1.0] - 2026-07-13

Adds several requested features: change which entity a tracker follows without deleting and recreating it, a new attribute showing how long the entity spent in its previous state, and the option to ignore extra device-specific states (not just the two universal ones) with a handy suggestion picker. A repair notification now also appears if the tracked entity is removed or disabled, so it's obvious why the sensor stopped updating. Also fixes two real bugs: renaming the tracked entity used to break the tracker (it now follows renames automatically), and ignoring "unavailable"/"unknown" states only worked in one direction ([#9](https://github.com/klaptafel/ha-previous-state-tracker/issues/9)). Naming is clearer too, especially for devices with more than one trackable sensor.

### Fixed
- `manifest.json`'s `version` field was stale at `1.0.0` despite five patch releases (1.0.1–1.0.5) already being live on GitHub, corrected.
- `ignore_unknown`/`ignore_unavailable` only checked the state being transitioned *from*, not the one being transitioned *to*: meant a transition like `off → unavailable` wasn't recognized as ignorable, only the reverse direction was ([#9](https://github.com/klaptafel/ha-previous-state-tracker/issues/9)).
- The config flow's suggested default sensor name was hardcoded in Dutch ("... Vorige Status") regardless of the user's language setting; now in English ("... Previous State").
- If the tracked entity was renamed via the entity registry (same entity, new `entity_id`), the tracker kept listening to the dead old `entity_id` forever instead of following the rename; it's now followed automatically, including across multiple renames, with the config entry updated so a restart doesn't revert it.
- Two meaningless leftover Dutch debug comments removed.
- `manifest.json` was missing `recorder` under `after_dependencies`, despite the "Additional states to ignore" suggestion picker using it (best-effort, already tolerates it being absent); caught by `hassfest`.

### Added
- `diagnostics.py`: downloadable diagnostics under Settings > Devices & Services.
- `async_step_reconfigure`: change the tracked entity without deleting and recreating the helper. Uses `async_update_and_abort()` rather than `async_update_reload_and_abort()`, since the existing update listener in `__init__.py` already reloads on any entry change -- combining both would double-reload (deprecated as of HA 2026.6, an error from 2026.12). The dialog now also names which tracker you're changing (`description_placeholders`), since with more than one tracker configured the generic step text alone didn't say which one you'd opened.
- A repair issue is now raised (and self-heals) when the tracked entity is gone from the entity registry entirely, distinct from a normal transient `unavailable`. A second, dismissible issue is raised when the tracked entity is merely disabled rather than removed, since that's often a deliberate, reversible choice.
- The "Configure" (options) dialog now also names which entity the tracker is following, the same gap the reconfigure dialog above already had fixed: with more than one tracker configured, the generic step text alone didn't say which one you'd opened.
- `PARALLEL_UPDATES = 0`, logging when the tracked entity becomes (un)available, `icons.json` instead of a hardcoded icon.
- README: Removal, example automation, Troubleshooting, and Known limitations sections; clearer explanation of what the ignore options actually do.
- `dependabot.yml` for GitHub Actions updates.
- `duration_in_previous_state` attribute: how long (in seconds) the tracked entity spent in the state now recorded as its previous one, computed from the source state's own `last_changed` rather than tracked separately. Restored across restarts like the existing `last_changed` attribute.
- "Additional states to ignore" option (`ignore_extra_states`): a picker alongside the existing `ignore_unknown`/`ignore_unavailable` toggles, for skipping integration-specific intermediate states (e.g. a media player's `idle`/`standby`, an EV charger's `ready_to_charge`) that aren't the two universal HA states. Suggests the tracked entity's known/recent state values (current state + up to 30 days of recorder history, best-effort), displayed using the same translated label the entity itself shows (e.g. "Detected" for a motion sensor) via `homeassistant.helpers.translation.async_translate_state` -- the same helper backing HA's built-in `state_translated` Jinja function -- while the option's underlying stored value is always the raw `state.state` (`on`), since that's what's actually compared against. Typing a custom value works too, case-insensitively matched at two levels: at save time, anything matching a currently-suggested label (e.g. typing "detected"/"Detected"/"DETECTED") is reverse-mapped to the correct raw value; at runtime, the raw value itself is compared case-insensitively too (e.g. "On"/"on"/"ON" are all treated the same), even for values that were never suggested. Anything that doesn't match a known label or the entity's actual raw state is stored exactly as typed.

### Changed
- `actions/checkout` bumped from the outdated `v3` to `v7` in `hassfest.yaml`.
- `typing.Set`/`typing.Tuple` modernized to the builtin `set[...]`/`tuple[...]` generics.
- `brands` quality-scale reasoning updated: since HA 2026.3 the local `brand/` folder (already present here) is the current standard, not the `home-assistant/brands` submission this project already had from before: see [Brands Proxy API](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/).
- The sensor now sets `has_entity_name = True`, and its display name is computed rather than frozen at setup. When the tracked entity has a device, the sensor is merged onto that same device (via matching identifiers, unchanged from before); its name combines the tracked entity's own entity-only name (read from the entity registry, not its already device-prefixed state name) with the existing `translation_key`'s "Previous State" suffix, auto-prefixed with the device's own always-current name, e.g. tracking a device's `send_status` sensor now yields "Send Status Previous State" instead of a bare "Previous State" that couldn't tell apart which of a device's several sensors was being tracked. Without a device, the name is built from the tracked entity's *current* full name at read time, so a later rename of the tracked entity now updates the tracker's name too (previously frozen from whatever was typed at setup). The "Name" field in the config flow now only sets the config entry's title (used to identify the tracker under Settings > Devices & Services); it no longer overrides the entity's own display name directly.
- README title given an SEO-friendly subtitle ("Home Assistant helper integration"), matching the rest of this HACS collection.

### Quality Scale
- Self-assessed against Home Assistant's Integration Quality Scale: 31 done / 17 exempt / 3 todo (up from 23/17/11). Remaining gaps: no test suite at all (blocks `config-flow-test-coverage`, `test-coverage`, and makes `strict-typing` unverifiable).
