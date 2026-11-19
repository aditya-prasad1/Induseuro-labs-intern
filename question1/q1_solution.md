# Question 1 Submission

## Changes to `agent.py`


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

## Design
Question 1 uses local hybrid retrieval followed by one focused LLM call.

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

## Retriever

```mermaid
flowchart TD
    Q[Query] --> B[BM25 lexical search]
    Q --> E[Semantic embedding search]
    B --> F[Reciprocal Rank Fusion]
    E --> F
    F --> A[Top 2 KB articles]

    classDef input fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef search fill:#dcfce7,stroke:#16a34a,color:#111827
    classDef fusion fill:#fef3c7,stroke:#d97706,color:#111827
    classDef output fill:#fce7f3,stroke:#db2777,color:#111827
    class Q input
    class B,E search
    class F fusion
    class A output
```

Implementation: [question1/retriever.py](question1/retriever.py)

## Per-call billing breakdown

Measured using the current implementation:

| Ticket | Points |
|---|---:|
| `T-1001` | 1,704 |
| `T-1002` | 1,575 |
| `T-1003` | 1,515 |
| `T-1004` | 1,476 |
| `T-1091` | 1,566 |
| **Average** | **1,567.2** |

This design is averaging **1,567 points per
ticket**. 
Every public ticket is below the **3,000-point target**.


