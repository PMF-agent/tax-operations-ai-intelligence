
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "Dashboard"))

from recommendation_engine import recommend_case_action

base = {
    "case_type": "New Tax Registration",
    "agency_name": "California Employment Development Department",
    "agency_submission_date": None,
}

scenarios = [
    ("Agency follow-up", "Pending Agency", "Agency", "Within SLA", "Agency Follow-up"),
    ("Customer follow-up", "Pending Customer", "Customer", "Within SLA", "Customer Follow-up"),
    ("Agency notice", "In Progress", "None", "Within SLA", "Notice Triage"),
    ("SLA at risk", "Pending Agency", "Agency", "At Risk", "Preventive Intervention"),
    ("SLA breached", "Pending Agency", "Agency", "Breached", "SLA Escalation"),
]

passed = 0

for name, status, dependency, risk, expected in scenarios:
    case = {
        **base,
        "status": status,
        "dependency": dependency,
        "sla_risk": risk,
        "case_type": "Agency Notice" if name == "Agency notice" else "New Tax Registration",
    }

    result = recommend_case_action(case)
    actual = result["action_type"]
    ok = actual == expected
    passed += ok

    print(f"\n{name}: {'PASS' if ok else 'FAIL'}")
    print(f"Expected: {expected}")
    print(f"Actual:   {actual}")
    print(f"Action:   {result['action']}")

print(f"\nRESULT: {passed}/{len(scenarios)} scenarios passed")
