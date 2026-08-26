from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import spelldraft_runtime  # noqa: E402


class SpellDraftRuntimeInstallerTests(unittest.TestCase):
    def make_layout(self, root: Path) -> tuple[Path, Path]:
        source = root / "source"
        data = root / "data"
        source.mkdir()
        data.mkdir()
        return source, data

    def write_package(self, source: Path, conf: str, cards: str) -> None:
        (source / "spelldraft.conf").write_text(conf, encoding="utf-8")
        (source / "cards.csv").write_text(cards, encoding="utf-8")

    def install_with_source(self, source: Path, data: Path) -> None:
        with patch.object(spelldraft_runtime, "SOURCE", source):
            spelldraft_runtime.install(data, data)

    def test_fresh_install_creates_managed_live_and_dist_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, data = self.make_layout(root)
            self.write_package(source, "conf-v1\n", "cards-v1\n")

            self.install_with_source(source, data)

            target = data / "spelldraft"
            for name, expected in (("spelldraft.conf", "conf-v1\n"), ("cards.csv", "cards-v1\n")):
                self.assertEqual((target / name).read_text(), expected)
                self.assertEqual((target / f"{name}.dist").read_text(), expected)
                marker = target / f".{name}{spelldraft_runtime.MARKER_SUFFIX}"
                self.assertEqual(marker.read_text().strip(), hashlib.sha256(expected.encode()).hexdigest())

    def test_package_update_advances_unedited_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, data = self.make_layout(root)
            self.write_package(source, "conf-v1\n", "cards-v1\n")
            self.install_with_source(source, data)

            self.write_package(source, "conf-v2\n", "cards-v2\n")
            self.install_with_source(source, data)

            target = data / "spelldraft"
            self.assertEqual((target / "spelldraft.conf").read_text(), "conf-v2\n")
            self.assertEqual((target / "cards.csv").read_text(), "cards-v2\n")
            self.assertEqual((target / "spelldraft.conf.dist").read_text(), "conf-v2\n")
            self.assertEqual((target / "cards.csv.dist").read_text(), "cards-v2\n")

    def test_local_runtime_edits_are_preserved_while_dist_advances(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, data = self.make_layout(root)
            self.write_package(source, "conf-v1\n", "cards-v1\n")
            self.install_with_source(source, data)

            target = data / "spelldraft"
            (target / "spelldraft.conf").write_text("my-local-conf\n", encoding="utf-8")
            (target / "cards.csv").write_text("my-local-cards\n", encoding="utf-8")
            self.write_package(source, "conf-v2\n", "cards-v2\n")
            self.install_with_source(source, data)

            self.assertEqual((target / "spelldraft.conf").read_text(), "my-local-conf\n")
            self.assertEqual((target / "cards.csv").read_text(), "my-local-cards\n")
            self.assertEqual((target / "spelldraft.conf.dist").read_text(), "conf-v2\n")
            self.assertEqual((target / "cards.csv.dist").read_text(), "cards-v2\n")

    def test_pre_marker_live_matching_previous_dist_is_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, data = self.make_layout(root)
            self.write_package(source, "conf-v2\n", "cards-v2\n")
            target = data / "spelldraft"
            target.mkdir()
            (target / "spelldraft.conf").write_text("conf-v1\n", encoding="utf-8")
            (target / "spelldraft.conf.dist").write_text("conf-v1\n", encoding="utf-8")
            (target / "cards.csv").write_text("cards-v1\n", encoding="utf-8")
            (target / "cards.csv.dist").write_text("cards-v1\n", encoding="utf-8")

            self.install_with_source(source, data)

            self.assertEqual((target / "spelldraft.conf").read_text(), "conf-v2\n")
            self.assertEqual((target / "cards.csv").read_text(), "cards-v2\n")

    def test_known_legacy_package_is_migrated_even_if_dist_was_already_refreshed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, data = self.make_layout(root)
            self.write_package(source, "conf-v2\n", "cards-v2\n")
            target = data / "spelldraft"
            target.mkdir()
            old_conf = "legacy-conf\n"
            old_cards = "legacy-cards\n"
            (target / "spelldraft.conf").write_text(old_conf, encoding="utf-8")
            (target / "cards.csv").write_text(old_cards, encoding="utf-8")
            (target / "spelldraft.conf.dist").write_text("conf-v2\n", encoding="utf-8")
            (target / "cards.csv.dist").write_text("cards-v2\n", encoding="utf-8")

            legacy = {
                "spelldraft.conf": {hashlib.sha256(old_conf.encode()).hexdigest()},
                "cards.csv": {hashlib.sha256(old_cards.encode()).hexdigest()},
            }
            with patch.object(spelldraft_runtime, "SOURCE", source), patch.object(
                spelldraft_runtime, "LEGACY_PACKAGED_SHA256", legacy
            ):
                spelldraft_runtime.install(data, data)

            self.assertEqual((target / "spelldraft.conf").read_text(), "conf-v2\n")
            self.assertEqual((target / "cards.csv").read_text(), "cards-v2\n")


if __name__ == "__main__":
    unittest.main()
