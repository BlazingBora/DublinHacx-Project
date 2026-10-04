import os
from datetime import datetime, timezone

# DATABASE_URL points at Postgres (e.g. Vercel Postgres, Neon, Supabase).
# It's required in production because Vercel's filesystem is ephemeral -
# a SQLite file wouldn't survive between requests/deploys there. Locally,
# without it set, we fall back to a SQLite file for convenience.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    import psycopg
    from psycopg.rows import dict_row

    def _connect():
        return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)

    _PH = "%s"
    _ID_COLUMN = "id SERIAL PRIMARY KEY"
else:
    import sqlite3

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLITE_PATH = os.getenv("INVENTORY_DB_PATH", os.path.join(BASE_DIR, "inventory.db"))

    os.makedirs(os.path.dirname(SQLITE_PATH) or ".", exist_ok=True)

    def _connect():
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    _PH = "?"
    _ID_COLUMN = "id INTEGER PRIMARY KEY AUTOINCREMENT"


def init_db():
    with _connect() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS inventory (
                {_ID_COLUMN},
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
                added_at TEXT NOT NULL,
                stale_use_tip TEXT,
                grace_days INTEGER
            )
        """)


def add_items(items, source, purchase_date=None):
    """Persists scanned items (source is 'grocery' or 'medication'). Returns the new row ids."""

    added_at = datetime.now(timezone.utc).isoformat()
    new_ids = []

    with _connect() as conn:
        for item in items:
            row = conn.execute(
                f"""
                INSERT INTO inventory (
                    source, name, quantity, price, dosage, refills_left,
                    instructions, storage, storage_tip, estimated_expiration,
                    purchase_date, added_at, stale_use_tip, grace_days
                ) VALUES (
                    {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH},
                    {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH}
                )
                RETURNING id
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
            ).fetchone()
            new_ids.append(row["id"])

    return new_ids


def list_items(source=None):
    """Returns persisted items as dicts, optionally filtered by source."""

    with _connect() as conn:
        if source:
            rows = conn.execute(
                f"SELECT * FROM inventory WHERE source = {_PH} ORDER BY id DESC",
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

    placeholders = ",".join(_PH for _ in ids)

    with _connect() as conn:
        cursor = conn.execute(
            f"DELETE FROM inventory WHERE id IN ({placeholders})",
            ids,
        )
        return cursor.rowcount


def remove_all_items(source):
    """Deletes every row for the given source. Returns the number of rows removed."""

    with _connect() as conn:
        cursor = conn.execute(f"DELETE FROM inventory WHERE source = {_PH}", (source,))
        return cursor.rowcount


init_db()
