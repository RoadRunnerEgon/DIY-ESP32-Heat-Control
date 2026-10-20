"""Coordinator for the DIY Heat Control integration."""

from __future__ import annotations

import logging
import struct
from datetime import timedelta
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError

from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

# UUIDs aus der ESPHome-YAML – bitte anpassen!
WRITE_UUID = "E9E76F0C-E3E7-40A7-9976-2C921750DEEC"
NOTIFY_UUID = "D50D1277-8781-47ED-91D5-5D9F2FF91FF0"


def parse_notification(data: bytearray) -> dict[str, Any]:
    """Parse the 6 bytes of the notify characteristic."""
    if len(data) < 6:
        return {}
    flow_raw, return_raw, status, switch_state = struct.unpack("<HHBB", data[:6])
    return {
        "flow_temp": flow_raw / 10.0,
        "return_temp": return_raw / 10.0,
        "is_alarm": bool(status),
        "switch_on": bool(switch_state),
    }


class DiyHeatControlCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for the DIY Heat Control device."""

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

    async def _async_update_data(self) -> dict[str, Any]:
        """Connect to the device and subscribe to notifications."""
        if self._client is not None and self._client.is_connected:
            return self.data or {}

        device = async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )
        if device is None:
            raise UpdateFailed(f"Could not find BLE device {self._address}")

        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                self._address,  # Name für Logs
                max_attempts=3,
                )
            _LOGGER.debug("Connected to %s", self._address)
            await self._client.start_notify(NOTIFY_UUID, self._notification_handler)
            return self.data or {}
        except BleakError as err:
            self._client = None
            raise UpdateFailed(f"BLE connection failed: {err}") from err

    @callback
    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle incoming notifications."""
        parsed = parse_notification(data)
        if parsed:
            _LOGGER.debug("Received notification: %s", parsed)
            self.async_set_updated_data(parsed)

    async def async_write_target_temp(self, raw_value: int) -> None:
        """Write the target temperature (scaled uint16) to the device."""
        if self._client is None or not self._client.is_connected:
            _LOGGER.warning("Not connected, cannot write target temp")
            return
        payload = struct.pack("<H", raw_value)
        await self._client.write_gatt_char(WRITE_UUID, payload, response=False)
        _LOGGER.debug("Wrote target temp raw value: %s", raw_value)

    async def async_write_switch(self, state: bool) -> None:
        """Write the switch state to the device."""
        if self._client is None or not self._client.is_connected:
            _LOGGER.warning("Not connected, cannot write switch state")
            return
        payload = struct.pack("<B", 1 if state else 0)
        await self._client.write_gatt_char(WRITE_UUID, payload, response=False)
        _LOGGER.debug("Wrote switch state: %s", state)