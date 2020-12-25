"""Пока не сделано"""

import logging

import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.components import mqtt
from homeassistant.const import CONF_HOST, CONF_ID, CONF_NAME, CONF_PASSWORD
from .const import DOMAIN  # pylint:disable=unused-import
from .hub import MegaD
from . import exceptions

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID, default='def'): str,
        vol.Required(CONF_HOST, default="192.168.0.14"): str,
        vol.Required(CONF_PASSWORD, default="sec"): str,
    },
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    if data[CONF_ID] in hass.data[DOMAIN]:
        raise exceptions.DuplicateId('duplicate_id')
    _mqtt = hass.data.get(mqtt.DOMAIN)
    if not isinstance(_mqtt, mqtt.MQTT):
        raise exceptions.MqttNotConfigured("mqtt must be configured first")
    hub = MegaD(hass, **data, mqtt=_mqtt)
    if not await hub.authenticate():
        raise exceptions.InvalidAuth

    return hub


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for mega."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_ASSUMED

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except exceptions.CannotConnect:
            errors["base"] = "cannot_connect"
        except exceptions.InvalidAuth:
            errors["base"] = "invalid_auth"
        except exceptions.DuplicateId:
            errors["base"] = "duplicate_id"
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors[CONF_ID] = str(exc)
        else:
            return self.async_create_entry(
                title=user_input.get(CONF_ID, user_input[CONF_HOST]),
                data=user_input,
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
