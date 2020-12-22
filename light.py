"""Platform for light integration."""
import json
import logging

import voluptuous as vol

from homeassistant.components.light import (
    PLATFORM_SCHEMA as LIGHT_SCHEMA,
    SUPPORT_BRIGHTNESS,
    Light,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_PLATFORM,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .hub import MegaD
from .const import CONF_DIMMER, CONF_SWITCH

_LOGGER = logging.getLogger(__name__)


# Validation of the user's configuration
_EXTENDED = {
    vol.Required(CONF_PORT): int,
    vol.Optional(CONF_NAME): str,
}
_ITEM = vol.Any(int, _EXTENDED)
DIMMER = {vol.Required(CONF_DIMMER): [_ITEM]}
SWITCH = {vol.Required(CONF_SWITCH): [_ITEM]}
PLATFORM_SCHEMA = LIGHT_SCHEMA.extend(
    {
        vol.Optional(str, description="mega id"): {
            vol.Optional("dimmer", default=[]): [_ITEM],
            vol.Optional("switch", default=[]): [_ITEM],
        }
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    config.pop(CONF_PLATFORM)
    ents = []
    for mid, _config in config.items():
        mega = hass.data["mega"][mid]
        for x in _config["dimmer"]:
            if isinstance(x, int):
                ent = MegaLight(hass, mega=mega, port=x, dimmer=True)
            else:
                ent = MegaLight(
                    hass, mega=mega, port=x[CONF_PORT], name=x[CONF_NAME], dimmer=True
                )
            ents.append(ent)
        for x in _config["switch"]:
            if isinstance(x, int):
                ent = MegaLight(hass, mega=mega, port=x, dimmer=False)
            else:
                ent = MegaLight(
                    hass, mega=mega, port=x[CONF_PORT], name=x[CONF_NAME], dimmer=False
                )
            ents.append(ent)
    add_entities(ents)
    return True


class MegaLight(Light, RestoreEntity):
    def __init__(
        self, hass: HomeAssistant, mega: MegaD, port: int, dimmer=False, name=None
    ):
        self._state = None
        self._is_on = False
        self._brightness = None
        self.dimmer = dimmer
        self.mega: MegaD = mega
        self.port = port
        self._name = name
        self.hass = hass

    @property
    def brightness(self):
        return self._brightness

    @property
    def name(self):
        return self._name or f"mega_p{self.port}"

    @property
    def unique_id(self):
        return f"mega_{self.mega.host}_{self.port}"

    async def async_added_to_hass(self) -> None:
        await self.mega.subscribe(self.port, callback=self._set_state_from_msg)
        state = await self.async_get_last_state()
        if state:
            self._is_on = state.state == "on"
            self._brightness = state.attributes.get("brightness")

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS if self.dimmer else 0

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, brightness=None, **kwargs) -> None:
        brightness = brightness or self._brightness
        if self.dimmer and brightness == 0:
            cmd = 255
        elif self.dimmer:
            cmd = brightness
        else:
            cmd = 1
        if await self.mega.send_command(self.port, f"{self.port}:{cmd}"):
            self._is_on = True
            self._brightness = brightness
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:

        cmd = "0"

        if await self.mega.send_command(self.port, f"{self.port}:{cmd}"):
            self._is_on = False
        await self.async_update_ha_state()

    def _set_state_from_msg(self, msg):
        state = json.loads(msg.payload)
        self._is_on = state.get("value") == "ON"
        self.hass.async_create_task(self.async_update_ha_state())
