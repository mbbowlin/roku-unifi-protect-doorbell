# UniFi Protect Roku Viewer

This repo contains a sideloadable Roku SceneGraph channel and a local bridge for playing a UniFi Protect `rtsps://` stream on Roku.

Roku does not play RTSP/RTSPS streams directly. The channel plays HLS, and the bridge uses `ffmpeg` to convert the UniFi Protect RTSPS stream into a live HLS playlist that Roku can consume.

## Requirements

- A Roku device on the same LAN as your computer and Home Assistant host.
- For Home Assistant installation: a Home Assistant host that can run `ffmpeg`.
- For Mac-only pre-install testing: Node.js 18 or newer and `ffmpeg` on your Mac.
- A UniFi Protect RTSPS stream URL from your camera.

On macOS with Homebrew, install `ffmpeg` before running the Mac test bridge:

```sh
brew install ffmpeg
```

## Package and sideload the Roku channel

First enable Developer Mode on the Roku so it can accept a sideloaded app:

1. On the Roku remote, press **Home** three times, **Up** twice, then **Right**, **Left**, **Right**, **Left**, **Right**.
2. Write down the Roku URL shown on the developer settings screen. It will look like `http://YOUR_ROKU_IP`.
3. Select **Enable installer** or **Enable Developer Mode**.
4. Read and accept the Developer Tools License Agreement.
5. Create a Developer Mode password. You will use this with username `rokudev` when uploading the app.
6. Let the Roku reboot.

After the Roku reboots, package the channel before trying to open or configure it:

```sh
make package
```

Install it through the Roku Developer Application Installer:

1. Open the Roku URL from the developer settings screen in a browser.
2. Sign in with username `rokudev` and your Developer Mode password.
3. Upload `unifi-protect-viewer.zip`.

Or install from the command line:

```sh
ROKU_DEV_TARGET=YOUR_ROKU_IP ROKU_DEV_PASSWORD='YOUR_DEV_PASSWORD' make install
```

## Test the bridge on your Mac before Home Assistant

This section is only for testing the Roku app and stream settings from your Mac before you install the Home Assistant integration. The temporary Node bridge is not required after the Home Assistant bridge is installed.

Use your Mac while it is on the same LAN as the Roku and UniFi Protect console.

From this repo:

```sh
UNIFI_RTSPS_URL='rtsps://YOUR_UNIFI_HOST:7441/YOUR_STREAM_TOKEN' npm start --prefix bridge
```

Optional bridge settings:

```sh
PORT=8123
HOST=0.0.0.0
HLS_TRANSCODE=0
HLS_KEEP_AUDIO=1
HLS_SEGMENT_SECONDS=1
HLS_LIST_SIZE=3
HLS_VIDEO_MAX_WIDTH=1920
HLS_VIDEO_MAX_HEIGHT=1080
RTSP_TLS_VERIFY=0
```

If your Roku cannot play the copied camera stream, enable transcoding:

```sh
HLS_TRANSCODE=1 UNIFI_RTSPS_URL='rtsps://YOUR_UNIFI_HOST:7441/YOUR_STREAM_TOKEN' npm start --prefix bridge
```

Check the bridge from another device on the LAN:

```sh
curl http://YOUR_COMPUTER_LAN_IP:8123/health
curl http://YOUR_COMPUTER_LAN_IP:8123/live/stream.m3u8
```

For this Mac test only, use this HLS URL in the sideloaded Roku app:

```text
http://YOUR_COMPUTER_LAN_IP:8123/live/stream.m3u8
```

After you install the Home Assistant integration, replace the Roku URL with the Home Assistant URL shown in the integration sensor.

## Configure the Roku channel

You can configure the HLS URL directly on the Roku after sideloading the app. The app shows a compact settings/status panel on the left and the video stream on the right. If a URL is already saved, it attempts playback as soon as the app starts.

1. Open the app.
2. Select **Edit HLS URL**.
3. Enter the Home Assistant HLS URL ending in `stream.m3u8`. If you are still doing the Mac pre-install test, use the temporary Mac bridge URL instead.
4. Select **Save**.
5. The app will immediately try to play the saved stream.

