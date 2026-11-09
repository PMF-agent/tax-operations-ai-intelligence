
"""
Step 32 — Integration Validation Report Runner

Creates a persistent report under Output.
"""

from datetime import datetime
from pathlib import Path

from test_integration import main


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Output"
REPORT = OUTPUT / "integration_validation_report.txt"


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    try:
        exit_code, test_output = main()
    except Exception as exc:
        exit_code = 1
        test_output = (
            f"Integration validation could not run:\n"
            f"{type(exc).__name__}: {exc}"
        )

    status = "PASS" if exit_code == 0 else "FAIL"

    report = "\n".join([
        "STEP 32 — INTEGRATION VALIDATION",
        "=" * 50,
        "Generated: "
        + datetime.now().isoformat(
            timespec="seconds"
        ),
        "",
        "RESULT: " + status,
        "",
        "AUTOMATED TEST OUTPUT",
        "-" * 50,
        test_output,
        "",
        "TEST ISOLATION",
        "-" * 50,
        "Python modules copied to temporary project.",
        "SQLite database backed up to temporary file.",
        "Status updates run against temporary database.",
        "Original database remains unchanged.",
        "",
        "SCOPE LIMITATIONS",
        "-" * 50,
        "Validates database, lifecycle, audit,",
        "fingerprinting, freshness, recommendations,",
        "queue ordering, and simulation consistency.",
        "Does not automate Streamlit browser interaction.",
        "Does not execute live Ollama inference.",
        "Does not exercise the case-intake form.",
        "Does not independently validate SLA law or",
        "government processing deadlines.",
        "",
        "FINAL RESULT: " + status,
    ])

    REPORT.write_text(
        report,
        encoding="utf-8",
    )

    print("\n" + "=" * 50)
    print("STEP 32 FINAL RESULT:", status)
    print("Report:", REPORT)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
