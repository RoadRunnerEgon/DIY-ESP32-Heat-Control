"""Sensor platform for the DIY Heat Control integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    """Set up the sensor entities from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    async_add_entities(
        [
            FlowTemperatureSensor(coordinator, entry),
            ReturnTemperatureSensor(coordinator, entry),
        ]
    )


class _BaseTemperatureSensor(
    CoordinatorEntity[DiyHeatControlCoordinator], SensorEntity
):
    """Base class for the temperature sensors."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    _data_key: str
    _attr_translation_key: str

    def __init__(
        self,
        coordinator: DiyHeatControlCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_{self._attr_translation_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="DIY",
            model="ESP32 Heat Control",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)


class FlowTemperatureSensor(_BaseTemperatureSensor):
    """Sensor for the flow (Vorlauf) temperature."""

    _data_key = "flow_temp"
    _attr_translation_key = "flow_temperature"


class ReturnTemperatureSensor(_BaseTemperatureSensor):
    """Sensor for the return (Rücklauf) temperature."""

    _data_key = "return_temp"
    _attr_translation_key = "return_temperature"