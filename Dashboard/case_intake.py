
import sqlite3
from pathlib import Path
from datetime import datetime

import streamlit as st

from ai_engine import process_case

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "Data" / "operations.db"

STATES = [
    "Arizona", "California", "Colorado", "Florida",
    "Georgia", "Illinois", "Massachusetts",
    "New Jersey", "New York", "Oregon",
    "Texas", "Washington"
]

CASE_TYPES = [
    "New Tax Registration",
    "Registration Maintenance",
    "Agency Notice",
    "Agency Follow-up",
    "Missing Documentation",
    "Document Collection",
    "Other"
]

STATUSES = [
    "New",
    "In Progress",
    "Pending Customer",
    "Waiting on Customer",
    "Pending Agency",
    "Waiting on Agency"
]


def save_case(data):
    with sqlite3.connect(DB_PATH, timeout=30) as con:
        con.execute("BEGIN IMMEDIATE")

        existing = {
            row[0] for row in con.execute(
                "SELECT case_id FROM cases"
            )
        }

        number = 1051

        while f"TX-{number}" in existing:
            number += 1

        case_id = f"TX-{number}"
        now = datetime.now().isoformat(timespec="seconds")

        con.execute("""
            INSERT INTO cases (
                case_id, customer, state, case_type,
                subject, message, received_date,
                priority, status, sla_hours, sla_policy,
                assigned_to, registration_type,
                agency_name, submission_method,
                agency_submission_date, created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id,
            data["customer"],
            data["state"],
            data["case_type"],
            data["subject"],
            data["message"],
            data["received_date"],
            data["priority"],
            data["status"],
            data["sla_hours"],
            data["sla_policy"],
            data["assigned_to"],
            data["registration_type"],
            data["agency_name"],
            data["submission_method"],
            data["agency_submission_date"],
            now,
            now
        ))

    return case_id


def render_case_intake():
    st.header("Create New Case")
    st.caption("Synthetic operations case intake with local AI analysis")

    with st.form("case_intake", clear_on_submit=True):
        st.subheader("Customer & Case Information")

        customer = st.text_input("Customer Name *")
        state = st.selectbox("State", STATES)
        case_type = st.selectbox("Initial Case Type", CASE_TYPES)
        subject = st.text_input("Case Subject *")
        message = st.text_area("Case Description *", height=130)

        st.subheader("Operational Information")

        c1, c2 = st.columns(2)

        with c1:
            priority = st.selectbox(
                "Initial Priority",
                ["Medium", "Low", "High", "Critical"]
            )
            status = st.selectbox("Case Status", STATUSES)
            sla_hours = st.number_input(
                "SLA Hours",
                min_value=1.0,
                max_value=720.0,
                value=24.0
            )

        with c2:
            sla_policy = st.selectbox(
                "SLA Policy",
                ["Business Hours", "Calendar Hours"]
            )
            assigned_to = st.text_input(
                "Assigned Analyst",
                value="Unassigned"
            )
            received_date = st.datetime_input(
                "Received Date & Time",
                value=datetime.now()
            )

        st.subheader("Agency Information (Optional)")

        registration_type = st.text_input("Registration Type")
        agency_name = st.text_input("Agency Name")

        submission_method = st.selectbox(
            "Submission Method",
            ["Unknown", "Online", "Mail", "Other"]
        )

        date_known = st.checkbox(
            "Agency submission date is known"
        )

        agency_date = (
            st.date_input("Agency Submission Date")
            if date_known else None
        )

        submitted = st.form_submit_button(
            "Create Case & Run AI",
            type="primary"
        )

    if submitted:
        if not all([
            customer.strip(),
            subject.strip(),
            message.strip()
        ]):
            st.error("Customer, subject and description are required.")
            return

        if agency_date and agency_date > received_date.date():
            st.error(
                "Agency submission date cannot be after received date."
            )
            return

        data = {
            "customer": customer.strip(),
            "state": state,
            "case_type": case_type,
            "subject": subject.strip(),
            "message": message.strip(),
            "received_date": received_date.isoformat(
                timespec="seconds"
            ),
            "priority": priority,
            "status": status,
            "sla_hours": sla_hours,
            "sla_policy": sla_policy,
            "assigned_to": assigned_to.strip(),
            "registration_type": registration_type.strip() or "Unknown",
            "agency_name": agency_name.strip() or "Unknown",
            "submission_method": submission_method,
            "agency_submission_date": (
                agency_date.isoformat() if agency_date else None
            )
        }

        try:
            case_id = save_case(data)
        except sqlite3.Error as exc:
            st.error(f"Could not save case: {exc}")
            return

        st.success(f"Case {case_id} saved successfully in SQLite.")

        with st.spinner("Running local Ollama AI analysis..."):
            success, result = process_case(case_id)

        if success:
            st.success("AI classification completed.")

            st.write(
                "**Predicted Category:**",
                result["predicted_case_type"]
            )
            st.write(
                "**Predicted State:**",
                result["predicted_state"]
            )
            st.write(
                "**Predicted Dependency:**",
                result["predicted_dependency"]
            )
            st.write(
                "**Missing Information:**",
                result["missing_information"]
            )
            st.write(
                "**Recommended Next Action:**",
                result["recommended_next_action"]
            )

            st.caption(
                "AI analysis is advisory. Operational SLA "
                "calculations remain rule-based."
            )
        else:
            st.warning(
                "Case saved, but AI analysis did not complete."
            )
            st.code(str(result))
            st.info(
                "You can retry AI analysis from the live dashboard."
            )
