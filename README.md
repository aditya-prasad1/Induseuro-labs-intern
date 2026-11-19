# ShopAssist Design

## Submission

- Design document: `[Add design document link]`
- Video explanation: `[Add video explanation link]`

## Solution:

## 1. Question 1

### Architecture-Based Changes
1. <span style="color:red">LLM based KB article selection</span> →
<span style="color:green">Local hybrid retriever using BM25 (lexical) and embeddings (semantic) search with reciprocal rank fusion (RRF)</span>
2. <span style="color:red">Full article blobs</span> →
<span style="color:green">Relevant articles</span>

### Prompt Engineering
3. <span style="color:red">4 redundant few-shot examples</span> →
<span style="color:green">2 concise examples</span>
4. <span style="color:red">Verbose reasoning</span> →
<span style="color:green">Only the required JSON</span>
5. <span style="color:green">Run ID removed from the prompt</span>

### Design

Question1 uses local hybrid retrieval followed by one focused LLM call.

```mermaid
flowchart TD
    T[Ticket] --> Q[Build query]
    O[Order] --> Q
    Q --> R[Retriever]
    R --> P[Compose prompt]
    T --> P
    O --> P
    P --> L[One LLM call]
    L --> J[Resolution JSON]

    classDef input fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef retrieve fill:#dcfce7,stroke:#16a34a,color:#111827
    classDef llm fill:#fef3c7,stroke:#d97706,color:#111827
    classDef output fill:#fce7f3,stroke:#db2777,color:#111827
    class T,O,Q input
    class R retrieve
    class P,L llm
    class J output
```

### Retriever

```mermaid
flowchart TD
    Q[Query] --> B[BM25 lexical search]
    Q --> E[Embedding semantic search]
    B --> F[Reciprocal Rank Fusion]
    E --> F
    F --> A[Top KB articles]

    classDef input fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef search fill:#dcfce7,stroke:#16a34a,color:#111827
    classDef fusion fill:#fef3c7,stroke:#d97706,color:#111827
    classDef output fill:#fce7f3,stroke:#db2777,color:#111827
    class Q input
    class B,E search
    class F fusion
    class A output
```

Implementation: [question1/agent.py](https://github.com/aditya-prasad1/Induseuro-labs-intern/blob/main/question1/agent.py)

### Per-ticket points

| Ticket | Points |
|---|---:|
| `T-1001` | 1,704 |
| `T-1002` | 1,575 |
| `T-1003` | 1,515 |
| `T-1004` | 1,476 |
| `T-1091` | 1,566 |
| **Average** | **1,567.2** |

## 2. Question 2

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

### Overall design

Question2 keeps the pipeline stages explicit:

```mermaid
flowchart TD
    T[Ticket + order] --> R[Retriever]
    R --> C[Compose]
    T --> C
    C --> A[Deterministic policy audit]
    K[rules.py<br/>Rules from KB articles] --> A
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
    class K audit
    class F output
```

### Deterministic audit

```mermaid
flowchart TD
    J[Typed model output] --> D[Deterministic policy validator]
    D --> V[Check action, citation, confidence]
    V --> C{Checks pass?}
    C -- No --> X[Escalate]
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

Implementation: [question2/agent.py](https://github.com/aditya-prasad1/Induseuro-labs-intern/blob/main/question2/agent.py).
Rules are defined from the KB articles in
[question2/rules.py](question2/rules.py).

### Per-ticket points

| Ticket | Points |
|---|---:|
| `T-1001` | 1,752 |
| `T-1002` | 1,623 |
| `T-1003` | 1,563 |
| `T-1004` | 1,524 |
| `T-1091` | 1,614 |
| **Average** | **1,615.2** |

## Further Improvements

1. **Summarize KB articles:** Send only relevant policy facts to the LLM to
   reduce token usage.
2. **Cache results:** Reuse retrieval and embedding results for recurring queries.
3. **Skip unnecessary nodes:** Bypass later pipeline stages for high-confidence
   deterministic cases.

