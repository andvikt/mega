import asyncio

import aiohttp

from homeassistant.components import mqtt
from .exceptions import CannotConnect


class MegaD:
    """MegaD Hub"""

    def __init__(
        self, host: str, password: str, mqtt: mqtt.MQTT, mqtt_id: str = None, **kwargs
    ):
        """Initialize."""
        self.host = host
        self.sec = password
        self.mqtt = mqtt
        self.id = id
        self.lck = asyncio.Lock()
        if not mqtt_id:
            _id = host.split(".")[-1]
            self.mqtt_id = f"megad/{_id}"
        else:
            self.mqtt_id = mqtt_id

    async def send_command(self, port = None, cmd = None):
        if port:
            url = f"http://{self.host}/{self.sec}/?pt={port}&cmd={cmd}"
        else:
            url = f"http://{self.host}/{self.sec}/?cmd={cmd}"
        print(url)
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
        print(f"{self.mqtt_id}/{port}")
        await self.mqtt.async_subscribe(
            topic=f"{self.mqtt_id}/{port}",
            msg_callback=callback,
            qos=0,
        )

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        async with aiohttp.request("get", url=f"http://{self.host}/{self.sec}") as req:
            if "Unauthorized" in await req.text():
                return False
            else:
                if req.status != 200:
                    raise CannotConnect
                return True
