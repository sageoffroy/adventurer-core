#!/usr/bin/env python3
"""Syntax-check installed payloads with the core's real CMake compiler flags.

No fake headers, linking, or server startup. CMake must already be configured
with compile_commands.json and without precompiled headers.
"""

import argparse
import json
from pathlib import Path
import shlex
import subprocess

from core_patch import PAYLOAD_FILES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", required=True, type=Path)
    args = parser.parse_args()
    commands = json.loads((args.build_dir / "compile_commands.json").read_text())
    wanted = {Path(path).name for path in PAYLOAD_FILES if path.endswith(".cpp")}
    checked = set()
    for entry in commands:
        name = Path(entry["file"]).name
        if name not in wanted or name in checked:
            continue
        command = entry.get("arguments") or shlex.split(entry["command"])
        filtered = []
        skip = False
        for token in command:
            if skip:
                skip = False
                continue
            if token == "-o":
                skip = True
            elif token != "-c":
                filtered.append(token)
        filtered.append("-fsyntax-only")
        subprocess.run(filtered, cwd=entry["directory"], check=True)
        checked.add(name)
        print(f"C++ syntax OK: {name}", flush=True)
    if wanted != checked:
        raise RuntimeError(f"Payloads absent from CMake compilation: {sorted(wanted - checked)}")


if __name__ == "__main__":
    main()
