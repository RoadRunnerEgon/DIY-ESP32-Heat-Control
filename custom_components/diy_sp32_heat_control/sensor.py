"""Sensor platform for the DIY Heat Control integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CIRCUIT_COUNT
from .coordinator import DiyHeatControlCoordinator
from .entity import DiyHeatControlEntity

# (translation_key, Schlüssel im Coordinator-Datensatz)
# Die translation_keys der ersten beiden bleiben unverändert -> bestehende
# Entitäten (unique_id) und ihre Historie bleiben erhalten.
TEMPERATURE_SENSORS: tuple[tuple[str, str], ...] = (
    ("flow_temperature", "flow_temp"),
    ("return_temperature", "return_temp"),
    ("supply_temperature", "supply_temp"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor entities from a config entry."""
    coordinator: DiyHeatControlCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        TemperatureSensor(coordinator, entry, key, data_key)
        for key, data_key in TEMPERATURE_SENSORS
    ]
    for circuit in range(1, CIRCUIT_COUNT + 1):
        entities.append(CircuitTemperatureSensor(coordinator, entry, circuit, is_return=False))
        entities.append(CircuitTemperatureSensor(coordinator, entry, circuit, is_return=True))
        entities.append(CircuitSpreadSensor(coordinator, entry, circuit))
    async_add_entities(entities)


class TemperatureSensor(DiyHeatControlEntity, SensorEntity):
    """A temperature reported by the ESP (Vorlauf, Rücklauf, Zulauf)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: DiyHeatControlCoordinator,
        entry: ConfigEntry,
        translation_key: str,
        data_key: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.unique_id}_{translation_key}"
        self._data_key = data_key

    @property
    def native_value(self) -> float | None:
        """Return the temperature (None = Fühler ungültig/nicht angeschlossen)."""
        return (self.coordinator.data or {}).get(self._data_key)


def _circuit_values(coordinator: DiyHeatControlCoordinator, circuit: int) -> tuple[float | None, float | None]:
    """Return (Vorlauf, Rücklauf) of a circuit (1-based). Slot 2n-1 = Vorlauf, 2n = Rücklauf."""
    temps = (coordinator.data or {}).get("circuit_temps") or []
    i = (circuit - 1) * 2
    flow = temps[i] if i < len(temps) else None
    ret = temps[i + 1] if i + 1 < len(temps) else None
    return flow, ret


class CircuitTemperatureSensor(DiyHeatControlEntity, SensorEntity):
    """Vorlauf- oder Rücklauftemperatur eines einzelnen Heizkreises (DS18B20)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: DiyHeatControlCoordinator,
        entry: ConfigEntry,
        circuit: int,
        is_return: bool,
    ) -> None:
        super().__init__(coordinator, entry)
        kind = "return" if is_return else "flow"
        self._circuit = circuit
        self._is_return = is_return
        self._attr_translation_key = f"circuit_{kind}"
        self._attr_translation_placeholders = {"circuit": str(circuit)}
        self._attr_unique_id = f"{entry.unique_id}_circuit_{circuit}_{kind}"

    @property
    def native_value(self) -> float | None:
        flow, ret = _circuit_values(self.coordinator, self._circuit)
        return ret if self._is_return else flow


class CircuitSpreadSensor(DiyHeatControlEntity, SensorEntity):
    """Spreizung (Vorlauf − Rücklauf) eines Heizkreises in Kelvin."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "K"
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:thermometer-lines"

    def __init__(
        self, coordinator: DiyHeatControlCoordinator, entry: ConfigEntry, circuit: int
    ) -> None:
        super().__init__(coordinator, entry)
        self._circuit = circuit
        self._attr_translation_key = "circuit_spread"
        self._attr_translation_placeholders = {"circuit": str(circuit)}
        self._attr_unique_id = f"{entry.unique_id}_circuit_{circuit}_spread"

    @property
    def native_value(self) -> float | None:
        flow, ret = _circuit_values(self.coordinator, self._circuit)
        if flow is None or ret is None:
            return None
        return round(flow - ret, 2)
