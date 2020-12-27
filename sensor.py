"""Platform for light integration."""
import logging

import typing
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_SCHEMA,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PLATFORM,
    CONF_PORT,
    CONF_UNIQUE_ID,
    CONF_ID,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant
from .entities import BaseMegaEntity
from .const import CONF_KEY, TEMP, HUM, W1, W1BUS
from .hub import MegaD
import re

lg = logging.getLogger(__name__)

PATT_TEMP = re.compile(r'temp:([01234567890.]+|(NA))')
PATT_HUM = re.compile(r'hum:([01234567890.]+|(NA))')
PATTERNS = {
    TEMP: PATT_TEMP,
    HUM: PATT_HUM,
}
UNITS = {
    TEMP: '°C',
    HUM: '%'
}
CLASSES = {
    TEMP: DEVICE_CLASS_TEMPERATURE,
    HUM: DEVICE_CLASS_HUMIDITY
}
# Validation of the user's configuration
_ITEM = {
    vol.Required(CONF_PORT): int,
    vol.Optional(CONF_NAME): str,
    vol.Optional(CONF_UNIQUE_ID): str,
    vol.Required(CONF_TYPE): vol.Any(
        W1,
        W1BUS,
    ),
    vol.Optional(CONF_KEY, default=TEMP): vol.Any(*PATTERNS),
}
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
        for x in _config:
            ent = _make_entity(mid, **x)
            ents.append(ent)
    add_entities(ents)
    return True


def _make_entity(mid: str, port: int, conf: dict):
    key = conf[CONF_KEY]
    if conf[CONF_TYPE] == W1:
        return Mega1WSensor(
            key=key,
            mega_id=mid,
            port=port,
            patt=PATTERNS[key],
            unit_of_measurement=UNITS[key],  # TODO: make other units
            device_class=CLASSES[key],
            id_suffix=key
        )


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices):
    mid = config_entry.data[CONF_ID]
    hub: MegaD = hass.data['mega'][mid]
    devices = []
    async for port, pty, m in hub.scan_ports():
        if pty == "3" and m == "3":
            page = await hub.get_port_page(port)
            lg.debug(f'html: %s', page)
            for key, patt in PATTERNS.items():
                if not patt.search(page):
                    continue
                hub.lg.debug(f'add sensor {W1}:{key}')
                sensor = _make_entity(
                    mid=mid,
                    port=port,
                    conf={
                        CONF_TYPE: W1,
                        CONF_KEY: key,
                    })
                devices.append(sensor)

    async_add_devices(devices)


class Mega1WSensor(BaseMegaEntity):

    def __init__(self, key, patt, unit_of_measurement, device_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = None
        self.patt: typing.Pattern = patt
        self.key = key
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement

    async def async_added_to_hass(self) -> None:
        await super(Mega1WSensor, self).async_added_to_hass()
        self.mega.sensors.append(self)

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def unique_id(self):
        return super().unique_id + f'_{self.key}'

    @property
    def device_class(self):
        return self._device_class

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        if self._value is None and self._state is not None:
            return self._state.state
        return self._value

    def _update(self, payload: dict):
        val = payload.get('value', '')
        if isinstance(val, str):
            val = self.patt.findall(val)
            if val:
                self._value = val[0]
        elif isinstance(val, (float, int)):
            self._value = val
        self.mega.lg.debug('parsed: %s', self._value)
