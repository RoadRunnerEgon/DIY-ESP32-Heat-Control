"""Switch platform for the DIY Heat Control integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DiyHeatControlCoordinator
from .entity import DiyHeatControlEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch entity from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    async_add_entities([HeatControlSwitch(coordinator, entry)])


class HeatControlSwitch(DiyHeatControlEntity, SwitchEntity):
    """Heizung ein/aus (gleichbedeutend mit HEAT/OFF am Climate)."""

    _attr_translation_key = "heat_control"

    def __init__(self, coordinator: DiyHeatControlCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_switch"

    @property
    def is_on(self) -> bool | None:
        return (self.coordinator.data or {}).get("switch_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_switch(False)
