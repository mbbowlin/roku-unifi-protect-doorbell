const fs = require("fs");
const http = require("http");
const path = require("path");
const { spawn } = require("child_process");

const PORT = Number(process.env.PORT || 8123);
const HOST = process.env.HOST || "0.0.0.0";
const RTSPS_URL = process.env.UNIFI_RTSPS_URL;
const FFMPEG_BIN = process.env.FFMPEG_BIN || "ffmpeg";
const OUTPUT_DIR = process.env.HLS_OUTPUT_DIR || path.join("/tmp", "unifi-protect-roku-hls");
const SEGMENT_SECONDS = String(Number(process.env.HLS_SEGMENT_SECONDS || 1));
const LIST_SIZE = String(Number(process.env.HLS_LIST_SIZE || 3));
const TRANSCODE = process.env.HLS_TRANSCODE === "1";
const KEEP_AUDIO = process.env.HLS_KEEP_AUDIO !== "0";
const VIDEO_MAX_WIDTH = String(Number(process.env.HLS_VIDEO_MAX_WIDTH || 1920));
const VIDEO_MAX_HEIGHT = String(Number(process.env.HLS_VIDEO_MAX_HEIGHT || 1080));
const PLAYLIST_WAIT_MS = Number(process.env.HLS_PLAYLIST_WAIT_MS || 8000);
const RTSP_TLS_VERIFY = process.env.RTSP_TLS_VERIFY === "1";

let ffmpegProcess = null;
let ffmpegStartedAt = 0;
let lastFfmpegExit = null;
let lastFfmpegError = null;

function ensureOutputDir() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  for (const file of fs.readdirSync(OUTPUT_DIR)) {
    if (file.endsWith(".m3u8") || file.endsWith(".ts")) {
      fs.unlinkSync(path.join(OUTPUT_DIR, file));
    }
  }
}

function ffmpegArgs() {
  const args = [
    "-hide_banner",
    "-loglevel",
    process.env.FFMPEG_LOG_LEVEL || "warning",
    "-tls_verify",
    RTSP_TLS_VERIFY ? "1" : "0",
    "-rtsp_transport",
    process.env.RTSP_TRANSPORT || "tcp",
    "-i",
    RTSPS_URL
  ];

  if (TRANSCODE) {
    args.push(
      "-c:v",
      "libx264",
      "-preset",
      process.env.HLS_X264_PRESET || "veryfast",
      "-tune",
      "zerolatency",
      "-profile:v",
      "high",
      "-level",
      process.env.HLS_H264_LEVEL || "4.1",
      "-pix_fmt",
      "yuv420p",
      "-vf",
      `scale=w=min(${VIDEO_MAX_WIDTH}\\,iw):h=min(${VIDEO_MAX_HEIGHT}\\,ih):force_original_aspect_ratio=decrease:force_divisible_by=2`,
      "-g",
      process.env.HLS_GOP_SIZE || "30",
      "-sc_threshold",
      "0",
      "-force_key_frames",
      `expr:gte(t,n_forced*${SEGMENT_SECONDS})`
    );
  } else {
    args.push("-c:v", "copy");
  }

  if (KEEP_AUDIO) {
    args.push("-c:a", "aac", "-b:a", process.env.HLS_AUDIO_BITRATE || "96k");
  } else {
    args.push("-an");
  }

  args.push(
    "-f",
    "hls",
    "-hls_time",
    SEGMENT_SECONDS,
    "-hls_list_size",
    LIST_SIZE,
    "-hls_flags",
    TRANSCODE
      ? "delete_segments+omit_endlist+program_date_time+independent_segments"
      : "delete_segments+omit_endlist+program_date_time",
    "-hls_segment_type",
    "mpegts",
    "-hls_segment_filename",
    path.join(OUTPUT_DIR, "segment_%05d.ts"),
    path.join(OUTPUT_DIR, "stream.m3u8")
  );

  return args;
}

