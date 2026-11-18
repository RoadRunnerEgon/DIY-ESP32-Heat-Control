"""Binary sensor platform for the DIY Heat Control integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DiyHeatControlCoordinator
from .entity import DiyHeatControlEntity


@dataclass(frozen=True, kw_only=True)
class DiyBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a status bit of the ESP."""

    data_key: str
    unique_suffix: str


BINARY_SENSORS: tuple[DiyBinarySensorDescription, ...] = (
    # Sammelalarm (Übertemperatur ODER Fühlerfehler) – unique_id wie bisher
    DiyBinarySensorDescription(
        key="alarm",
        translation_key="alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        data_key="is_alarm",
        unique_suffix="alarm",
    ),
    DiyBinarySensorDescription(
        key="overtemperature",
        translation_key="overtemperature",
        device_class=BinarySensorDeviceClass.HEAT,
        data_key="is_overtemp",
        unique_suffix="overtemperature",
    ),
    DiyBinarySensorDescription(
        key="sensor_fault",
        translation_key="sensor_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        data_key="is_sensor_fault",
        unique_suffix="sensor_fault",
    ),
    DiyBinarySensorDescription(
        key="valve_moving",
        translation_key="valve_moving",
        device_class=BinarySensorDeviceClass.MOVING,
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key="is_moving",
        unique_suffix="valve_moving",
    ),
    DiyBinarySensorDescription(
        key="homed",
        translation_key="homed",
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key="is_homed",
        unique_suffix="homed",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor entities from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    async_add_entities(
        DiyStatusBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class DiyStatusBinarySensor(DiyHeatControlEntity, BinarySensorEntity):
    """A single status bit from the ESP."""

    entity_description: DiyBinarySensorDescription

    def __init__(
        self,
        coordinator: DiyHeatControlCoordinator,
        entry: ConfigEntry,
        description: DiyBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.unique_suffix}"

    @property
    def is_on(self) -> bool | None:
        return (self.coordinator.data or {}).get(self.entity_description.data_key)
