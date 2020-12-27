"""The mega integration."""
import asyncio
import logging
import typing
from functools import partial

import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PLATFORM, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.service import bind_hass
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from .hub import MegaD


_LOGGER = logging.getLogger(__name__)
CONF_MQTT_ID = "mqtt_id"
CONF_PORT_TO_SCAN = 'port_to_scan'

MEGA = {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_MQTT_ID, default=""): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=60): int,
        vol.Optional(CONF_PORT_TO_SCAN, default=0): int,
    }
MEGA_MAPPED = {str: MEGA}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Any(MEGA, MEGA_MAPPED)
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [
    "light",
    "binary_sensor",
    "sensor",
]
ALIVE_STATE = 'alive'
DEF_ID = 'def'
_POLL_TASKS = {}


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the mega component."""
    conf = config.get(DOMAIN)
    hass.data[DOMAIN] = {}
    if conf is None:
        return True
    if CONF_HOST in conf:
        conf = {DEF_ID: conf}
    for id, data in conf.items():
        await _add_mega(hass, id, data)
    hass.services.async_register(
        DOMAIN, 'save', _save_service,
    )
    return True


async def _add_mega(hass: HomeAssistant, id, data: dict):
    data.update(id=id)
    _mqtt = hass.data.get(mqtt.DOMAIN)
    if _mqtt is None:
        raise Exception('mqtt not configured, please configure mqtt first')
    hass.data[DOMAIN][id] = hub = MegaD(hass, **data, mqtt=_mqtt, lg=_LOGGER)
    if not await hub.authenticate():
        raise Exception("not authentificated")
    mid = await hub.get_mqtt_id()
    hub.mqtt_id = mid
    _POLL_TASKS[id] = asyncio.create_task(hub.poll())
    return hub


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    id = entry.data.get('id', entry.entry_id)
    await _add_mega(hass, id, dict(entry.data))

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                entry, platform
            )
        )
    return True


async def async_remove_entry(hass, entry) -> None:
    """Handle removal of an entry."""
    id = entry.data.get('id', entry.entry_id)
    hass.data[DOMAIN][id].unsubscribe_all()
    task: asyncio.Task = _POLL_TASKS.pop(id)
    task.cancel()
    return True


@bind_hass
async def _save_service(hass: HomeAssistant, mega_id='def'):
    hub: MegaD = hass.data[DOMAIN][mega_id]
    await hub.save()


async def _is_alive(cond: asyncio.Condition, msg):
    async with cond:
        cond.notify_all()

