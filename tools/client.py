#!/usr/bin/env python3
"""Build and safely install the Adventurer Core WotLK client patch."""

from __future__ import annotations

import argparse
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
)
DBC_NAMES = CLASS_DBCS + TALENT_DBCS

# Native talents are one atomic client bundle. Some 3.3.5a client patch stacks
# can resolve DBFilesClient data from the root and locale archives differently.
# Keeping the exact same TalentTab/Talent/Spell bytes in both Z archives avoids
# a split state where the tree exists but its cloned spell rows come from a
# lower-priority stock Spell.dbc.
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
    root_files = {
        "Interface\\GlueXML\\CharacterCreate.lua": build_character_create_lua(),
        **{
            f"DBFilesClient\\{name}": (work / name).read_bytes()
            for name in ROOT_SHARED_DBCS
        },
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

    manifest = {
        "schema": 1,
        "owner": "adventurer-core",
        "class_id": 10,
        "locale": locale,
        "dbc_source": str(dbc_source),
        "dbc_payload": list(DBC_NAMES),
        "root_dbc_payload": list(ROOT_SHARED_DBCS),
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
        raise ClientError(f"Refusing to overwrite unowned {label}: {path}")
    actual = sha256(path)
    if actual != expected_hash:
        raise ClientError(
            f"Refusing to overwrite modified {label}: {path}\n"
            f"  owned sha256: {expected_hash}\n  current sha256: {actual}"
        )


def existing_ownership(client: Path) -> tuple[str | None, dict | None]:
    current = load_json(client / OWNER_MANIFEST)
    if current:
        if current.get("owner") != "adventurer-core":
            raise ClientError(f"Invalid Adventurer Core owner marker: {client / OWNER_MANIFEST}")
        return "current", current

    legacy = load_json(client / LEGACY_OWNER_MANIFEST)
    if legacy:
        if legacy.get("owner") != "Aventureros de Azeroth / SpellDraft":
            raise ClientError(f"Refusing unknown legacy owner marker: {client / LEGACY_OWNER_MANIFEST}")
        return "legacy", legacy
    return None, None


def install_patch(client: Path, build: Path, locale: str = DEFAULT_LOCALE) -> dict:
    client = client.expanduser().resolve()
    build = build.expanduser().resolve()
    wow = client / "Wow.exe"
    if not wow.is_file():
        wow = client / "wow.exe"
    if not wow.is_file():
        raise ClientError(f"Not a WoW 3.3.5a client directory: {client}")

    build_manifest = load_json(build / "manifest.json")
    if not build_manifest or build_manifest.get("owner") != "adventurer-core":
        raise ClientError(f"Invalid Adventurer Core build manifest: {build / 'manifest.json'}")
    if build_manifest.get("locale") != locale:
        raise ClientError(
            f"Build locale {build_manifest.get('locale')!r} does not match requested {locale!r}"
        )

    source_root = build / build_manifest["root_patch"]
    source_locale = build / build_manifest["locale_patch"]
    if sha256(source_root) != build_manifest["root_sha256"]:
        raise ClientError("Generated root MPQ does not match build manifest")
    if sha256(source_locale) != build_manifest["locale_sha256"]:
        raise ClientError("Generated locale MPQ does not match build manifest")

    target_root = client / "Data" / f"patch-{PROJECT_SUFFIX}.mpq"
    target_locale = client / "Data" / locale / f"patch-{locale}-{PROJECT_SUFFIX.lower()}.mpq"
    target_locale.parent.mkdir(parents=True, exist_ok=True)

    owner_kind, owner = existing_ownership(client)
    if owner:
        verify_owned_file(target_root, owner.get("root_sha256"), "root Z patch")
        old_locale_rel = owner.get("locale_patch")
        old_locale = client / old_locale_rel if old_locale_rel else None
        if old_locale and old_locale.exists():
            verify_owned_file(old_locale, owner.get("locale_sha256"), "locale Z patch")
        if old_locale != target_locale and target_locale.exists():
            raise ClientError(f"Requested locale target is occupied: {target_locale}")
    else:
        verify_owned_file(target_root, None, "root Z patch")
        verify_owned_file(target_locale, None, "locale Z patch")
        old_locale = None

    backup_dir = client / ".adventurer-core-backup"
    backup_dir.mkdir(exist_ok=True)
    backup_records: dict[str, str] = {}
    for target in (target_root, target_locale):
        if target.is_file():
            relative = target.relative_to(client).as_posix()
            backup = backup_dir / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                shutil.copy2(target, backup)
            backup_records[relative] = sha256(backup)

    shutil.copy2(source_root, target_root)
    shutil.copy2(source_locale, target_locale)

    if owner and old_locale and old_locale != target_locale and old_locale.exists():
        old_locale.unlink()

    installed = {
        "schema": 1,
        "owner": "adventurer-core",
        "locale": locale,
        "official_patch_family": PROJECT_SUFFIX,
        "root_patch": target_root.relative_to(client).as_posix(),
        "root_sha256": sha256(target_root),
        "locale_patch": target_locale.relative_to(client).as_posix(),
        "locale_sha256": sha256(target_locale),
        "build_manifest_sha256": sha256(build / "manifest.json"),
        "migrated_from": owner_kind,
        "backups": backup_records,
    }
    (client / OWNER_MANIFEST).write_text(
        json.dumps(installed, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if owner_kind == "legacy":
        (client / LEGACY_OWNER_MANIFEST).unlink(missing_ok=True)

    wdb = client / "Cache" / "WDB"
    if wdb.exists():
        shutil.rmtree(wdb)
    return installed


def install_server_dbcs(build: Path, server_dbc_dir: Path) -> dict[str, str]:
    build = build.expanduser().resolve()
    server_dbc_dir = server_dbc_dir.expanduser().resolve()
    source = build / "server-dbc"
    if not source.is_dir():
        raise ClientError(f"Generated server DBC directory missing: {source}")
    server_dbc_dir.mkdir(parents=True, exist_ok=True)

    hashes: dict[str, str] = {}
    for name in DBC_NAMES:
        src = source / name
        if not src.is_file():
            raise ClientError(f"Generated server DBC missing: {src}")
        dst = server_dbc_dir / name
        backup = dst.with_name(dst.name + ".pre-adventurer-core.bak")
        if dst.exists() and not backup.exists():
            shutil.copy2(dst, backup)
        shutil.copy2(src, dst)
        hashes[name] = sha256(dst)
    return hashes


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build")
    build_parser.add_argument("--dbc-src", required=True, type=Path)
    build_parser.add_argument("--output-dir", required=True, type=Path)
    build_parser.add_argument("--locale", default=DEFAULT_LOCALE)

    install_parser = sub.add_parser("install")
    install_parser.add_argument("--client-dir", required=True, type=Path)
    install_parser.add_argument("--build-dir", required=True, type=Path)
    install_parser.add_argument("--server-dbc-dir", required=True, type=Path)
    install_parser.add_argument("--locale", default=DEFAULT_LOCALE)

    args = parser.parse_args()
    try:
        if args.command == "build":
            manifest = build_patch(args.dbc_src, args.output_dir, args.locale)
            print("Adventurer client/server DBC bundle built.")
            print(f"  root MPQ sha256:   {manifest['root_sha256']}")
            print(f"  locale MPQ sha256: {manifest['locale_sha256']}")
        else:
            install_server_dbcs(args.build_dir, args.server_dbc_dir)
            installed = install_patch(args.client_dir, args.build_dir, args.locale)
            print("Adventurer client/server DBC bundle installed.")
            print(f"  client root: {installed['root_patch']}")
            print(f"  client locale: {installed['locale_patch']}")
        return 0
    except (ClientError, DBCError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
