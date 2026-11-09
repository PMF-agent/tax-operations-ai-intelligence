
"""
STEP 32 — ISOLATED INTEGRATION TESTS

Creates a temporary project containing:
- Copies of Dashboard Python modules
- A SQLite backup of the original database

Runs integration tests in a separate Python process.
The original database is never opened for writing.

Tests:
1. Database snapshot and case schema
2. Lifecycle update and audit persistence
3. AI input fingerprint invalidation
4. Context-aware recommendation changes
5. Queue priority ordering
6. Original simulation integrity

Actual Ollama calls and Streamlit browser rendering
are verified separately through manual checks.
"""

import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "Dashboard"
DATABASE = ROOT / "Data" / "operations.db"
SIMULATION = (
    ROOT / "Output" / "integrated_priority_queue.csv"
)


def snapshot_project(destination):
    """Copy code and snapshot SQLite into a temporary root."""
    destination = Path(destination)

    for folder in ("Dashboard", "Data", "Output"):
        (destination / folder).mkdir(
            parents=True, exist_ok=True
        )

    for source in DASHBOARD.glob("*.py"):
        if source.name.startswith("test_"):
            continue
        if source.name == "run_integration_validation.py":
            continue
        shutil.copy2(
            source,
            destination / "Dashboard" / source.name
        )

    if not DATABASE.exists():
        raise FileNotFoundError(
            f"Source database not found: {DATABASE}"
        )

    # SQLite backup handles a source database that
    # may be using write-ahead logging.
    source_con = sqlite3.connect(
        f"file:{DATABASE.as_posix()}?mode=ro",
        uri=True,
    )
    try:
        target_con = sqlite3.connect(
            destination / "Data" / "operations.db"
        )
        try:
            source_con.backup(target_con)
        finally:
            target_con.close()
    finally:
        source_con.close()

    if SIMULATION.exists():
        shutil.copy2(
            SIMULATION,
            destination / "Output" / SIMULATION.name
        )


