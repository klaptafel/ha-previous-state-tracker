DOMAIN = "previous_state_tracker"
PLATFORMS = ["sensor"]
CONF_ENTITY_ID = "entity_id"
CONF_IGNORE_UNKNOWN = "ignore_unknown"
CONF_IGNORE_UNAVAILABLE = "ignore_unavailable"
CONF_IGNORE_EXTRA_STATES = "ignore_extra_states"

DEFAULT_IGNORE_UNKNOWN = True
DEFAULT_IGNORE_UNAVAILABLE = True
# Deliberately not a shared DEFAULT_IGNORE_EXTRA_STATES constant: every call
# site below builds its own fresh [] instead, so nothing could ever mutate
# a module-level list shared across every config/options flow instance.
