import asyncio

import aiohttp
import typing
from bs4 import BeautifulSoup

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from .exceptions import CannotConnect


class MegaD:
    """MegaD Hub"""

    def __init__(
            self,
            hass: HomeAssistant,
            host: str,
            password: str,
            mqtt: mqtt.MQTT,
            id: str = None,
            mqtt_id: str = None,
            scan_interval=60,
            **kwargs,
    ):
        """Initialize."""
        self.hass = hass
        self.host = host
        self.sec = password
        self.mqtt = mqtt
        self.id = id
        self.lck = asyncio.Lock()
        self.is_alive = asyncio.Condition()
        self.online = True
        self.entities: typing.List[Entity] = []
        self.poll_interval = scan_interval
        self.subscriptions = []
        if not mqtt_id:
            _id = host.split(".")[-1]
            self.mqtt_id = f"megad/{_id}"
        else:
            self.mqtt_id = mqtt_id
            self._loop: asyncio.AbstractEventLoop = None

    async def add_entity(self, ent):
        async with self.lck:
            self.entities.append(ent)

    async def poll(self):
        """
        Send get port 0 every poll_interval. When answer is received, mega.<id> becomes online else mega.<id> becomes
        offline
        """
        self._loop = asyncio.get_event_loop()
        await self.subscribe(0, callback=self._notify)
        while True:
            async with self.is_alive:
                await self.get_port(0)
                try:
                    await asyncio.wait_for(self.is_alive.wait(), timeout=5)
                    self.hass.states.async_set(
                        f'mega.{self.id}',
                        'online',
                    )
                    self.online = True
                except asyncio.TimeoutError:
                    self.online = False
                    self.hass.states.async_set(
                        f'mega.{self.id}',
                        'offline',
                    )
                for x in self.entities:
                    try:
                        await x.async_update_ha_state()
                    except RuntimeError:
                        pass
            await asyncio.sleep(self.poll_interval)

    async def _async_notify(self):
        async with self.is_alive:
            self.is_alive.notify_all()

    def _notify(self, *args):
        asyncio.run_coroutine_threadsafe(self._async_notify(), self._loop)

    async def get_mqtt_id(self):
        async with aiohttp.request(
            'get', f'http://{self.host}/{self.sec}/?cf=2'
        ) as req:
            data = await req.text()
            data = BeautifulSoup(data, features="lxml")
            _id = data.find(attrs={'name': 'mdid'})
            if _id:
                _id = _id['value']
            return _id or 'megad/' + self.host.split('.')[-1]

    async def send_command(self, port=None, cmd=None):
        if port:
            url = f"http://{self.host}/{self.sec}/?pt={port}&cmd={cmd}"
        else:
            url = f"http://{self.host}/{self.sec}/?cmd={cmd}"
        async with self.lck:
            async with aiohttp.request("get", url=url) as req:
                if req.status != 200:
                    return False
                else:
                    return True

    async def save(self):
        await self.send_command(cmd='s')

    async def get_port(self, port):
        async with self.lck:
            await self.mqtt.async_publish(
                topic=f'{self.mqtt_id}/cmd',
                payload=f'get:{port}',
                qos=0,
                retain=False,
            )
            await asyncio.sleep(0.1)

    async def get_all_ports(self):
        for x in range(37):
            await self.get_port(x)

    async def reboot(self, save=True):
        await self.save()
        # await self.send_command(cmd=)

    async def subscribe(self, port, callback):
        subs = await self.mqtt.async_subscribe(
            topic=f"{self.mqtt_id}/{port}",
            msg_callback=callback,
            qos=0,
        )
        self.subscriptions.append(subs)

    def unsubscribe_all(self):
        for x in self.subscriptions:
            x()

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        async with aiohttp.request("get", url=f"http://{self.host}/{self.sec}") as req:
            if "Unauthorized" in await req.text():
                return False
            else:
                if req.status != 200:
                    raise CannotConnect
                return True

    async def scan_port(self, port):
        async with aiohttp.request('get', f'http://{self.host}/{self.sec}/?pt={port}') as req:
            html = await req.text()
        tree = BeautifulSoup(html, features="lxml")
        pty = tree.find('select', attrs={'name': 'pty'})
        if pty is None:
            return
        else:
            pty = pty.find(selected=True)['value']
        if pty in ['0', '1']:
            m = tree.find('select', attrs={'name': 'm'})
            if m:
                m = m.find(selected=True)['value']
            return pty, m

    async def scan_ports(self):
        for x in range(37):
            ret = await self.scan_port(x)
            if ret:
                yield [x, *ret]