def execute_isolated_tests(temp_root):
    """Run the worker in its own interpreter."""
    worker = Path(temp_root) / "integration_worker.py"
    worker.write_text(WORKER_CODE, encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    return subprocess.run(
        [sys.executable, str(worker)],
        cwd=str(temp_root),
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )


WORKER_CODE = r'''
import importlib
import sqlite3
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Dashboard"))

DB = ROOT / "Data" / "operations.db"

from case_intelligence import (
    case_fingerprint,
    quality_summary,
)
from case_lifecycle import (
    initialize_audit_table,
    update_case_status,
    get_case_history,
)
from recommendation_engine import recommend_case_action
from priority_validation import (
    build_priority_queue,
    validate_simulation,
)


def read_case(case_id):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT * FROM cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()
    return dict(row) if row else None


def make_case(
    case_id,
    status="In Progress",
    risk="Within SLA",
    dependency="None",
    deadline="2026-11-11 15:00:00",
):
    return {
        "case_id": case_id,
        "status": status,
        "sla_risk": risk,
        "dependency": dependency,
        "sla_deadline": deadline,
        "case_type": "New Tax Registration",
        "agency_name": "Example Agency",
        "agency_submission_date": None,
    }


class IntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_audit_table()

    def test_01_database_snapshot(self):
        self.assertTrue(DB.exists())
        with sqlite3.connect(DB) as con:
            columns = {
                row[1] for row in con.execute(
                    "PRAGMA table_info(cases)"
                )
            }

        required = {
            "case_id",
            "status",
            "subject",
            "message",
            "received_date",
            "sla_hours",
            "sla_policy",
            "assigned_to",
        }
        self.assertTrue(required.issubset(columns))

    def test_02_lifecycle_and_audit(self):
        original = read_case("TX-1051")
        self.assertIsNotNone(
            original,
            "TX-1051 must exist in the snapshot."
        )

        before_history = get_case_history("TX-1051")
        old_status = original["status"]

        new_status = (
            "In Progress"
            if old_status != "In Progress"
            else "Waiting on Agency"
        )

        success, message = update_case_status(
            "TX-1051",
            new_status,
            "Integration Test Analyst",
            "Isolated integration validation",
        )

        self.assertTrue(success, str(message))

        updated = read_case("TX-1051")
        self.assertEqual(updated["status"], new_status)
        self.assertEqual(
            updated["received_date"],
            original["received_date"],
        )
        self.assertEqual(
            updated["sla_hours"],
            original["sla_hours"],
        )
        self.assertEqual(
            updated["sla_policy"],
            original["sla_policy"],
        )

        after_history = get_case_history("TX-1051")
        self.assertEqual(
            len(after_history),
            len(before_history) + 1,
        )

    def test_03_fingerprint_changes_with_status(self):
        base = read_case("TX-1051")
        self.assertIsNotNone(base)

        changed = dict(base)
        changed["status"] = (
            "Waiting on Customer"
            if base["status"] != "Waiting on Customer"
            else "In Progress"
        )

        self.assertNotEqual(
            case_fingerprint(base),
            case_fingerprint(changed),
        )

    def test_04_ai_freshness_detects_stale_input(self):
        base = read_case("TX-1051")
        self.assertIsNotNone(base)

        snapshot = {
            "analysis_status": "Completed",
            "input_fingerprint": case_fingerprint(base),
        }

        current = quality_summary(base, snapshot)
        self.assertEqual(
            current["freshness"],
            "Current",
        )

        changed = dict(base)
        changed["message"] = (
            str(base["message"])
            + " Integration validation update."
        )

        stale = quality_summary(changed, snapshot)
        self.assertEqual(
            stale["freshness"],
            "Stale — Reanalysis Recommended",
        )

    def test_05_recommendation_context(self):
        agency = make_case(
            "TEST-AGENCY",
            status="Waiting on Agency",
            dependency="Agency",
        )

        customer = make_case(
            "TEST-CUSTOMER",
            status="Waiting on Customer",
            dependency="Customer",
        )

        agency_result = recommend_case_action(agency)
        customer_result = recommend_case_action(customer)

        self.assertEqual(
            agency_result["action_type"],
            "Agency Follow-up",
        )
        self.assertEqual(
            customer_result["action_type"],
            "Customer Follow-up",
        )

    def test_06_escalation_precedence(self):
        case = make_case(
            "TEST-BREACH",
            status="Waiting on Agency",
            risk="Breached",
            dependency="Agency",
        )

        result = recommend_case_action(case)

        self.assertEqual(
            result["action_type"],
            "SLA Escalation",
        )
        self.assertEqual(
            result["urgency"],
            "Critical",
        )

    def test_07_queue_order(self):
        cases = [
            make_case("T-3", risk="Within SLA"),
            make_case("T-2", risk="At Risk"),
            make_case("T-1", risk="Breached"),
            make_case(
                "T-4",
                risk="Breached",
                status="Closed",
            ),
        ]

        queue = build_priority_queue(cases)

        self.assertEqual(
            queue["case_id"].tolist(),
            ["T-1", "T-2", "T-3", "T-4"],
        )

    def test_08_simulation_integrity(self):
        result = validate_simulation()

        self.assertEqual(result["total_cases"], 50)
        self.assertTrue(result["expected_distribution"])
        self.assertTrue(result["unique_case_ids"])
        self.assertTrue(result["valid_queue_ranks"])
        self.assertTrue(result["risk_priority_order_valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''


def main():
    with tempfile.TemporaryDirectory(
        prefix="taxops_integration_"
    ) as temp:
        snapshot_project(temp)

        result = execute_isolated_tests(temp)

        output = result.stdout + "\n" + result.stderr
        print(output)

        return result.returncode, output


if __name__ == "__main__":
    code, _ = main()
    sys.exit(code)
