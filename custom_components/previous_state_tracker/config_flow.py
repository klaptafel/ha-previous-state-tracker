import asyncio
import logging
import voluptuous as vol
from datetime import timedelta
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
    BooleanSelector,
    BooleanSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_ENTITY_ID,
    CONF_IGNORE_UNAVAILABLE,
    CONF_IGNORE_UNKNOWN,
    CONF_IGNORE_EXTRA_STATES,
)

_LOGGER = logging.getLogger(__name__)

_HISTORY_LOOKBACK = timedelta(days=30)
_MAX_SUGGESTED_STATES = 25
_SKIP_STATES = {"unknown", "unavailable", ""}


async def _async_raw_state_candidates(hass: HomeAssistant, entity_id: str) -> set[str]:
    """Collect raw state.state values seen for entity_id -- its current
    state plus, best-effort, up to _HISTORY_LOOKBACK of recorder history.
    Recorder history may be unavailable (not loaded, entity excluded from
    recording, nothing recent enough within the lookback window), in which
    case this just falls back to whatever's already in `seen`.
    """
    seen: set[str] = set()

    current = hass.states.get(entity_id)
    if current and current.state not in _SKIP_STATES:
        seen.add(current.state)

    try:
        from homeassistant.components.recorder import (
            get_instance,
            history,
            is_entity_recorded,
        )

        if not is_entity_recorded(hass, entity_id):
            return seen

        end = dt_util.utcnow()
        start = end - _HISTORY_LOOKBACK
        result = await get_instance(hass).async_add_executor_job(
            history.get_significant_states,
            hass,
            start,
            end,
            [entity_id],
            None,   # filters
            False,  # include_start_time_state
            False,  # significant_changes_only -- want every literal value seen
            False,  # minimal_response
            True,   # no_attributes -- only .state is read below, skip the fetch/deserialize
        )
        for state in result.get(entity_id, []):
            if state.state not in _SKIP_STATES:
                seen.add(state.state)
    except Exception:
        _LOGGER.debug("Couldn't look up state history for %s", entity_id, exc_info=True)

    return seen


async def _async_suggested_options(
    hass: HomeAssistant, entity_id: str, extra_raw_values: set[str] | None = None
) -> list[SelectOptionDict]:
    """Build picker options for the "Additional states to ignore" field.

    Shown label is the same translated display value the dashboard already
    shows for this entity (e.g. "Detected" for a motion binary_sensor's
    "on") -- directly recognizable, no need to know the raw value. But the
    option's stored *value* is always the untranslated state.state ("on"),
    since that's what sensor.py actually compares transitions against.
    Uses HA's own async_translate_state -- the same helper backing the
    built-in `state_translated` Jinja function -- rather than reimplementing
    state-display logic. Falls back to showing the raw value as its own
    label wherever no translation is found (also correct: no translation
    means the raw value *is* what's displayed for it already).
    """
    raw_values = await _async_raw_state_candidates(hass, entity_id)
    if extra_raw_values:
        raw_values |= extra_raw_values
    if not raw_values:
        return []

    domain = entity_id.split(".", 1)[0]
    device_class = None
    state_obj = hass.states.get(entity_id)
    if state_obj:
        device_class = state_obj.attributes.get("device_class")
    entry = er.async_get(hass).async_get(entity_id)
    platform = entry.platform if entry else None
    translation_key = entry.translation_key if entry else None

    try:
        from homeassistant.helpers.translation import (
            async_get_translations,
            async_translate_state,
        )

        language = hass.config.language
        # async_get_translations *populates* the cache; async_translate_state
        # only ever reads from it, so both of these have to complete before
        # any lookup below, or it would silently miss and fall back to the
        # raw value anyway. The two categories are independent, so fetch
        # them concurrently rather than one after the other.
        translation_fetches = [async_get_translations(hass, language, "entity_component", [domain])]
        if platform and translation_key:
            translation_fetches.append(async_get_translations(hass, language, "entity", [platform]))
        await asyncio.gather(*translation_fetches)

        options = [
            SelectOptionDict(
                value=raw,
                label=async_translate_state(
                    hass, raw, domain, platform, translation_key, device_class
                ),
            )
            for raw in raw_values
        ]
    except Exception:
        _LOGGER.debug("Couldn't translate state labels for %s", entity_id, exc_info=True)
        options = [SelectOptionDict(value=raw, label=raw) for raw in raw_values]

    options.sort(key=lambda opt: opt["label"])
    return options[:_MAX_SUGGESTED_STATES]


