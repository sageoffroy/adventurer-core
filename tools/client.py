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
from subclasses import patch_subclass_directory
from talents import patch_talent_directory

ROOT = Path(__file__).resolve().parent.parent
CHARACTER_CREATE_BASELINE = ROOT / "client" / "baseline" / "CharacterCreate.lua"
FRAME_XML_BASELINE = ROOT / "client" / "baseline" / "FrameXML.toc"
ADVENTURER_PLAYER_FRAME = ROOT / "client" / "AdventurerPlayerFrame.xml"
ADVENTURER_RESOURCES = ROOT / "client" / "AdventurerResources.lua"
ADVENTURER_DRAFT_META = ROOT / "client" / "AdventurerDraftMeta.lua"
ADVENTURER_COLLECTIONS = ROOT / "client" / "AdventurerCollections.lua"
ADVENTURER_FRAME_ART = ROOT / "client" / "art" / "UI-AdventurerFrame.blp"
ADVENTURER_PLAYER_FRAME_INTERNAL = "Interface\\FrameXML\\AdventurerPlayerFrame.xml"
ADVENTURER_DRAFT_META_INTERNAL = "Interface\\FrameXML\\AdventurerDraftMeta.lua"
ADVENTURER_COLLECTIONS_INTERNAL = "Interface\\FrameXML\\AdventurerCollections.lua"
ADVENTURER_FRAME_INTERNAL = "Interface\\Adventurer\\UI-AdventurerFrame.blp"
DEFAULT_LOCALE = "esMX"
PROJECT_SUFFIX = "Z"
OWNER_MANIFEST = ".adventurer-core.json"
LEGACY_OWNER_MANIFEST = ".aventureros-spelldraft.json"

CLASS_DBCS = (
    "ChrClasses.dbc",
    "CharBaseInfo.dbc",
    "CharStartOutfit.dbc",
    "SkillLine.dbc",
    "SkillLineAbility.dbc",
    "SkillRaceClassInfo.dbc",
)
TALENT_DBCS = (
    "TalentTab.dbc",
    "Talent.dbc",
    "Spell.dbc",
)
# SpellIcon.dbc is read only to resolve existing Blizzard icon IDs by name. It is
# never modified or packaged by Adventurer Core.
TALENT_SOURCE_ONLY_DBCS = ("SpellIcon.dbc",)
DBC_NAMES = CLASS_DBCS + TALENT_DBCS
DBC_SOURCE_NAMES = DBC_NAMES + TALENT_SOURCE_ONLY_DBCS

# Native talents are one atomic client bundle. Some 3.3.5a client patch stacks
# can resolve DBFilesClient data from root and locale archives differently.
# Keeping the exact same TalentTab/Talent/Spell bytes in both Z archives avoids
# a split state where the tree exists but its cloned spell rows come from stock.
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
    if not CHARACTER_CREATE_BASELINE.is_file():
        raise ClientError(
            f"Missing bundled CharacterCreate baseline: {CHARACTER_CREATE_BASELINE}"
        )
    text = CHARACTER_CREATE_BASELINE.read_text(encoding="utf-8")

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


def build_frame_xml_toc() -> bytes:
    if not FRAME_XML_BASELINE.is_file():
        raise ClientError(f"Missing bundled FrameXML baseline: {FRAME_XML_BASELINE}")

    text = FRAME_XML_BASELINE.read_text(encoding="utf-8")
    marker = "PlayerFrame.xml\nPartyFrame.xml"
    replacement = (
        "PlayerFrame.xml\n"
        "AdventurerPlayerFrame.xml\n"
        "AdventurerResources.lua\n"
        "AdventurerDraftMeta.lua\n"
        "AdventurerCollections.lua\n"
        "PartyFrame.xml"
    )

    if replacement in text:
        raise ClientError("FrameXML baseline must remain pristine")
    if text.count(marker) != 1:
        raise ClientError(
            "FrameXML baseline is not the expected 3.3.5a revision: "
            f"PlayerFrame/PartyFrame anchor count={text.count(marker)}"
        )

    return text.replace(marker, replacement, 1).encode("utf-8")


