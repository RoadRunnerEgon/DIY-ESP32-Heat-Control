"""Climate platform for the DIY Heat Control integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    """Set up the climate entity from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    async_add_entities([DiyHeatControlClimate(coordinator, entry)])


class DiyHeatControlClimate(
    CoordinatorEntity[DiyHeatControlCoordinator], ClimateEntity
):
    """Representation of the DIY Heat Control thermostat."""

    _attr_has_entity_name = True
    _attr_name = None  # Use the device name as the entity name
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = 0.1
    _attr_min_temp = 5.0
    _attr_max_temp = 35.0

    def __init__(
        self,
        coordinator: DiyHeatControlCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="DIY",
            model="ESP32 Heat Control",
        )

    @property
    def native_current_temperature(self) -> float | None:
        """Return the current (flow) temperature."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("flow_temp")

    @property
    def native_target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("target_temp")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self.coordinator.data and self.coordinator.data.get("switch_on"):
            return HVACMode.HEAT
        return HVACMode.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        if (temp := kwargs.get("temperature")) is not None:
            # Scale float to uint16 with one decimal place
            raw_value = int(round(temp * 10))
            await self.coordinator.async_write_target_temp(raw_value)
            # Optimistically update the state until the next notification arrives
            if self.coordinator.data is not None:
                self.coordinator.data["target_temp"] = temp
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode (on/off)."""
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.async_write_switch(True)
        elif hvac_mode == HVACMode.OFF:
            await self.coordinator.async_write_switch(False)
        if self.coordinator.data is not None:
            self.coordinator.data["switch_on"] = hvac_mode == HVACMode.HEAT
        self.async_write_ha_state()
