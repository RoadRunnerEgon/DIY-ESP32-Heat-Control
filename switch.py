"""Switch platform for the DIY Heat Control integration."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DiyHeatControlCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch entity from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    async_add_entities([HeatControlSwitch(coordinator, entry)])


class HeatControlSwitch(CoordinatorEntity[DiyHeatControlCoordinator], SwitchEntity):
    """Representation of the heat control switch."""

    _attr_has_entity_name = True
    _attr_translation_key = "heat_control"

    def __init__(
        self,
        coordinator: DiyHeatControlCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="DIY",
            model="ESP32 Heat Control",
        )

    @property
    def is_on(self) -> bool | None:
        """Return the current switch state."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("switch_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_write_switch(True)
        if self.coordinator.data is not None:
            self.coordinator.data["switch_on"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_write_switch(False)
        if self.coordinator.data is not None:
            self.coordinator.data["switch_on"] = False
        self.async_write_ha_state()
