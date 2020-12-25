"""Platform for light integration."""
import asyncio
import json
import logging

import voluptuous as vol

from homeassistant.components.light import (
    PLATFORM_SCHEMA as LIGHT_SCHEMA,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PLATFORM,
    CONF_PORT,
    CONF_UNIQUE_ID,
    CONF_ID
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .hub import MegaD
from .const import CONF_DIMMER, CONF_SWITCH


lg = logging.getLogger(__name__)


# Validation of the user's configuration
_EXTENDED = {
    vol.Required(CONF_PORT): int,
    vol.Optional(CONF_NAME): str,
    vol.Optional(CONF_UNIQUE_ID): str,
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
                ent = MegaLight(
                    mega=mega, port=x, dimmer=True)
            else:
                ent = MegaLight(
                    mega=mega, port=x[CONF_PORT], name=x[CONF_NAME], dimmer=True
                )
            ents.append(ent)
        for x in _config["switch"]:
            if isinstance(x, int):
                ent = MegaLight(
                    mega=mega, port=x, dimmer=False
                )
            else:
                ent = MegaLight(
                    mega=mega, port=x[CONF_PORT], name=x[CONF_NAME], dimmer=False
                )
            await mega.add_entity(ent)
            ents.append(ent)
    add_entities(ents)
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices):
    hub: MegaD = hass.data['mega'][config_entry.data[CONF_ID]]
    devices = []
    async for port, pty, m in hub.scan_ports():
        if pty == "1" and m in ['0', '1']:
            light = MegaLight(hub, port, dimmer=m == '1')
            await hub.add_entity(light)
            devices.append(light)
    async_add_devices(devices)


class MegaLight(LightEntity, RestoreEntity):

    def __init__(
            self,
            mega: MegaD,
            port: int,
            dimmer=False,
            name=None,
            unique_id=None
    ):
        self._state = None
        self._is_on = False
        self._brightness = None
        self.dimmer = dimmer
        self.mega: MegaD = mega
        self.port = port
        self._name = name
        self._unique_id = unique_id

    @property
    def available(self) -> bool:
        return self.mega.online

    @property
    def brightness(self):
        return self._brightness

    @property
    def name(self):
        return self._name or f"{self.mega.id}_p{self.port}"

    @property
    def unique_id(self):
        return self._unique_id or f"mega_{self.mega.id}_{self.port}"

    async def async_added_to_hass(self) -> None:
        await self.mega.subscribe(self.port, callback=self._set_state_from_msg)
        state = await self.async_get_last_state()
        if state:
            self._is_on = state.state == "on"
            self._brightness = state.attributes.get("brightness")
        await asyncio.sleep(0.1)
        await self.mega.get_port(self.port)


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
        try:
            state = json.loads(msg.payload)
            self._is_on = state.get("value") == "ON"
            self.hass.async_create_task(self.async_update_ha_state())
        except Exception as exc:
            print(msg, exc)