def build_adventurer_player_frame_xml() -> bytes:
    if not ADVENTURER_PLAYER_FRAME.is_file():
        raise ClientError(f"Missing Adventurer PlayerFrame XML: {ADVENTURER_PLAYER_FRAME}")

    payload = ADVENTURER_PLAYER_FRAME.read_bytes()
    required = (
        b'name="PlayerFrameEnergyBar"',
        b'name="PlayerFrameRageBar"',
        b'name="PlayerFrameEnergyBarText"',
        b'name="PlayerFrameRageBarText"',
        b'<AbsDimension x="92" y="11"/>',
        b'<AbsDimension x="117" y="-65"/>',
        b'<AbsDimension x="12" y="38"/>',
        b'<AbsDimension x="3" y="-24"/>',
        b'orientation="VERTICAL"',
        b'Interface\\TargetingFrame\\UI-StatusBar',
    )
    missing = [token.decode("ascii") for token in required if token not in payload]
    if missing:
        raise ClientError(
            "Adventurer PlayerFrame XML is missing reference-layout markers: "
            + ", ".join(missing)
        )

    forbidden = (
        b"TotalAbsorbBarTemplate",
        b"HealAbsorbBarTemplate",
        b"SetAtlas",
        b"PlayerPrimaryStat",
    )
    present = [token.decode("ascii") for token in forbidden if token in payload]
    if present:
        raise ClientError(
            "Adventurer PlayerFrame XML contains non-stock client widgets: "
            + ", ".join(present)
        )

    return payload


def build_adventurer_resources_lua() -> bytes:
    if not ADVENTURER_RESOURCES.is_file():
        raise ClientError(f"Missing Adventurer resource HUD: {ADVENTURER_RESOURCES}")

    payload = ADVENTURER_RESOURCES.read_bytes()
    required = (
        b"ADVENTURER_CLASS_ID = 10",
        b"AdventurerResourceFrame",
        b"PlayerFrameRageBar",
        b"PlayerFrameEnergyBar",
        b"ADVENTURER_FRAME_TEXTURE",
        b"ADVENTURER_FRAME_TEX_RIGHT = 0.07421875",
        b"ApplyReferencePlayerFrameLayout",
        b"PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)",
        b"PlayerFrameHealthBar:SetWidth(HEALTH_WIDTH)",
        b"PlayerFrameManaBar:SetWidth(MANA_WIDTH)",
        b"hooksecurefunc(\"PlayerFrame_ToPlayerArt\"",
        b'COMBO_PREFIX = \"AdventurerCP\"',
        b"local nativeGetComboPoints = GetComboPoints",
        b"GetComboPoints = function(unit, target)",
        b'unit == \"player\" and target == \"target\"',
        b"return nativeGetComboPoints(unit, target)",
        b'RegisterEvent(\"CHAT_MSG_ADDON\")',
        b"RegisterAddonMessagePrefix(COMBO_PREFIX)",
    )
    missing = [token.decode("ascii") for token in required if token not in payload]
    if missing:
        raise ClientError(
            "Adventurer resource HUD is missing required contract markers: "
            + ", ".join(missing)
        )

    forbidden = (
        b"POWER_RUNIC_POWER",
        b"AdventurerRunicPowerBar",
        b"RuneFrame",
        b"RUNE_POWER_UPDATE",
        b"GetRuneCooldown",
        b"RuneButton_Update",
        b"AdventurerPlayerFrameArtOverlay",
        b"CreateResourceBar",
        b'CreateFrame(\"StatusBar\"',
        b"AdventurerRageBar",
        b"AdventurerEnergyBar",
    )
    present = [token.decode("ascii") for token in forbidden if token in payload]
    if present:
        raise ClientError(
            "Adventurer resource HUD contains removed resource/layout state: "
            + ", ".join(present)
        )

    if payload.count(b"GetComboPoints = function(unit, target)") != 1:
        raise ClientError("Adventurer resource HUD must contain exactly one combo-point shim")
    if b"SpellDraft" in payload:
        raise ClientError("Adventurer resource HUD must not depend on SpellDraft")

    return payload


