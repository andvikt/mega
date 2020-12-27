import asyncio

import json

from homeassistant.core import State
from .hub import MegaD
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN


class BaseMegaEntity(RestoreEntity):

    def __init__(
            self,
            mega_id: str,
            port: int,
            name=None,
            unique_id=None
    ):
        self._state: State = None
        self.port = port
        self._name = name
        self._unique_id = unique_id
        self._mega_id = mega_id

    @property
    def mega(self) -> MegaD:
        return self.hass.data[DOMAIN][self._mega_id]

    @property
    def available(self) -> bool:
        return self.mega.online

    @property
    def name(self):
        return self._name or f"{self.mega.id}_p{self.port}"

    @property
    def unique_id(self):
        return self._unique_id or f"mega_{self.mega.id}_{self.port}"

    async def async_added_to_hass(self) -> None:
        await self.mega.subscribe(self.port, callback=self.__update)
        self._state = await self.async_get_last_state()
        await asyncio.sleep(0.1)
        await self.mega.get_port(self.port)

    def __update(self, msg):
        try:
            value = json.loads(msg.payload)
            self._update(value)
            self.mega.lg.debug(f'state after update %s', self._state)
            self.hass.async_create_task(self.async_update_ha_state())
            return
        except:
            self.mega.lg.warning(f'could not parse json: {msg.payload}')

    def _update(self, payload: dict):
        raise NotImplementedError