The URL is saved in Roku registry storage and will be reused when the app restarts.

You can still set a packaged fallback by editing `source/config.brs`:

```brightscript
hlsUrl: "http://YOUR_COMPUTER_LAN_IP:8123/live/stream.m3u8"
```

Use your computer's LAN IP address, not `localhost`, because the Roku device must connect to the bridge over the network.

## Home Assistant integration

This is the intended installed bridge. The Mac/Node bridge above is only a temporary test before installing this Home Assistant custom integration.

```text
custom_components/unifi_roku_bridge
```

Install it by copying that directory to:

```text
<home-assistant-config>/custom_components/unifi_roku_bridge
```

Then restart Home Assistant and add:

```text
Settings > Devices & services > Add integration > UniFi Roku Bridge
```

### Install or verify ffmpeg in Home Assistant

The bridge starts `ffmpeg` from the Home Assistant host/container.

For Home Assistant OS or the official Home Assistant Container, `ffmpeg` is already included. Leave the integration option **ffmpeg executable path** set to:

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

Use that value in **Settings > Devices & services > UniFi Roku Bridge > Configure > ffmpeg executable path**. If `which ffmpeg` returns `/usr/bin/ffmpeg`, enter `/usr/bin/ffmpeg`. If it returns only `ffmpeg`, leave the field as `ffmpeg`.

Do not install a separate Home Assistant app/add-on just to provide `ffmpeg` for this integration. Add-ons run separately and usually do not place their binaries on Home Assistant Core's PATH.

For your stream, enter:

```text
UniFi Protect host or IP: YOUR_UNIFI_PROTECT_IP
RTSPS port: 7441
Stream token: YOUR_STREAM_TOKEN
Append enableSrtp: enabled
```

The integration creates a diagnostic sensor with a `short_hls_url` attribute. Enter that URL in the Roku app's **Edit HLS URL** screen. For a single bridge, it should look like:

```text
http://HOME_ASSISTANT_IP:8123/api/unifi_roku_bridge/live.m3u8
```

## Roku controls

- Up/Down: choose a settings menu item.
- OK: select the highlighted item.
- Play: start or reconnect the stream.
- Options: show or hide the status panel.
- Back while playing: stop playback.

## Notes

- Keep the bridge on your trusted LAN. It exposes the live camera feed to any device that can reach the bridge URL.
- UniFi camera streams are usually H.264, which can often be copied into HLS without transcoding. If the stream format is incompatible with your Roku model, use `HLS_TRANSCODE=1`.
- Live HLS has latency. The default settings use 1-second segments and a 3-segment playlist to reduce delay, but Roku will still buffer a few seconds behind live.

## Troubleshooting

If the bridge logs `spawn ffmpeg ENOENT`, `ffmpeg` is not installed or is not on the PATH used by Node. Install it with Homebrew:

```sh
brew install ffmpeg
```

Then verify:

```sh
which ffmpeg
ffmpeg -version
```

If `ffmpeg` is installed somewhere custom, run the bridge with an explicit path:

```sh
FFMPEG_BIN=/path/to/ffmpeg UNIFI_RTSPS_URL='rtsps://YOUR_UNIFI_HOST:7441/YOUR_STREAM_TOKEN' npm start --prefix bridge
```

If ffmpeg logs `certificate verify failed`, the UniFi Protect console is presenting a certificate ffmpeg does not trust. The bridge defaults to `RTSP_TLS_VERIFY=0` for this reason. If you want certificate verification, install a trusted certificate on the UniFi side and start the bridge with:

```sh
RTSP_TLS_VERIFY=1 UNIFI_RTSPS_URL='rtsps://YOUR_UNIFI_HOST:7441/YOUR_STREAM_TOKEN' npm start --prefix bridge
```

If Roku reaches 99 percent and then shows a black screen, use `HLS_TRANSCODE=1`. Some UniFi cameras output tall streams such as 1920x1440, which exceed the default H.264 level used for Roku compatibility. The bridge transcode path caps video at 1920x1080 by default while preserving aspect ratio.
