[![Made for Home Assistant](https://img.shields.io/badge/Made%20for-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Previous State Tracker: Home Assistant helper integration

> [!NOTE]
> This integration is vibe coded


A simple yet powerful Home Assistant helper to track the previous state of any entity. Perfect for creating more intelligent and context-aware automations.

![Logo](/custom_components/previous_state_tracker/brand/logo.png)

This integration provides a helper to track the previous state of an entity. While this can be partially replicated with `template` sensors, this integration is designed to be a more reliable and convenient solution that handles several complexities automatically.

---

## Features

*   **Fully UI-driven:** Can be fully managed through the **Settings > Devices & Services > Helpers** menu. No YAML is required.
*   **Automatic device linking and naming:** Automatically links the tracker sensor to the source entity's device (when it has one), keeping your setup organized (not possible with standalone template helpers). The sensor's display name is computed too, not frozen at setup: it always reflects the tracked entity's *current* name, so renaming that entity later keeps the tracker's name correct automatically.
*   **Reliable state persistence:** Reliably restores its last known value after a restart and dynamically copies sensor properties (`unit_of_measurement`, `state_class`, etc.) to prevent errors with long-term statistics.
*   **Timestamp and duration tracking:** Attributes store the exact time of the last change (`last_changed`) and how long the entity spent in that previous state (`duration_in_previous_state`, in seconds).
*   **Live updates:** The sensor updates the instant the tracked entity changes state; it listens for state changes directly, no polling involved.
*   **Configurable filtering:** Optionally ignore `unavailable` and `unknown` states, plus any custom list of extra state values (e.g. `idle`/`standby` for a media player), during setup or from the integration's options. When ignored, a transition into or out of that state is simply not recorded as a "previous state"; the sensor keeps showing the last *meaningful* value instead of briefly flashing to it. The extra-states field suggests the entity's own known/recent state values (from its current state and, if available, recorder history), shown with the same translated label the entity itself displays (e.g. "Detected" for a motion sensor); pick it and the correct underlying raw value (`on`) is stored automatically, no need to know or type it yourself.
*   **Duplicate prevention:** Prevents creating more than one tracker for the same entity.

---

## Installation

This integration is available via [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=klaptafel&repository=ha-previous-state-tracker&category=integration)

1.  Go to HACS in your Home Assistant.
2.  Search for "Previous State Tracker" and download it.
3.  Restart Home Assistant.

---

## Configuration

[![Add integrations](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=previous_state_tracker)

1.  Navigate to **Settings > Devices & Services > [Helpers](https://my.home-assistant.io/redirect/helpers/)**.
2.  Click the **Create Helper** button.
3.  Find and select **Previous State Tracker** in the list.
4.  Follow the on-screen instructions to select your source entity and configure the sensor.

---

## Removal

1.  Navigate to **Settings > Devices & Services > [Helpers](https://my.home-assistant.io/redirect/helpers/)**.
2.  Find the tracker you want to remove and click it.
3.  Click the trash-can icon, then confirm.

This removes the previous-state sensor only; the entity you were tracking is unaffected.

---

## Example automation

The most common reason to want a "previous state" is to tell a genuine transition apart from a
state that just happens to already be what you expected. For example, notify only when a washing
machine actually *finishes* a cycle, not when it's simply idle at startup:

```yaml
automation:
  - alias: "Notify when the washing machine finishes"
    trigger:
      - platform: state
        entity_id: sensor.washing_machine_power
        to: "off"
    condition:
      - condition: state
        entity_id: sensor.washing_machine_power_previous_state
        state: "running"
    action:
      - service: notify.mobile_app
        data:
          message: "The washing machine has finished."
```

Without the previous-state check, this automation would also fire the very first time the sensor
reports "off" after a Home Assistant restart, even if the machine was never running.

---

## Troubleshooting

- **Sensor shows "Unavailable (source entity not found)"**: the tracked entity is temporarily or
  permanently gone. A rename (same entity, new `entity_id`) is followed automatically. A full
  removal isn't; a repair issue appears under **Settings > Devices & Services > Repairs**, and
  you'll need to either wait for the entity to come back or pick a different one via
  **Reconfigure**.
- **The previous state briefly shows a state you meant to filter out**:
  check you enabled the right option: "Ignore the 'unknown' state", "Ignore the 'unavailable'
  state", and "Additional states to ignore" are independent. Also note what "ignore" actually does:
  it skips recording *that particular* state as the previous value, it doesn't suppress the sensor
  updating at all.
- **Nothing happens after a Home Assistant restart**: the sensor restores its last known value
  automatically via Home Assistant's own restore-state mechanism; no action needed on your part.

## Known limitations

- Only the tracked entity's plain `state` string is tracked, not any of its attributes.
- `unit_of_measurement`/`device_class`/`state_class` are copied dynamically from the tracked
  entity, so if those change on the source entity, there can be a brief moment of mismatch until
  the next state update arrives.
- If the tracked entity is deleted entirely (not just renamed), the tracker doesn't automatically
  pick a replacement; you'll need to use **Reconfigure** to point it at a different entity.
- The state suggestions in "Additional states to ignore" are best-effort: they come from the
  entity's current state plus up to 30 days of recorder history. If you don't use the recorder, have
  excluded that entity from it, or the state you want hasn't occurred recently, it just won't be
  suggested. You can still type it manually: if what you type matches one of the suggested labels
  shown at the time (case doesn't matter, e.g. `detected`/`Detected`/`DETECTED` all count), it's
  mapped back to the correct raw value automatically, same as picking it. The raw value itself is
  also matched case-insensitively at runtime (so `On`/`on`/`ON` are all treated the same), even if
  it was never offered as a suggestion. Typing something that doesn't match any known state or
  label at all (e.g. a value from a device class this entity doesn't have) is stored exactly as
  typed.
- A value in "Additional states to ignore" can contain `*` as a wildcard, matching any run of
  characters (including none). Useful for a family of related states you don't want to list one by
  one, e.g. a robot vacuum's `Error: *` covers `Error: dustbin full`, `Error: stuck`, etc., without
  needing to record any particular error text as a meaningful previous state.
  Everything else in the value is matched literally -- only `*` is special.

---

## Discussions
Share ideas, feedback, questions, or your setups with this integration.

- 💬 [General](../../discussions/categories/general): Anything related to this integration.  
- 💡 [Ideas](../../discussions/categories/ideas): Suggest improvements **and vote** on ideas. 
- 🙏 [Q&A](../../discussions/categories/q-a): Ask questions and get help.  
- 🙌 [Show and tell](../../discussions/categories/show-and-tell): See examples of how others use this integration, or share your own.
