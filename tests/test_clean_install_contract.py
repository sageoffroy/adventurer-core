from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import adventurer  # noqa: E402
import core_patch  # noqa: E402


class CleanInstallContractTests(unittest.TestCase):
    def test_clean_install_uses_versioned_runtime_payload(self) -> None:
        runtime = (
            adventurer.PAYLOAD_ROOT
            / "src/server/scripts/Custom/adventurer_core.cpp"
        )
        collection = (
            adventurer.PAYLOAD_ROOT
            / "src/server/scripts/Custom/adventurer_collections.cpp"
        )
        self.assertTrue(runtime.is_file())
        self.assertTrue(collection.is_file())

        source = runtime.read_text(encoding="utf-8")
        self.assertIn("ADVENTURER_MAX_RAGE = 1000", source)
        self.assertIn("ADVENTURER_MAX_ENERGY = 100", source)
        self.assertIn("SetMaxPower(POWER_RAGE, ADVENTURER_MAX_RAGE)", source)
        self.assertIn("SetMaxPower(POWER_ENERGY, ADVENTURER_MAX_ENERGY)", source)
        self.assertIn('ADVENTURER_COMBO_PREFIX[] = "AdventurerCP"', source)
        for token in (
            "CLASS_DEATH_KNIGHT",
            "POWER_RUNIC_POWER",
            "POWER_RUNE",
            "MAX_RUNES",
            "GetRuneCooldown",
            "ResyncRunes",
            "AddRunePower",
            "PLAYERHOOK_ON_PLAYER_IS_CLASS",
        ):
            self.assertNotIn(token, source)

        collection_source = collection.read_text(encoding="utf-8")
        self.assertIn('TALENT_COLLECTION_REQUEST[] = "ADRAFT_TALENTS"', collection_source)
        self.assertIn('ADVENTURER_SUBCLASS_SKILLS[] = {900, 901, 902, 903}', collection_source)
        self.assertIn('"card_subclasses.csv"', collection_source)

    def test_core_patch_copies_all_packaged_runtimes_verbatim(self) -> None:
        source = inspect.getsource(core_patch.plan)
        self.assertIn("for payload_rel in PAYLOAD_FILES", source)
        self.assertIn("payload = payload_root / payload_rel", source)
        self.assertIn("patched = payload.read_bytes()", source)
        self.assertIn("PlannedFile(payload_rel, original, patched)", source)
        self.assertEqual(
            core_patch.PAYLOAD_FILES,
            (
                "src/server/scripts/Custom/adventurer_core.cpp",
                "src/server/scripts/Custom/adventurer_collections.cpp",
                "src/server/game/Spells/AdventurerSpellScaling.h",
            ),
        )

    def test_apply_path_uses_the_same_payload_root(self) -> None:
        source = inspect.getsource(adventurer.cmd_apply)
        self.assertIn("planned = plan_core(core, PAYLOAD_ROOT)", source)
        self.assertIn("build_patch(dbc_source, staged, args.locale)", source)
        self.assertIn("install_server_dbcs(generated, server_dbc)", source)
        self.assertIn("install_patch(client_dir, generated, args.locale)", source)
        self.assertIn("verify_state(core, state)", source)


if __name__ == "__main__":
    unittest.main()
