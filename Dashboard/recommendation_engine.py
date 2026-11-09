"""Evidence-aware, deterministic recommendations for synthetic US tax operations.

Advisory only. No database writes, AI calls, or external requests.
Preserves recommend_case_action(case) and its original return keys.
"""

from case_intelligence import is_unknown


def _known(value):
    return not is_unknown(value)


def _result(action_type, urgency, action, reason, checks=(), owner="Operations Analyst", escalation="None indicated"):
    return {
        "action_type": action_type,
        "urgency": urgency,
        "action": action,
        "reason": reason,
        # Optional additional fields for future dashboard enhancements.
        "verification_checks": list(checks),
        "suggested_owner": owner,
        "escalation_path": escalation,
    }


def recommend_case_action(case):
    status = str(case.get("status") or "").strip()
    risk = str(case.get("sla_risk") or "Unknown").strip()
    case_type = str(case.get("case_type") or "").strip()
    dependency = str(case.get("dependency") or "Unknown").strip()
    agency = case.get("agency_name")
    submitted = case.get("agency_submission_date")
    method = case.get("submission_method")
    state = case.get("state")
    subject = str(case.get("subject") or "")
    message = str(case.get("message") or "")

    # Status is authoritative for workflow routing. This also prevents stale
    # derived 'dependency' values from sending a pending case to analyst review.
    if status in ("Pending Agency", "Waiting on Agency"):
        dependency = "Agency"
    elif status in ("Pending Customer", "Waiting on Customer"):
        dependency = "Customer"

    if status in ("Resolved", "Closed"):
        return _result(
            "Closure Review", "Closed",
            "Verify the documented outcome and supporting evidence; confirm that the customer and internal records reflect the final status.",
            "The case is marked closed or resolved; closure evidence should be checked.",
            ("Outcome evidence", "Customer communication", "Internal record accuracy"),
        )

    if risk == "Breached":
        blocker = (
            "the agency blocker and available submission evidence" if dependency == "Agency"
            else "the outstanding customer request and its impact" if dependency == "Customer"
            else "the current case blocker and accountable owner"
        )
        return _result(
            "SLA Escalation", "Critical",
            f"Escalate the modeled SLA breach to the responsible operations lead; verify {blocker}, document a recovery plan, and give the customer a factual status update.",
            "The modeled SLA deadline has passed. This is an internal SLA signal, not a verified statutory deadline.",
            ("SLA policy and timestamp", "Blocking dependency", "Escalation owner", "Next customer update"),
            escalation="Operations lead; involve specialist or engineering only when supported by evidence",
        )

    if risk == "At Risk":
        blocker = (
            "confirm the agency follow-up channel and submission evidence" if dependency == "Agency"
            else "request the specific missing customer information" if dependency == "Customer"
            else "identify the immediate analyst action and accountable owner"
        )
        return _result(
            "Preventive Intervention", "High",
            f"Prioritize this case before the modeled SLA deadline: {blocker}; record the next checkpoint and proactively communicate any verified risk to the customer.",
            "The modeled SLA is within its configured at-risk threshold; no statutory deadline is inferred.",
            ("Modeled SLA deadline", "Next milestone", "Owner", "Customer update"),
            escalation="Operations lead if the blocker cannot be resolved in time",
        )

    if risk == "Unknown":
        return _result(
            "SLA Data Validation", "Review",
            "Validate the received timestamp, SLA policy, and configured SLA duration; then rerun prioritization before promising a completion date.",
            "The system cannot calculate a reliable modeled SLA risk.",
            ("Received timestamp", "SLA policy", "SLA hours"),
        )

    if case_type == "Agency Notice":
        return _result(
            "Notice Triage", "Routine",
            "Read the complete notice, verify its issuing agency and account, identify any stated response date and required action, assign an owner, and document the response plan. Escalate immediately if a verified deadline is imminent.",
            "Agency notices may contain specific instructions and deadlines that cannot be inferred from the case category alone.",
            ("Notice copy and identifier", "Issuing agency", "Stated response deadline", "Response owner"),
            escalation="Tax operations specialist if interpretation or deadline risk is unclear",
        )

    if dependency == "Agency":
        checks = []
        if not _known(agency):
            checks.append("confirm the correct agency")
        if not _known(submitted):
            checks.append("verify whether and when submission occurred")
        if not _known(method):
            checks.append("confirm the submission channel")
        prefix = "; ".join(checks)
        if prefix:
            prefix = prefix[0].upper() + prefix[1:] + "; "
        return _result(
            "Agency Follow-up", "Routine",
            prefix + "review available portal status or correspondence, locate the acknowledgement/reference if one exists, determine the next appropriate follow-up, and update the case and customer. Do not assume a submission was completed.",
            "The recorded workflow status indicates an external agency dependency; submission and response details require verification.",
            ("Agency identity", "Submission status and date", "Acknowledgement/reference", "Next follow-up checkpoint"),
        )

    if dependency == "Customer":
        return _result(
            "Customer Follow-up", "Routine",
            "Identify the exact information or authorization blocking progress, send a concise customer request explaining why it is needed, set a follow-up checkpoint, and record the response.",
            "The recorded workflow status indicates that customer input is required.",
            ("Specific information gap", "Customer request", "Follow-up checkpoint"),
        )

    if case_type == "New Tax Registration":
        agency_text = str(agency).strip() if _known(agency) else "the responsible agency"
        return _result(
            "Registration Readiness", "Routine",
            f"Confirm the applicable jurisdiction and tax account type, validate client entity and payroll details against authorized records, check prerequisites for {agency_text}, and verify whether an application has already been submitted before proceeding through the approved workflow.",
            "A new registration requires a verified intake and evidence trail; the case record alone does not prove filing readiness.",
            ("Jurisdiction and account type", "Authorized entity details", "Existing account check", "Submission evidence"),
        )

    if case_type == "Registration Maintenance":
        return _result(
            "Account Maintenance", "Routine",
            "Confirm the requested account change, compare it with the authorized client record and agency portal, identify required supporting evidence, and document the outcome or blocker before updating internal systems.",
            "Account maintenance requires verification of the existing record and the requested change.",
            ("Current account state", "Requested change", "Authorization", "Completion evidence"),
        )

    if case_type in ("Missing Documentation", "Document Collection"):
        return _result(
            "Document Collection", "Routine",
            "Identify the exact outstanding documents, check whether they already exist in approved records, request only the necessary items through an approved secure channel, and record receipt and validation.",
            "The case category indicates a documentation-dependent workflow.",
            ("Document checklist", "Existing records", "Secure request", "Receipt validation"),
        )

    if case_type == "Agency Follow-up":
        return _result(
            "Agency Follow-up Preparation", "Routine",
            "Verify the agency, previous correspondence, current account status, and any existing acknowledgement before selecting the appropriate agency follow-up channel; record the result and next checkpoint.",
            "The case type indicates follow-up work, but no pending-agency status has been recorded.",
            ("Agency identity", "Previous correspondence", "Current account status", "Next checkpoint"),
        )

    return _result(
        "Analyst Triage", "Routine",
        "Review the inbound request, verify the client and jurisdiction, identify the actual operational task and blocker, assign an accountable owner, and record the next milestone. Flag a reproducible system or process gap to the appropriate internal team if evidence supports it.",
        "No higher-priority SLA, dependency, or category-specific workflow is established from the structured case fields.",
        ("Client and jurisdiction", "Task classification", "Blocker", "Owner", "Next milestone"),
    )
