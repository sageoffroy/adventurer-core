from __future__ import annotations

import os
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import adventurer  # noqa: E402
import client  # noqa: E402
import core_patch  # noqa: E402
import upgrade  # noqa: E402
from adventurer import sha256_file  # noqa: E402
from test_core_patch import FILES  # noqa: E402
from upgrade import verify_owned_source_state  # noqa: E402


class UpgradeStateTests(unittest.TestCase):
    def test_generated_runtime_drift_is_not_part_of_source_verification(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            owned = core / "src" / "owned.cpp"
            owned.parent.mkdir(parents=True)
            owned.write_text("owned\n", encoding="utf-8")

            # Runtime hashes may be stale after a supported tools/client.py
            # refresh. The upgrade validates those artifacts through their own
            # ownership path later instead of treating them as source edits.
            state = {
                "files": [
                    {
                        "path": "src/owned.cpp",
                        "after_sha256": sha256_file(owned),
                    }
                ],
                "dbc": {
                    "directory": str(core / "dbc"),
                    "files": {"Spell.dbc": "stale-hash"},
                },
                "client": {
                    "directory": str(core / "client"),
                    "installed": {
                        "root_patch": "Data/patch-Z.mpq",
                        "root_sha256": "stale-hash",
                    },
                },
            }

            self.assertEqual(verify_owned_source_state(core, state), [])

    def test_source_drift_still_blocks_upgrade(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            owned = core / "src" / "owned.cpp"
            owned.parent.mkdir(parents=True)
            owned.write_text("original\n", encoding="utf-8")
            expected = sha256_file(owned)
            owned.write_text("manual edit\n", encoding="utf-8")

            problems = verify_owned_source_state(
                core,
                {
                    "files": [
                        {
                            "path": "src/owned.cpp",
                            "after_sha256": expected,
                        }
                    ]
                },
            )

            self.assertEqual(len(problems), 1)
            self.assertIn("modified: src/owned.cpp", problems[0])


class UpgradeOwnershipMigrationTests(unittest.TestCase):
    SPELL_INFO = "src/server/game/Spells/SpellInfo.cpp"
    HEADER = "src/server/game/Spells/AdventurerSpellScaling.h"
    # The stable installer owned these eight files, but not SpellInfo.cpp.
    STABLE_PATHS = {
        "src/server/shared/SharedDefines.h",
        "src/server/shared/enuminfo_SharedDefines.cpp",
        "src/server/game/Entities/Unit/StatSystem.cpp",
        "src/server/game/Entities/Player/PlayerStorage.cpp",
        "src/server/game/Entities/Player/Player.cpp",
        "src/server/scripts/Custom/custom_script_loader.cpp",
        "src/server/scripts/Custom/adventurer_core.cpp",
        "src/server/scripts/Custom/adventurer_collections.cpp",
    }

    @classmethod
    def setUpClass(cls):
        core_reference = os.environ.get("ADVENTURER_TEST_CORE")
        cls.native_sources = FILES if not core_reference else {
            relative: (Path(core_reference) / relative).read_text(encoding="utf-8")
            for relative in FILES
        }

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="adventurer-upgrade-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.core = self.root / "core"
        self.core.mkdir()
        for relative, source in self.native_sources.items():
            target = self.core / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        self.git("init")
        self.git("config", "user.name", "Upgrade test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("add", "src")
        self.git("commit", "-m", "native core fixture")
        commit = adventurer.validate_core_root(self.core)
        planned = core_patch.plan(self.core, adventurer.PAYLOAD_ROOT)
        stable = [item for item in planned if item.relative_path in self.STABLE_PATHS]
        self.assertEqual(len(stable), 8)
        self.state = adventurer.write_transaction(self.core, stable, commit)

        self.server_dbc = self.core / "env/dist/data/dbc"
        self.server_dbc.mkdir(parents=True)
        self.client_dir = self.root / "client"
        self.client_dir.mkdir()
        (self.client_dir / "Wow.exe").write_bytes(b"test client placeholder")
        for name in client.DBC_NAMES:
            (self.server_dbc / name).write_bytes(b"native " + name.encode())
        old_bundle = self.root / "stable-bundle"
        self.stage_bundle(old_bundle, b"stable ")
        self.state["dbc"] = {
            "directory": str(self.server_dbc),
            "files": client.install_server_dbcs(old_bundle, self.server_dbc),
        }
        self.state["client"] = {
            "directory": str(self.client_dir),
            "installed": client.install_patch(self.client_dir, old_bundle, "esMX"),
        }
        adventurer.save_state(self.core, self.state)
        self.spell_info = self.core / self.SPELL_INFO
        self.native = self.spell_info.read_bytes()
        self.backup = self.core / adventurer.STATE_DIR_NAME / "backups" / self.SPELL_INFO
        self.args = Namespace(
            core_dir=self.core, client_dir=self.client_dir,
            server_data_dir=self.server_dbc.parent, dbc_src=self.server_dbc,
            locale="esMX",
        )

    def git(self, *args):
        return adventurer.git(self.core, *args)

    def stage_bundle(self, destination, prefix):
        # Only generation is substituted: exercise the real preflight, source
        # transforms, Git checks, source/runtime installers and manifest writes.
        dbc = destination / "server-dbc"
        dbc.mkdir(parents=True)
        for name in client.DBC_NAMES:
            (dbc / name).write_bytes(prefix + name.encode())
        for relative in ("Data/patch-Z.mpq", "Data/esMX/patch-esMX-z.mpq"):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(prefix + relative.encode())

    def build_bundle(self, source, destination, locale):
        self.assertEqual(source, self.server_dbc)
        self.assertEqual(locale, "esMX")
        self.stage_bundle(destination, b"icy touch ")

    def apply_upgrade(self, builder=None):
        with patch.object(upgrade, "build_patch", side_effect=builder or self.build_bundle):
            with redirect_stdout(StringIO()):
                upgrade.apply_upgrade(self.args)

    def file_snapshot(self):
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for directory in (self.core / "src", self.core / "data",
                              self.core / "env", self.core / adventurer.STATE_DIR_NAME,
                              self.client_dir)
            for path in directory.rglob("*") if path.is_file()
        }

    def test_stable_upgrade_records_native_backup_and_is_idempotent(self):
        old_backups = {
            entry["path"]: (self.core / adventurer.STATE_DIR_NAME / "backups" / entry["path"]).read_bytes()
            for entry in self.state["files"] if entry["existed_before"]
        }
        self.apply_upgrade()
        state = adventurer.load_state(self.core)
        owned = upgrade.state_file_map(state)
        self.assertEqual(owned[self.SPELL_INFO], {
            "path": self.SPELL_INFO,
            "existed_before": True,
            "before_sha256": adventurer.sha256_bytes(self.native),
            "after_sha256": adventurer.sha256_file(self.spell_info),
        })
        self.assertFalse(owned[self.HEADER]["existed_before"])
        self.assertIsNone(owned[self.HEADER]["before_sha256"])
        self.assertEqual(self.backup.read_bytes(), self.native)
        self.assertNotEqual(self.spell_info.read_bytes(), self.native)
        self.assertEqual(adventurer.verify_state(self.core, state), [])
        for entry in self.state["files"]:
            self.assertEqual(owned[entry["path"]], entry)
        for relative, original in old_backups.items():
            self.assertEqual(
                (self.core / adventurer.STATE_DIR_NAME / "backups" / relative).read_bytes(), original
            )
        first = self.file_snapshot()
        self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), first)

    def test_full_source_rollback_restores_spell_info_instead_of_deleting_it(self):
        self.apply_upgrade()
        unrelated = self.core / "src/unrelated.txt"
        unrelated.write_bytes(b"keep me")
        with redirect_stdout(StringIO()):
            adventurer.cmd_rollback(self.args)
        self.assertEqual(self.spell_info.read_bytes(), self.native)
        for relative, source in self.native_sources.items():
            self.assertEqual((self.core / relative).read_bytes(), source.encode())
        self.assertFalse((self.core / self.HEADER).exists())
        self.assertFalse((self.core / adventurer.STATE_DIR_NAME).exists())
        self.assertEqual(unrelated.read_bytes(), b"keep me")

    def test_manual_edit_in_unowned_spell_info_is_rejected_without_writes(self):
        self.spell_info.write_bytes(self.native + b"// local edit\n")
        before = self.file_snapshot()
        with patch.object(upgrade, "build_patch") as build:
            with self.assertRaisesRegex(upgrade.UpgradeError, "differs from the installed core baseline"):
                upgrade.apply_upgrade(self.args)
        build.assert_not_called()
        self.assertEqual(self.file_snapshot(), before)

    def test_staged_edit_with_pristine_worktree_is_rejected(self):
        self.spell_info.write_bytes(self.native + b"// staged edit\n")
        self.git("add", self.SPELL_INFO)
        self.spell_info.write_bytes(self.native)
        before = self.file_snapshot()
        with self.assertRaisesRegex(adventurer.InstallError, "pre-existing local changes"):
            self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)
        self.assertIn("staged edit", self.git("show", f":{self.SPELL_INFO}").stdout)

    def test_hidden_worktree_edit_is_rejected(self):
        self.git("update-index", "--assume-unchanged", self.SPELL_INFO)
        self.spell_info.write_bytes(self.native + b"// hidden edit\n")
        self.assertEqual(self.git("status", "--porcelain", "--", self.SPELL_INFO).stdout, "")
        before = self.file_snapshot()
        with self.assertRaisesRegex(upgrade.UpgradeError, "differs from the installed core baseline"):
            self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)

    def test_other_unowned_existing_source_is_still_rejected(self):
        other = "src/server/shared/SharedDefines.h"
        self.state["files"] = [entry for entry in self.state["files"] if entry["path"] != other]
        adventurer.save_state(self.core, self.state)
        before = self.file_snapshot()
        with self.assertRaisesRegex(upgrade.UpgradeError, "not present in the ownership manifest.*SharedDefines"):
            self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)

    def test_existing_unowned_generated_header_is_still_rejected(self):
        (self.core / self.HEADER).write_bytes((adventurer.PAYLOAD_ROOT / self.HEADER).read_bytes())
        before = self.file_snapshot()
        with self.assertRaisesRegex(upgrade.UpgradeError, "not present in the ownership manifest.*AdventurerSpellScaling"):
            self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)

    def test_missing_or_unavailable_git_baseline_is_rejected(self):
        for commit in (None, "0" * 40):
            with self.subTest(commit=commit):
                state = dict(self.state, source_core_commit=commit)
                with self.assertRaisesRegex(upgrade.UpgradeError, "core commit|core baseline"):
                    upgrade.plan_owned_upgrade(self.core, state)
                self.assertFalse(self.backup.exists())

    def test_new_core_head_is_still_rejected(self):
        self.git("commit", "--allow-empty", "-m", "core changed")
        before = self.file_snapshot()
        with self.assertRaisesRegex(upgrade.UpgradeError, "HEAD changed"):
            self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)

    def test_existing_rollback_backup_is_never_overwritten(self):
        self.backup.parent.mkdir(parents=True)
        for content in (b"unknown backup", self.native):
            with self.subTest(content=content[:20]):
                self.backup.write_bytes(content)
                before = self.file_snapshot()
                with self.assertRaisesRegex(upgrade.UpgradeError, "existing rollback backup"):
                    self.apply_upgrade()
                self.assertEqual(self.file_snapshot(), before)

    def test_symlink_source_and_backup_are_rejected(self):
        saved = self.spell_info.with_name("native.cpp")
        self.spell_info.rename(saved)
        self.spell_info.symlink_to(saved)
        with self.assertRaisesRegex(upgrade.UpgradeError, "symlink"):
            self.apply_upgrade()
        self.assertEqual(saved.read_bytes(), self.native)
        self.spell_info.unlink()
        saved.rename(self.spell_info)
        self.backup.parent.mkdir(parents=True)
        self.backup.symlink_to(self.root / "absent-backup")
        with self.assertRaisesRegex(upgrade.UpgradeError, "symlink"):
            self.apply_upgrade()
        self.assertFalse((self.root / "absent-backup").exists())

    def test_build_failure_leaves_sources_manifest_and_backups_untouched(self):
        before = self.file_snapshot()
        def fail_build(*args):
            raise RuntimeError("injected build failure")
        with self.assertRaisesRegex(RuntimeError, "injected build failure"):
            self.apply_upgrade(fail_build)
        self.assertEqual(self.file_snapshot(), before)

    def test_edit_during_generation_is_preserved_and_blocks_before_source_writes(self):
        before = self.file_snapshot()
        def edit_during_build(*args):
            self.build_bundle(*args)
            self.spell_info.write_bytes(self.native + b"// concurrent edit\n")
        with self.assertRaisesRegex(upgrade.UpgradeError, "Source changed while preparing"):
            self.apply_upgrade(edit_during_build)
        before[str(self.spell_info.relative_to(self.root))] = self.native + b"// concurrent edit\n"
        self.assertEqual(self.file_snapshot(), before)

    def test_failure_after_runtime_install_restores_previous_state_and_allows_retry(self):
        before = self.file_snapshot()
        def install_then_fail(*args):
            client.install_patch(*args)
            self.assertEqual(self.backup.read_bytes(), self.native)
            self.assertNotEqual(self.spell_info.read_bytes(), self.native)
            raise RuntimeError("injected client failure")
        with patch.object(upgrade, "install_patch", side_effect=install_then_fail):
            with self.assertRaisesRegex(RuntimeError, "injected client failure"):
                self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)
        self.assertEqual(adventurer.load_state(self.core), self.state)
        self.assertFalse(self.backup.exists())
        self.apply_upgrade()
        self.assertEqual(self.backup.read_bytes(), self.native)

    def test_post_save_verification_failure_rolls_back_manifest_and_migration(self):
        before = self.file_snapshot()
        def fail_verify(core, state):
            self.assertEqual(adventurer.load_state(core), state)
            self.assertIn(self.SPELL_INFO, upgrade.state_file_map(state))
            return ["injected verification failure"]
        with patch.object(upgrade, "verify_state", side_effect=fail_verify):
            with self.assertRaisesRegex(upgrade.UpgradeError, "injected verification failure"):
                self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)

    def test_partial_source_write_failure_restores_native_and_removes_migration_backup(self):
        before = self.file_snapshot()
        write_bytes = Path.write_bytes
        failed = False
        def fail_source_once(path, content):
            nonlocal failed
            if path == self.spell_info and not failed:
                failed = True
                write_bytes(path, content[:20])
                raise OSError("injected source write failure")
            return write_bytes(path, content)
        with patch.object(Path, "write_bytes", fail_source_once):
            with self.assertRaisesRegex(OSError, "injected source write failure"):
                self.apply_upgrade()
        self.assertTrue(failed)
        self.assertEqual(self.file_snapshot(), before)

    def test_backup_creation_failure_does_not_patch_or_adopt_source(self):
        before = self.file_snapshot()
        open_path = Path.open
        def fail_backup(path, mode="r", *args, **kwargs):
            if path == self.backup and mode == "xb":
                raise OSError("injected backup failure")
            return open_path(path, mode, *args, **kwargs)
        with patch.object(Path, "open", fail_backup):
            with self.assertRaisesRegex(OSError, "injected backup failure"):
                self.apply_upgrade()
        self.assertEqual(self.file_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
