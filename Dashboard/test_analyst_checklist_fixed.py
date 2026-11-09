"""Run: python test_analyst_checklist.py (no production DB changes)."""
import sqlite3
from contextlib import closing
import tempfile
from pathlib import Path
from analyst_checklist import (ensure_case_checklist, set_task_completion,
                               get_case_checklist, get_checklist_history)

with tempfile.TemporaryDirectory() as folder:
    db = Path(folder) / 'test.db'
    with closing(sqlite3.connect(db)) as con:
        con.execute('CREATE TABLE cases (case_id TEXT PRIMARY KEY)')
        con.execute("INSERT INTO cases VALUES ('TX-TEST')")
        con.commit()
    tasks = ensure_case_checklist('TX-TEST', 'Agency Follow-up', db)
    assert len(tasks) == 6
    assert len(ensure_case_checklist('TX-TEST', 'Agency Follow-up', db)) == 6
    key = tasks[0]['task_key']
    assert set_task_completion('TX-TEST', 'Agency Follow-up', key, True, 'Demo Analyst', db_path=db)
    assert not set_task_completion('TX-TEST', 'Agency Follow-up', key, True, 'Demo Analyst', db_path=db)
    assert get_case_checklist('TX-TEST', 'Agency Follow-up', db)[0]['completed'] == 1
    assert set_task_completion('TX-TEST', 'Agency Follow-up', key, False, 'Demo Analyst', db_path=db)
    assert len(get_checklist_history('TX-TEST', db)) == 2
    ensure_case_checklist('TX-TEST', 'Notice Triage', db)
    assert len(get_case_checklist('TX-TEST', 'Agency Follow-up', db)) == 6
    assert len(get_case_checklist('TX-TEST', 'Notice Triage', db)) == 5
    print('PASS: checklist creation, idempotency, persistence, history, reopening, workflow isolation')
