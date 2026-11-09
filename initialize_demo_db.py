
"""Create a standalone synthetic SQLite demo database.

Run from the GitHub_Release directory:
    python initialize_demo_db.py

This script never overwrites an existing database.
"""

import random
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "Data" / "operations.db"

SEED = 42
CASE_COUNT = 50

CASE_TYPES = (
    ["New Tax Registration"] * 12
    + ["Registration Maintenance"] * 12
    + ["Agency Notice"] * 10
    + ["Document Collection"] * 2
    + ["Agency Follow-up"] * 7
    + ["Missing Documentation"] * 7
)

PRIORITIES = (
    ["High"] * 17
    + ["Medium"] * 24
    + ["Critical"] * 2
    + ["Low"] * 7
)

STATUSES = (
    ["New"] * 18
    + ["In Progress"] * 13
    + ["Waiting on Customer"] * 2
    + ["Waiting on Agency"] * 2
    + ["Pending Customer"] * 8
    + ["Pending Agency"] * 7
)

SLA_HOURS = [48] * 14 + [72] * 21 + [24] * 8 + [96] * 7

STATES = (
    ["California"] * 3
    + ["Texas"] * 5
    + ["New York"] * 5
    + ["Florida"] * 7
    + ["Illinois"] * 5
    + ["Washington"] * 5
    + ["Colorado"] * 5
    + ["New Jersey"]
    + ["Georgia"] * 4
    + ["Massachusetts"] * 4
    + ["Arizona"] * 3
    + ["Oregon"] * 3
)

SUBJECTS = {
    "New Tax Registration": "State employer tax registration request",
    "Registration Maintenance": "Employer registration account update",
    "Agency Notice": "State tax agency notice review",
    "Document Collection": "Required registration document collection",
    "Agency Follow-up": "Pending state agency response",
    "Missing Documentation": "Outstanding employer documentation",
}

MESSAGES = {
    "New Tax Registration":
        "Synthetic employer requests assistance with a new state tax registration.",
    "Registration Maintenance":
        "Synthetic employer requests an update to an existing registration.",
    "Agency Notice":
        "A simulated state agency notice requires operational review.",
    "Document Collection":
        "Supporting documentation must be collected for a simulated case.",
    "Agency Follow-up":
        "A simulated agency submission requires a status follow-up.",
    "Missing Documentation":
        "Required information is missing from the simulated registration request.",
}

SCHEMA = """
CREATE TABLE cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT UNIQUE NOT NULL,
    customer TEXT NOT NULL,
    state TEXT NOT NULL,
    case_type TEXT,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    received_date TEXT NOT NULL,
    priority TEXT,
    status TEXT NOT NULL,
    sla_hours REAL NOT NULL,
    sla_policy TEXT NOT NULL,
    assigned_to TEXT,
    registration_type TEXT,
    agency_name TEXT,
    submission_method TEXT,
    agency_submission_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE ai_case_analysis (
    case_id TEXT PRIMARY KEY,
    predicted_case_type TEXT,
    predicted_state TEXT,
    predicted_dependency TEXT,
    missing_information TEXT,
    recommended_next_action TEXT,
    model_name TEXT,
    analyzed_at TEXT,
    analysis_status TEXT,
    error_message TEXT,
    input_fingerprint TEXT
);

CREATE TABLE case_audit_history (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    field_changed TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT NOT NULL,
    change_reason TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
"""


def shuffled(values, rng):
    result = list(values)
    rng.shuffle(result)
    return result


def generate_cases():
    rng = random.Random(SEED)

    case_types = shuffled(CASE_TYPES, rng)
    priorities = shuffled(PRIORITIES, rng)
    statuses = shuffled(STATUSES, rng)
    sla_values = shuffled(SLA_HOURS, rng)
    states = shuffled(STATES, rng)

    # Fixed reference date keeps the generated dataset reproducible.
    reference = datetime(2026, 11, 6, 17, 0, 0)
    now_text = reference.isoformat(timespec="seconds")

    records = []

    for index in range(CASE_COUNT):
        case_id = f"TX-{1001 + index}"
        case_type = case_types[index]
        state = states[index]

        # Deterministic weekday timestamps for demonstration.
        days_ago = index % 10
        received = reference - timedelta(
            days=days_ago,
            hours=index % 7,
        )

        received_text = received.isoformat(timespec="seconds")

        records.append(
            (
                case_id,
                f"Demo Employer {index + 1:03d}",
                state,
                case_type,
                SUBJECTS[case_type],
                MESSAGES[case_type],
                received_text,
                priorities[index],
                statuses[index],
                float(sla_values[index]),
                "Business Hours",
                f"Demo Analyst {(index % 5) + 1}",
                "SUI",
                f"{state} Tax Agency",
                "Online",
                None,
                now_text,
                now_text,
            )
        )

    return records


def initialize():
    if DB_PATH.exists():
        print(f"STOPPED: Database already exists at {DB_PATH}")
        print("No files were changed.")
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    records = generate_cases()

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.executescript(SCHEMA)

            connection.executemany(
                """
                INSERT INTO cases (
                    case_id, customer, state, case_type,
                    subject, message, received_date,
                    priority, status, sla_hours, sla_policy,
                    assigned_to, registration_type,
                    agency_name, submission_method,
                    agency_submission_date, created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                records,
            )

            count = connection.execute(
                "SELECT COUNT(*) FROM cases"
            ).fetchone()[0]

            if count != CASE_COUNT:
                raise RuntimeError(
                    f"Expected {CASE_COUNT} cases, found {count}"
                )

    except Exception:
        if DB_PATH.exists():
            DB_PATH.unlink()
        raise

    print("Synthetic demo database created successfully.")
    print(f"Database: {DB_PATH}")
    print(f"Cases created: {len(records)}")
    print("Case types:", dict(Counter(CASE_TYPES)))
    print("Priorities:", dict(Counter(PRIORITIES)))
    print("All records are synthetic.")


if __name__ == "__main__":
    initialize()
