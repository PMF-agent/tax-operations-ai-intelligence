
import sqlite3
from datetime import time
from pathlib import Path

import pandas as pd
import streamlit as st

from case_intake import render_case_intake
from ai_engine import (
    process_case,
    get_analysis,
    initialize_ai_table,
)
from case_lifecycle import (
    ALLOWED_STATUSES,
    initialize_audit_table,
    update_case_status,
    get_case_history,
)
from case_intelligence import quality_summary
from recommendation_engine import recommend_case_action


st.set_page_config(
    page_title="Tax Operations AI",
    page_icon="📊",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "Data" / "operations.db"
SIMULATION_CSV = (
    ROOT / "Output" / "integrated_priority_queue.csv"
)

RISK_ORDER = {
    "Breached": 1,
    "At Risk": 2,
    "Within SLA": 3,
    "Unknown": 4,
}


# ============================================
# SLA CALCULATIONS
# ============================================

def business_deadline(received, hours):
    current = pd.Timestamp(received)
    remaining = float(hours)

    if pd.isna(current):
        return pd.NaT

    while True:
        if current.weekday() >= 5:
            current = (
                current.normalize()
                + pd.Timedelta(days=1, hours=9)
            )
            continue

        if current.time() < time(9):
            current = (
                current.normalize()
                + pd.Timedelta(hours=9)
            )

        if current.time() >= time(18):
            current = (
                current.normalize()
                + pd.Timedelta(days=1, hours=9)
            )
            continue

        closing = (
            current.normalize()
            + pd.Timedelta(hours=18)
        )

        available = (
            closing - current
        ).total_seconds() / 3600

        if remaining <= available:
            return current + pd.Timedelta(
                hours=remaining
            )

        remaining -= available
        current = (
            current.normalize()
            + pd.Timedelta(days=1, hours=9)
        )


def business_hours_between(start, end):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    if pd.isna(start) or pd.isna(end):
        return None

    if end < start:
        return -business_hours_between(end, start)

    total = 0.0
    day = start.normalize()

    while day <= end.normalize():
        if day.weekday() < 5:
            opening = day + pd.Timedelta(hours=9)
            closing = day + pd.Timedelta(hours=18)

            a = max(start, opening)
            b = min(end, closing)

            if b > a:
                total += (
                    b - a
                ).total_seconds() / 3600

        day += pd.Timedelta(days=1)

    return round(total, 2)


def calculate_sla(received, hours, policy, now):
    received = pd.to_datetime(
        received,
        errors="coerce",
    )

    if pd.isna(received):
        return pd.NaT, None, "Unknown"

    hours = float(hours)

    if policy == "Business Hours":
        deadline = business_deadline(
            received, hours
        )
        remaining = business_hours_between(
            now, deadline
        )

    elif policy == "Calendar Hours":
        deadline = (
            received + pd.Timedelta(hours=hours)
        )
        remaining = round(
            (deadline - now).total_seconds() / 3600,
            2,
        )

    else:
        return pd.NaT, None, "Unknown"

    if remaining is None:
        risk = "Unknown"
    elif now > deadline:
        risk = "Breached"
    elif remaining <= hours * 0.25:
        risk = "At Risk"
    else:
        risk = "Within SLA"

    return deadline, remaining, risk


# ============================================
# DEPENDENCY
# ============================================

def dependency_from_status(status):
    status = str(status).strip().lower()

    if status in (
        "pending customer",
        "waiting on customer",
    ):
        return "Customer"

    if status in (
        "pending agency",
        "waiting on agency",
    ):
        return "Agency"

    if status in (
        "new",
        "in progress",
        "resolved",
        "closed",
    ):
        return "None"

    return "Unknown"


# ============================================
# DATA LOADERS
# ============================================

def load_live_cases():
    if not DB_PATH.exists():
        return pd.DataFrame()

    initialize_ai_table()
    initialize_audit_table()

    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql_query(
            "SELECT * FROM cases",
            con,
        )

    if df.empty:
        return df

    now = pd.Timestamp.now()
    records = []

    for _, row in df.iterrows():
        item = row.to_dict()

        deadline, remaining, risk = calculate_sla(
            item["received_date"],
            item["sla_hours"],
            item["sla_policy"],
            now,
        )

        dependency = dependency_from_status(
            item["status"]
        )

        analysis = get_analysis(item["case_id"])
        quality = quality_summary(item, analysis)

        item.update({
            "sla_deadline": deadline,
            "hours_remaining": remaining,
            "sla_risk": risk,
            "dependency": dependency,
            "is_active": item["status"] not in (
                "Resolved",
                "Closed",
            ),
            "risk_order": RISK_ORDER.get(risk, 4),
            "ai_freshness": quality["freshness"],
            "unrecorded_count": (
                quality["unrecorded_count"]
            ),
            "agency_processing_status": (
                "Insufficient Information"
            ),
        })

        recommendation = recommend_case_action(item)

        item["priority_action"] = recommendation["action"]
        item["action_type"] = recommendation["action_type"]
        item["action_urgency"] = recommendation["urgency"]
        item["action_reason"] = recommendation["reason"]

        records.append(item)

    result = pd.DataFrame(records)

    result = result.sort_values(
        [
            "is_active",
            "risk_order",
            "sla_deadline",
            "case_id",
        ],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)

    result["action_queue_rank"] = range(
        1, len(result) + 1
    )

    return result


def load_simulation():
    if not SIMULATION_CSV.exists():
        return pd.DataFrame()

    return pd.read_csv(
        SIMULATION_CSV,
        keep_default_na=False,
    )


# ============================================
# LIVE DASHBOARD
# ============================================

def show_live_dashboard(df):
    active = df[df["is_active"]]

    cols = st.columns(5)

    cols[0].metric("Total Cases", len(df))
    cols[1].metric(
        "Active Breached",
        int((
            active["sla_risk"] == "Breached"
        ).sum()),
    )
    cols[2].metric(
        "Active At Risk",
        int((
            active["sla_risk"] == "At Risk"
        ).sum()),
    )
    cols[3].metric(
        "Active Within SLA",
        int((
            active["sla_risk"] == "Within SLA"
        ).sum()),
    )
    cols[4].metric(
        "Resolved / Closed",
        len(df) - len(active),
    )

    st.divider()
    st.subheader("Operational Priority Queue")

    c1, c2, c3 = st.columns(3)

    with c1:
        risks = st.multiselect(
            "SLA Risk",
            sorted(df["sla_risk"].dropna().unique()),
            key="risk_filter",
        )

    with c2:
        statuses = st.multiselect(
            "Status",
            sorted(df["status"].dropna().unique()),
            key="status_filter",
        )

    with c3:
        freshness = st.multiselect(
            "AI Freshness",
            sorted(df["ai_freshness"].dropna().unique()),
            key="freshness_filter",
        )

    filtered = df.copy()

    if risks:
        filtered = filtered[
            filtered["sla_risk"].isin(risks)
        ]

    if statuses:
        filtered = filtered[
            filtered["status"].isin(statuses)
        ]

    if freshness:
        filtered = filtered[
            filtered["ai_freshness"].isin(freshness)
        ]

    columns = [
        "action_queue_rank",
        "case_id",
        "customer",
        "state",
        "case_type",
        "status",
        "dependency",
        "sla_policy",
        "sla_risk",
        "hours_remaining",
        "action_type",
        "action_urgency",
        "priority_action",
        "ai_freshness",
        "unrecorded_count",
    ]

    st.dataframe(
        filtered[columns],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Live Queue",
        filtered.to_csv(index=False),
        file_name="live_priority_queue.csv",
        mime="text/csv",
    )

    if filtered.empty:
        st.info("No cases match these filters.")
        return

    st.divider()
    st.subheader("Case Intelligence & Lifecycle")

    selected = st.selectbox(
        "Select Case",
        filtered["case_id"].tolist(),
        key="selected_live_case",
    )

    case = filtered[
        filtered["case_id"] == selected
    ].iloc[0]

    st.markdown(
        f"### {selected} — {case['customer']}"
    )

    left, right = st.columns(2)

    with left:
        st.write("**State:**", case["state"])
        st.write("**Case Type:**", case["case_type"])
        st.write("**Status:**", case["status"])
        st.write("**Dependency:**", case["dependency"])
        st.write(
            "**Assigned To:**",
            case["assigned_to"],
        )

    with right:
        st.write(
            "**SLA Policy:**",
            case["sla_policy"],
        )
        st.write(
            "**SLA Risk:**",
            case["sla_risk"],
        )
        st.write(
            "**Hours Remaining:**",
            case["hours_remaining"],
        )
        st.write(
            "**SLA Deadline:**",
            case["sla_deadline"],
        )
        st.write(
            "**Agency Processing:**",
            case["agency_processing_status"],
        )

    st.markdown("#### Case Description")
    st.write("**Subject:**", case["subject"])
    st.write(case["message"])

    # ========================================
    # CONTEXT-AWARE RECOMMENDATION
    # ========================================

    st.divider()
    st.subheader("Context-Aware Recommendation")

    a, b = st.columns(2)

    with a:
        st.write(
            "**Action Type:**",
            case["action_type"],
        )

    with b:
        st.write(
            "**Action Urgency:**",
            case["action_urgency"],
        )

    st.info(case["priority_action"])

    st.write(
        "**Why this action?**",
        case["action_reason"],
    )

    st.caption(
        "This recommendation is generated by "
        "explainable rules. It does not use Ollama "
        "or assume unverified agency deadlines."
    )

    # ========================================
    # QUALITY & FRESHNESS
    # ========================================

    st.divider()
    st.subheader(
        "AI Quality & Information Completeness"
    )

    analysis = get_analysis(selected)
    quality = quality_summary(
        case.to_dict(),
        analysis,
    )

    st.write(
        "**AI Freshness:**",
        quality["freshness"],
    )

    if quality["freshness"] == "Current":
        st.success(
            "Saved AI analysis matches the "
            "current case inputs."
        )

    elif quality["freshness"] == "Unverified Snapshot":
        st.warning(
            "This analysis predates input "
            "fingerprinting. Rerun AI to establish "
            "a verified snapshot."
        )

    elif quality["freshness"] == (
        "Stale — Reanalysis Recommended"
    ):
        st.warning(
            "Case inputs changed since the last "
            "successful AI analysis."
        )

    else:
        st.info(
            "A current successful AI analysis "
            "is not available."
        )

    st.write(
        "**Unrecorded Operational Fields:**",
        quality["unrecorded_count"],
    )

    if quality["unrecorded_fields"]:
        for gap in quality["unrecorded_fields"]:
            st.write("•", gap)
    else:
        st.success(
            "All monitored operational fields "
            "have recorded values."
        )

    st.caption(
        "These are data-completeness checks, "
        "not proof that an agency or legal "
        "requirement has not been fulfilled."
    )

    # ========================================
    # STATUS UPDATE
    # ========================================

    st.divider()
    st.subheader("Update Case Status")

    current_status = case["status"]

    with st.form(f"status_form_{selected}"):
        new_status = st.selectbox(
            "New Status",
            ALLOWED_STATUSES,
            index=(
                ALLOWED_STATUSES.index(current_status)
                if current_status in ALLOWED_STATUSES
                else 0
            ),
        )

        assigned = case["assigned_to"]

        analyst = st.text_input(
            "Analyst Name",
            value=(
                str(assigned)
                if pd.notna(assigned)
                else ""
            ),
        )

        reason = st.text_area(
            "Reason for Status Change"
        )

        submitted = st.form_submit_button(
            "Save Status Update",
            type="primary",
        )

    if submitted:
        success, message = update_case_status(
            selected,
            new_status,
            analyst,
            reason,
        )

        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    st.caption(
        "Status changes do not reset or pause "
        "SLA deadlines. Closed cases are excluded "
        "from active risk metrics."
    )

    # ========================================
    # AI ANALYSIS
    # ========================================

    st.divider()
    st.subheader("Local Ollama AI Analysis")

    if (
        analysis
        and analysis["analysis_status"] == "Completed"
    ):
        st.success("AI analysis available")

        st.write(
            "**Predicted Category:**",
            analysis["predicted_case_type"],
        )
        st.write(
            "**Predicted State:**",
            analysis["predicted_state"],
        )
        st.write(
            "**AI Dependency Prediction:**",
            analysis["predicted_dependency"],
        )
        st.write(
            "**AI Missing Information:**",
            analysis["missing_information"],
        )
        st.write(
            "**AI Suggested Action:**",
            analysis["recommended_next_action"],
        )

        st.caption(
            f"Model: {analysis['model_name']} | "
            f"Analyzed: {analysis['analyzed_at']}"
        )

    else:
        st.warning(
            "No successful AI analysis available."
        )

        if analysis and analysis.get("error_message"):
            st.caption(
                "Last AI error: "
                + analysis["error_message"]
            )

    if st.button(
        "Run / Retry AI Analysis",
        key=f"run_ai_{selected}",
    ):
        with st.spinner(
            "Running local qwen3:8b..."
        ):
            success, result = process_case(selected)

        if success:
            st.success("AI analysis saved.")
            st.rerun()
        else:
            st.error(
                f"AI analysis failed: {result}"
            )

    st.caption(
        "AI output is advisory. Deterministic "
        "SLA and recommendation rules remain "
        "separate from Ollama."
    )

    # ========================================
    # AUDIT HISTORY
    # ========================================

    st.divider()
    st.subheader("Case Audit History")

    history = get_case_history(selected)

    if history:
        history_df = pd.DataFrame(history)

        st.dataframe(
            history_df[
                [
                    "changed_at",
                    "field_changed",
                    "old_value",
                    "new_value",
                    "changed_by",
                    "change_reason",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download Audit History",
            history_df.to_csv(index=False),
            file_name=(
                f"{selected}_audit_history.csv"
            ),
            mime="text/csv",
            key=f"audit_download_{selected}",
        )

    else:
        st.info(
            "No status changes recorded yet."
        )


# ============================================
# ORIGINAL 50-CASE SIMULATION
# ============================================

def show_simulation(df):
    st.subheader(
        "Original 50-Case Simulation"
    )

    st.info(
        "Fixed simulation: 7 November 2026, "
        "12:00 PM. Business hours: "
        "Monday–Friday, 9 AM–6 PM."
    )

    cols = st.columns(4)

    cols[0].metric("Total Cases", len(df))
    cols[1].metric(
        "Breached",
        int((
            df["business_sla_risk"] == "Breached"
        ).sum()),
    )
    cols[2].metric(
        "At Risk",
        int((
            df["business_sla_risk"] == "At Risk"
        ).sum()),
    )
    cols[3].metric(
        "Within SLA",
        int((
            df["business_sla_risk"] == "Within SLA"
        ).sum()),
    )

    columns = [
        "action_queue_rank",
        "case_id",
        "customer",
        "state",
        "case_type",
        "status",
        "dependency",
        "business_sla_risk",
        "remaining_business_hours",
        "priority_action",
    ]

    st.dataframe(
        df[columns],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Simulation Queue",
        df.to_csv(index=False),
        file_name="simulation_priority_queue.csv",
        mime="text/csv",
    )

    selected = st.selectbox(
        "Select Simulation Case",
        df["case_id"].tolist(),
        key="simulation_case",
    )

    case = df[
        df["case_id"] == selected
    ].iloc[0]

    st.markdown(
        "#### Simulation Case Intelligence"
    )

    st.write(
        "**Customer:**",
        case["customer"],
    )
    st.write(
        "**Status:**",
        case["status"],
    )
    st.write(
        "**SLA Risk:**",
        case["business_sla_risk"],
    )
    st.write(
        "**Subject:**",
        case["subject"],
    )
    st.write(case["message"])

    st.write(
        "**AI Predicted Category:**",
        case.get(
            "predicted_case_type",
            "Unavailable",
        ),
    )
    st.write(
        "**AI Suggested Action:**",
        case.get(
            "recommended_next_action",
            "Unavailable",
        ),
    )

    st.divider()
    st.subheader("SLA Policy Sensitivity")

    comparison = pd.DataFrame({
        "Policy": [
            "Calendar Hours",
            "Business Hours",
        ],
        "Breached Cases": [
            int((
                df["calendar_sla_status"]
                == "Breached"
            ).sum()),
            int((
                df["business_sla_risk"]
                == "Breached"
            ).sum()),
        ],
    })

    st.bar_chart(
        comparison.set_index("Policy")
    )

    st.caption(
        "Differences reflect SLA policy "
        "assumptions, not improved "
        "operational performance."
    )


# ============================================
# NAVIGATION
# ============================================

with st.sidebar:
    st.title("Tax Operations AI")
    st.caption(
        "Operations Intelligence Prototype"
    )

    page = st.radio(
        "Navigation",
        [
            "Operations Dashboard",
            "Create New Case",
        ],
    )

    st.divider()
    st.caption(
        "Independent synthetic prototype"
    )


if page == "Create New Case":
    render_case_intake()
    st.stop()


st.title(
    "AI-Powered SLA Prevention "
    "& Prioritisation"
)

live_df = load_live_cases()
simulation_df = load_simulation()

tab1, tab2 = st.tabs([
    "Live Cases (SQLite)",
    "Original 50-Case Simulation",
])

with tab1:
    st.info(
        "Live SLA evaluation uses local computer "
        "time. Business hours are Monday–Friday, "
        "9 AM–6 PM. Holidays, timezone differences "
        "and SLA pauses are not modeled."
    )

    st.caption(
        "Evaluation time: "
        + pd.Timestamp.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    if live_df.empty:
        st.warning(
            "No SQLite cases found."
        )
    else:
        show_live_dashboard(live_df)

with tab2:
    if simulation_df.empty:
        st.error(
            "Original simulation CSV not found."
        )
    else:
        show_simulation(simulation_df)

st.divider()
st.caption(
    "Synthetic educational prototype. "
    "AI recommendations require human review. "
    "Not affiliated with Rippling."
)
