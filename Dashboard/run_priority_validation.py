
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
    ]

    lines += [
        "",
        "VALIDATION SCOPE",
        "-" * 48,
        "Synthetic deterministic test cases.",
        "Production recommendation function tested directly.",
        "Queue ordering policy tested independently.",
        "Live Streamlit rendering and SQLite writes are not tested.",
        "No real-world SLA accuracy is claimed.",
        "No agency deadlines are independently verified.",
        "",
    ]

    success = result.wasSuccessful()

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
