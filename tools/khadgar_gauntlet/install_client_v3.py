#!/usr/bin/env python3
"""Build the SpellDraft v3 client bundle with Gauntlet custom spells included."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import client
import spelldraft_v3_icons
from khadgar_gauntlet.patch_spell_dbc import patch as patch_gauntlet_spells


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--dbc-src", required=True, type=Path)
    parser.add_argument("--server-data-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument("--locale", default="esMX")
    parser.add_argument("--icon-pack-dir", type=Path, default=spelldraft_v3_icons.default_pack_dir())
    args = parser.parse_args()

    try:
        spell_ranks = (
            args.core_dir.expanduser().resolve()
            / "data" / "sql" / "base" / "db_world" / "spell_ranks.sql"
        )
        icons, assigned = spelldraft_v3_icons.install_wrappers(
            args.icon_pack_dir.expanduser().resolve(),
            spell_ranks,
        )
        original_patch_dbc_copy = client.patch_dbc_copy

        def patch_dbc_copy(source: Path, work: Path):
            changed = original_patch_dbc_copy(source, work)
            before = (work / "Spell.dbc").read_bytes()
            patch_gauntlet_spells(work / "Spell.dbc")
            changed["Spell.dbc"] = (
                (work / "Spell.dbc").read_bytes() != before
                or changed.get("Spell.dbc", False)
            )
            return changed

        client.patch_dbc_copy = patch_dbc_copy

        with tempfile.TemporaryDirectory(prefix="gauntlet-v3-client-") as tmp_name:
            build_dir = Path(tmp_name)
            client.build_patch(args.dbc_src, build_dir, args.locale)
            client.install_server_dbcs(build_dir, args.server_data_dir / "dbc")
            client.install_patch(args.client_dir, build_dir, args.locale)

        lone_key = spelldraft_v3_icons.normalized_path("Interface\\Icons\\lobo_solitario")
        lone_id = assigned.get(lone_key)
        if lone_id != spelldraft_v3_icons.LONE_WOLF_ICON_ID:
            raise RuntimeError(
                "lobo_solitario.blp must be a new custom icon and resolve to SpellIcon ID 910000"
            )

        print(f"Gauntlet v3 client bundle installed with {len(icons)} icon textures.")
        print("Lobo solitario client spell: 910501 / SpellIcon: 910000.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
