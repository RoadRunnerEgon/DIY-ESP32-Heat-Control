"""Coordinator for the DIY Heat Control integration."""

from __future__ import annotations

import logging
import struct
from datetime import timedelta
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CIRCUIT_COUNT,
    CIRCUIT_INVALID,
    CIRCUIT_NOTIFY_UUID,
    NOTIFY_UUID,
    STATUS_HOMED,
    STATUS_MOVING,
    STATUS_OVERTEMP,
    STATUS_SENSOR_FAULT,
    WRITE_UUID,
)

_LOGGER = logging.getLogger(__name__)


def _temp(raw: int) -> float | None:
    """Convert a raw value (°C * 10) to °C. 0 means 'invalid / not connected'."""
    if raw == 0:
        return None
    return raw / 10.0


def parse_notification(data: bytearray) -> dict[str, Any]:
    """Parse the notify characteristic.

    Layout (little endian):
      [0..1] Vorlauf*10   [2..3] Rücklauf*10   [4] Status-Bits
      [5]    Schalter     [6..7] Sollwert*10
      [8..9] Zulauf*10    (optional, nur neuere Firmware)
    """
    if len(data) < 8:
        _LOGGER.debug("Notification too short (%d bytes): %s", len(data), bytes(data).hex())
        return {}

    flow_raw, return_raw, status, switch_state, target_raw = struct.unpack_from(
        "<HHBBH", data, 0
    )
    parsed: dict[str, Any] = {
        "flow_temp": _temp(flow_raw),
        "return_temp": _temp(return_raw),
        "status": status,
        "is_moving": bool(status & STATUS_MOVING),
        "is_overtemp": bool(status & STATUS_OVERTEMP),
        "is_sensor_fault": bool(status & STATUS_SENSOR_FAULT),
        "is_homed": bool(status & STATUS_HOMED),
        # Alarm = echte Fehler, NICHT "fährt" oder "referenziert"
        "is_alarm": bool(status & (STATUS_OVERTEMP | STATUS_SENSOR_FAULT)),
        "switch_on": bool(switch_state),
        "target_temp": target_raw / 10.0,
        "target_raw": target_raw,
        "supply_temp": None,
    }
    if len(data) >= 10:
        (supply_raw,) = struct.unpack_from("<H", data, 8)
        parsed["supply_temp"] = _temp(supply_raw)
    return parsed


