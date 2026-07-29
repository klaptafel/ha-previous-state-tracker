from __future__ import annotations
import logging
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, State, Event
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
    EventEntityRegistryUpdatedData,
    EventStateChangedData,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    CONF_ENTITY_ID,
    CONF_IGNORE_UNKNOWN,
    CONF_IGNORE_UNAVAILABLE,
    CONF_IGNORE_EXTRA_STATES,
    DEFAULT_IGNORE_UNAVAILABLE,
    DEFAULT_IGNORE_UNKNOWN,
)
from .util import IgnoredStates, humanize_entity_id, merged_config

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = merged_config(config_entry)

    entity_id = config[CONF_ENTITY_ID]
    ignore_unknown = config.get(CONF_IGNORE_UNKNOWN, DEFAULT_IGNORE_UNKNOWN)
    ignore_unavailable = config.get(CONF_IGNORE_UNAVAILABLE, DEFAULT_IGNORE_UNAVAILABLE)
    ignore_extra_states = config.get(CONF_IGNORE_EXTRA_STATES, [])

    sensor = PreviousStateSensor(
        hass=hass,
        entity_id=entity_id,
        ignore_unknown=ignore_unknown,
        ignore_unavailable=ignore_unavailable,
        ignore_extra_states=ignore_extra_states,
        unique_id=config_entry.entry_id,
    )
    async_add_entities([sensor])


