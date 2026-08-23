#!/usr/bin/env python3
"""Experimental client/server split for Adventurer rune-cost spells.

WotLK 3.3.5a keeps part of Death Knight rune usability state in the client.
For native class ID 10 that cache can remain stale after the last rune of a
family is spent, even though AzerothCore has already regenerated the rune.

This experiment keeps the server Spell.dbc completely native and creates a
client-only Spell.dbc variant for three known test spells. The client variant
removes local power/rune-cost validation; AzerothCore remains authoritative for
checking, spending and regenerating the actual runes.

Nothing here changes the spell ID sent to the server. Icy Touch is still 45477,
Plague Strike is still 45462 and Blood Strike is still 45902.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from adventurer import (
    InstallError,
    load_state,
    save_state,
    validate_runtime_inputs,
    verify_state,
)
from client import (
    ADVENTURER_FRAME_INTERNAL,
    DBC_NAMES,
    DEFAULT_LOCALE,
    PROJECT_SUFFIX,
    ROOT_SHARED_DBCS,
    build_adventurer_frame_art,
    build_adventurer_resources_lua,
    build_character_create_lua,
    build_frame_xml_toc,
    install_patch,
    install_server_dbcs,
    patch_dbc_copy,
    sha256,
)
from dbc import DBC, DBCError, set_u32, u32
from mpq import write_mpq


# Deliberately limited to the three spells already used for the rune regression
# tests. If the architecture works in-game, it can be generalized safely to all
# POWER_RUNE spells in a later production commit.
EXPERIMENT_SPELL_IDS = (45477, 45462, 45902)

SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
SPELL_POWER_TYPE_FIELD = 41
SPELL_MANA_COST_FIELDS = (42, 43, 44, 45)
SPELL_MANA_COST_PERCENT_FIELD = 204
SPELL_RUNE_COST_ID_FIELD = 226
POWER_MANA = 0


class RuneClientExperimentError(RuntimeError):
    pass


def spell_row(dbc: DBC, spell_id: int) -> bytearray:
    row = next((row for row in dbc.records if u32(row, 0) == spell_id), None)
    if row is None:
        raise RuneClientExperimentError(f"Spell.dbc is missing spell {spell_id}")
    return row


def rune_signature(path: Path, spell_id: int) -> tuple[int, int, int, int]:
    dbc = DBC.read(path)
    row = spell_row(dbc, spell_id)
    return (
        u32(row, SPELL_POWER_TYPE_FIELD),
        u32(row, SPELL_RUNE_COST_ID_FIELD),
        u32(row, 42),
        u32(row, SPELL_MANA_COST_PERCENT_FIELD),
    )


def patch_client_rune_validation(path: Path) -> None:
    dbc = DBC.read(path)
    if dbc.fields != SPELL_FIELDS or dbc.record_size != SPELL_RECORD_SIZE:
        raise RuneClientExperimentError(
            f"{path}: unexpected Spell.dbc layout {dbc.fields}/{dbc.record_size}"
        )

    for spell_id in EXPERIMENT_SPELL_IDS:
        row = spell_row(dbc, spell_id)

        # The client must not run its DK-only rune usability cache for these
        # actions. The server still loads the untouched row and therefore keeps
        # the real POWER_RUNE / RuneCostID mechanics authoritative.
        set_u32(row, SPELL_POWER_TYPE_FIELD, POWER_MANA)
        for field in SPELL_MANA_COST_FIELDS:
            set_u32(row, field, 0)
        set_u32(row, SPELL_MANA_COST_PERCENT_FIELD, 0)
        set_u32(row, SPELL_RUNE_COST_ID_FIELD, 0)

    dbc.write(path)


def client_dbc_bytes(server_work: Path, client_spell: Path, name: str) -> bytes:
    if name == "Spell.dbc":
        return client_spell.read_bytes()
    return (server_work / name).read_bytes()


def build_experimental_bundle(dbc_source: Path, output: Path, locale: str) -> dict:
    dbc_source = dbc_source.expanduser().resolve()
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="adventurer-rune-client-") as tmp_name:
        temp = Path(tmp_name)
        server_work = temp / "server"
        server_work.mkdir()
        changed = patch_dbc_copy(dbc_source, server_work)

        # Freeze the server spell bytes first. Only the separate client copy is
        # modified below.
        server_spell = server_work / "Spell.dbc"
        server_signatures = {
            spell_id: rune_signature(server_spell, spell_id)
            for spell_id in EXPERIMENT_SPELL_IDS
        }

        client_spell = temp / "Spell.client.dbc"
        shutil.copy2(server_spell, client_spell)
        patch_client_rune_validation(client_spell)

        client_signatures = {
            spell_id: rune_signature(client_spell, spell_id)
            for spell_id in EXPERIMENT_SPELL_IDS
        }

        # Guard the experiment itself: server rows must remain rune-powered and
        # client rows must be cost-neutral. If either invariant is false, refuse
        # to install anything.
        for spell_id in EXPERIMENT_SPELL_IDS:
            server_power, server_rune_cost, _, _ = server_signatures[spell_id]
            client_power, client_rune_cost, client_mana, client_mana_pct = client_signatures[spell_id]
            if server_rune_cost == 0:
                raise RuneClientExperimentError(
                    f"Server spell {spell_id} unexpectedly has RuneCostID=0"
                )
            if client_power != POWER_MANA or client_rune_cost != 0 or client_mana != 0 or client_mana_pct != 0:
                raise RuneClientExperimentError(
                    f"Client spell {spell_id} was not neutralized correctly: {client_signatures[spell_id]}"
                )
            if server_spell.read_bytes() == client_spell.read_bytes():
                raise RuneClientExperimentError("Client/server Spell.dbc split did not change any bytes")

        root_files = {
            "Interface\\GlueXML\\CharacterCreate.lua": build_character_create_lua(),
            "Interface\\FrameXML\\FrameXML.toc": build_frame_xml_toc(),
            "Interface\\FrameXML\\AdventurerResources.lua": build_adventurer_resources_lua(),
            ADVENTURER_FRAME_INTERNAL: build_adventurer_frame_art(),
            **{
                f"DBFilesClient\\{name}": client_dbc_bytes(server_work, client_spell, name)
                for name in ROOT_SHARED_DBCS
            },
        }
        locale_files = {
            f"DBFilesClient\\{name}": client_dbc_bytes(server_work, client_spell, name)
            for name in DBC_NAMES
        }

        # Root and locale client archives must still agree with each other. The
        # only intentional divergence is client Spell.dbc vs server Spell.dbc.
        for name in ROOT_SHARED_DBCS:
            internal = f"DBFilesClient\\{name}"
            if root_files[internal] != locale_files[internal]:
                raise RuneClientExperimentError(
                    f"Root/locale client payload differs for {internal}"
                )

        root_patch = output / "Data" / f"patch-{PROJECT_SUFFIX}.mpq"
        locale_patch = output / "Data" / locale / f"patch-{locale}-{PROJECT_SUFFIX.lower()}.mpq"
        write_mpq(root_patch, root_files)
        write_mpq(locale_patch, locale_files)

        server_dbc_dir = output / "server-dbc"
        server_dbc_dir.mkdir(parents=True, exist_ok=True)
        for name in DBC_NAMES:
            shutil.copy2(server_work / name, server_dbc_dir / name)

    manifest = {
        "schema": 1,
        "owner": "adventurer-core-rune-client-experiment",
        "class_id": 10,
        "locale": locale,
        "dbc_source": str(dbc_source),
        "dbc_changed": changed,
        "experimental_spell_ids": list(EXPERIMENT_SPELL_IDS),
        "server_signatures": {str(key): list(value) for key, value in server_signatures.items()},
        "client_signatures": {str(key): list(value) for key, value in client_signatures.items()},
        "root_patch": str(root_patch.relative_to(output)),
        "root_sha256": sha256(root_patch),
        "locale_patch": str(locale_patch.relative_to(output)),
        "locale_sha256": sha256(locale_patch),
    }
    (output / "experiment-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def apply_experiment(args) -> None:
    core = args.core_dir.expanduser().resolve()
    server_dbc, dbc_source, client_dir = validate_runtime_inputs(
        core, args, build_smoke_test=False
    )

    state = load_state(core)

    with tempfile.TemporaryDirectory(prefix="adventurer-rune-install-") as tmp_name:
        staged = Path(tmp_name) / "build"
        manifest = build_experimental_bundle(dbc_source, staged, args.locale)

        dbc_hashes = install_server_dbcs(staged, server_dbc)
        installed_client = install_patch(client_dir, staged, args.locale)

        # Keep Adventurer's ownership state truthful so a later normal
        # update/verify knows exactly which generated artifacts are installed.
        state["dbc"] = {
            "directory": str(server_dbc),
            "files": dbc_hashes,
        }
        state["client"] = {
            "directory": str(client_dir),
            "installed": installed_client,
        }
        save_state(core, state)

        problems = verify_state(core, state)
        if problems:
            raise RuneClientExperimentError(
                "Post-install ownership verification failed:\n  " + "\n  ".join(problems)
            )

    print("Rune client-authority experiment installed.")
    print(f"  core:          {core}")
    print(f"  server DBC:    {server_dbc}")
    print(f"  client:        {client_dir}")
    print(f"  spell IDs:     {', '.join(str(x) for x in EXPERIMENT_SPELL_IDS)}")
    for spell_id in EXPERIMENT_SPELL_IDS:
        print(
            f"  {spell_id}: server(power,rune,mana,mana%)={manifest['server_signatures'][str(spell_id)]} "
            f"client={manifest['client_signatures'][str(spell_id)]}"
        )
    print("  NEXT: fully close WoW, reopen it, then reproduce the two-rune regression.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="rune_client_authority_experiment.py")
    result.add_argument("--core-dir", required=True, type=Path)
    result.add_argument("--client-dir", required=True, type=Path)
    result.add_argument("--server-data-dir", type=Path)
    result.add_argument("--dbc-src", type=Path)
    result.add_argument("--locale", default=DEFAULT_LOCALE)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        apply_experiment(args)
    except (InstallError, RuneClientExperimentError, DBCError, OSError) as exc:
        parser().error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