def _extra_states_selector(suggested_options: list[SelectOptionDict]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=suggested_options,
            custom_value=True,
            multiple=True,
            mode=SelectSelectorMode.DROPDOWN,
            sort=True,
        )
    )


def _normalize_extra_states(values: list[str], label_to_raw: dict[str, str]) -> list[str]:
    """Reverse-map typed values back to the matching raw state, if any.

    Picking a dropdown option already submits its raw value, never its
    label -- this only ever affects genuinely free-typed entries. Without
    it, someone typing the label they see displayed (e.g. "Detected", or
    the raw value itself with the wrong case, e.g. "On") instead of picking
    it from the list would silently store a value that can never match
    anything, the same trap the picker exists to avoid. Case-insensitive on
    purpose: HA's own translated labels and raw state strings both have a
    fixed, consistent case by convention, so a case difference here is
    always a typo, never a deliberately distinct value.
    """
    lowercase_map = {label.lower(): raw for label, raw in label_to_raw.items()}
    return [lowercase_map.get(value.lower(), value) for value in values]


def _stash_label_map(flow: config_entries.ConfigFlow | config_entries.OptionsFlow, suggested_options: list[SelectOptionDict]) -> None:
    """Remember the label->raw mapping shown on this render, for
    _resolve_submitted_input to read back on the next call to the same
    step (same flow instance across the render/submit round-trip) -- both
    PreviousStateTrackerConfigFlow.async_step_options and
    PreviousStateTrackerOptionsFlow.async_step_init need this identically,
    with no common base class to hang it on instead.
    """
    flow._extra_states_label_to_raw = {opt["label"]: opt["value"] for opt in suggested_options}


def _resolve_submitted_input(flow: config_entries.ConfigFlow | config_entries.OptionsFlow, user_input: dict[str, Any]) -> dict[str, Any]:
    """Reverse-map CONF_IGNORE_EXTRA_STATES in submitted input using the
    label map _stash_label_map saved for this same flow instance."""
    return {
        **user_input,
        CONF_IGNORE_EXTRA_STATES: _normalize_extra_states(
            user_input.get(CONF_IGNORE_EXTRA_STATES, []),
            getattr(flow, "_extra_states_label_to_raw", {}),
        ),
    }


class PreviousStateTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return PreviousStateTrackerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ENTITY_ID])
            self._abort_if_unique_id_configured()

            self.data[CONF_ENTITY_ID] = user_input[CONF_ENTITY_ID]
            return await self.async_step_options()

        schema = vol.Schema({
            vol.Required(CONF_ENTITY_ID): EntitySelector(EntitySelectorConfig()),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_options(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if user_input is None:
            entity_registry = er.async_get(self.hass)
            original_entity_id = self.data[CONF_ENTITY_ID]
            entity = entity_registry.async_get(original_entity_id)
            
            base_name = ""
            if entity and entity.name:
                base_name = entity.name
            else:
                state = self.hass.states.get(original_entity_id)
                if state and state.attributes.get("friendly_name"):
                    base_name = state.attributes.get("friendly_name")
                else:
                    base_name = original_entity_id.split('.')[-1].replace('_', ' ').title()

            suggested_name = f"{base_name} Previous State"
            suggested_options = await _async_suggested_options(self.hass, original_entity_id)
            _stash_label_map(self, suggested_options)

            options_schema = vol.Schema({
                vol.Required("name", default=suggested_name): TextSelector(TextSelectorConfig()),
                vol.Required(CONF_IGNORE_UNKNOWN, default=True): BooleanSelector(BooleanSelectorConfig()),
                vol.Required(CONF_IGNORE_UNAVAILABLE, default=True): BooleanSelector(BooleanSelectorConfig()),
                # Dropdown showing the entity's known/recent states using the
                # same translated labels the dashboard shows (e.g. "Detected"
                # for a motion sensor), while storing the underlying raw
                # value. custom_value=True still allows typing one that
                # hasn't been seen yet -- covers states an arbitrary
                # third-party integration invented itself (e.g. an EV
                # charger's "ready_to_charge") that can't be enumerated
                # up front.
                vol.Optional(CONF_IGNORE_EXTRA_STATES, default=[]): _extra_states_selector(
                    suggested_options
                ),
            })
            return self.async_show_form(
                step_id="options",
                data_schema=options_schema,
                description_placeholders={"entity_id": original_entity_id},
            )

        user_input = _resolve_submitted_input(self, user_input)
        final_data = {CONF_ENTITY_ID: self.data[CONF_ENTITY_ID], **user_input}

        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(final_data[CONF_ENTITY_ID])
        if entity_entry:
            final_data["device_id"] = entity_entry.device_id

        return self.async_create_entry(title=final_data["name"], data=final_data)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Let the user change which entity is tracked, without deleting and recreating the helper."""
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            new_entity_id = user_input[CONF_ENTITY_ID]
            await self.async_set_unique_id(new_entity_id)
            self._abort_if_unique_id_configured()

            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(new_entity_id)
            new_data = {**reconfigure_entry.data, CONF_ENTITY_ID: new_entity_id}
            new_data["device_id"] = entity_entry.device_id if entity_entry else None
            # async_update_and_abort, not async_update_reload_and_abort --
            # this integration already has an entry.add_update_listener in
            # __init__.py that reloads on any entry change (fired via
            # async_update_entry, which this method also calls under the
            # hood); combining that listener with the *_reload_and_abort
            # variant would reload the entry twice / race, deprecated as of
            # HA 2026.6, becomes an error in 2026.12.
            return self.async_update_and_abort(reconfigure_entry, data=new_data)

        schema = vol.Schema({
            vol.Required(
                CONF_ENTITY_ID, default=reconfigure_entry.data[CONF_ENTITY_ID]
            ): EntitySelector(EntitySelectorConfig()),
        })
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            description_placeholders={"name": reconfigure_entry.title},
        )


class PreviousStateTrackerOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if user_input is not None:
            user_input = _resolve_submitted_input(self, user_input)
            return self.async_create_entry(title="", data=user_input)

        current_ignore_unknown = self.config_entry.options.get(CONF_IGNORE_UNKNOWN, True)
        current_ignore_unavailable = self.config_entry.options.get(CONF_IGNORE_UNAVAILABLE, True)
        current_ignore_extra_states = self.config_entry.options.get(CONF_IGNORE_EXTRA_STATES, [])
        tracked_entity_id = self.config_entry.data[CONF_ENTITY_ID]
        # Passing the already-saved values in so a state that's no longer
        # current/in-window still shows up as a (translated) option, not
        # just a bare chip with nothing to reselect it from if removed by
        # accident.
        suggested_options = await _async_suggested_options(
            self.hass, tracked_entity_id, extra_raw_values=set(current_ignore_extra_states)
        )
        _stash_label_map(self, suggested_options)

        schema = vol.Schema({
            vol.Required(CONF_IGNORE_UNKNOWN, default=current_ignore_unknown): BooleanSelector(BooleanSelectorConfig()),
            vol.Required(CONF_IGNORE_UNAVAILABLE, default=current_ignore_unavailable): BooleanSelector(BooleanSelectorConfig()),
            vol.Optional(CONF_IGNORE_EXTRA_STATES, default=current_ignore_extra_states): _extra_states_selector(
                suggested_options
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "name": self.config_entry.title,
                "entity_id": tracked_entity_id,
            },
        )
