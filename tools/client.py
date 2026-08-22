#!/usr/bin/env python3
"""Build and safely install the Adventurer Core WotLK client patch."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from dbc import DBCError, patch_directory
from mpq import write_mpq
from talents import patch_talent_directory

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "client" / "baseline" / "CharacterCreate.lua"
ICON_DIR = ROOT / "client" / "icons"
DEFAULT_LOCALE = "esMX"
PROJECT_SUFFIX = "Z"
OWNER_MANIFEST = ".adventurer-core.json"
LEGACY_OWNER_MANIFEST = ".aventureros-spelldraft.json"

CLASS_DBCS = (
    "ChrClasses.dbc",
    "CharBaseInfo.dbc",
    "CharStartOutfit.dbc",
    "SkillRaceClassInfo.dbc",
)
TALENT_DBCS = (
    "TalentTab.dbc",
    "Talent.dbc",
    "Spell.dbc",
    "SpellIcon.dbc",
)
DBC_NAMES = CLASS_DBCS + TALENT_DBCS

# Native talents are one atomic client bundle. Some 3.3.5a client patch stacks
# can resolve DBFilesClient data from root and locale archives differently.
# Keeping the exact same talent DBC bytes in both Z archives avoids split state
# where the tree exists but its cloned spell/icon rows come from stock DBCs.
ROOT_SHARED_DBCS = TALENT_DBCS


class ClientError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_lua_function(text: str, start_marker: str, next_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ClientError(f"CharacterCreate baseline missing {start_marker}")
    end = text.find(next_marker, start)
    if end < 0:
        raise ClientError(f"CharacterCreate baseline missing boundary {next_marker}")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def build_character_create_lua() -> bytes:
    if not BASELINE.is_file():
        raise ClientError(f"Missing bundled CharacterCreate baseline: {BASELINE}")
    text = BASELINE.read_text(encoding="utf-8")

    marker = "local TECHNICAL_CLASS_ID = 1; -- Warrior; hidden from the player."
    if marker not in text:
        raise ClientError("CharacterCreate baseline is not the expected known-good revision")
    text = text.replace(marker, "local ADVENTURER_CLASS_INDEX = nil;", 1)

    start = text.find("local function SelectTechnicalClassForCurrentRace()")
    end = text.find("function CharacterCreate_OnLoad(self)", start)
    if start < 0 or end < 0:
        raise ClientError("CharacterCreate baseline missing class resolver")
    text = text[:start] + """local function ResolveOnlyValidClassForCurrentRace()
\tlocal selectedRace = GetSelectedRace();
\tlocal found = nil;
\tlocal validCount = 0;

\tfor classIndex=1, CharacterCreate.numClasses do
\t\tif ( IsRaceClassValid(selectedRace, classIndex) ) then
\t\t\tfound = classIndex;
\t\t\tvalidCount = validCount + 1;
\t\tend
\tend

