# Question 2 Submission

## Changes to `agent.py`

### Architecture-Based Changes

1. <span style="color:red">Multi-node pipeline with multiple LLM calls</span> →
<span style="color:green">Triage/Retriever (local) → Compose (LLM) → Audit
(local)</span>

2. <span style="color:red">4 LLM Calls</span> →
<span style="color:green">1 LLM Call</span>

3. <span style="color:red">LLM-based KB article selection</span> →
<span style="color:green">Local hybrid retriever using BM25 (lexical) and
embeddings (semantic) search with reciprocal rank fusion (RRF)</span>

4. <span style="color:red">LLM-based audit</span> →
<span style="color:green">Deterministic boundary rules from the KB articles</span>

### Prompt Engineering

3. <span style="color:red">4 redundant few shot examples</span> →
<span style="color:green">2 concise examples</span>
4. <span style="color:red">Verbose reasoning</span> →
<span style="color:green">Only the required JSON</span>
5. <span style="color:green">Run ID removed from the prompt</span>
6. <span style="color:green"> Second triage call removed </span>

## Overall design

```mermaid
flowchart TD
    T[Ticket + order] --> R[Retriever]
    R --> C[Compose]
    T --> C
    C --> A[Deterministic policy audit]
    A --> F[Final result]

    classDef input fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef retrieve fill:#dcfce7,stroke:#16a34a,color:#111827
    classDef compose fill:#fef3c7,stroke:#d97706,color:#111827
    classDef audit fill:#ede9fe,stroke:#7c3aed,color:#111827
    classDef output fill:#fce7f3,stroke:#db2777,color:#111827
    class T input
    class R retrieve
    class C compose
    class A audit
    class F output
```

## Deterministic audit

```mermaid
flowchart TD
    J[Typed model output] --> D[Deterministic policy validator]
    D --> V[Check action, citation, confidence]
    V --> C{Checks pass?}
    C -- No --> X[ESCALATE_TIER2]
    C -- Yes --> F[AuditResult]

    classDef input fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef check fill:#ede9fe,stroke:#7c3aed,color:#111827
    classDef escalation fill:#fee2e2,stroke:#dc2626,color:#111827
    classDef output fill:#dcfce7,stroke:#16a34a,color:#111827
    class J input
    class D,V,C check
    class X escalation
    class F output
```

Rules are defined from the KB articles in
[question2/rules.py](question2/rules.py).

## Per-call billing breakdown

Measured using the current implementation:

| Ticket | Points |
|---|---:|
| `T-1001` | 1,752 |
| `T-1002` | 1,623 |
| `T-1003` | 1,563 |
| `T-1004` | 1,524 |
| `T-1091` | 1,614 |
| **Average** | **1,615.2** |


Each ticket remains below the Question2 target of 2,500 points.
