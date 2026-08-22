from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import database  # noqa: E402
from database import DatabaseError, DatabaseInfo  # noqa: E402


class DatabaseRollbackTests(unittest.TestCase):
    def test_reads_azerothcore_database_config_without_storing_secret(self):
        with tempfile.TemporaryDirectory() as td:
            conf = Path(td) / "worldserver.conf"
            conf.write_text(
                '# WorldDatabaseInfo = "wrong;3306;x;x;x"\n'
                'WorldDatabaseInfo = "127.0.0.1;3306;acore;very-secret;acore_world"\n'
                'CharacterDatabaseInfo = "127.0.0.1;3306;acore;very-secret;acore_characters"\n',
                encoding="utf-8",
            )
            info = database.read_database_info(conf, "WorldDatabaseInfo")
            self.assertEqual(info.database, "acore_world")
            self.assertEqual(info.password, "very-secret")
            public = json.dumps(info.public())
            self.assertNotIn("very-secret", public)
            self.assertNotIn("acore;", public)

    def test_defaults_file_omits_database_for_mysqldump_compatibility(self):
        info = DatabaseInfo("127.0.0.1", 3306, "acore", "secret", "acore_world")
        with tempfile.TemporaryDirectory() as td:
            defaults = Path(td) / "client.cnf"
            database._write_defaults(defaults, info)
            text = defaults.read_text(encoding="utf-8")
        self.assertNotIn("database=", text)
        self.assertIn("host=127.0.0.1", text)
        self.assertIn("user=acore", text)

    @patch.object(database.subprocess, "run")
    @patch.object(database, "find_program", return_value="/usr/bin/mysql")
    def test_mysql_selects_database_positionally(self, _find_program, run):
        info = DatabaseInfo("127.0.0.1", 3306, "acore", "secret", "acore_world")
        run.return_value = subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")
        database._run_mysql(info, b"SELECT 1;\n", capture=True)
        args = run.call_args.args[0]
        self.assertEqual(args[-1], "acore_world")

    @patch.object(database, "_dump_scope")
    @patch.object(database, "count_scope")
    @patch.object(database, "validate_connection")
    def test_snapshot_covers_every_owned_world_range(self, validate, count, dump):
        info = DatabaseInfo("127.0.0.1", 3306, "acore", "secret", "acore_world")
        count.return_value = 2
        dump.side_effect = lambda _info, table, _where: (
            f"INSERT INTO `{table}` VALUES (1);\n".encode()
        )

        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / database.SNAPSHOT_FILE
            metadata = database.create_world_snapshot(info, output)
            sql = output.read_text(encoding="utf-8")

        self.assertEqual(len(metadata["scopes"]), len(database.WORLD_SCOPES))
        self.assertEqual(len(metadata["counts"]), len(database.WORLD_SCOPES))
        self.assertNotIn("secret", json.dumps(metadata))
        for table, where in database.WORLD_SCOPES:
            self.assertIn(f"DELETE FROM `{table}` WHERE {where};", sql)
            self.assertIn(f"INSERT INTO `{table}` VALUES (1);", sql)
        self.assertIn(database.MIGRATION_NAME, sql)
        validate.assert_called_once_with(info)

    def test_modified_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / database.SNAPSHOT_FILE
            path.write_bytes(b"safe snapshot\n")
            metadata = {"snapshot_sha256": database.sha256_file(path)}
            path.write_bytes(b"tampered snapshot\n")
            with self.assertRaises(DatabaseError):
                database.validate_snapshot(path, metadata)

    @patch.object(database, "count_scope")
    @patch.object(database, "_run_mysql")
    @patch.object(database, "validate_connection")
    def test_restore_verifies_every_scope_count(self, validate, run_mysql, count_scope):
        info = DatabaseInfo("127.0.0.1", 3306, "acore", "secret", "acore_world")
        counts = {f"{table}:{where}": 0 for table, where in database.WORLD_SCOPES}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / database.SNAPSHOT_FILE
            path.write_bytes(b"SET FOREIGN_KEY_CHECKS=0;\nSET FOREIGN_KEY_CHECKS=1;\n")
            metadata = {
                "database": info.public(),
                "snapshot_sha256": database.sha256_file(path),
                "counts": counts,
            }
            count_scope.return_value = 0
            database.restore_world_snapshot(info, path, metadata)

        run_mysql.assert_called_once()
        self.assertEqual(count_scope.call_count, len(database.WORLD_SCOPES))
        validate.assert_called_once_with(info)

    @patch.object(database, "adventurer_character_count", return_value=1)
    @patch.object(database, "validate_connection")
    def test_existing_class10_character_blocks_clean_baseline(self, validate, count):
        info = DatabaseInfo("127.0.0.1", 3306, "acore", "secret", "acore_characters")
        with self.assertRaises(DatabaseError):
            database.validate_character_baseline(info)


if __name__ == "__main__":
    unittest.main()
