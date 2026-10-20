"""Binary sensor platform for the DIY Heat Control integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the binary sensor entity from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    async_add_entities([AlarmBinarySensor(coordinator, entry)])


class AlarmBinarySensor(
    CoordinatorEntity[DiyHeatControlCoordinator], BinarySensorEntity
):
    """Representation of the alarm/status binary sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "alarm"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: DiyHeatControlCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_alarm"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="DIY",
            model="ESP32 Heat Control",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the alarm is active."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("is_alarm")