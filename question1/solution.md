1) Prompt Engineering
- No need to use Run ID in the prompt
- Shorten FEW SHOT (4x to 2x in each query)
- Instead of full blown explanation, should output only the relevant JSON
2) Instead of using LLM over each kb article, we could find relevant article via BM25 + embeddings -> RRF
we wouldn't use vector db as the article size would stay the same over the period of time, unlike most prod db, as bm25 (lexical) + embeddings (semantic) suffice.