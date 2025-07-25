from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import selector
from .const import DOMAIN

class PreviousStateTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Previous State Tracker", data=user_input)

        schema = vol.Schema({
            vol.Required("entities"): selector.selector({"entity": {"multiple": True}})
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema
        )