def parse_circuit_notification(data: bytearray) -> list[float | None]:
    """Parse the circuit characteristic: 10 x int16 (°C*10), 0x8000 = kein Wert.

    Slot 1 = Kreis 1 Vorlauf, Slot 2 = Kreis 1 Rücklauf, ... Slot 10 = Kreis 5 Rücklauf
    """
    count = min(len(data) // 2, CIRCUIT_COUNT * 2)
    values = struct.unpack_from(f"<{count}h", data, 0) if count else ()
    temps: list[float | None] = [None if v == CIRCUIT_INVALID else v / 10.0 for v in values]
    temps += [None] * (CIRCUIT_COUNT * 2 - len(temps))
    return temps


class DiyHeatControlCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for the DIY Heat Control device.

    Die Daten kommen per BLE-Notify (Push). Der 60-s-Zyklus dient nur dazu,
    eine abgerissene Verbindung wieder aufzubauen.
    """

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="DIY Heat Control",
            update_interval=timedelta(seconds=60),
        )
        self._address = address
        self._client: BleakClient | None = None
        # Zustand des ESP – wird NUR aus dessen Notify übernommen.
        # None = noch nichts empfangen (dann wird nichts geschrieben, damit
        # HA nach einem Neustart nicht versehentlich Default-Werte zum ESP schickt).
        self._esp_switch: bool | None = None
        self._esp_target_raw: int | None = None
        # Die beiden Notifies kommen getrennt; zusammengeführt in self.data
        self._main: dict[str, Any] = {}
        self._circuits: list[float | None] = [None] * (CIRCUIT_COUNT * 2)

    # ------------------------------------------------------------------ #
    # Verbindung
    # ------------------------------------------------------------------ #
    async def _async_update_data(self) -> dict[str, Any]:
        """Ensure we are connected and subscribed to notifications."""
        if self._client is not None and self._client.is_connected:
            return self.data or {}

        device = async_ble_device_from_address(self.hass, self._address, connectable=True)
        if device is None:
            raise UpdateFailed(f"Could not find BLE device {self._address}")

        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                self._address,
                disconnected_callback=self._on_disconnect,
                max_attempts=3,
            )
            _LOGGER.debug("Connected to %s", self._address)
            await self._client.start_notify(NOTIFY_UUID, self._notification_handler)
            # Heizkreis-Fühler: gibt es erst ab neuerer Firmware -> Fehler tolerieren
            try:
                await self._client.start_notify(
                    CIRCUIT_NOTIFY_UUID, self._circuit_notification_handler
                )
            except (BleakError, ValueError) as err:
                _LOGGER.info("Heizkreis-Fühler nicht verfügbar (ältere Firmware?): %s", err)
        except BleakError as err:
            self._client = None
            raise UpdateFailed(f"BLE connection failed: {err}") from err

        return self.data or {}

    @callback
    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle an unexpected disconnect: reconnect as soon as possible."""
        _LOGGER.debug("Disconnected from %s", self._address)
        self._client = None
        self.hass.async_create_task(self.async_request_refresh())

    async def async_disconnect(self) -> None:
        """Disconnect (used when the config entry is unloaded)."""
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            try:
                await client.disconnect()
            except BleakError as err:
                _LOGGER.debug("Error while disconnecting: %s", err)

    # ------------------------------------------------------------------ #
    # Empfangen
    # ------------------------------------------------------------------ #
    @callback
    def _notification_handler(self, sender: Any, data: bytearray) -> None:
        """Handle incoming notifications."""
        parsed = parse_notification(data)
        if not parsed:
            return
        # Den Zustand des ESP als Wahrheit übernehmen
        self._esp_switch = parsed["switch_on"]
        self._esp_target_raw = parsed["target_raw"]
        _LOGGER.debug("Received notification: %s", parsed)
        self._main = parsed
        self._publish()

    @callback
    def _circuit_notification_handler(self, sender: Any, data: bytearray) -> None:
        """Handle the circuit sensor notification."""
        self._circuits = parse_circuit_notification(data)
        _LOGGER.debug("Received circuit notification: %s", self._circuits)
        if self._main:  # erst anzeigen, wenn auch das Hauptpaket da ist
            self._publish()

    @callback
    def _publish(self) -> None:
        self.async_set_updated_data({**self._main, "circuit_temps": list(self._circuits)})

    # ------------------------------------------------------------------ #
    # Schreiben
    # ------------------------------------------------------------------ #
    async def _async_write(self, switch_on: bool, target_raw: int) -> None:
        """Send [Schalter, Sollwert_L, Sollwert_H] to the device."""
        if self._client is None or not self._client.is_connected:
            raise HomeAssistantError("DIY Heat Control: keine Verbindung zum Gerät")
        payload = bytes([1 if switch_on else 0, target_raw & 0xFF, (target_raw >> 8) & 0xFF])
        try:
            await self._client.write_gatt_char(WRITE_UUID, payload, response=False)
        except BleakError as err:
            raise HomeAssistantError(f"DIY Heat Control: Schreiben fehlgeschlagen: {err}") from err
        _LOGGER.debug("Wrote payload %s", payload.hex())

        self._esp_switch = switch_on
        self._esp_target_raw = target_raw
        # Sofort in der UI anzeigen; der ESP bestätigt per Notify.
        if self._main:
            self._main = {
                **self._main,
                "switch_on": switch_on,
                "target_raw": target_raw,
                "target_temp": target_raw / 10.0,
            }
            self._publish()

    def _require_esp_state(self) -> tuple[bool, int]:
        if self._esp_switch is None or self._esp_target_raw is None:
            raise HomeAssistantError(
                "DIY Heat Control: noch keine Daten vom Gerät empfangen – bitte kurz warten"
            )
        return self._esp_switch, self._esp_target_raw

    async def async_write_target_temp(self, raw_value: int) -> None:
        """Write a new target temperature (°C * 10), keep the switch state."""
        switch_on, _ = self._require_esp_state()
        await self._async_write(switch_on, raw_value)

    async def async_write_switch(self, state: bool) -> None:
        """Write the switch state, keep the target temperature."""
        _, target_raw = self._require_esp_state()
        await self._async_write(state, target_raw)
