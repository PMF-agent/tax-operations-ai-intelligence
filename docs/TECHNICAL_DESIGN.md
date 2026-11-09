# Technical Design and Operational Rules

## SLA Policies

### Business Hours

Monday–Friday, 09:00–18:00.
No holidays, timezone offsets, or pause rules.

### Calendar Hours

Elapsed time from received timestamp to deadline.

### Risk Classification

- Breached: modeled deadline has passed
- At Risk: remaining time is within the configured
  threshold of 25% of the case SLA duration
- Within SLA: deadline has not passed and the
  at-risk threshold has not been reached
- Unknown: insufficient information or unsupported policy

## Priority Ordering

Live queue policy:

1. Active cases before Resolved or Closed cases
2. Breached before At Risk
3. At Risk before Within SLA
4. Within SLA before Unknown
5. Earlier deadlines before later deadlines
6. Case ID as a deterministic tie-breaker

Resolved and Closed cases are excluded from active
SLA metrics, but can remain visible in the full queue.

## Recommendation Precedence

1. Resolved or Closed: closure review
2. Breached: SLA escalation
3. At Risk: preventive intervention
4. Unknown SLA: data validation
5. Agency dependency: agency follow-up
6. Customer dependency: customer follow-up
7. Case-type-specific review
8. General analyst review

These are operational suggestions, not instructions
to disregard internal procedures or legal obligations.

## AI Input Freshness

The fingerprint covers:

- State
- Status
- Subject
- Message

Changes to other fields may not invalidate AI analysis.
This is an explicit limitation of the current design.

## Audit Trail

Lifecycle status changes are recorded with the
previous status, new status, analyst, reason, and time.

Status changes do not reset or pause modeled SLA time.

## Evaluation Methodology

AI predictions are compared with provisional synthetic
reference labels.

Agreement percentage:

    agreements / evaluable cases * 100

Records with missing reference or prediction values
are excluded from the corresponding field's agreement
denominator and counted as not evaluable.

The evaluation does not establish independently
verified model accuracy.

## Validation Scope

Unit-style tests verify ordering and recommendation
rules using synthetic examples.

Integration tests exercise lifecycle persistence,
audit behavior, fingerprints, recommendations, and
simulation consistency in an isolated database copy.

Manual checks cover the Streamlit interface and
a live local Ollama call.

## Known Engineering Gaps

- No independent production data validation
- No automated browser testing
- No authentication or authorization
- No holiday-aware SLA calendar
- No formal SLA policy versioning
- No full data-change event history
- No agency integration or API
- No demonstrated performance at scale
