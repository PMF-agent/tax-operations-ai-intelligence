
"""
Step 31B — Context-Aware Operational Recommendations

Deterministic, explainable recommendations.
No Ollama calls, database writes, or external APIs.
"""

from case_intelligence import is_unknown


def recommend_case_action(case):
    status = str(case.get("status") or "").strip()
    risk = str(case.get("sla_risk") or "Unknown").strip()
    dependency = str(case.get("dependency") or "Unknown").strip()
    case_type = str(case.get("case_type") or "").strip()

    agency = case.get("agency_name")
    submission_date = case.get("agency_submission_date")

    if status in ("Resolved", "Closed"):
        return {
            "action": (
                "Review closure evidence and confirm "
                "that the case outcome is documented."
            ),
            "reason": "Case is no longer active.",
            "action_type": "Closure Review",
            "urgency": "Closed",
        }

    # SLA risk takes precedence over routine follow-up.
    if risk == "Breached":
        if dependency == "Agency":
            action = (
                "Escalate the SLA breach, review the "
                "agency blocker, and communicate the "
                "current position to the customer."
            )
        elif dependency == "Customer":
            action = (
                "Escalate the SLA breach, identify the "
                "outstanding customer information, and "
                "request an urgent update."
            )
        else:
            action = (
                "Escalate the SLA breach to the "
                "responsible analyst and document "
                "the recovery plan."
            )

        return {
            "action": action,
            "reason": "The modeled SLA deadline has passed.",
            "action_type": "SLA Escalation",
            "urgency": "Critical",
        }

    if risk == "At Risk":
        if dependency == "Agency":
            action = (
                "Prioritise agency follow-up, verify "
                "submission evidence, and review "
                "escalation options before the deadline."
            )
        elif dependency == "Customer":
            action = (
                "Prioritise the outstanding customer "
                "request and confirm the next action "
                "before the SLA deadline."
            )
        else:
            action = (
                "Prioritise analyst action and confirm "
                "the next milestone before the deadline."
            )

        return {
            "action": action,
            "reason": (
                "The modeled SLA is within its "
                "configured at-risk threshold."
            ),
            "action_type": "Preventive Intervention",
            "urgency": "High",
        }

    if risk == "Unknown":
        return {
            "action": (
                "Verify the received date, SLA policy, "
                "and applicable SLA duration before "
                "assigning a risk-based action."
            ),
            "reason": "SLA risk could not be determined.",
            "action_type": "Data Validation",
            "urgency": "Review",
        }

    # Context-specific recommendations for cases
    # that are currently within the modeled SLA.
    if dependency == "Agency":
        if case_type == "New Tax Registration":
            checks = []

            if is_unknown(submission_date):
                checks.append("agency submission date")

            if is_unknown(agency):
                checks.append("agency name")

            if checks:
                detail = (
                    "Verify the "
                    + " and ".join(checks)
                    + ", obtain or verify the agency "
                    "confirmation reference if available, "
                )
            else:
                detail = (
                    "Verify the recorded agency submission "
                    "details and confirmation reference "
                    "if available, "
                )

            action = (
                detail
                + "follow up with the agency as "
                "appropriate, and update the customer."
            )

        else:
            action = (
                "Verify the agency submission or "
                "correspondence details, follow up "
                "as appropriate, and record the "
                "latest status for the customer."
            )

        return {
            "action": action,
            "reason": (
                "The case is waiting on an external "
                "agency, even though the modeled "
                "SLA is currently within its limit."
            ),
            "action_type": "Agency Follow-up",
            "urgency": "Routine",
        }

    if dependency == "Customer":
        return {
            "action": (
                "Identify the outstanding customer "
                "information, send a targeted follow-up, "
                "and record the response or next check-in."
            ),
            "reason": (
                "Customer input is required to "
                "progress the case."
            ),
            "action_type": "Customer Follow-up",
            "urgency": "Routine",
        }

    if case_type == "Missing Documentation":
        return {
            "action": (
                "Review the outstanding document "
                "requirements, confirm what has been "
                "received, and request any remaining "
                "items through the approved workflow."
            ),
            "reason": (
                "The case type indicates a "
                "documentation workflow."
            ),
            "action_type": "Document Review",
            "urgency": "Routine",
        }

    if case_type == "Agency Notice":
        return {
            "action": (
                "Review the agency notice, identify "
                "any stated response requirements, "
                "and assign the next analyst action."
            ),
            "reason": (
                "Agency notices require review "
                "of their specific contents."
            ),
            "action_type": "Notice Review",
            "urgency": "Routine",
        }

    return {
        "action": (
            "Review the case details, confirm the "
            "next operational milestone, and "
            "document the planned follow-up."
        ),
        "reason": (
            "No urgent SLA trigger or explicit "
            "external dependency was identified."
        ),
        "action_type": "Analyst Review",
        "urgency": "Routine",
    }
