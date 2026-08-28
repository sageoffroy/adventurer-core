from __future__ import annotations

import csv
import io
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from client import build_archive_files, build_frame_xml_toc, DBC_NAMES
from core_patch import patch_spell_info, PatchError
from dbc import DBC, DBCError, set_u32, u32
from dk_adaptations import damage_range, load_spec, MARKER, patch_dk_directory, render_header, render_lua_data
from spelldraft_runtime import build_runtime_cards, build_runtime_subclasses, parse_talent_dbc
from subclasses import load_spec as load_subclasses

# Approved values, independently recorded before this implementation.
APPROVED = tuple(tuple(map(int, pair.split("-"))) for pair in """
8-9 9-10 10-11 11-12 13-14 14-15 15-16 16-17 18-20 21-22
23-25 25-27 28-30 30-32 33-35 35-37 37-40 40-43 42-45 44-48
47-50 49-53 51-55 54-58 56-60 59-63 61-66 63-68 66-71 68-73
70-76 73-78 75-81 77-83 80-86 82-88 84-91 87-94 89-96 92-99
94-101 96-104 99-106 101-109 103-111 106-114 108-117 110-119 113-122 115-124
118-127 120-129 122-132 125-134 127-137 130-140 133-143 136-147 138-150 141-153
144-156 147-159 150-162 153-165 155-167 158-170 161-173 165-178 170-183 174-188
178-193 183-198 187-203 195-211 203-220 211-228 219-237 227-245 227-245 227-245
""".split())

TALENTS = {
    49175: [49175, 50031, 50040],
    55061: [55061, 55062],
    49140: [49140, 49661, 49662, 49663, 49664],
    49036: [49036, 49562],
}


def make_native_dbcs(directory: Path) -> None:
    spec = load_spec()
    spells = []
    for spell, level in zip(spec["native_ranks"], spec["native_levels"]):
        row = bytearray(936)
        for field, value in {0: spell, 38: level, 39: level, 41: 5, 42: 0xFFFFFFF6,
                             71: 2, 72: 64, 74: 11, 80: 126, 117: 55095,
                             208: 15, 209: 2, 226: 3, 227: 16, 228: 77,
                             46: 3, 205: 133, 206: 1500, 86: 6, 87: 6}.items():
            set_u32(row, field, value)
        spells.append(row)
    for spell in (55095, 48263, 61261, 133, *(s for ranks in TALENTS.values() for s in ranks)):
        row = bytearray(936)
        # Arbitrary nonzero bytes detect accidental changes to auxiliaries.
        for field in range(234):
            set_u32(row, field, field + 100)
        set_u32(row, 0, spell)
        spells.append(row)
    DBC(234, 936, spells, bytearray(b"\0")).write(directory / "Spell.dbc")
    talents = []
    for root, ranks in TALENTS.items():
        row = bytearray(92)
        set_u32(row, 0, root)
        for i, rank in enumerate(ranks):
            set_u32(row, 4 + i, rank)
        talents.append(row)
    DBC(23, 92, talents, bytearray(b"\0")).write(directory / "Talent.dbc")


