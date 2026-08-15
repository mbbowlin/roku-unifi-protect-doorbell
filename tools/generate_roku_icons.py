#!/usr/bin/env python3
"""Generate Roku channel icon PNGs without external image dependencies."""

from __future__ import annotations

from pathlib import Path
import struct
import zlib


FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "b": ["10000", "10000", "10110", "11001", "10001", "11001", "10110"],
    "e": ["00000", "00000", "01110", "10001", "11110", "10000", "01110"],
    "l": ["11000", "01000", "01000", "01000", "01000", "01000", "11100"],
    "o": ["00000", "00000", "01110", "10001", "10001", "10001", "01110"],
    "r": ["00000", "00000", "10110", "11001", "10000", "10000", "10000"],
}


def chunk(kind: bytes, data: bytes) -> bytes:
    """Build one PNG chunk."""
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def set_pixel(canvas: list[list[tuple[int, int, int]]], x: int, y: int, color: tuple[int, int, int]) -> None:
    """Set a pixel when it is inside the canvas."""
    if 0 <= y < len(canvas) and 0 <= x < len(canvas[0]):
        canvas[y][x] = color


def draw_text(
    canvas: list[list[tuple[int, int, int]]],
    text: str,
    x: int,
    y: int,
    scale: int,
    color: tuple[int, int, int],
) -> None:
    """Draw simple block text."""
    cursor = x
    for char in text:
        glyph = FONT.get(char)
        if glyph is None:
            cursor += scale * 4
            continue

        for row_index, row in enumerate(glyph):
            for col_index, bit in enumerate(row):
                if bit != "1":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        set_pixel(
                            canvas,
                            cursor + col_index * scale + dx,
                            y + row_index * scale + dy,
                            color,
                        )
        cursor += (len(glyph[0]) + 1) * scale


def text_width(text: str, scale: int) -> int:
    """Measure simple block text."""
    width = 0
    for char in text:
        glyph = FONT.get(char)
        width += ((len(glyph[0]) + 1) if glyph else 4) * scale
    return max(0, width - scale)


def make_png(path: Path, width: int, height: int) -> None:
    """Create one Roku icon."""
    bg = (11, 15, 20)
    green = (45, 125, 70)
    green_dark = (29, 92, 50)
    white = (244, 248, 252)
    muted = (143, 163, 184)
    red = (210, 58, 52)

    canvas: list[list[tuple[int, int, int]]] = []
    for y in range(height):
        row: list[tuple[int, int, int]] = []
        for x in range(width):
            shade = int(18 * y / max(1, height - 1))
            color = (bg[0] + shade, bg[1] + shade, bg[2] + shade)

            if x < width * 0.22:
                color = (12, 32 + shade, 27 + shade)

            cx1, cy1 = int(width * 0.26), int(height * 0.26)
            cx2, cy2 = int(width * 0.68), int(height * 0.60)
            if cx1 <= x <= cx2 and cy1 <= y <= cy2:
                color = green
                if x < cx1 + int(width * 0.025) or y < cy1 + int(height * 0.03):
                    color = (57, 150, 86)

            lx, ly = int(width * 0.47), int(height * 0.43)
            r_outer = int(min(width, height) * 0.13)
            r_inner = int(min(width, height) * 0.07)
            d2 = (x - lx) ** 2 + (y - ly) ** 2
            if d2 <= r_outer**2:
                color = green_dark
            if d2 <= r_inner**2:
                color = (9, 13, 18)
            highlight_x = lx - r_inner // 3
            highlight_y = ly - r_inner // 3
            if (x - highlight_x) ** 2 + (y - highlight_y) ** 2 <= max(2, r_inner // 4) ** 2:
                color = white

            ax, ay = int(width * 0.75), int(height * 0.28)
            ar = int(min(width, height) * 0.055)
            if (x - ax) ** 2 + (y - ay) ** 2 <= ar**2:
                color = red

            row.append(color)
        canvas.append(row)

    scale = max(3, int(width / 90))
    label = "Doorbell"
    label_width = text_width(label, scale)
    label_x = (width - label_width) // 2
    label_y = int(height * 0.72)
    draw_text(canvas, label, label_x + scale, label_y + scale, scale, (3, 6, 8))
    draw_text(canvas, label, label_x, label_y, scale, white)

    sub_width = int(width * 0.46)
    sub_y = int(height * 0.88)
    sub_x1 = (width - sub_width) // 2
    sub_x2 = sub_x1 + sub_width
    for y in range(sub_y, min(height, sub_y + max(3, scale))):
        for x in range(sub_x1, sub_x2):
            set_pixel(canvas, x, y, muted)

    raw_rows = []
    for row in canvas:
        raw = bytearray([0])
        for color in row:
            raw.extend(color)
        raw_rows.append(bytes(raw))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(raw_rows), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    """Generate all Roku tile sizes."""
    images = Path("images")
    images.mkdir(exist_ok=True)
    make_png(images / "channel-icon_FHD.png", 540, 405)
    make_png(images / "channel-icon_HD.png", 290, 218)


if __name__ == "__main__":
    main()