function startFfmpeg() {
  if (!RTSPS_URL) {
    return;
  }

  if (ffmpegProcess && ffmpegProcess.exitCode === null) {
    return;
  }

  ensureOutputDir();
  ffmpegStartedAt = Date.now();
  lastFfmpegExit = null;
  lastFfmpegError = null;

  ffmpegProcess = spawn(FFMPEG_BIN, ffmpegArgs(), {
    stdio: ["ignore", "ignore", "pipe"]
  });

  ffmpegProcess.on("error", (err) => {
    lastFfmpegError = {
      code: err.code,
      message: err.message,
      path: err.path,
      at: new Date().toISOString()
    };
    ffmpegProcess = null;
    console.error(`ffmpeg failed to start: ${err.message}`);
  });

  ffmpegProcess.stderr.on("data", (chunk) => {
    process.stderr.write(`[ffmpeg] ${chunk}`);
  });

  ffmpegProcess.on("exit", (code, signal) => {
    lastFfmpegExit = { code, signal, at: new Date().toISOString() };
    ffmpegProcess = null;
    console.error(`ffmpeg exited: code=${code} signal=${signal}`);
  });
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload, null, 2);
  res.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store"
  });
  res.end(body);
}

function sendFile(res, filePath, contentType) {
  fs.readFile(filePath, (err, body) => {
    if (err) {
      res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      res.end("Not ready\n");
      return;
    }

    res.writeHead(200, {
      "content-type": contentType,
      "cache-control": "no-store",
      "access-control-allow-origin": "*"
    });
    res.end(body);
  });
}

function sendFileWhenReady(res, filePath, contentType, deadline) {
  if (fs.existsSync(filePath)) {
    sendFile(res, filePath, contentType);
    return;
  }

  if (lastFfmpegError) {
    sendJson(res, 503, {
      ok: false,
      error: "ffmpeg failed to start",
      ffmpegRunning: false,
      lastFfmpegExit,
      lastFfmpegError
    });
    return;
  }

  if (Date.now() >= deadline) {
    sendJson(res, 503, {
      ok: false,
      error: "HLS playlist is not ready yet",
      ffmpegRunning: Boolean(ffmpegProcess),
      lastFfmpegExit,
      lastFfmpegError
    });
    return;
  }

  setTimeout(() => {
    sendFileWhenReady(res, filePath, contentType, deadline);
  }, 250);
}

function handleRequest(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (url.pathname === "/health") {
    sendJson(res, 200, {
      ok: true,
      configured: Boolean(RTSPS_URL),
      outputDir: OUTPUT_DIR,
      ffmpegRunning: Boolean(ffmpegProcess),
      ffmpegStartedAt: ffmpegStartedAt ? new Date(ffmpegStartedAt).toISOString() : null,
      lastFfmpegExit,
      lastFfmpegError
    });
    return;
  }

  if (!RTSPS_URL) {
    sendJson(res, 500, {
      ok: false,
      error: "UNIFI_RTSPS_URL is required"
    });
    return;
  }

  if (url.pathname === "/live/stream.m3u8") {
    startFfmpeg();
    sendFileWhenReady(
      res,
      path.join(OUTPUT_DIR, "stream.m3u8"),
      "application/vnd.apple.mpegurl",
      Date.now() + PLAYLIST_WAIT_MS
    );
    return;
  }

  if (/^\/live\/segment_\d+\.ts$/.test(url.pathname)) {
    sendFile(res, path.join(OUTPUT_DIR, path.basename(url.pathname)), "video/mp2t");
    return;
  }

  sendJson(res, 404, {
    ok: false,
    error: "Not found"
  });
}

function shutdown() {
  if (ffmpegProcess) {
    ffmpegProcess.kill("SIGTERM");
  }
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

const server = http.createServer(handleRequest);

server.on("error", (err) => {
  console.error(`Bridge failed to listen on ${HOST}:${PORT}: ${err.message}`);
  process.exit(1);
});

server.listen(PORT, HOST, () => {
  console.log(`Bridge listening on http://${HOST}:${PORT}`);
  console.log(`HLS URL: http://<this-computer-LAN-IP>:${PORT}/live/stream.m3u8`);
  if (!RTSPS_URL) {
    console.log("Set UNIFI_RTSPS_URL before requesting /live/stream.m3u8");
  }
});