class IcyTouchTests(unittest.TestCase):
    def test_all_eighty_levels_match_the_approved_table(self):
        self.assertEqual(tuple(damage_range(level) for level in range(1, 81)), APPROVED)
        for level in (0, 81):
            with self.assertRaises(ValueError):
                damage_range(level)

    def test_native_rows_only_cost_level_and_description_are_changed(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            make_native_dbcs(directory)
            spell_path = directory / "Spell.dbc"
            before = DBC.read(spell_path)
            originals = {u32(row, 0): bytes(row) for row in before.records}
            talent_bytes = (directory / "Talent.dbc").read_bytes()
            self.assertTrue(patch_dk_directory(directory)["Spell.dbc"])
            after = DBC.read(spell_path)
            self.assertEqual(len(before.records), len(after.records))
            self.assertEqual(set(originals), {u32(row, 0) for row in after.records})
            changed_fields = {12, 13, 14, 15, 41, 42, 43, 44, 45, 77, 204, 226, 228, *range(170, 186)}
            for row in after.records:
                spell = u32(row, 0)
                if spell not in load_spec()["native_ranks"]:
                    self.assertEqual(bytes(row), originals[spell], spell)
                    continue
                allowed = changed_fields | ({38, 39, 74, 80} if spell == 45477 else set())
                for field in range(234):
                    if field not in allowed:
                        self.assertEqual(row[4*field:4*field+4], originals[spell][4*field:4*field+4], (spell, field))
                self.assertEqual(u32(row, 204), 8)
                for field in (41, 42, 226, 228):
                    self.assertEqual(u32(row, field), 0)
                self.assertEqual(u32(row, 117), 55095)
                self.assertEqual(struct.unpack_from("<f", row, 77*4)[0], 0)
                for locale in (0, 6, 7):
                    start = u32(row, 170 + locale)
                    text = bytes(after.strings[start:]).split(b"\0", 1)[0].decode()
                    self.assertIn(MARKER, text)
                    self.assertIn("$55095d", text)
            root = next(row for row in after.records if u32(row, 0) == 45477)
            self.assertEqual((u32(root, 38), u32(root, 39)), (1, 1))
            self.assertEqual((u32(root, 80)+1, u32(root, 80)+u32(root, 74)), (8, 9))
            self.assertEqual((directory / "Talent.dbc").read_bytes(), talent_bytes)
            first = spell_path.read_bytes()
            self.assertFalse(patch_dk_directory(directory)["Spell.dbc"])
            self.assertEqual(spell_path.read_bytes(), first)

    def test_missing_rank_trigger_or_talent_fails_before_writing(self):
        for case in ("rank", "trigger", "talent", "duplicate", "layout"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as td:
                directory = Path(td)
                make_native_dbcs(directory)
                path = directory / "Spell.dbc"
                dbc = DBC.read(path)
                if case == "rank":
                    dbc.records = [r for r in dbc.records if u32(r, 0) != 49909]
                elif case == "trigger":
                    set_u32(dbc.records[0], 117, 0)
                elif case == "talent":
                    dbc.records = [r for r in dbc.records if u32(r, 0) != 50040]
                elif case == "duplicate":
                    dbc.records.append(bytearray(dbc.records[0]))
                else:
                    dbc.fields = 233
                dbc.write(path)
                before = path.read_bytes()
                with self.assertRaises(DBCError):
                    patch_dk_directory(directory)
                self.assertEqual(path.read_bytes(), before)

    def test_native_catalog_generates_dependent_talents_through_existing_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            make_native_dbcs(directory)
            base = (ROOT / "config/spelldraft/cards.csv").read_text()
            metadata = (ROOT / "config/spelldraft/catalog_metadata.csv").read_text()
            generated, _ = build_runtime_cards(base, metadata, parse_talent_dbc(directory / "Talent.dbc"))
            rows = list(csv.DictReader(io.StringIO(generated), delimiter=";"))
            icy = [r for r in rows if r["key"] == "icy_touch"]
            self.assertEqual(len(icy), 1)
            self.assertEqual((icy[0]["rank_grants"], icy[0]["source_level"]), ("45477", "1"))
            for root, ranks in TALENTS.items():
                talent = next(r for r in rows if r["key"] == f"talent_{root}")
                self.assertEqual(talent["requires_any"], "211:1")
                self.assertEqual(talent["rank_grants"], "/".join(map(str, ranks)))
            self.assertIn("211;spellcaster", build_runtime_subclasses(generated, base, load_subclasses()))

    def test_native_core_patch_preserves_other_spells_and_explicit_overrides(self):
        from test_core_patch import FILES
        source = FILES["src/server/game/Spells/SpellInfo.cpp"]
        result = patch_spell_info(source)
        self.assertEqual(patch_spell_info(result), result)
        for token in ("(!bp || *bp == BasePoints)", "EffectIndex == EFFECT_0",
                      "caster->getClass() == CLASS_ADVENTURER",
                      "IcyTouchManaCost(caster->GetCreateMana())", "powerCost += int32(CalculatePct"):
            self.assertIn(token, result)
        with self.assertRaises(PatchError):
            patch_spell_info(source.replace("int32 randomPoints", "int randomPoints"))

    def test_client_packages_the_same_curve_after_native_tooltip_creation(self):
        header = ROOT / "payload/core/src/server/game/Spells/AdventurerSpellScaling.h"
        self.assertEqual(header.read_bytes(), render_header())
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            for name in DBC_NAMES:
                (directory / name).write_bytes(name.encode())
            root, locale = build_archive_files(directory)
            self.assertTrue(root["Interface\\FrameXML\\AdventurerSpellTooltips.lua"].startswith(render_lua_data()))
            toc = build_frame_xml_toc().decode()
            self.assertLess(toc.index("ItemRef.xml"), toc.index("AdventurerSpellTooltips.lua"))
            self.assertEqual(root["DBFilesClient\\Spell.dbc"], locale["DBFilesClient\\Spell.dbc"])

    @unittest.skipUnless(shutil.which("lua5.1"), "Lua 5.1 not installed (required in CI)")
    def test_lua_tooltips_follow_all_levels_and_support_both_spell_api_shapes(self):
        bootstrap = '''
local level, spell, api, className, classId = 1, 45477, 3, "Aventurero", 10
function UnitLevel() return level end
function UnitClass() return className, nil, classId end
local function frame(name)
    local result = {}
    local line = {text=""}
    function line:GetText() return self.text end
    function line:SetText(value) self.text = value end
    _G[name .. "TextLeft1"] = line
    function result:GetName() return name end
    function result:NumLines() return 1 end
    function result:GetSpell()
        if api == 2 then return "Icy Touch", spell end
        return "Icy Touch", "Rank 1", spell
    end
    function result:HookScript(event, callback)
        assert(event == "OnTooltipSetSpell")
        self.callback = callback
    end
    function result:Show() end
    return result
end
GameTooltip, ItemRefTooltip = frame("GameTooltip"), frame("ItemRefTooltip")
'''
        assertions = '''
for _, tooltip in ipairs({GameTooltip, ItemRefTooltip}) do
    local line = _G[tooltip:GetName() .. "TextLeft1"]
    for _, id in ipairs({45477, 49896, 49903, 49904, 49909}) do
        spell = id
        for mode = 2, 3 do
            api = mode
            for n = 1, 80 do
                level = n
                line.text = "Base: " .. IcyTouchDamageMarker
                tooltip.callback(tooltip)
                local expected = IcyTouchLevels[n][1] .. "–" .. IcyTouchLevels[n][2]
                assert(line.text == "Base: " .. expected, tostring(n) .. ": " .. line.text)
            end
        end
    end
    -- WotLK may return no class ID/token for the custom class.
    level, spell, classId = 20, 45477, nil
    line.text = IcyTouchDamageMarker
    tooltip.callback(tooltip)
    assert(line.text == "44–48")
    -- Non-Adventurer spell links retain the static native-rank fallback.
    className, classId, spell = "Mage", 8, 49896
    line.text = IcyTouchDamageMarker
    tooltip.callback(tooltip)
    assert(line.text == "144–156")
    -- Never change another spell's description.
    spell = 133
    line.text = "Fireball unchanged"
    tooltip.callback(tooltip)
    assert(line.text == "Fireball unchanged")
    className, classId = "Aventurero", 10
end
'''
        payload = (bootstrap + render_lua_data().decode()
                   + (ROOT / "client/AdventurerSpellTooltips.lua").read_text() + assertions)
        subprocess.run(["lua5.1", "-"], input=payload, text=True, check=True, capture_output=True)

    @unittest.skipUnless(shutil.which("g++"), "C++ compiler not installed")
    def test_production_cpp_curve_and_cost_execute_with_exact_rounding(self):
        header_dir = ROOT / "payload/core/src/server/game/Spells"
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            source = directory / "curve.cpp"
            source.write_text('''#include "AdventurerSpellScaling.h"
#include <iostream>
int main() {
    using namespace AdventurerSpells;
    static_assert(IsIcyTouch(45477) && IsIcyTouch(49909) && !IsIcyTouch(55095));
    static_assert(IcyTouchRange(0).minimum == 8 && IcyTouchRange(81).maximum == 245);
    for (unsigned level = 1; level <= 80; ++level) {
        auto r = IcyTouchRange(level);
        std::cout << r.minimum << " " << r.maximum << "\\n";
    }
    for (unsigned mana : {0u, 1u, 6u, 7u, 18u, 19u, 100u, 0xFFFFFFFFu})
        std::cout << IcyTouchManaCost(mana) << "\\n";
}
''')
            binary = directory / "curve"
            subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", str(header_dir), str(source), "-o", str(binary)], check=True, capture_output=True, text=True)
            lines = subprocess.check_output([str(binary)], text=True).splitlines()
            self.assertEqual(tuple(tuple(map(int, line.split())) for line in lines[:80]), APPROVED)
            self.assertEqual(list(map(int, lines[80:])), [1, 1, 1, 1, 1, 2, 8, 343597384])


if __name__ == "__main__":
    unittest.main()