def build_adventurer_draft_meta_lua() -> bytes:
    if not ADVENTURER_DRAFT_META.is_file():
        raise ClientError(f"Missing Adventurer Draft meta UI: {ADVENTURER_DRAFT_META}")

    payload = ADVENTURER_DRAFT_META.read_bytes()
    required = (
        b'ADRAFT_REROLL',
        b'ADRAFT_BLESS:',
        b'ADRAFT_DESTROY:',
        b'AdventurerDraftRerollButton',
        b'AdventurerDraftBlessButton',
        b'AdventurerDraftDestroyButton',
        b'adventurerOriginalDraftClick',
        b'blessedCardId',
        b'CHAT_MSG_ADDON',
    )
    missing = [token.decode("ascii") for token in required if token not in payload]
    if missing:
        raise ClientError(
            "Adventurer Draft meta UI is missing required contract markers: "
            + ", ".join(missing)
        )
    return payload


def build_adventurer_collections_lua() -> bytes:
    if not ADVENTURER_COLLECTIONS.is_file():
        raise ClientError(f"Missing Adventurer talent collection UI: {ADVENTURER_COLLECTIONS}")

    payload = ADVENTURER_COLLECTIONS.read_bytes()
    required = (
        b'ADRAFT_TALENTS',
        b'AdventurerTalentCollectionFrame',
        b'AdventurerTalentCollectionTab',
        b'FauxScrollFrameTemplate',
        b'NativeToggleTalentFrame',
        b'function ToggleTalentFrame()',
        b'mercenary',
        b'explorer',
        b'spellcaster',
        b'illuminated',
        b'CHAT_MSG_ADDON',
    )
    missing = [token.decode("ascii") for token in required if token not in payload]
    if missing:
        raise ClientError(
            "Adventurer talent collection UI is missing required contract markers: "
            + ", ".join(missing)
        )
    return payload


def build_adventurer_frame_art() -> bytes:
    if not ADVENTURER_FRAME_ART.is_file():
        raise ClientError(f"Missing Adventurer frame art: {ADVENTURER_FRAME_ART}")

    payload = ADVENTURER_FRAME_ART.read_bytes()
    if len(payload) < 20 or payload[:4] != b"BLP2":
        raise ClientError("Adventurer frame art must be a BLP2 texture")

    width = int.from_bytes(payload[12:16], "little")
    height = int.from_bytes(payload[16:20], "little")
    if (width, height) != (256, 128):
        raise ClientError(
            f"Adventurer frame art must be 256x128, got {width}x{height}"
        )

    return payload


def patch_dbc_copy(source: Path, work: Path) -> dict[str, bool]:
    missing = [name for name in DBC_SOURCE_NAMES if not (source / name).is_file()]
    if missing:
        raise ClientError("DBC source is incomplete: " + ", ".join(missing))
    for name in DBC_SOURCE_NAMES:
        shutil.copy2(source / name, work / name)
    changed = patch_directory(work)
    changed.update(patch_subclass_directory(work))
    changed.update(patch_talent_directory(work))
    return changed


def build_archive_files(work: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    root_files = {
        "Interface\\GlueXML\\CharacterCreate.lua": build_character_create_lua(),
        "Interface\\FrameXML\\FrameXML.toc": build_frame_xml_toc(),
        ADVENTURER_PLAYER_FRAME_INTERNAL: build_adventurer_player_frame_xml(),
        "Interface\\FrameXML\\AdventurerResources.lua": build_adventurer_resources_lua(),
        ADVENTURER_DRAFT_META_INTERNAL: build_adventurer_draft_meta_lua(),
        ADVENTURER_COLLECTIONS_INTERNAL: build_adventurer_collections_lua(),
        ADVENTURER_FRAME_INTERNAL: build_adventurer_frame_art(),
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
        "frame_xml_toc_sha256": hashlib.sha256(build_frame_xml_toc()).hexdigest(),
        "player_frame_xml_sha256": hashlib.sha256(build_adventurer_player_frame_xml()).hexdigest(),
        "resource_hud_sha256": hashlib.sha256(build_adventurer_resources_lua()).hexdigest(),
        "draft_meta_sha256": hashlib.sha256(build_adventurer_draft_meta_lua()).hexdigest(),
        "talent_collection_sha256": hashlib.sha256(build_adventurer_collections_lua()).hexdigest(),
        "adventurer_frame_sha256": hashlib.sha256(build_adventurer_frame_art()).hexdigest(),
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