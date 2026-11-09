
import hashlib
import json

UNKNOWN_VALUES = {
    "", "unknown", "not specified", "none", "null", "nan"
}


def is_unknown(value):
    if value is None:
        return True
    return str(value).strip().lower() in UNKNOWN_VALUES


def case_fingerprint(case):
    """Fingerprint the inputs used for AI classification."""
    fields = ["state", "status", "subject", "message"]
    data = {
        field: str(case.get(field) or "").strip()
        for field in fields
    }
    encoded = json.dumps(
        data, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def information_gaps(case):
    """Identify unrecorded fields, without inventing requirements."""
    gaps = []

    if is_unknown(case.get("assigned_to")) or (
        str(case.get("assigned_to", "")).strip().lower()
        == "unassigned"
    ):
        gaps.append("Assigned analyst is not recorded")

    if is_unknown(case.get("registration_type")):
        gaps.append("Registration type is not recorded")

    if is_unknown(case.get("agency_name")):
        gaps.append("Agency name is not recorded")

    if is_unknown(case.get("submission_method")):
        gaps.append("Submission method is not recorded")

    if is_unknown(case.get("agency_submission_date")):
        gaps.append("Agency submission date is not recorded")

    return gaps


def ai_freshness(case, analysis):
    if not analysis:
        return "Not Analyzed"

    if analysis.get("analysis_status") != "Completed":
        return "Analysis Failed"

    saved = analysis.get("input_fingerprint")

    if not saved:
        return "Unverified Snapshot"

    if saved != case_fingerprint(case):
        return "Stale — Reanalysis Recommended"

    return "Current"


def quality_summary(case, analysis):
    gaps = information_gaps(case)
    freshness = ai_freshness(case, analysis)

    return {
        "freshness": freshness,
        "unrecorded_fields": gaps,
        "unrecorded_count": len(gaps),
        "needs_ai_review": freshness != "Current"
    }
