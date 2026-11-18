"""Climate platform for the DIY Heat Control integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MAX_TARGET_TEMP, MIN_TARGET_TEMP
from .coordinator import DiyHeatControlCoordinator
from .entity import DiyHeatControlEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the climate entity from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    async_add_entities([DiyHeatControlClimate(coordinator, entry)])


class DiyHeatControlClimate(DiyHeatControlEntity, ClimateEntity):
    """Vorlauf-Regler: Ist = Vorlauftemperatur, Soll = Vorlauf-Sollwert."""

    _attr_name = None  # Gerätename als Entitätsname
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 0.1
    _attr_min_temp = MIN_TARGET_TEMP
    _attr_max_temp = MAX_TARGET_TEMP

    def __init__(self, coordinator: DiyHeatControlCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_climate"

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    @property
    def current_temperature(self) -> float | None:
        return self._data.get("flow_temp")

    @property
    def target_temperature(self) -> float | None:
        return self._data.get("target_temp")

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT if self._data.get("switch_on") else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        if not self._data:
            return None
        if not self._data.get("switch_on"):
            return HVACAction.OFF
        if self._data.get("is_alarm"):
            return HVACAction.IDLE
        return HVACAction.HEATING

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "supply_temperature": self._data.get("supply_temp"),
            "return_temperature": self._data.get("return_temp"),
            "status_raw": self._data.get("status"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        temp = min(max(float(temp), MIN_TARGET_TEMP), MAX_TARGET_TEMP)
        await self.coordinator.async_write_target_temp(int(round(temp * 10)))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.coordinator.async_write_switch(hvac_mode == HVACMode.HEAT)

    async def async_turn_on(self) -> None:
        await self.coordinator.async_write_switch(True)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_write_switch(False)
