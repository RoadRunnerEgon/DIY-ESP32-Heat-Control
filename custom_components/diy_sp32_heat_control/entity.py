"""Common base entity for the DIY Heat Control integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DiyHeatControlCoordinator


class DiyHeatControlEntity(CoordinatorEntity[DiyHeatControlCoordinator]):
    """Base entity: shared device info and availability."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DiyHeatControlCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="DIY",
            model="ESP32 Heat Control",
        )

    @property
    def available(self) -> bool:
        """Only available once the device has sent data."""
        return super().available and bool(self.coordinator.data)
