
"""
Step 31C: Priority Queue Validation

Read-only validation utilities.
No Ollama calls or database writes.
"""

from pathlib import Path
import pandas as pd

from recommendation_engine import recommend_case_action

ROOT = Path(__file__).resolve().parent.parent
SIMULATION_FILE = (
    ROOT / "Output" / "integrated_priority_queue.csv"
)

RISK_ORDER = {
    "Breached": 1,
    "At Risk": 2,
    "Within SLA": 3,
    "Unknown": 4,
}

CLOSED_STATUSES = {"Resolved", "Closed"}


def build_priority_queue(cases):
    """
    Apply the same ordering policy as the live dashboard:
    active first, then SLA risk, deadline, case ID.

    This is an independently callable implementation
    of the current queue-ordering policy.
    """
    df = pd.DataFrame(cases).copy()

    required = [
        "case_id",
        "status",
        "sla_risk",
        "sla_deadline",
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    if df.empty:
        df["is_active"] = pd.Series(dtype=bool)
        df["risk_order"] = pd.Series(dtype=int)
        df["action_queue_rank"] = pd.Series(dtype=int)
        return df

    if df["case_id"].isna().any():
        raise ValueError("Case IDs cannot be null.")

    df["case_id"] = df["case_id"].astype(str).str.strip()

    if df["case_id"].eq("").any():
        raise ValueError("Case IDs cannot be blank.")

    if df["case_id"].duplicated().any():
        raise ValueError("Duplicate case IDs detected.")

    df["is_active"] = ~df["status"].isin(
        CLOSED_STATUSES
    )

    df["risk_order"] = (
        df["sla_risk"]
        .map(RISK_ORDER)
        .fillna(4)
        .astype(int)
    )

    df["sla_deadline"] = pd.to_datetime(
        df["sla_deadline"],
        errors="coerce",
    )

    df = df.sort_values(
        [
            "is_active",
            "risk_order",
            "sla_deadline",
            "case_id",
        ],
        ascending=[False, True, True, True],
        kind="stable",
    ).reset_index(drop=True)

    df["action_queue_rank"] = range(
        1, len(df) + 1
    )

    return df


def active_queue(cases):
    """
    Return only active cases, preserving their rank
    from the full queue.
    """
    ranked = build_priority_queue(cases)
    return ranked[ranked["is_active"]].copy()


def check_queue_order(queue):
    """
    Verify that a supplied queue follows the policy.
    """
    if queue.empty:
        return True

    required = [
        "case_id",
        "status",
        "sla_risk",
        "sla_deadline",
    ]

    if any(col not in queue.columns for col in required):
        return False

    try:
        expected = build_priority_queue(
            queue[required]
        )
    except (ValueError, TypeError):
        return False

    return (
        queue["case_id"].astype(str).tolist()
        == expected["case_id"].tolist()
    )


def evaluate_recommendation(case):
    """
    Call the existing production recommendation engine.
    """
    return recommend_case_action(case)