\tif ( validCount ~= 1 ) then
\t\tmessage(\"Adventurer Core: expected exactly one valid class for this race, found \"..validCount..\".\");
\t\treturn nil;
\tend

\treturn found;
end

local function SelectTechnicalClassForCurrentRace()
\tADVENTURER_CLASS_INDEX = ResolveOnlyValidClassForCurrentRace();
\tif ( not ADVENTURER_CLASS_INDEX ) then
\t\treturn nil;
\tend

\tSetSelectedClass(ADVENTURER_CLASS_INDEX);
\tSetCharacterClass(ADVENTURER_CLASS_INDEX);
\treturn ADVENTURER_CLASS_INDEX;
end

""" + text[end:]

    text = replace_lua_function(
        text,
        "function CharacterCreateEnumerateClasses(...)",
        "function SetCharacterRace(id)",
        """function CharacterCreateEnumerateClasses(...)
\tCharacterCreate.numClasses = select(\"#\", ...)/3;
\tADVENTURER_CLASS_INDEX = nil;
\tHideClassSelectionUI();
end""",
    )

    text = replace_lua_function(
        text,
        "function SetCharacterClass(id)",
        "function CharacterCreate_OnChar()",
        """function SetCharacterClass(id)
\tCharacterCreate.selectedClass = id;

\tlocal className, classFileName = GetSelectedClass();
\tlocal abilityIndex = 0;
\tlocal tempText = _G[\"CLASS_INFO_\"..classFileName..abilityIndex];
\tabilityText = \"\";
\twhile ( tempText ) do
\t\tabilityText = abilityText..tempText..\"\\n\\n\";
\t\tabilityIndex = abilityIndex + 1;
\t\ttempText = _G[\"CLASS_INFO_\"..classFileName..abilityIndex];
\tend

\tlocal coords = CLASS_ICON_TCOORDS[classFileName] or CLASS_ICON_TCOORDS[\"WARRIOR\"];
\tCharacterCreateClassIcon:SetTexCoord(coords[1], coords[2], coords[3], coords[4]);
\tCharacterCreateClassLabel:SetText(className);
\tCharacterCreateClassRolesText:SetText(abilityText);
\tCharacterCreateClassText:SetText(GetFlavorText(\"CLASS_\"..strupper(classFileName), GetSelectedSex())..\"|n|n\");
\tCharacterCreateClassScrollFrameScrollBar:SetValue(0);
end""",
    )

    old_create = """\telse
\t\tCreateCharacter(CharacterCreateNameEdit:GetText());
\tend"""
    new_create = """\telse
\t\tif ( not SelectTechnicalClassForCurrentRace() ) then
\t\t\treturn;
\t\tend
\t\tCreateCharacter(CharacterCreateNameEdit:GetText());
\tend"""
    if old_create not in text:
        raise ClientError("CharacterCreate baseline could not guard character creation")
    text = text.replace(old_create, new_create, 1)

    if "TECHNICAL_CLASS_ID" in text:
        raise ClientError("CharacterCreate still contains legacy technical class state")
    return text.encode("utf-8")


def load_custom_icon_assets() -> dict[str, bytes]:
    if not ICON_DIR.is_dir():
        return {}
    result: dict[str, bytes] = {}
    for source in sorted(ICON_DIR.glob("*.blp.b64")):
        name = source.name.removesuffix(".blp.b64")
        try:
            payload = base64.b64decode(source.read_text(encoding="ascii").strip(), validate=True)
        except ValueError as exc:
            raise ClientError(f"Invalid base64 icon asset: {source}") from exc
        if not payload.startswith(b"BLP2"):
            raise ClientError(f"Custom icon is not a BLP2 texture: {source}")
        internal = f"Interface\\Icons\\{name}.blp"
        if internal in result:
            raise ClientError(f"Duplicate custom icon asset: {internal}")
        result[internal] = payload
    return result


def patch_dbc_copy(source: Path, work: Path) -> dict[str, bool]:
    missing = [name for name in DBC_NAMES if not (source / name).is_file()]
    if missing:
        raise ClientError("DBC source is incomplete: " + ", ".join(missing))
    for name in DBC_NAMES:
        shutil.copy2(source / name, work / name)
    changed = patch_directory(work)
    changed.update(patch_talent_directory(work))
    return changed


def build_archive_files(work: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    icon_files = load_custom_icon_assets()
    root_files = {
        "Interface\\GlueXML\\CharacterCreate.lua": build_character_create_lua(),
        **{
            f"DBFilesClient\\{name}": (work / name).read_bytes()
            for name in ROOT_SHARED_DBCS
        },
        **icon_files,
    }
    locale_files = {
        f"DBFilesClient\\{name}": (work / name).read_bytes()
        for name in DBC_NAMES
    }

    shared = set(root_files) & set(locale_files)
    expected_shared = {
        f"DBFilesClient\\{name}" for name in ROOT_SHARED_DBCS
    }
    if shared != expected_shared:
        raise ClientError(
            "Unexpected root/locale DBC overlap: " + ", ".join(sorted(shared))
        )
    for internal_name in expected_shared:
        if root_files[internal_name] != locale_files[internal_name]:
            raise ClientError(f"Root/locale DBC payload differs for {internal_name}")

    return root_files, locale_files


def build_patch(dbc_source: Path, output: Path, locale: str = DEFAULT_LOCALE) -> dict:
    dbc_source = dbc_source.expanduser().resolve()
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="adventurer-core-") as tmp_name:
        work = Path(tmp_name)
        changed = patch_dbc_copy(dbc_source, work)

        root_patch = output / "Data" / f"patch-{PROJECT_SUFFIX}.mpq"
        locale_patch = output / "Data" / locale / f"patch-{locale}-{PROJECT_SUFFIX.lower()}.mpq"
        root_files, locale_files = build_archive_files(work)
        write_mpq(root_patch, root_files)
        write_mpq(locale_patch, locale_files)

        patched_dbc_dir = output / "server-dbc"
        patched_dbc_dir.mkdir(parents=True, exist_ok=True)
        for name in DBC_NAMES:
            shutil.copy2(work / name, patched_dbc_dir / name)

    custom_icons = sorted(load_custom_icon_assets())
    manifest = {
        "schema": 1,
        "owner": "adventurer-core",
        "class_id": 10,
        "locale": locale,
        "dbc_source": str(dbc_source),
        "dbc_payload": list(DBC_NAMES),
        "root_dbc_payload": list(ROOT_SHARED_DBCS),
        "custom_icon_payload": custom_icons,
        "dbc_changed": changed,
        "root_patch": str(root_patch.relative_to(output)),
        "root_sha256": sha256(root_patch),
        "locale_patch": str(locale_patch.relative_to(output)),
        "locale_sha256": sha256(locale_patch),
        "character_create_sha256": hashlib.sha256(build_character_create_lua()).hexdigest(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ClientError(f"Invalid ownership manifest {path}: {exc}") from exc


def verify_owned_file(path: Path, expected_hash: str | None, label: str) -> None:
    if not path.exists():
        return
    if not path.is_file():
        raise ClientError(f"{label} is not a file: {path}")
    if not expected_hash:
        raise ClientError(f"{label} already exists but is not owned by Adventurer Core: {path}")
    actual = sha256(path)
    if actual != expected_hash:
        raise ClientError(
            f"{label} was modified outside Adventurer Core: expected {expected_hash}, got {actual}"
        )


def existing_ownership(client_dir: Path) -> tuple[Path, dict | None]:
    modern = client_dir / OWNER_MANIFEST
    legacy = client_dir / LEGACY_OWNER_MANIFEST
    if modern.exists():
        return modern, load_json(modern)
    if legacy.exists():
        return legacy, load_json(legacy)
    return modern, None


def install_patch(client_dir: Path, build_dir: Path, locale: str = DEFAULT_LOCALE) -> dict:
    client_dir = client_dir.expanduser().resolve()
    build_dir = build_dir.expanduser().resolve()
    wow = client_dir / "Wow.exe"
    if not wow.is_file():
        wow = client_dir / "wow.exe"
    if not wow.is_file():
        raise ClientError(f"WoW 3.3.5a client not found: {client_dir}")

    source_root = build_dir / "Data" / f"patch-{PROJECT_SUFFIX}.mpq"
    source_locale = build_dir / "Data" / locale / f"patch-{locale}-{PROJECT_SUFFIX.lower()}.mpq"
    if not source_root.is_file() or not source_locale.is_file():
        raise ClientError(f"Built patch files missing under {build_dir}")

    data_dir = client_dir / "Data"
    locale_dir = data_dir / locale
    locale_dir.mkdir(parents=True, exist_ok=True)
    target_root = data_dir / source_root.name
    target_locale = locale_dir / source_locale.name

    owner_path, old_owner = existing_ownership(client_dir)
    old_owner = old_owner or {}
    verify_owned_file(target_root, old_owner.get("root_sha256"), "root Z patch")
    old_locale_rel = old_owner.get("locale_patch")
    if old_locale_rel:
        old_locale = client_dir / old_locale_rel
        verify_owned_file(old_locale, old_owner.get("locale_sha256"), "locale Z patch")
        if old_locale != target_locale and old_locale.exists():
            old_locale.unlink()
    else:
        verify_owned_file(target_locale, None, "locale Z patch")

    shutil.copy2(source_root, target_root)
    shutil.copy2(source_locale, target_locale)
    owner = {
        "schema": 1,
        "owner": "adventurer-core",
        "root_patch": str(target_root.relative_to(client_dir)),
        "root_sha256": sha256(target_root),
        "locale_patch": str(target_locale.relative_to(client_dir)),
        "locale_sha256": sha256(target_locale),
    }
    modern_owner = client_dir / OWNER_MANIFEST
    modern_owner.write_text(json.dumps(owner, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    legacy_owner = client_dir / LEGACY_OWNER_MANIFEST
    if legacy_owner.exists() and legacy_owner != modern_owner:
        legacy_owner.unlink()
    return owner


def install_server_dbcs(build_dir: Path, server_dbc_dir: Path) -> dict[str, str]:
    build_dir = build_dir.expanduser().resolve()
    server_dbc_dir = server_dbc_dir.expanduser().resolve()
    source = build_dir / "server-dbc"
    if not source.is_dir():
        raise ClientError(f"Built server DBC directory missing: {source}")
    if not server_dbc_dir.is_dir():
        raise ClientError(f"Server DBC directory not found: {server_dbc_dir}")
    result: dict[str, str] = {}
    for name in DBC_NAMES:
        source_file = source / name
        if not source_file.is_file():
            raise ClientError(f"Built server DBC missing: {source_file}")
        target = server_dbc_dir / name
        backup = server_dbc_dir / f"{name}.adventurer-backup"
        if target.is_file() and not backup.exists():
            shutil.copy2(target, backup)
        shutil.copy2(source_file, target)
        result[name] = sha256(target)
    return result


def restore_server_dbcs(server_dbc_dir: Path) -> None:
    server_dbc_dir = server_dbc_dir.expanduser().resolve()
    for name in DBC_NAMES:
        target = server_dbc_dir / name
        backup = server_dbc_dir / f"{name}.adventurer-backup"
        if backup.is_file():
            shutil.copy2(backup, target)
            backup.unlink()


def remove_client_patch(client_dir: Path) -> None:
    client_dir = client_dir.expanduser().resolve()
    owner_path, owner = existing_ownership(client_dir)
    if not owner:
        return
    root = client_dir / owner.get("root_patch", "")
    locale = client_dir / owner.get("locale_patch", "")
    verify_owned_file(root, owner.get("root_sha256"), "root Z patch")
    verify_owned_file(locale, owner.get("locale_sha256"), "locale Z patch")
    if root.is_file():
        root.unlink()
    if locale.is_file():
        locale.unlink()
    if owner_path.is_file():
        owner_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--dbc-src", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--locale", default=DEFAULT_LOCALE)

    install = sub.add_parser("install")
    install.add_argument("--client-dir", type=Path, required=True)
    install.add_argument("--build-dir", type=Path, required=True)
    install.add_argument("--server-dbc-dir", type=Path, required=True)
    install.add_argument("--locale", default=DEFAULT_LOCALE)

    remove = sub.add_parser("remove")
    remove.add_argument("--client-dir", type=Path, required=True)
    remove.add_argument("--server-dbc-dir", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "build":
            manifest = build_patch(args.dbc_src, args.output_dir, args.locale)
            print("Adventurer client/server DBC bundle built.")
            print(f"root patch: {manifest['root_patch']}")
            print(f"locale patch: {manifest['locale_patch']}")
            print(f"custom icons: {len(manifest['custom_icon_payload'])}")
        elif args.command == "install":
            install_server_dbcs(args.build_dir, args.server_dbc_dir)
            owner = install_patch(args.client_dir, args.build_dir, args.locale)
            print("Adventurer client/server DBC bundle installed.")
            print(f"client root: {owner['root_patch']}")
            print(f"client locale: {owner['locale_patch']}")
        elif args.command == "remove":
            remove_client_patch(args.client_dir)
            restore_server_dbcs(args.server_dbc_dir)
            print("Adventurer client/server DBC bundle removed.")
    except (ClientError, DBCError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
