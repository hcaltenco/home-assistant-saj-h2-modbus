"""SAJ H2 Modbus select entities."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity import SajBaseEntity
from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)

EV_STRATEGY_OPTIONS = {
    "Off": 0,
    "Standard": 1,
    "Scheduled": 2,
    "Surplus Solar": 3,
}
EV_STRATEGY_REVERSE = {v: k for k, v in EV_STRATEGY_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SAJ select entities."""
    hub: SAJModbusHub = entry.runtime_data
    device_info = hub.device_info
    async_add_entities([EvChargeStrategySelect(hub, device_info)])


class EvChargeStrategySelect(CoordinatorEntity, SelectEntity, SajBaseEntity):
    """Select entity for EV charger charge strategy (0x4B12)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_name = "EV Charge Strategy"
    _attr_icon = "mdi:ev-station"

    def __init__(self, hub: SAJModbusHub, device_info: dict) -> None:
        super().__init__(hub)
        SajBaseEntity.__init__(self, hub, device_info)
        self._attr_unique_id = f"{hub.name}_ev_charge_strategy_select"
        self._attr_options = list(EV_STRATEGY_OPTIONS.keys())

    @property
    def current_option(self) -> str | None:
        raw = self._hub.inverter_data.get("ev_charge_strategy")
        if raw is not None:
            return EV_STRATEGY_REVERSE.get(raw)
        return None

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self._hub.inverter_data.get("ev_charge_strategy") is not None
        )

    async def async_select_option(self, option: str) -> None:
        value = EV_STRATEGY_OPTIONS.get(option)
        if value is None:
            _LOGGER.error("Invalid EV charge strategy option: %s", option)
            return
        await self._hub.set_ev_charge_strategy(value)
