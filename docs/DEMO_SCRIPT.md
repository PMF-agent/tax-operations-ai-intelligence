# Interview Demonstration Script

Target duration: 5–7 minutes

## 0:00–0:45 — Business Problem

"This is an independent synthetic prototype I built
to explore how AI and deterministic rules can support
tax operations case management.

The goal was to make SLA risk, external dependencies,
and next actions more visible to an operations analyst."

## 0:45–1:30 — Architecture

Show ARCHITECTURE.md.

"The application uses Streamlit for the interface,
SQLite for case persistence, Python for SLA and
recommendation rules, and a local Ollama model
for advisory analysis."

Emphasize that deterministic rules and AI are separate.

## 1:30–2:30 — Operational Queue

Open the Live Cases tab.

Show the risk filters, priority ordering, and
context-aware action recommendations.

Explain that breached and at-risk active cases
are prioritized before routine cases.

## 2:30–3:30 — Case Lifecycle

Select TX-1051, if it still exists.

Show its status, dependency, recommendation,
and audit history.

Explain that case status changes are traceable
and do not silently reset the SLA clock.

Avoid changing the case during a short demo
unless the environment has been prepared.

## 3:30–4:30 — AI Freshness

Show the saved AI analysis and freshness indicator.

"The model predicts case information, but the system
also checks whether the case inputs have changed
since the analysis was generated."

If practical, demonstrate a status change and
the stale indicator using a disposable test case.

## 4:30–5:30 — Evaluation

Open the evaluation summary.

Explain agreement against provisional synthetic
reference labels, including disagreements and
the distinction between raw and hybrid predictions.

Do not describe these numbers as real-world accuracy.

## 5:30–6:30 — Validation

Open the saved priority and integration reports.

"The queue validation checks ordering and
recommendation behavior. The integration suite
runs against a temporary database snapshot,
so the original data remains unchanged."

Mention the eight integration tests and
seven manual checks.

## 6:30–7:00 — Reflection

"The strongest part of the design is the separation
between deterministic operational controls and
advisory AI. If I extended this project, I would
focus on independently reviewed labels,
configurable SLA calendars, security, and
end-to-end UI testing."

## Before Recording

- Start Streamlit and Ollama
- Confirm the dashboard loads
- Verify the selected case exists
- Check that the saved reports are present
- Avoid showing personal paths, secrets,
  or unrelated desktop content
- Keep the demonstration within seven minutes
