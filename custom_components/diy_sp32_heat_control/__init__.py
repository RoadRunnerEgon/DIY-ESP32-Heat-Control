"""The DIY Valve Control integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import DiyHeatControlCoordinator

_LOGGER = logging.getLogger(__name__)

# Alle Plattformen, die deine Integration bereitstellt
_PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]

# Typ-Alias für den Config Entry mit dem Coordinator als runtime_data
type DiyValveControlConfigEntry = ConfigEntry[DiyHeatControlCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DIY Heat Control from a config entry."""
    address = entry.unique_id
    if address is None:
        return False

    coordinator = DiyHeatControlCoordinator(hass, address)
    entry.runtime_data = coordinator

    # Ersten Datenabruf auslösen (verbindet sich mit dem Gerät)
    await coordinator.async_config_entry_first_refresh()

    # Plattformen laden
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True

async def async_unload_entry(
    hass: HomeAssistant, entry: DiyValveControlConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
