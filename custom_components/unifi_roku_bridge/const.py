"""Constants for the UniFi Roku Bridge integration."""

from __future__ import annotations

DOMAIN = "unifi_roku_bridge"

ACCESS_TOKEN = "access_token"
CONF_ENABLE_SRTP = "enable_srtp"
CONF_FFMPEG_BIN = "ffmpeg_bin"
CONF_H264_LEVEL = "h264_level"
CONF_IDLE_TIMEOUT = "idle_timeout"
CONF_KEEP_AUDIO = "keep_audio"
CONF_LIST_SIZE = "list_size"
CONF_MAX_HEIGHT = "max_height"
CONF_MAX_WIDTH = "max_width"
CONF_PLAYLIST_WAIT_MS = "playlist_wait_ms"
CONF_RTSP_TRANSPORT = "rtsp_transport"
CONF_SEGMENT_SECONDS = "segment_seconds"
CONF_STREAM_TOKEN = "stream_token"
CONF_TLS_VERIFY = "tls_verify"
CONF_TRANSCODE = "transcode"
CONF_X264_PRESET = "x264_preset"

DEFAULT_ENABLE_SRTP = True
DEFAULT_FFMPEG_BIN = "ffmpeg"
DEFAULT_H264_LEVEL = "4.1"
DEFAULT_IDLE_TIMEOUT = 120
DEFAULT_KEEP_AUDIO = True
DEFAULT_LIST_SIZE = 6
DEFAULT_MAX_HEIGHT = 1080
DEFAULT_MAX_WIDTH = 1920
DEFAULT_PLAYLIST_WAIT_MS = 8000
DEFAULT_PORT = 7441
DEFAULT_RTSP_TRANSPORT = "tcp"
DEFAULT_SEGMENT_SECONDS = 2
DEFAULT_TLS_VERIFY = False
DEFAULT_TRANSCODE = True
DEFAULT_X264_PRESET = "veryfast"