class PreviousStateSensor(SensorEntity, RestoreEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "previous_state"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        ignore_unknown: bool,
        ignore_unavailable: bool,
        ignore_extra_states: list[str],
        unique_id: str,
    ) -> None:
        self.hass = hass
        self._tracked_entity_id = entity_id
        # A single IgnoredStates covering all three ignore options --
        # "unknown"/"unavailable" are HA's own state constants (always
        # exactly lowercase already) folded in alongside the user-supplied
        # extra states (which may include '*' wildcards, e.g. "Error: *"),
        # so _update_and_write_state only needs one matches() check instead
        # of separate comparisons. Case-insensitivity is a second line of
        # defense on top of config_flow.py's own case-insensitive
        # reverse-mapping, for anything that slips through that (e.g. a raw
        # value typed with the wrong case that was never offered as a
        # suggestion in the first place). The originally-typed/picked case
        # is still what's stored in the config entry and shown in
        # diagnostics -- only this internal lookup is normalized. Safe to
        # compute once here: these options only change via a full entity
        # reload (config-entry options update), never in place.
        extra_states = list(ignore_extra_states)
        if ignore_unknown:
            extra_states.append("unknown")
        if ignore_unavailable:
            extra_states.append("unavailable")
        self._ignore_states = IgnoredStates(extra_states)
        self._attr_unique_id = unique_id
        self._attr_native_value = None
        self._attr_extra_state_attributes = {
            "tracked_entity_id": entity_id,
            "last_changed": None,
            "duration_in_previous_state": None,
        }
        self._attr_native_unit_of_measurement = None
        self._attr_device_class = None
        self._attr_state_class = None
        self._removed_issue_id = f"tracked_entity_removed_{unique_id}"
        self._disabled_issue_id = f"tracked_entity_disabled_{unique_id}"
        self._remove_state_listener: Callable[[], None] | None = None

        # Link, not merge (found by review, 2026-07-30, ahead of HA 2026.8's
        # single-config-entry-per-device model): a device can belong to only
        # one config entry now, so reusing the tracked entity's own
        # identifiers to *merge* onto its device (the old approach here)
        # would make this integration's own config entry try to co-own it.
        # async_entity_id_to_device is the same helper core's own threshold/
        # derivative/trend etc. use to show their entity on a source
        # entity's device without claiming any part of it -- confirmed
        # against their real source (home-assistant/core). Guard mirrors
        # threshold's own binary_sensor.py: only entity_id="" in preview
        # mode is falsy here, never a real tracked entity.
        if entity_id:
            self.device_entry = async_entity_id_to_device(hass, entity_id)

    @property
    def name(self) -> str | None:
        """Entity display name.

        Both branches include the tracked entity's own name, not just its
        device's name -- a device can have several trackable entities (e.g.
        a photo frame's media player and its own send-status sensor), so a
        bare "<device> Previous State" would be ambiguous about which one's
        history this actually is.

        With a device (linked to the tracked entity's own real device, see
        __init__'s own comment): read the tracked entity's own entity-only
        name from the registry (its *state*'s friendly name is already
        device-prefixed -- has_entity_name would double the device name if
        used directly) and combine it with the normal translated "Previous
        State" suffix (entity.sensor.previous_state). HA's own
        has_entity_name/device machinery still prepends the (always
        current) device name on top of whatever this property returns.

        Without a device to prefix with: compute the full name ourselves
        from the tracked entity's *current* name, so it stays in sync if
        the source entity gets renamed later, instead of freezing a name at
        config time the way this used to work.
        """
        if self.device_entry is not None:
            entity_entry = er.async_get(self.hass).async_get(self._tracked_entity_id)
            source_name = (entity_entry.name or entity_entry.original_name) if entity_entry else None
            if not source_name:
                source_name = humanize_entity_id(self._tracked_entity_id)
            # Defensive: a source entity that doesn't use has_entity_name
            # itself stores its already-fully-prefixed name in the registry
            # (e.g. "Woonkamer Fraimic Send Status") -- strip that prefix so
            # it isn't doubled when HA re-prepends the same device name.
            device_name = self.device_entry.name_by_user or self.device_entry.name
            if device_name and source_name.startswith(f"{device_name} "):
                source_name = source_name[len(device_name) + 1:]
            return f"{source_name} {super().name}"
        source_state = self.hass.states.get(self._tracked_entity_id)
        source_name = source_state.name if source_state else self._tracked_entity_id
        return f"{source_name} Previous State"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        
        last_state = await self.async_get_last_state()
        if last_state:
            self._attr_native_value = last_state.state
            self._attr_native_unit_of_measurement = last_state.attributes.get("unit_of_measurement")
            self._attr_device_class = last_state.attributes.get("device_class")
            self._attr_state_class = last_state.attributes.get("state_class")
            if "last_changed" in last_state.attributes:
                self._attr_extra_state_attributes["last_changed"] = last_state.attributes["last_changed"]
            if "duration_in_previous_state" in last_state.attributes:
                self._attr_extra_state_attributes["duration_in_previous_state"] = (
                    last_state.attributes["duration_in_previous_state"]
                )

        source_state = self.hass.states.get(self._tracked_entity_id)
        if source_state:
            self._update_and_write_state(None, source_state)

        self._subscribe_state_listener()
        # Single on_remove registration that always unsubscribes whichever
        # listener is *currently* stored in self._remove_state_listener --
        # safe to swap that out any number of times (see
        # _resubscribe_state_listener) without ever double-unsubscribing a
        # stale one, since only this one indirection is ever registered.
        self.async_on_remove(self._unsubscribe_state_listener)

        @callback
        def entity_rename_listener(
            event: Event[EventEntityRegistryUpdatedData],
        ) -> None:
            if event.data["action"] != "update":
                return

            if "old_entity_id" in event.data:
                # entity_id itself was one of the changed fields -- a true
                # rename to a new entity_id, follow it.
                old_entity_id = self._tracked_entity_id
                new_entity_id = event.data["entity_id"]
                self._tracked_entity_id = new_entity_id
                self._attr_extra_state_attributes["tracked_entity_id"] = new_entity_id
                _LOGGER.info(
                    "Tracked entity renamed from %s to %s, following", old_entity_id, new_entity_id
                )
                self._persist_tracked_entity_id(new_entity_id)
                self._resubscribe_state_listener()
                new_source_state = self.hass.states.get(new_entity_id)
                self._update_and_write_state(None, new_source_state)
                return

            # Some other registry field changed on the same entity_id (most
            # relevantly its display name) -- our own name property can
            # depend on the source's live name (see the no-device fallback
            # above), so refresh our own state to pick that up right away
            # instead of waiting for the source's next real state change.
            if self.hass.is_running:
                self.async_write_ha_state()

        # async_track_entity_registry_updated_event moves its own internal
        # tracking key to the new entity_id after a rename fires, so this
        # subscription itself keeps following the same entity through any
        # number of later renames without needing to be re-created here.
        self.async_on_remove(
            async_track_entity_registry_updated_event(
                self.hass, [self._tracked_entity_id], entity_rename_listener
            )
        )

    def _subscribe_state_listener(self) -> None:
        @callback
        def state_change_listener(
            event: Event[EventStateChangedData],
        ) -> None:
            self._update_and_write_state(event.data.get("old_state"), event.data.get("new_state"), event.time_fired)

        self._remove_state_listener = async_track_state_change_event(
            self.hass, [self._tracked_entity_id], state_change_listener
        )

    def _unsubscribe_state_listener(self) -> None:
        if self._remove_state_listener:
            self._remove_state_listener()
            self._remove_state_listener = None

    def _resubscribe_state_listener(self) -> None:
        """Swap the state listener over to self._tracked_entity_id's new
        value after a rename. Safe to call any number of times -- the
        on_remove callback registered in async_added_to_hass always reads
        self._remove_state_listener fresh, so there's never a stale
        reference left registered for entity removal to double-unsubscribe."""
        self._unsubscribe_state_listener()
        self._subscribe_state_listener()

    def _persist_tracked_entity_id(self, new_entity_id: str) -> None:
        """Update the config entry's stored entity_id so a restart doesn't
        revert to the stale, pre-rename value from disk."""
        if not self.registry_entry or not self.registry_entry.config_entry_id:
            return
        entry = self.hass.config_entries.async_get_entry(self.registry_entry.config_entry_id)
        if entry:
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_ENTITY_ID: new_entity_id}
            )

    def _update_and_write_state(self, old_state: State | None, new_state: State | None, time_fired = None) -> None:
        was_available = self._attr_available
        self._attr_available = new_state is not None
        if was_available and not self._attr_available:
            _LOGGER.warning(
                "Tracked entity %s is no longer available", self._tracked_entity_id
            )
        elif not was_available and self._attr_available:
            _LOGGER.info(
                "Tracked entity %s is available again", self._tracked_entity_id
            )

        if not self._attr_available:
            self._check_tracked_entity_removed()
        else:
            ir.async_delete_issue(self.hass, DOMAIN, self._removed_issue_id)
            ir.async_delete_issue(self.hass, DOMAIN, self._disabled_issue_id)

        if new_state and self._tracked_entity_id.startswith("sensor."):
            self._attr_native_unit_of_measurement = new_state.attributes.get("unit_of_measurement")
            self._attr_device_class = new_state.attributes.get("device_class")
            self._attr_state_class = new_state.attributes.get("state_class")
        
        if old_state is None:
            if self.hass.is_running:
                self.async_write_ha_state()
            return

        # Checking only old_state here would ignore unavailable/unknown on
        # the way *back* to a real state (e.g. unavailable -> off) but miss
        # it on the way *into* unavailable/unknown (e.g. off -> unavailable)
        # -- in that second case old_state is the real value "off", so the
        # guard never triggered and "off" got recorded as the previous
        # state, even though nothing meaningful actually changed. Checking
        # new_state too covers both directions: whichever side of the
        # transition is unavailable/unknown, skip recording it.
        new_state_value = new_state.state if new_state else None

        if self._ignore_states and (
            self._ignore_states.matches(old_state.state)
            or (new_state_value is not None and self._ignore_states.matches(new_state_value))
        ):
            return

        self._attr_native_value = old_state.state
        if time_fired:
            self._attr_extra_state_attributes["last_changed"] = time_fired.isoformat()
            # old_state.last_changed is when its *value* started (unlike
            # last_updated, which also moves on attribute-only changes) --
            # exactly the moment the state we're now recording as "previous"
            # began, so the gap to time_fired is how long it lasted.
            self._attr_extra_state_attributes["duration_in_previous_state"] = round(
                (time_fired - old_state.last_changed).total_seconds()
            )

        if self.hass.is_running:
            self.async_write_ha_state()

    def _check_tracked_entity_removed(self) -> None:
        """Raise a repair issue explaining why the tracked entity has no
        state: either it's still registered but disabled (a deliberate,
        reversible choice -- a dismissible heads-up rather than a
        "something's broken" warning, since the user can just ignore it if
        that's what they intended), or it's gone from the entity registry
        entirely -- a much stronger signal of "renamed or removed" than
        merely having no current state, which also happens normally (e.g.
        during startup ordering, or a genuinely transient unavailable).
        """
        entity_registry = er.async_get(self.hass)
        entry = entity_registry.async_get(self._tracked_entity_id)

        # The two issues are mutually exclusive -- at most one is ever
        # active. Figure out which (if either), then delete the other and
        # (re-)create the active one in one shared place.
        if entry is not None and entry.disabled_by is not None:
            active_id, other_id, translation_key = (
                self._disabled_issue_id, self._removed_issue_id, "tracked_entity_disabled"
            )
        elif entry is None:
            active_id, other_id, translation_key = (
                self._removed_issue_id, self._disabled_issue_id, "tracked_entity_removed"
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, self._removed_issue_id)
            ir.async_delete_issue(self.hass, DOMAIN, self._disabled_issue_id)
            return

        ir.async_delete_issue(self.hass, DOMAIN, other_id)
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            active_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders={
                "entity_id": self._tracked_entity_id,
                "name": self.name or self._tracked_entity_id,
            },
        )
