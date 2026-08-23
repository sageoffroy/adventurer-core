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
        self.assertTrue(runtime.is_file())

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

    def test_core_patch_copies_packaged_runtime_verbatim(self) -> None:
        source = inspect.getsource(core_patch.plan)
        self.assertIn(
            'payload_rel = "src/server/scripts/Custom/adventurer_core.cpp"',
            source,
        )
        self.assertIn("payload = payload_root / payload_rel", source)
        self.assertIn("patched = payload.read_bytes()", source)
        self.assertIn("PlannedFile(payload_rel, original, patched)", source)

    def test_apply_path_uses_the_same_payload_root(self) -> None:
        source = inspect.getsource(adventurer.cmd_apply)
        self.assertIn("planned = plan_core(core, PAYLOAD_ROOT)", source)
        self.assertIn("build_patch(dbc_source, staged, args.locale)", source)
        self.assertIn("install_server_dbcs(generated, server_dbc)", source)
        self.assertIn("install_patch(client_dir, generated, args.locale)", source)
        self.assertIn("verify_state(core, state)", source)


if __name__ == "__main__":
    unittest.main()
