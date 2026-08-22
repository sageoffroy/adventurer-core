#!/usr/bin/env python3
"""Selective AzerothCore database backup/restore for Adventurer Core.

The installer never stores database credentials. It re-reads the normal
worldserver.conf when it needs to connect, snapshots only rows owned/overwritten
by the class-10 bootstrap, and produces a deterministic rollback SQL file.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile


class DatabaseError(RuntimeError):
    pass


MIGRATION_NAME = "rev_1787358000000000000.sql"

# Every world-DB row range touched by sql/world/001_adventurer.sql, plus the
# AzerothCore updater marker it creates after applying that pending update.
WORLD_SCOPES: tuple[tuple[str, str], ...] = (
    ("playercreateinfo", "`class` = 10"),
    ("player_class_stats", "`Class` = 10"),
    ("playercreateinfo_skills", "`classMask` = 512"),
    ("playercreateinfo_spell_custom", "`classmask` = 512"),
    ("playercreateinfo_action", "`class` = 10"),
    ("gtchancetomeleecritbase_dbc", "`ID` = 9"),
    ("gtchancetospellcritbase_dbc", "`ID` = 9"),
    ("gtchancetomeleecrit_dbc", "`ID` BETWEEN 900 AND 999"),
    ("gtchancetospellcrit_dbc", "`ID` BETWEEN 900 AND 999"),
    ("gtoctclasscombatratingscalar_dbc", "`ID` BETWEEN 289 AND 320"),
    ("gtoctregenhp_dbc", "`ID` BETWEEN 900 AND 999"),
    ("gtregenhpperspt_dbc", "`ID` BETWEEN 900 AND 999"),
    ("gtregenmpperspt_dbc", "`ID` BETWEEN 900 AND 999"),
    ("updates", f"`name` = '{MIGRATION_NAME}'"),
)


@dataclass(frozen=True)
class DatabaseInfo:
    host: str
    port: int
    user: str
    password: str
    database: str

    def public(self) -> dict[str, str | int]:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
        }


def parse_database_info(value: str) -> DatabaseInfo:
    parts = value.split(";")
    if len(parts) < 5:
        raise DatabaseError(
            "AzerothCore database string must contain host;port;user;password;database"
        )
    host, raw_port, user, password, database = parts[:5]
    if not all((host, raw_port, user, database)):
        raise DatabaseError("AzerothCore database string contains an empty required field")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise DatabaseError(f"Invalid database port: {raw_port!r}") from exc
    if not (1 <= port <= 65535):
        raise DatabaseError(f"Invalid database port: {port}")
    return DatabaseInfo(host, port, user, password, database)


def read_database_info(conf_path: Path, key: str) -> DatabaseInfo:
    if not conf_path.is_file():
        raise DatabaseError(f"worldserver.conf not found: {conf_path}")
    pattern = re.compile(rf'^\s*{re.escape(key)}\s*=\s*"([^"]+)"\s*(?:#.*)?$')
    matches: list[str] = []
    for line in conf_path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            matches.append(match.group(1))
    if len(matches) != 1:
        raise DatabaseError(
            f"Expected exactly one active {key} in {conf_path}, found {len(matches)}"
        )
    if "${" in matches[0]:
        raise DatabaseError(
            f"{key} in {conf_path} uses unresolved environment substitution; "
            "pass a concrete worldserver.conf for safe rollback"
        )
    return parse_database_info(matches[0])


def find_program(candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    raise DatabaseError("Required database client not found: " + " or ".join(candidates))


def _write_defaults(path: Path, info: DatabaseInfo) -> None:
    # Quotes in MySQL option files are parsed as value delimiters, not shell
    # syntax. Escape the two characters that can alter the line itself.
    password = info.password.replace("\\", "\\\\").replace("\n", "\\n")
    text = (
        "[client]\n"
        f"host={info.host}\n"
        f"port={info.port}\n"
        f"user={info.user}\n"
        f"password={password}\n"
        f"database={info.database}\n"
        "protocol=tcp\n"
    )
    path.write_text(text, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _run_mysql(info: DatabaseInfo, sql: bytes, *, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
    mysql = find_program(("mysql", "mariadb"))
    with tempfile.TemporaryDirectory(prefix="adventurer-db-auth-") as td:
        defaults = Path(td) / "client.cnf"
        _write_defaults(defaults, info)
        return subprocess.run(
            [mysql, f"--defaults-extra-file={defaults}", "--batch", "--raw", "--skip-column-names"],
            input=sql,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )


def query_scalar(info: DatabaseInfo, sql: str) -> str:
    try:
        result = _run_mysql(info, (sql.rstrip(";") + ";\n").encode(), capture=True)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        raise DatabaseError(f"Database query failed: {detail or exc}") from exc
    lines = result.stdout.decode("utf-8", errors="strict").splitlines()
    if len(lines) != 1:
        raise DatabaseError(f"Expected one scalar row, got {len(lines)} for query: {sql}")
    return lines[0]


def validate_connection(info: DatabaseInfo) -> None:
    selected = query_scalar(info, "SELECT DATABASE()")
    if selected != info.database:
        raise DatabaseError(
            f"Connected to unexpected database {selected!r}; expected {info.database!r}"
        )


def count_scope(info: DatabaseInfo, table: str, where: str) -> int:
    raw = query_scalar(info, f"SELECT COUNT(*) FROM `{table}` WHERE {where}")
    try:
        return int(raw)
    except ValueError as exc:
        raise DatabaseError(f"Invalid COUNT result for {table}: {raw!r}") from exc


def _dump_scope(info: DatabaseInfo, table: str, where: str) -> bytes:
    dump = find_program(("mysqldump", "mariadb-dump"))
    with tempfile.TemporaryDirectory(prefix="adventurer-db-auth-") as td:
        defaults = Path(td) / "client.cnf"
        _write_defaults(defaults, info)
        args = [
            dump,
            f"--defaults-extra-file={defaults}",
            "--no-create-info",
            "--skip-triggers",
            "--skip-add-locks",
            "--skip-comments",
            "--compact",
            "--complete-insert",
            "--hex-blob",
            f"--where={where}",
            info.database,
            table,
        ]
        try:
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode(errors="replace").strip()
            raise DatabaseError(f"Failed to snapshot {table}: {detail or exc}") from exc
    return result.stdout


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_world_snapshot(info: DatabaseInfo, output: Path) -> dict:
    """Create rollback SQL without modifying the live world database."""
    validate_connection(info)
    output.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    chunks: list[bytes] = [
        b"-- Adventurer Core selective world DB rollback snapshot.\n",
        b"SET FOREIGN_KEY_CHECKS=0;\n",
    ]
    for table, where in WORLD_SCOPES:
        key = f"{table}:{where}"
        counts[key] = count_scope(info, table, where)
        chunks.append(f"DELETE FROM `{table}` WHERE {where};\n".encode())
        dumped = _dump_scope(info, table, where)
        if dumped:
            chunks.append(dumped)
            if not dumped.endswith(b"\n"):
                chunks.append(b"\n")
    chunks.append(b"SET FOREIGN_KEY_CHECKS=1;\n")

    output.write_bytes(b"".join(chunks))
    return {
        "schema": 1,
        "kind": "selective-world-rollback",
        "database": info.public(),
        "snapshot_file": output.name,
        "snapshot_sha256": sha256_file(output),
        "counts": counts,
        "scopes": [{"table": table, "where": where} for table, where in WORLD_SCOPES],
    }


def validate_snapshot(path: Path, metadata: dict) -> None:
    if not path.is_file():
        raise DatabaseError(f"Database rollback snapshot missing: {path}")
    actual = sha256_file(path)
    expected = metadata.get("snapshot_sha256")
    if actual != expected:
        raise DatabaseError(
            f"Database rollback snapshot was modified: expected {expected}, got {actual}"
        )


def assert_same_database(info: DatabaseInfo, metadata: dict) -> None:
    expected = metadata.get("database", {})
    actual = info.public()
    if actual != expected:
        raise DatabaseError(
            "worldserver.conf now points at a different world database; refusing rollback. "
            f"snapshot={expected}, current={actual}"
        )


def restore_world_snapshot(info: DatabaseInfo, path: Path, metadata: dict) -> None:
    validate_connection(info)
    validate_snapshot(path, metadata)
    assert_same_database(info, metadata)
    try:
        _run_mysql(info, path.read_bytes())
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        raise DatabaseError(f"World database rollback failed: {detail or exc}") from exc

    expected_counts = metadata.get("counts", {})
    for table, where in WORLD_SCOPES:
        key = f"{table}:{where}"
        expected = expected_counts.get(key)
        if expected is None:
            raise DatabaseError(f"Snapshot metadata missing row count for {key}")
        actual = count_scope(info, table, where)
        if actual != expected:
            raise DatabaseError(
                f"World database rollback verification failed for {table}: "
                f"expected {expected} rows, found {actual}"
            )


def adventurer_character_count(info: DatabaseInfo) -> int:
    validate_connection(info)
    # Include soft-deleted characters as well. Removing class-10 support while a
    # recoverable class-10 row exists makes a later restore unsafe.
    raw = query_scalar(info, "SELECT COUNT(*) FROM `characters` WHERE `class` = 10")
    try:
        return int(raw)
    except ValueError as exc:
        raise DatabaseError(f"Invalid Adventurer character count: {raw!r}") from exc


def database_metadata_json(metadata: dict) -> str:
    return json.dumps(metadata, indent=2, sort_keys=True) + "\n"
