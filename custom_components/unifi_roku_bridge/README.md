# UniFi Roku Bridge for Home Assistant

This custom integration runs the RTSPS-to-HLS bridge inside Home Assistant and exposes an unauthenticated HLS URL for Roku.

The Mac/Node bridge in the repo root README is only a temporary test harness for checking the Roku app and stream settings before installing this Home Assistant integration. Once this integration is installed, the Roku app should use the Home Assistant HLS URL from the sensor attributes.

## Install

Copy this directory to Home Assistant:

```text
<home-assistant-config>/custom_components/unifi_roku_bridge
```

Restart Home Assistant, then add the integration from:

```text
Settings > Devices & services > Add integration > UniFi Roku Bridge
```

## Configure

For your stream, use:

```text
UniFi Protect host or IP: YOUR_UNIFI_PROTECT_IP
RTSPS port: 7441
Stream token: YOUR_STREAM_TOKEN
Append enableSrtp: enabled
```

Leave the default options unless playback fails. The defaults match the bridge settings that worked with Roku:

```text
Transcode: enabled
Keep audio: enabled
HLS segment seconds: 1
HLS playlist segment count: 3
Maximum video width: 1920
Maximum video height: 1080
Verify UniFi TLS certificate: disabled
```

### Install or verify ffmpeg

The bridge starts `ffmpeg` from the Home Assistant host/container.

For Home Assistant OS or the official Home Assistant Container, `ffmpeg` is already included. Leave **ffmpeg executable path** set to:

```text
ffmpeg
```

For Home Assistant Core or Supervised installs, install `ffmpeg` on the operating system that runs Home Assistant before configuring the integration.

Debian or Ubuntu, including Home Assistant Supervised:

```sh
sudo apt update
sudo apt install ffmpeg
```

Alpine, run as root:

```sh
apk add ffmpeg
```

macOS:

```sh
brew install ffmpeg
```

Then find the executable path:

```sh
which ffmpeg
```

Use that value in:

```text
Settings > Devices & services > UniFi Roku Bridge > Configure > ffmpeg executable path
```

If `which ffmpeg` returns `/usr/bin/ffmpeg`, enter `/usr/bin/ffmpeg`. If it returns only `ffmpeg`, leave the field as `ffmpeg`.

Do not install a separate Home Assistant app/add-on just to provide `ffmpeg` for this integration. Add-ons run separately and usually do not place their binaries on Home Assistant Core's PATH.

To update the UniFi Protect IP, stream token, SRTP flag, ffmpeg path, or transcoding settings later:

```text
Settings > Devices & services > UniFi Roku Bridge > Configure
```

## Roku URL

The generated Roku HLS URL keeps the same entry ID and access token when you change options.

After setup, Home Assistant creates a diagnostic sensor named similar to:

```text
sensor.unifi_roku_bridge_bridge
```

Open that sensor's attributes and use `short_hls_url` as the Roku channel URL.

For one configured bridge, the short URL is:

```text
http://HOME_ASSISTANT_IP:8123/api/unifi_roku_bridge/live.m3u8
```

The longer `hls_url` remains available and includes a per-entry access token.

You can also open the integration's health endpoint from a browser:

```text
http://HOME_ASSISTANT_IP:8123/api/unifi_roku_bridge/<entry_id>/<access_token>/health
```

The `hls_path` field shows the exact path for the Roku channel:

```text
http://HOME_ASSISTANT_IP:8123/api/unifi_roku_bridge/<entry_id>/<access_token>/stream.m3u8
```

Set that full URL in the Roku app's `source/config.brs`, repackage, and sideload the app again.

## ffmpeg

The integration must be able to run `ffmpeg` from the Home Assistant host/container. If the bridge reports that `ffmpeg` cannot be found, confirm your Home Assistant installation type and update the integration option with the full executable path.
