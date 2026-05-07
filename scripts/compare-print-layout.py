#!/usr/bin/env python3
import argparse
import json
import struct
import sys
import zlib


def read_png(path):
    with open(path, "rb") as fh:
        data = fh.read()

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{path}: not a PNG file")

    pos = 8
    width = height = color_type = None
    bit_depth = None
    idat = []

    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk_data[:10])
        elif chunk_type == b"IDAT":
            idat.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if bit_depth != 8 or color_type not in (0, 2, 6):
        raise ValueError(f"{path}: unsupported PNG format bit_depth={bit_depth} color_type={color_type}")

    channels = {0: 1, 2: 3, 6: 4}[color_type]
    row_bytes = width * channels
    raw = zlib.decompress(b"".join(idat))
    rows = []
    prev = [0] * row_bytes
    offset = 0

    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        scan = list(raw[offset:offset + row_bytes])
        offset += row_bytes
        recon = [0] * row_bytes

        for i, value in enumerate(scan):
          left = recon[i - channels] if i >= channels else 0
          up = prev[i]
          up_left = prev[i - channels] if i >= channels else 0

          if filter_type == 0:
              recon[i] = value
          elif filter_type == 1:
              recon[i] = (value + left) & 255
          elif filter_type == 2:
              recon[i] = (value + up) & 255
          elif filter_type == 3:
              recon[i] = (value + ((left + up) // 2)) & 255
          elif filter_type == 4:
              p = left + up - up_left
              pa = abs(p - left)
              pb = abs(p - up)
              pc = abs(p - up_left)
              predictor = left if pa <= pb and pa <= pc else up if pb <= pc else up_left
              recon[i] = (value + predictor) & 255
          else:
              raise ValueError(f"{path}: unsupported PNG filter {filter_type}")

        prev = recon
        row = []
        for x in range(width):
            start = x * channels
            if color_type == 0:
                gray = recon[start]
                row.append((gray, gray, gray))
            else:
                row.append(tuple(recon[start:start + 3]))
        rows.append(row)

    return width, height, rows


def luminance(rgb):
    r, g, b = rgb
    return (299 * r + 587 * g + 114 * b) // 1000


def bbox(mask):
    xs = []
    ys = []
    for y, row in enumerate(mask):
        for x, value in enumerate(row):
            if value:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return {
        "left": min(xs),
        "top": min(ys),
        "right": max(xs),
        "bottom": max(ys),
        "width": max(xs) - min(xs) + 1,
        "height": max(ys) - min(ys) + 1,
        "count": len(xs),
        "centerX": (min(xs) + max(xs)) / 2,
        "centerY": (min(ys) + max(ys)) / 2,
    }


def make_masks(full, background, blank, diff_threshold, ink_threshold):
    full_w, full_h, full_rows = full
    bg_w, bg_h, bg_rows = background
    blank_w, blank_h, blank_rows = blank
    if (full_w, full_h) != (bg_w, bg_h) or (full_w, full_h) != (blank_w, blank_h):
        raise ValueError(f"image sizes differ: full={full_w}x{full_h}, bg={bg_w}x{bg_h}, blank={blank_w}x{blank_h}")

    text_from_full = []
    text_from_blank = []
    for y in range(full_h):
        full_row = []
        blank_row = []
        for x in range(full_w):
            f = full_rows[y][x]
            b = bg_rows[y][x]
            p = blank_rows[y][x]

            diff = max(abs(f[0] - b[0]), abs(f[1] - b[1]), abs(f[2] - b[2]))
            full_row.append(diff > diff_threshold and luminance(f) < luminance(b) - 8)
            blank_row.append(luminance(p) < ink_threshold)
        text_from_full.append(full_row)
        text_from_blank.append(blank_row)

    return text_from_full, text_from_blank


def main():
    parser = argparse.ArgumentParser(description="Compare text placement in printed postal form PNG renders.")
    parser.add_argument("--full", required=True, help="PNG rendered from PDF with background and text")
    parser.add_argument("--background", required=True, help="PNG rendered from PDF with background only")
    parser.add_argument("--blank", required=True, help="PNG rendered from PDF with text only")
    parser.add_argument("--tolerance-px", type=int, default=3)
    parser.add_argument("--diff-threshold", type=int, default=20)
    parser.add_argument("--ink-threshold", type=int, default=245)
    args = parser.parse_args()

    full = read_png(args.full)
    background = read_png(args.background)
    blank = read_png(args.blank)
    full_mask, blank_mask = make_masks(full, background, blank, args.diff_threshold, args.ink_threshold)
    full_box = bbox(full_mask)
    blank_box = bbox(blank_mask)

    result = {
        "fullTextBox": full_box,
        "blankTextBox": blank_box,
        "tolerancePx": args.tolerance_px,
        "ok": False,
    }

    if not full_box or not blank_box:
        print(json.dumps(result, indent=2))
        print("Missing text pixels in one of the renders.", file=sys.stderr)
        return 1

    deltas = {
        key: abs(full_box[key] - blank_box[key])
        for key in ("left", "top", "right", "bottom", "centerX", "centerY")
    }
    result["deltas"] = deltas
    result["ok"] = all(value <= args.tolerance_px for value in deltas.values())

    print(json.dumps(result, indent=2))
    if not result["ok"]:
        print("Printed text placement differs beyond tolerance.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
