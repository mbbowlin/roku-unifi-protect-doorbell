"""Config flow for UniFi Roku Bridge."""

from __future__ import annotations

from typing import Any
import secrets

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback

from .const import (
    ACCESS_TOKEN,
    CONF_ENABLE_SRTP,
    CONF_FFMPEG_BIN,
    CONF_H264_LEVEL,
    CONF_IDLE_TIMEOUT,
    CONF_KEEP_AUDIO,
    CONF_LIST_SIZE,
    CONF_MAX_HEIGHT,
    CONF_MAX_WIDTH,
    CONF_PLAYLIST_WAIT_MS,
    CONF_RTSP_TRANSPORT,
    CONF_SEGMENT_SECONDS,
    CONF_STREAM_TOKEN,
    CONF_TLS_VERIFY,
    CONF_TRANSCODE,
    CONF_X264_PRESET,
    DEFAULT_ENABLE_SRTP,
    DEFAULT_FFMPEG_BIN,
    DEFAULT_H264_LEVEL,
    DEFAULT_IDLE_TIMEOUT,
    DEFAULT_KEEP_AUDIO,
    DEFAULT_LIST_SIZE,
    DEFAULT_MAX_HEIGHT,
    DEFAULT_MAX_WIDTH,
    DEFAULT_PLAYLIST_WAIT_MS,
    DEFAULT_PORT,
    DEFAULT_RTSP_TRANSPORT,
    DEFAULT_SEGMENT_SECONDS,
    DEFAULT_TLS_VERIFY,
    DEFAULT_TRANSCODE,
    DEFAULT_X264_PRESET,
    DOMAIN,
)


class UnifiRokuBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi Roku Bridge."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_HOST].strip():
                errors[CONF_HOST] = "required"
            if not user_input[CONF_STREAM_TOKEN].strip():
                errors[CONF_STREAM_TOKEN] = "required"

            if not errors:
                title = user_input.get(CONF_NAME) or "UniFi Roku Bridge"
                data = {
                    CONF_NAME: title,
                    CONF_HOST: user_input[CONF_HOST].strip(),
                    CONF_PORT: int(user_input[CONF_PORT]),
                    CONF_STREAM_TOKEN: user_input[CONF_STREAM_TOKEN].strip(),
                    CONF_ENABLE_SRTP: bool(user_input[CONF_ENABLE_SRTP]),
                    ACCESS_TOKEN: secrets.token_urlsafe(18),
                }
                options = _default_options()
                return self.async_create_entry(title=title, data=data, options=options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default="UniFi Roku Bridge"): str,
                    vol.Required(CONF_HOST, default="192.168.10.1"): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_STREAM_TOKEN): str,
                    vol.Required(CONF_ENABLE_SRTP, default=DEFAULT_ENABLE_SRTP): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UnifiRokuBridgeOptionsFlow:
        """Create the options flow."""
        return UnifiRokuBridgeOptionsFlow(config_entry)


class UnifiRokuBridgeOptionsFlow(config_entries.OptionsFlow):
    """Handle UniFi Roku Bridge options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage bridge options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {**_default_options(), **self._config_entry.options}
        host = options.get(CONF_HOST) or self._config_entry.data.get(
            CONF_HOST, "192.168.10.1"
        )
        port = options.get(CONF_PORT) or self._config_entry.data.get(
            CONF_PORT, DEFAULT_PORT
        )
        stream_token = options.get(CONF_STREAM_TOKEN) or self._config_entry.data.get(
            CONF_STREAM_TOKEN, ""
        )
        enable_srtp = options.get(
            CONF_ENABLE_SRTP,
            self._config_entry.data.get(CONF_ENABLE_SRTP, DEFAULT_ENABLE_SRTP),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=host): str,
                    vol.Required(CONF_PORT, default=port): int,
                    vol.Required(CONF_STREAM_TOKEN, default=stream_token): str,
                    vol.Required(CONF_ENABLE_SRTP, default=enable_srtp): bool,
                    vol.Required(
                        CONF_FFMPEG_BIN, default=options[CONF_FFMPEG_BIN]
                    ): str,
                    vol.Required(
                        CONF_TRANSCODE, default=options[CONF_TRANSCODE]
                    ): bool,
                    vol.Required(
                        CONF_KEEP_AUDIO, default=options[CONF_KEEP_AUDIO]
                    ): bool,
                    vol.Required(
                        CONF_SEGMENT_SECONDS, default=options[CONF_SEGMENT_SECONDS]
                    ): int,
                    vol.Required(CONF_LIST_SIZE, default=options[CONF_LIST_SIZE]): int,
                    vol.Required(CONF_MAX_WIDTH, default=options[CONF_MAX_WIDTH]): int,
                    vol.Required(CONF_MAX_HEIGHT, default=options[CONF_MAX_HEIGHT]): int,
                    vol.Required(
                        CONF_RTSP_TRANSPORT, default=options[CONF_RTSP_TRANSPORT]
                    ): vol.In(["tcp", "udp"]),
                    vol.Required(CONF_TLS_VERIFY, default=options[CONF_TLS_VERIFY]): bool,
                    vol.Required(
                        CONF_X264_PRESET, default=options[CONF_X264_PRESET]
                    ): vol.In(
                        [
                            "ultrafast",
                            "superfast",
                            "veryfast",
                            "faster",
                            "fast",
                            "medium",
                        ]
                    ),
                    vol.Required(CONF_H264_LEVEL, default=options[CONF_H264_LEVEL]): str,
                    vol.Required(
                        CONF_PLAYLIST_WAIT_MS, default=options[CONF_PLAYLIST_WAIT_MS]
                    ): int,
                    vol.Required(
                        CONF_IDLE_TIMEOUT, default=options[CONF_IDLE_TIMEOUT]
                    ): int,
                }
            ),
        )


def _default_options() -> dict[str, Any]:
    """Return default bridge options."""
    return {
        CONF_FFMPEG_BIN: DEFAULT_FFMPEG_BIN,
        CONF_TRANSCODE: DEFAULT_TRANSCODE,
        CONF_KEEP_AUDIO: DEFAULT_KEEP_AUDIO,
        CONF_SEGMENT_SECONDS: DEFAULT_SEGMENT_SECONDS,
        CONF_LIST_SIZE: DEFAULT_LIST_SIZE,
        CONF_MAX_WIDTH: DEFAULT_MAX_WIDTH,
        CONF_MAX_HEIGHT: DEFAULT_MAX_HEIGHT,
        CONF_RTSP_TRANSPORT: DEFAULT_RTSP_TRANSPORT,
        CONF_TLS_VERIFY: DEFAULT_TLS_VERIFY,
        CONF_X264_PRESET: DEFAULT_X264_PRESET,
        CONF_H264_LEVEL: DEFAULT_H264_LEVEL,
        CONF_PLAYLIST_WAIT_MS: DEFAULT_PLAYLIST_WAIT_MS,
        CONF_IDLE_TIMEOUT: DEFAULT_IDLE_TIMEOUT,
    }
