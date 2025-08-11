[![Made for Home Assistant](https://img.shields.io/badge/Made%20for-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge&cacheSeconds=3600)](https://github.com/hacs/integration)


# A simple yet powerful Home Assistant helper to track the previous state of any entity. Perfect for creating more intelligent and context-aware automations.
![Logo](/logo/logo.png)

Ever wanted to trigger an automation but needed to know what the *previous* state of a sensor was? This integration solves that problem by providing a dedicated helper that cleanly stores the last known value.


## Features

*   **Fully UI-Driven:** No YAML required. The entire configuration is done through the Home Assistant "Helpers" menu.
*   **Seamless Device Integration:** The new sensor is automatically added to the same device as the original entity, keeping your setup clean and organized.
*   **State & Timestamp Tracking:** Creates a new diagnostic sensor that holds the previous state and provides the exact timestamp of when that state was last active as an attribute.
*   **State Persistence:** Restores its last known state and timestamp after a Home Assistant restart, ensuring reliability.
*   **Smart Filtering:** Optionally ignore `unavailable` and `unknown` states to prevent unwanted updates.
*   **Duplicate Prevention:** The config flow prevents you from creating more than one tracker for the same source entity.


## Installation

This integration is available via [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=klaptafel&repository=ha-previous-state-tracker&category=integration)

1.  Go to HACS in your Home Assistant.
2.  Search for "Previous State Tracker" and click on it.
3.  Click the "Download" button and follow the instructions.
4.  Restart Home Assistant.


## Configuration

[![Add integrations](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=previous_state_tracker)

1.  Navigate to **Settings > Devices & Services > [Helpers](https://my.home-assistant.io/redirect/helpers/)**.
2.  Click the **Create Helper** button.
3.  Find and select **Previous State Tracker** in the list.
4.  Follow the on-screen instructions:
    *   **Step 1:** Choose the source entity you want to track.
    *   **Step 2:** Give your new sensor a name and configure the ignore options.
5.  That's it! You will find the new sensor attached to the same device as your source entity.


## Options

You can change the "ignore" options at any time after creation.
1.  Go to **Settings > Devices & Services > Integrations**.
2.  Find the "Previous State Tracker" entry you created.
3.  Click **Configure** and adjust the settings.


## Community
Discussions are the place to share ideas, give feedback, ask questions, or show how you use this integration.

## Join the discussion 
- [💬 General](../../discussions/categories/general) – Anything related to this integration.  
- [💡 Ideas](../../discussions/categories/ideas) – Suggest improvements **and vote** on ideas.  
- [📦 Polls](../../discussions/categories/polls) – Vote and share your opinion on upcoming changes.  
- [🙏 Q&A](../../discussions/categories/q-a) – Ask questions and get help.  
- [🙌 Show and tell](../../discussions/categories/show-and-tell) – See examples of how others use this integration, or share your own.
