"""Managed ffmpeg bridge and HTTP views for UniFi Roku Bridge."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import secrets
import subprocess
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLE_SRTP,
    ACCESS_TOKEN,
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

_LOGGER = logging.getLogger(__name__)
SEGMENT_RE = re.compile(r"^segment_\d+\.ts$")


@dataclass(frozen=True)
class BridgeSettings:
    """Runtime settings for one bridge instance."""

    name: str
    host: str
    port: int
    stream_token: str
    enable_srtp: bool
    ffmpeg_bin: str
    transcode: bool
    keep_audio: bool
    segment_seconds: int
    list_size: int
    max_width: int
    max_height: int
    rtsp_transport: str
    tls_verify: bool
    x264_preset: str
    h264_level: str
    playlist_wait_ms: int
    idle_timeout: int


class UnifiRokuBridge:
    """Run ffmpeg and expose its HLS output."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the bridge."""
        self.hass = hass
        self.entry = entry
        self.settings = self._settings_from_entry(entry)
        self.output_dir = Path(hass.config.path(".unifi_roku_bridge", entry.entry_id))
        self.process: asyncio.subprocess.Process | None = None
        self.stderr_task: asyncio.Task[None] | None = None
        self.exit_task: asyncio.Task[None] | None = None
        self.cleanup_task: asyncio.Task[None] | None = None
        self.started_at: datetime | None = None
        self.last_request_at: datetime | None = None
        self.last_exit: dict[str, Any] | None = None
        self.last_error: dict[str, Any] | None = None

    @property
    def access_token(self) -> str:
        """Return the per-entry path token."""
        token = self.entry.data.get(ACCESS_TOKEN)
        if isinstance(token, str) and token:
            return token
        return self.entry.entry_id

    @property
    def hls_path(self) -> str:
        """Return the relative HLS path served by Home Assistant."""
        return f"/api/{DOMAIN}/{self.entry.entry_id}/{self.access_token}/stream.m3u8"

    @property
    def short_hls_path(self) -> str:
        """Return the short HLS alias path."""
        return f"/api/{DOMAIN}/live.m3u8"

    def status(self) -> dict[str, Any]:
        """Return bridge status data."""
        return {
            "ok": True,
            "name": self.settings.name,
            "hls_path": self.hls_path,
            "short_hls_path": self.short_hls_path,
            "output_dir": str(self.output_dir),
            "ffmpeg_running": self.process is not None,
            "ffmpeg_started_at": self.started_at.isoformat() if self.started_at else None,
            "last_request_at": self.last_request_at.isoformat()
            if self.last_request_at
            else None,
            "last_exit": self.last_exit,
            "last_error": self.last_error,
        }

    async def async_stop(self) -> None:
        """Stop ffmpeg and background tasks."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            self.cleanup_task = None

        await self._stop_process()

    async def async_serve(self, filename: str) -> web.StreamResponse:
        """Serve a playlist, segment, or health response."""
        self.last_request_at = datetime.now(timezone.utc)

        if filename == "health":
            return self._json_response(self.status())

        if filename == "stream.m3u8":
            await self._start_process()
            return await self._serve_playlist()

        if SEGMENT_RE.match(filename):
            return self._file_response(filename, "video/mp2t")

        return self._json_response({"ok": False, "error": "Not found"}, status=404)

    async def _serve_playlist(self) -> web.StreamResponse:
        deadline = self.hass.loop.time() + (self.settings.playlist_wait_ms / 1000)
        playlist = self.output_dir / "stream.m3u8"

        while self.hass.loop.time() < deadline:
            if playlist.exists():
                return self._file_response("stream.m3u8", "application/vnd.apple.mpegurl")
            if self.last_error:
                return self._json_response(
                    {
                        "ok": False,
                        "error": "ffmpeg failed to start",
                        "last_error": self.last_error,
                    },
                    status=503,
                )
            await asyncio.sleep(0.25)

        return self._json_response(
            {
                "ok": False,
                "error": "HLS playlist is not ready yet",
                "ffmpeg_running": self.process is not None,
                "last_exit": self.last_exit,
                "last_error": self.last_error,
            },
            status=503,
        )

    def _file_response(self, filename: str, content_type: str) -> web.StreamResponse:
        file_path = self.output_dir / filename
        if not file_path.exists():
            return web.Response(status=404, text="Not ready\n")

        headers = {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
            "Content-Type": content_type,
        }
        return web.FileResponse(file_path, headers=headers, chunk_size=256 * 1024)

    def _json_response(self, payload: dict[str, Any], status: int = 200) -> web.Response:
        return web.Response(
            text=json.dumps(payload, indent=2),
            status=status,
            content_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    async def _start_process(self) -> None:
        if self.process is not None and self.process.returncode is None:
            return

        await self._stop_process()
        await self.hass.async_add_executor_job(self._prepare_output_dir)

        self.last_exit = None
        self.last_error = None
        self.started_at = datetime.now(timezone.utc)

        try:
            self.process = await asyncio.create_subprocess_exec(
                *self._ffmpeg_args(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as err:
            self.process = None
            self.last_error = {
                "code": "ENOENT",
                "message": str(err),
                "path": self.settings.ffmpeg_bin,
                "at": datetime.now(timezone.utc).isoformat(),
            }
            _LOGGER.error("ffmpeg failed to start: %s", err)
            return
        except OSError as err:
            self.process = None
            self.last_error = {
                "code": getattr(err, "errno", None),
                "message": str(err),
                "path": self.settings.ffmpeg_bin,
                "at": datetime.now(timezone.utc).isoformat(),
            }
            _LOGGER.error("ffmpeg failed to start: %s", err)
            return

        self.stderr_task = self.hass.async_create_task(self._read_stderr())
        self.exit_task = self.hass.async_create_task(self._watch_exit())
        self.cleanup_task = self.hass.async_create_task(self._stop_after_idle())

    async def _stop_process(self) -> None:
        tasks = [self.stderr_task, self.exit_task]
        self.stderr_task = None
        self.exit_task = None

        for task in tasks:
            if task:
                task.cancel()

        if self.process is None:
            return

        process = self.process
        self.process = None

        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=8)
            except TimeoutError:
                process.kill()
                await process.wait()

    async def _read_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return

        while True:
            line = await self.process.stderr.readline()
            if not line:
                return
            _LOGGER.warning("ffmpeg: %s", line.decode(errors="replace").rstrip())

    async def _watch_exit(self) -> None:
        if not self.process:
            return

        process = self.process
        returncode = await process.wait()
        self.last_exit = {
            "code": returncode,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        if self.process is process:
            self.process = None
        _LOGGER.warning("ffmpeg exited with code %s", returncode)

    async def _stop_after_idle(self) -> None:
        while self.process is not None:
            await asyncio.sleep(15)
            if self.last_request_at is None:
                continue
            idle_seconds = datetime.now(timezone.utc) - self.last_request_at
            if idle_seconds.total_seconds() >= self.settings.idle_timeout:
                _LOGGER.info("Stopping ffmpeg after %s idle seconds", self.settings.idle_timeout)
                await self._stop_process()
                return

    def _prepare_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for path in self.output_dir.iterdir():
            if path.suffix in {".m3u8", ".ts"}:
                path.unlink()

    def _ffmpeg_args(self) -> list[str]:
        settings = self.settings
        args = [
            settings.ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-tls_verify",
            "1" if settings.tls_verify else "0",
            "-rtsp_transport",
            settings.rtsp_transport,
            "-i",
            self._rtsps_url(),
        ]

        if settings.transcode:
            args.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    settings.x264_preset,
                    "-tune",
                    "zerolatency",
                    "-profile:v",
                    "high",
                    "-level",
                    settings.h264_level,
                    "-pix_fmt",
                    "yuv420p",
                    "-vf",
                    (
                        f"scale=w=min({settings.max_width}\\,iw):"
                        f"h=min({settings.max_height}\\,ih):"
                        "force_original_aspect_ratio=decrease:force_divisible_by=2"
                    ),
                    "-g",
                    str(settings.segment_seconds * 30),
                    "-sc_threshold",
                    "0",
                    "-force_key_frames",
                    f"expr:gte(t,n_forced*{settings.segment_seconds})",
                ]
            )
        else:
            args.extend(["-c:v", "copy"])

        if settings.keep_audio:
            args.extend(["-c:a", "aac", "-b:a", "96k"])
        else:
            args.append("-an")

        flags = "delete_segments+omit_endlist+program_date_time"
        if settings.transcode:
            flags += "+independent_segments"

        args.extend(
            [
                "-f",
                "hls",
                "-hls_time",
                str(settings.segment_seconds),
                "-hls_list_size",
                str(settings.list_size),
                "-hls_flags",
                flags,
                "-hls_segment_type",
                "mpegts",
                "-hls_segment_filename",
                str(self.output_dir / "segment_%05d.ts"),
                str(self.output_dir / "stream.m3u8"),
            ]
        )
        return args

    def _rtsps_url(self) -> str:
        settings = self.settings
        stream_token = settings.stream_token.strip()

        if stream_token.startswith("rtsps://"):
            return stream_token

        stream_token = stream_token.lstrip("/")
        if "?" in stream_token or not settings.enable_srtp:
            suffix = ""
        else:
            suffix = "?enableSrtp"

        return f"rtsps://{settings.host}:{settings.port}/{stream_token}{suffix}"

    @staticmethod
    def _settings_from_entry(entry: ConfigEntry) -> BridgeSettings:
        data = entry.data
        options = entry.options

        return BridgeSettings(
            name=data.get(CONF_NAME, "UniFi Roku Bridge"),
            host=options.get(CONF_HOST, data.get(CONF_HOST, "192.168.10.1")),
            port=int(options.get(CONF_PORT, data.get(CONF_PORT, DEFAULT_PORT))),
            stream_token=options.get(CONF_STREAM_TOKEN, data.get(CONF_STREAM_TOKEN, "")),
            enable_srtp=bool(
                options.get(CONF_ENABLE_SRTP, data.get(CONF_ENABLE_SRTP, DEFAULT_ENABLE_SRTP))
            ),
            ffmpeg_bin=options.get(CONF_FFMPEG_BIN, DEFAULT_FFMPEG_BIN),
            transcode=bool(options.get(CONF_TRANSCODE, DEFAULT_TRANSCODE)),
            keep_audio=bool(options.get(CONF_KEEP_AUDIO, DEFAULT_KEEP_AUDIO)),
            segment_seconds=int(options.get(CONF_SEGMENT_SECONDS, DEFAULT_SEGMENT_SECONDS)),
            list_size=int(options.get(CONF_LIST_SIZE, DEFAULT_LIST_SIZE)),
            max_width=int(options.get(CONF_MAX_WIDTH, DEFAULT_MAX_WIDTH)),
            max_height=int(options.get(CONF_MAX_HEIGHT, DEFAULT_MAX_HEIGHT)),
            rtsp_transport=options.get(CONF_RTSP_TRANSPORT, DEFAULT_RTSP_TRANSPORT),
            tls_verify=bool(options.get(CONF_TLS_VERIFY, DEFAULT_TLS_VERIFY)),
            x264_preset=options.get(CONF_X264_PRESET, DEFAULT_X264_PRESET),
            h264_level=options.get(CONF_H264_LEVEL, DEFAULT_H264_LEVEL),
            playlist_wait_ms=int(
                options.get(CONF_PLAYLIST_WAIT_MS, DEFAULT_PLAYLIST_WAIT_MS)
            ),
            idle_timeout=int(options.get(CONF_IDLE_TIMEOUT, DEFAULT_IDLE_TIMEOUT)),
        )


class BridgeView(HomeAssistantView):
    """Unauthenticated HLS endpoint for Roku."""

    requires_auth = False
    name = f"api:{DOMAIN}:stream"
    url = f"/api/{DOMAIN}/{{entry_id}}/{{access_token}}/{{filename}}"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(
        self, request: web.Request, entry_id: str, access_token: str, filename: str
    ) -> web.StreamResponse:
        """Handle a Roku HLS request."""
        bridge: UnifiRokuBridge | None = self.hass.data.get(DOMAIN, {}).get(entry_id)

        if bridge is None or not secrets.compare_digest(access_token, bridge.access_token):
            return web.Response(status=404, text="Not found\n")

        return await bridge.async_serve(filename)


class ShortBridgeView(HomeAssistantView):
    """Short unauthenticated HLS endpoint for the first configured bridge."""

    requires_auth = False
    name = f"api:{DOMAIN}:short_stream"
    url = f"/api/{DOMAIN}/{{filename}}"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request, filename: str) -> web.StreamResponse:
        """Handle a short Roku HLS request."""
        bridge = self._first_bridge()
        if bridge is None:
            return web.Response(status=404, text="No bridge configured\n")

        if filename == "live.m3u8":
            return await bridge.async_serve("stream.m3u8")

        return await bridge.async_serve(filename)

    def _first_bridge(self) -> UnifiRokuBridge | None:
        bridges = [
            value
            for value in self.hass.data.get(DOMAIN, {}).values()
            if isinstance(value, UnifiRokuBridge)
        ]
        if not bridges:
            return None

        return bridges[0]
