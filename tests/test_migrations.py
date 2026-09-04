"""Schema migrations and the read-only database mode."""

import sqlite3

import pytest


def test_upgrade_builds_every_table(migrated_db):
    """`flask db upgrade` from empty reaches the latest revision with all tables."""
    with sqlite3.connect(migrated_db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in rows}
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert {"orders", "coupon_redemption_log", "inv_reservation_ledger", "reviews"} <= tables
    assert version == "0003"


def test_read_only_connection_rejects_writes(migrated_db):
    """The ?mode=ro URI used for text-to-SQL can read but not write."""
    with sqlite3.connect(f"file:{migrated_db}?mode=ro", uri=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone() == (0,)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM products")
