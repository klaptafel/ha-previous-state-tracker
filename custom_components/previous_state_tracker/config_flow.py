from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from homeassistant.helpers import selector
from .const import DOMAIN, CONF_ENTITIES, CONF_NAME

class PreviousStateTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return PreviousStateTrackerOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_NAME, default="Previous States"): str,
            vol.Required(CONF_ENTITIES): selector.selector({"entity": {"multiple": True}})
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema
        )

class PreviousStateTrackerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_entities = self.config_entry.options.get(
            CONF_ENTITIES, self.config_entry.data.get(CONF_ENTITIES, [])
        )
        
        schema = vol.Schema({
            vol.Required(CONF_ENTITIES, default=current_entities): selector.selector({"entity": {"multiple": True}})
        })
        return self.async_show_form(step_id="init", data_schema=schema)
