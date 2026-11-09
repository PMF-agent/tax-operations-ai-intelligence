
"""
Step 31C — Automated Validation Runner

Runs unittest and writes a readable report.
No database modifications.
"""

import io
import sys
import unittest
from datetime import datetime
from pathlib import Path

from priority_validation import validate_simulation

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Output"
REPORT = OUTPUT / "priority_validation_report.txt"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    suite = unittest.defaultTestLoader.discover(
        start_dir=str(Path(__file__).resolve().parent),
        pattern="test_priority_validation.py",
    )

    stream = io.StringIO()

    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=2,
    )

    result = runner.run(suite)

    lines = [
        "STEP 31C — PRIORITY QUEUE VALIDATION",
        "=" * 48,
        "Generated: "
        + datetime.now().isoformat(timespec="seconds"),
        "",
        "AUTOMATED TEST RESULTS",
        "-" * 48,
        stream.getvalue(),
        "",
        f"Tests run: {result.testsRun}",
        f"Failures: {len(result.failures)}",
        f"Errors: {len(result.errors)}",
        f"Skipped: {len(result.skipped)}",
        f"Overall: {'PASS' if result.wasSuccessful() else 'FAIL'}",
        "",
        "ORIGINAL SIMULATION CHECKS",
        "-" * 48,
    ]

    try:
        simulation = validate_simulation()

        for key, value in simulation.items():
            lines.append(f"{key}: {value}")

    except Exception as exc:
        lines.append(f"Simulation validation failed: {exc}")
        result_success = False
    else:
        result_success = all([
            simulation["expected_distribution"],
            simulation["unique_case_ids"],
            simulation["valid_queue_ranks"],
            simulation["risk_priority_order_valid"],
        ])

    lines += [
        "",
        "VALIDATION SCOPE",
        "-" * 48,
        "Synthetic deterministic test cases.",
        "Production recommendation function tested directly.",
        "Queue ordering policy tested independently.",
        "Original saved simulation checked for risk ordering.",
        "Live Streamlit rendering and SQLite writes are not tested.",
        "No real-world SLA accuracy is claimed.",
        "No agency deadlines are independently verified.",
        "",
    ]

    success = result.wasSuccessful() and result_success

    lines.append(
        "FINAL RESULT: " + ("PASS" if success else "FAIL")
    )

    report_text = "\n".join(lines)

    REPORT.write_text(
        report_text,
        encoding="utf-8",
    )

    print(report_text)
    print(f"\nReport saved to: {REPORT}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
