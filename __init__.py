"""The mega integration."""

import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt
from .const import DOMAIN
from .hub import MegaD

CONF_MQTT_ID = "mqtt_id"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            str: {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_MQTT_ID, default=""): str,
            }
        }
    },
    extra=vol.ALLOW_EXTRA,
)


PLATFORMS = ["switch", "light"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the mega component."""
    for id, conf in config[DOMAIN].items():
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        _mqtt = hass.data.get(mqtt.DOMAIN)
        hub = MegaD(**conf, mqtt=_mqtt)
        if not await hub.authenticate():
            raise Exception("not authentificated")
        hass.data[DOMAIN][id] = hub
    return True
