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
        self.assertIn("player->ResyncRunes(MAX_RUNES)", source)
        self.assertIn("player->AddRunePower(index)", source)
        self.assertIn("previousReadyMask & ~readyMask", source)
        self.assertIn("readyMask & ~previousReadyMask", source)
        self.assertIn(
            "playerClass == CLASS_DEATH_KNIGHT && context == CLASS_CONTEXT_ABILITY",
            source,
        )

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
