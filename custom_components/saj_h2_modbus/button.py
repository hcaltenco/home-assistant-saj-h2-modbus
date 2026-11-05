"""SAJ H2 Modbus button entities."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SajBaseEntity
from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)

BUTTON_DEFINITIONS = [
    {
        "key": "ev_start_charging",
        "name": "EV Start Charging",
        "icon": "mdi:play",
    },
    {
        "key": "ev_stop_charging",
        "name": "EV Stop Charging",
        "icon": "mdi:stop",
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SAJ button entities."""
    hub: SAJModbusHub = entry.runtime_data
    device_info = hub.device_info
    entities = [
        EvChargingButton(hub, device_info, desc) for desc in BUTTON_DEFINITIONS
    ]
    async_add_entities(entities)


class EvChargingButton(ButtonEntity, SajBaseEntity):
    """Button entity for EV charger start/stop via strategy register 0x4B12."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self, hub: SAJModbusHub, device_info: dict, description: dict
    ) -> None:
        SajBaseEntity.__init__(self, hub, device_info)
        self._key = description["key"]
        self._attr_name = description["name"]
        self._attr_unique_id = f"{hub.name}_{description['key']}"
        self._attr_icon = description["icon"]

    async def async_press(self) -> None:
        if self._key == "ev_start_charging":
            await self._hub.start_ev_charging()
        elif self._key == "ev_stop_charging":
            await self._hub.stop_ev_charging()
