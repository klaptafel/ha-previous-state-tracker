[![Made for Home Assistant](https://img.shields.io/badge/Made%20for-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Previous State Tracker
A simple yet powerful Home Assistant helper to track the previous state of any entity. Perfect for creating more intelligent and context-aware automations.

![Logo](/logo/logo.png)

This integration provides a helper to track the previous state of an entity. While this can be partially replicated with `template` sensors, this integration is designed to be a more reliable and convenient solution that handles several complexities automatically.

---

## Features

*   **Fully UI-driven:** Can be fully managed through the **Settings > Devices & Services > Helpers** menu. No YAML is required.
*   **Automatic device linking:** Automatically links the tracker sensor to the source entity's device, keeping your setup organized. This is not possible with standalone template helpers.
*   **Reliable state persistence:** Reliably restores its last known value after a restart and dynamically copies sensor properties (`unit_of_measurement`, `state_class`, etc.) to prevent errors with long-term statistics.
*   **Timestamp tracking:** An attribute stores the exact time of the last change.
*   **Configurable filtering:** Optionally ignore `unavailable` and `unknown` states during setup or from the integration's options.
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

## Discussions
Share ideas, feedback, questions, or your setups with this integration.

- 💬 [General](../../discussions/categories/general) – Anything related to this integration.  
- 💡 [Ideas](../../discussions/categories/ideas) – Suggest improvements **and vote** on ideas. 
- 🙏 [Q&A](../../discussions/categories/q-a) – Ask questions and get help.  
- 🙌 [Show and tell](../../discussions/categories/show-and-tell) – See examples of how others use this integration, or share your own.
