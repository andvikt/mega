"""Platform for light integration."""
import asyncio
import json
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA as SENSOR_SCHEMA,
    BinarySensorEntity,
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

lg = logging.getLogger(__name__)


# Validation of the user's configuration
_EXTENDED = {
    vol.Required(CONF_PORT): int,
    vol.Optional(CONF_NAME): str,
    vol.Optional(CONF_UNIQUE_ID): str,
}
_ITEM = vol.Any(int, _EXTENDED)
PLATFORM_SCHEMA = SENSOR_SCHEMA.extend(
    {
        vol.Optional(str, description="mega id"): [_ITEM]
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    config.pop(CONF_PLATFORM)
    ents = []
    for mid, _config in config.items():
        mega = hass.data["mega"][mid]
        for x in _config:
            if isinstance(x, int):
                ent = MegaBinarySensor(
                    mega=mega, port=x
                )
            else:
                ent = MegaBinarySensor(
                    mega=mega, port=x[CONF_PORT], name=x[CONF_NAME]
                )
            ents.append(ent)
            await mega.add_entity(ent)
    add_entities(ents)
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices):
    hub: MegaD = hass.data['mega'][config_entry.data[CONF_ID]]
    devices = []
    async for port, pty, m in hub.scan_ports():
        if pty == "0":
            sensor = MegaBinarySensor(hub, port)
            devices.append(sensor)
            await hub.add_entity(sensor)
    async_add_devices(devices)


class MegaBinarySensor(BinarySensorEntity, RestoreEntity):

    def __init__(
            self,
            mega: MegaD,
            port: int,
            name=None,
            unique_id=None
    ):
        self._state = None
        self._is_on = False
        self._brightness = None
        self.mega: MegaD = mega
        self.port = port
        self._name = name
        self._unique_id = unique_id

    @property
    def name(self):
        return self._name or f"mega_p{self.port}"

    @property
    def unique_id(self):
        return self._unique_id or f"mega_{self.mega.id}_{self.port}"

    async def async_added_to_hass(self) -> None:
        await self.mega.subscribe(self.port, callback=self._set_state_from_msg)
        state = await self.async_get_last_state()
        if state:
            self._is_on = state.state == "on"
        await asyncio.sleep(0.1)
        await self.mega.get_port(self.port)

    @property
    def is_on(self) -> bool:
        return self._is_on

    def _set_state_from_msg(self, msg):
        state = json.loads(msg.payload)
        self._is_on = state.get("value") == "ON"
        self.hass.async_create_task(self.async_update_ha_state())
