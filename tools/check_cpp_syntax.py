#!/usr/bin/env python3
"""Compile-check changed units using actual AzerothCore headers and flags.

This checks translation units, not linking or gameplay; never supplies fake
headers or compatibility stubs. CI configures the same clean core as preflight.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", required=True, type=Path)
    args = parser.parse_args()
    commands = json.loads((args.build_dir / "compile_commands.json").read_text())
    wanted = {"SpellInfo.cpp", "adventurer_core.cpp", "adventurer_collections.cpp"}
    checked = set()
    for entry in commands:
        name = Path(entry["file"]).name
        if name not in wanted or name in checked:
            continue
        source = entry.get("arguments") or shlex.split(entry["command"])
        command = []
        index = 0
        while index < len(source):
            argument = source[index]
            if argument == "-o":
                index += 2
                continue
            if argument != "-c":
                command.append(argument)
            index += 1
        command.append("-fsyntax-only")
        print(f"Compile-check: {name}", flush=True)
        subprocess.run(command, cwd=entry["directory"], check=True)
        checked.add(name)
    if checked != wanted:
        raise SystemExit(f"Missing real compile commands: {sorted(wanted - checked)}")


if __name__ == "__main__":
    main()
