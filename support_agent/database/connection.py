"""
Database connection and initialization management.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Generator
from support_agent.config import DB_PATH, PACKAGE_ROOT


def get_db_path() -> Path:
    db_file = DB_PATH
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_database() -> None:
    schema_path = PACKAGE_ROOT / "database" / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
