"""UniFi Protect RTSPS to Roku HLS bridge."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .bridge import BridgeView, ShortBridgeView, UnifiRokuBridge
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UniFi Roku Bridge from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.data[DOMAIN].get("view_registered"):
        hass.http.register_view(BridgeView(hass))
        hass.http.register_view(ShortBridgeView(hass))
        hass.data[DOMAIN]["view_registered"] = True

    bridge = UnifiRokuBridge(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = bridge

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a UniFi Roku Bridge config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    bridge: UnifiRokuBridge | None = hass.data[DOMAIN].pop(entry.entry_id, None)
    if bridge is not None:
        await bridge.async_stop()

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the bridge when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
