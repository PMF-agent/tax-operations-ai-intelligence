"""Persistent, auditable analyst checklists for synthetic tax-operations cases.

No Streamlit dependency. Checklist items are generated from a deterministic
recommendation and stored separately from the existing case/audit tables.
"""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / 'Data' / 'operations.db'

PLAYBOOKS = {
    'Agency Follow-up': [
        ('verify_agency', 'Verify the agency and account details'),
        ('verify_submission', 'Confirm whether and when submission occurred'),
        ('check_acknowledgement', 'Locate submission acknowledgement or reference, if available'),
        ('review_correspondence', 'Review portal status or agency correspondence'),
        ('set_checkpoint', 'Record the next follow-up checkpoint'),
        ('update_records', 'Document findings and provide a factual customer update'),
    ],
    'Customer Follow-up': [
        ('identify_gap', 'Identify the specific missing information or authorization'),
        ('request_customer', 'Send a targeted request through an approved channel'),
        ('set_checkpoint', 'Set the next customer follow-up checkpoint'),
        ('record_response', 'Record the response or outstanding blocker'),
    ],
    'Notice Triage': [
        ('review_notice', 'Review the complete notice and its identifier'),
        ('verify_agency', 'Verify issuing agency and relevant tax account'),
        ('check_deadline', 'Check for an explicitly stated response deadline'),
        ('assign_owner', 'Assign response ownership and escalation if warranted'),
        ('record_plan', 'Document response plan and evidence'),
    ],
    'Preventive Intervention': [
        ('verify_sla', 'Verify modeled SLA deadline and policy'),
        ('identify_blocker', 'Identify the immediate blocker and responsible owner'),
        ('set_checkpoint', 'Record mitigation and next checkpoint'),
        ('update_customer', 'Communicate verified risks to the customer'),
    ],
    'SLA Escalation': [
        ('verify_breach', 'Verify modeled SLA breach and timestamps'),
        ('notify_lead', 'Notify the responsible operations lead'),
        ('document_blocker', 'Document blocker, owner, and recovery plan'),
        ('update_customer', 'Send a factual customer status update'),
    ],
    'Closure Review': [
        ('verify_outcome', 'Verify documented outcome and supporting evidence'),
        ('confirm_customer', 'Confirm customer communication'),
        ('verify_records', 'Check internal record accuracy'),
    ],
}

FALLBACK = [
    ('review_case', 'Review case details and confirm the next operational action'),
    ('record_checkpoint', 'Record the accountable owner and next checkpoint'),
    ('document_update', 'Document the outcome and any customer communication'),
]


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def initialize_checklist(db_path=DEFAULT_DB_PATH):
    """Create only new tables; leave existing schema and case records untouched."""
    with closing(sqlite3.connect(db_path, timeout=30)) as con, con:
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('''CREATE TABLE IF NOT EXISTS analyst_checklist_tasks (
            case_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            task_key TEXT NOT NULL,
            task_label TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0,1)),
            completed_by TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY(case_id, action_type, task_key),
            FOREIGN KEY(case_id) REFERENCES cases(case_id)
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS analyst_checklist_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            task_key TEXT NOT NULL,
            task_label TEXT NOT NULL,
            old_completed INTEGER NOT NULL,
            new_completed INTEGER NOT NULL,
            changed_by TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(case_id) REFERENCES cases(case_id)
        )''')


def ensure_case_checklist(case_id, action_type, db_path=DEFAULT_DB_PATH):
    """Idempotently add tasks for this case/action. Preserve historical workflows."""
    tasks = PLAYBOOKS.get(action_type, FALLBACK)
    now = _utc_now()
    initialize_checklist(db_path)
    with closing(sqlite3.connect(db_path, timeout=30)) as con, con:
        con.execute('PRAGMA foreign_keys=ON')
        if con.execute('SELECT 1 FROM cases WHERE case_id=?', (case_id,)).fetchone() is None:
            raise ValueError(f'Case not found: {case_id}')
        for key, label in tasks:
            con.execute('''INSERT OR IGNORE INTO analyst_checklist_tasks
                (case_id, action_type, task_key, task_label, created_at)
                VALUES (?, ?, ?, ?, ?)''', (case_id, action_type, key, label, now))
    return get_case_checklist(case_id, action_type, db_path)


def get_case_checklist(case_id, action_type, db_path=DEFAULT_DB_PATH):
    initialize_checklist(db_path)
    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute('''SELECT case_id, action_type, task_key, task_label,
            completed, completed_by, completed_at FROM analyst_checklist_tasks
            WHERE case_id=? AND action_type=? ORDER BY rowid''',
            (case_id, action_type)).fetchall()
    return [dict(row) for row in rows]


def set_task_completion(case_id, action_type, task_key, completed, analyst,
                        note='', db_path=DEFAULT_DB_PATH):
    """Change completion and append an event only when state actually changes."""
    analyst = (analyst or '').strip()
    if not analyst:
        raise ValueError('Analyst name is required')
    if not isinstance(completed, bool):
        raise ValueError('completed must be True or False')
    now = _utc_now()
    with closing(sqlite3.connect(db_path, timeout=30)) as con, con:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute('''SELECT completed, task_label FROM analyst_checklist_tasks
            WHERE case_id=? AND action_type=? AND task_key=?''',
            (case_id, action_type, task_key)).fetchone()
        if row is None:
            raise ValueError('Checklist task not found; initialize the checklist first')
        previous, label = row
        new = int(completed)
        if previous == new:
            return False
        con.execute('''UPDATE analyst_checklist_tasks SET completed=?, completed_by=?,
            completed_at=? WHERE case_id=? AND action_type=? AND task_key=?''',
            (new, analyst if completed else None, now if completed else None,
             case_id, action_type, task_key))
        con.execute('''INSERT INTO analyst_checklist_events
            (case_id, action_type, task_key, task_label, old_completed,
             new_completed, changed_by, changed_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (case_id, action_type, task_key, label, previous, new, analyst,
             now, (note or '').strip()))
    return True


def get_checklist_history(case_id, db_path=DEFAULT_DB_PATH):
    initialize_checklist(db_path)
    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute('''SELECT * FROM analyst_checklist_events
            WHERE case_id=? ORDER BY event_id DESC''', (case_id,)).fetchall()
    return [dict(row) for row in rows]
