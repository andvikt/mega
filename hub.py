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

    async def send_command(self, port, cmd):
        url = f"http://{self.host}/{self.sec}/?pt={port}&cmd={cmd}"
        print(url)
        async with self.lck:
            async with aiohttp.request("get", url=url) as req:
                if req.status != 200:
                    return False
                else:
                    return True

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
