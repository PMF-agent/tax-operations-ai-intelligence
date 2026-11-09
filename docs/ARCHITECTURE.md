# System Architecture

## Component Diagram

```mermaid
flowchart TD
    U[Operations Analyst] --> UI[Streamlit Dashboard]

    UI --> IN[Case Intake]
    UI --> LC[Lifecycle Management]
    UI --> Q[Operational Priority Queue]
    UI --> AI[AI Analysis Interface]

    IN --> DB[(SQLite Cases)]
    LC --> DB
    LC --> AUD[(SQLite Audit History)]

    DB --> SLA[Deterministic SLA Engine]
    DB --> REC[Recommendation Engine]
    DB --> F[Case Input Fingerprint]

    SLA --> Q
    REC --> Q

    AI --> O[Local Ollama qwen3:8b]
    O --> AIDB[(Saved AI Analysis)]

    F --> FR[AI Freshness Check]
    AIDB --> FR
    FR --> UI

    SIM[50-Case Simulation CSV] --> ST[Simulation Tab]
    ST --> UI
```

## Design Principles

1. SQLite stores live case records and audit information.
2. Deterministic logic owns SLA risk and operational priority.
3. Ollama provides advisory case interpretation.
4. Input fingerprints detect stale AI analysis.
5. The original simulation remains separate from live cases.
6. Evaluation and validation reports are reproducible
   from saved project artifacts.

## Important Boundaries

The AI model does not establish legal requirements,
calculate authoritative government deadlines,
or override the deterministic SLA engine.

The architecture represents the local prototype,
not a production cloud deployment.
