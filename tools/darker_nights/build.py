#!/usr/bin/env python3
import argparse
import struct
from pathlib import Path

CURVE = [
    (0, 0.25),      # 00:00
    (480, 0.30),    # 04:00
    (720, 0.65),    # 06:00
    (960, 1.00),    # 08:00
    (2160, 0.85),   # 18:00
    (2400, 0.55),   # 20:00
    (2640, 0.35),   # 22:00
    (2880, 0.25),   # 24:00
]


def brightness_factor(time_value: int) -> float:
    for (t0, f0), (t1, f1) in zip(CURVE, CURVE[1:]):
        if t0 <= time_value <= t1:
            if t1 == t0:
                return f0
            p = (time_value - t0) / (t1 - t0)
            return f0 + (f1 - f0) * p
    return 1.0


def darken_color(value: int, factor: float) -> int:
    high = value & 0xFF000000
    c0 = value & 0xFF
    c1 = (value >> 8) & 0xFF
    c2 = (value >> 16) & 0xFF
    c0 = round(c0 * factor)
    c1 = round(c1 * factor)
    c2 = round(c2 * factor)
    return high | c0 | (c1 << 8) | (c2 << 16)


def build(source: Path, output: Path) -> None:
    data = bytearray(source.read_bytes())
    magic, records, fields, record_size, _string_size = struct.unpack_from("<4s4I", data, 0)

    if magic != b"WDBC":
        raise SystemExit(f"ERROR: unexpected DBC magic: {magic!r}")
    if fields != 34 or record_size != 136:
        raise SystemExit(
            f"ERROR: unexpected LightIntBand layout: fields={fields}, record_size={record_size}"
        )

    changed_records = 0
    changed_colors = 0
    base = 20

    for index in range(records):
        pos = base + index * record_size
        values = list(struct.unpack_from("<34I", data, pos))
        row_id = values[0]
        num_entries = min(values[1], 16)

        # LightIntBand rows are grouped in sets of 18 bands per lighting profile.
        # We intentionally modify only the first two color bands for this experiment:
        # global diffuse and global ambient light.
        band_offset = (row_id - 1) % 18
        if band_offset not in (0, 1):
            continue

        changed = False
        for n in range(num_entries):
            time_value = values[2 + n]
            factor = brightness_factor(time_value)
            if factor >= 0.999:
                continue

            color_index = 18 + n
            old = values[color_index]
            new = darken_color(old, factor)
            if new != old:
                values[color_index] = new
                changed_colors += 1
                changed = True

        if changed:
            struct.pack_into("<34I", data, pos, *values)
            changed_records += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)

    print("Darker Nights test DBC generated")
    print(f"Source: {source}")
    print(f"Output: {output}")
    print(f"Records modified: {changed_records}")
    print(f"Colors modified: {changed_colors}")
    print(f"Size: {output.stat().st_size} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an experimental darker-night LightIntBand.dbc")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "wow335-extract/dbc/LightIntBand.dbc",
        help="Stock 3.3.5a LightIntBand.dbc",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "darker-nights-test/DBFilesClient/LightIntBand.dbc",
        help="Generated LightIntBand.dbc",
    )
    args = parser.parse_args()

    if not args.source.is_file():
        raise SystemExit(f"ERROR: source DBC not found: {args.source}")

    build(args.source, args.output)


if __name__ == "__main__":
    main()
