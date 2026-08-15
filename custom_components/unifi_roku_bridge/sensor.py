"""Diagnostic sensor for UniFi Roku Bridge."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.typing import StateType

from .bridge import UnifiRokuBridge
from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up UniFi Roku Bridge sensor."""
    bridge: UnifiRokuBridge = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([UnifiRokuBridgeSensor(hass, bridge, entry)])


class UnifiRokuBridgeSensor(SensorEntity):
    """Expose bridge status and URLs."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:cctv"
    _attr_name = "Bridge"

    def __init__(
        self, hass: HomeAssistant, bridge: UnifiRokuBridge, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.bridge = bridge
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_bridge"

    @property
    def native_value(self) -> StateType:
        """Return bridge state."""
        if self.bridge.last_error:
            return "error"
        if self.bridge.process is not None:
            return "running"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        hls_url = self._absolute_url(self.bridge.hls_path)
        health_path = self.bridge.hls_path.replace("stream.m3u8", "health")

        return {
            "hls_url": hls_url,
            "hls_path": self.bridge.hls_path,
            "short_hls_url": self._absolute_url(self.bridge.short_hls_path),
            "short_hls_path": self.bridge.short_hls_path,
            "health_url": self._absolute_url(health_path),
            "health_path": health_path,
            "unifi_host": self.bridge.settings.host,
            "unifi_port": self.bridge.settings.port,
            "transcode": self.bridge.settings.transcode,
            "keep_audio": self.bridge.settings.keep_audio,
            "max_width": self.bridge.settings.max_width,
            "max_height": self.bridge.settings.max_height,
            "ffmpeg_bin": self.bridge.settings.ffmpeg_bin,
            "ffmpeg_started_at": self.bridge.started_at.isoformat()
            if self.bridge.started_at
            else None,
            "last_request_at": self.bridge.last_request_at.isoformat()
            if self.bridge.last_request_at
            else None,
            "last_exit": self.bridge.last_exit,
            "last_error": self.bridge.last_error,
            "output_dir": str(self.bridge.output_dir),
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": self.entry.title,
            "manufacturer": "Local",
            "model": "RTSPS to HLS Bridge",
            "configuration_url": self._absolute_url(self.bridge.hls_path),
        }

    def _absolute_url(self, path: str) -> str | None:
        try:
            base_url = get_url(self.hass, allow_cloud=False)
        except NoURLAvailableError:
            return None

        return f"{base_url.rstrip('/')}{path}"
