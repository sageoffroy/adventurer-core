#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import gauntlet_spells


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbc", required=True, type=Path)
    args = parser.parse_args()
    changed = gauntlet_spells.patch(args.dbc)
    print(
        "Gauntlet Spell.dbc: "
        f"{'patched' if changed else 'already current'} "
        "(Juramento 910500 + Lobo solitario 910501)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
