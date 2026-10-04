import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# In production this points at a mounted persistent volume (e.g. Fly.io),
# so the inventory survives deploys/restarts instead of living on the
# container's ephemeral filesystem.
DB_PATH = os.getenv("INVENTORY_DB_PATH", os.path.join(BASE_DIR, "inventory.db"))

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                name TEXT NOT NULL,
                quantity TEXT,
                price REAL,
                dosage TEXT,
                refills_left INTEGER,
                instructions TEXT,
                storage TEXT,
                storage_tip TEXT,
                estimated_expiration TEXT,
                purchase_date TEXT,
                added_at TEXT NOT NULL
            )
        """)

        existing_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(inventory)")
        }

        for column, column_type in (("stale_use_tip", "TEXT"), ("grace_days", "INTEGER")):
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE inventory ADD COLUMN {column} {column_type}")


def add_items(items, source, purchase_date=None):
    """Persists scanned items (source is 'grocery' or 'medication'). Returns the new row ids."""

    added_at = datetime.now(timezone.utc).isoformat()
    new_ids = []

    with _connect() as conn:
        for item in items:
            cursor = conn.execute(
                """
                INSERT INTO inventory (
                    source, name, quantity, price, dosage, refills_left,
                    instructions, storage, storage_tip, estimated_expiration,
                    purchase_date, added_at, stale_use_tip, grace_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    item.get("name"),
                    str(item.get("quantity")) if item.get("quantity") is not None else None,
                    item.get("price"),
                    item.get("dosage"),
                    item.get("refills_left"),
                    item.get("instructions"),
                    item.get("storage"),
                    item.get("storage_tip"),
                    item.get("estimated_expiration"),
                    purchase_date,
                    added_at,
                    item.get("stale_use_tip"),
                    item.get("grace_days"),
                ),
            )
            new_ids.append(cursor.lastrowid)

    return new_ids


def list_items(source=None):
    """Returns persisted items as dicts, optionally filtered by source."""

    with _connect() as conn:
        if source:
            rows = conn.execute(
                "SELECT * FROM inventory WHERE source = ? ORDER BY id DESC",
                (source,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM inventory ORDER BY id DESC").fetchall()

    return [dict(row) for row in rows]


def remove_items(ids):
    """Deletes rows by id. Returns the number of rows removed."""

    ids = [int(i) for i in ids if str(i).isdigit()]

    if not ids:
        return 0

    placeholders = ",".join("?" for _ in ids)

    with _connect() as conn:
        cursor = conn.execute(
            f"DELETE FROM inventory WHERE id IN ({placeholders})",
            ids,
        )
        return cursor.rowcount


def remove_all_items(source):
    """Deletes every row for the given source. Returns the number of rows removed."""

    with _connect() as conn:
        cursor = conn.execute("DELETE FROM inventory WHERE source = ?", (source,))
        return cursor.rowcount


init_db()
