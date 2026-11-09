
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "Data"
    / "operations.db"
)

ALLOWED_STATUSES = [
    "New",
    "In Progress",
    "Pending Customer",
    "Waiting on Customer",
    "Pending Agency",
    "Waiting on Agency",
    "Resolved",
    "Closed"
]


def initialize_audit_table():
    with sqlite3.connect(DB_PATH, timeout=30) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS case_audit_history (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                field_changed TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                change_reason TEXT NOT NULL,
                changed_at TEXT NOT NULL
            )
        """)


def update_case_status(case_id, new_status, analyst, reason):
    initialize_audit_table()

    analyst = str(analyst).strip()
    reason = str(reason).strip()

    if new_status not in ALLOWED_STATUSES:
        return False, "Invalid case status."

    if not analyst:
        return False, "Analyst name is required."

    if not reason:
        return False, "Reason for the change is required."

    try:
        with sqlite3.connect(DB_PATH, timeout=30) as con:
            con.execute("BEGIN IMMEDIATE")

            row = con.execute(
                """
                SELECT status
                FROM cases
                WHERE case_id = ?
                """,
                (case_id,)
            ).fetchone()

            if row is None:
                return False, "Case not found."

            old_status = row[0]

            if old_status == new_status:
                return False, "The case already has this status."

            timestamp = datetime.now().isoformat(
                timespec="seconds"
            )

            con.execute(
                """
                UPDATE cases
                SET status = ?, updated_at = ?
                WHERE case_id = ?
                """,
                (new_status, timestamp, case_id)
            )

            con.execute(
                """
                INSERT INTO case_audit_history (
                    case_id,
                    field_changed,
                    old_value,
                    new_value,
                    changed_by,
                    change_reason,
                    changed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    "status",
                    old_status,
                    new_status,
                    analyst,
                    reason,
                    timestamp
                )
            )

        return True, (
            f"{case_id} updated from "
            f"{old_status} to {new_status}."
        )

    except sqlite3.Error as exc:
        return False, f"Database error: {exc}"


def get_case_history(case_id):
    initialize_audit_table()

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row

        rows = con.execute(
            """
            SELECT
                audit_id,
                field_changed,
                old_value,
                new_value,
                changed_by,
                change_reason,
                changed_at
            FROM case_audit_history
            WHERE case_id = ?
            ORDER BY audit_id DESC
            """,
            (case_id,)
        ).fetchall()

    return [dict(row) for row in rows]
