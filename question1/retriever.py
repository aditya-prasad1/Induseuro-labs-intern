"""
Hybrid article retriever for ShopAssist: BM25 (lexical) + embeddings (semantic),
fused with Reciprocal Rank Fusion.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from shared.kb import article_ids, load_article

DEFAULT_MODEL = "all-MiniLM-L6-v2"
RRF_K = 60
CACHE_DIR = Path(".retriever_cache")

_STOPWORDS = frozenset(
    "a an and are as at be but by for from had has have he her his i in is it "
    "its me my of on or our she so that the their them they this to was we were "
    "what when which who will with would you your".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in _STOPWORDS]


def load_articles() -> list[dict]:
    """
    Build article dicts from shared.kb. The article ID is the slug and the
    value the model cites as kb_article, so it doubles as the title for BM25.
    """
    return [
        {"slug": aid, "title": aid.replace("-", " "), "body": load_article(aid)}
        for aid in article_ids()
    ]


@dataclass
class ScoredArticle:
    slug: str
    title: str
    body: str
    score: float


class ArticleRetriever:
    def __init__(
        self,
        articles: list[dict] | None = None,
        model_name: str = DEFAULT_MODEL,
        rrf_k: int = RRF_K,
        cache: bool = True,
    ):
        articles = articles if articles is not None else load_articles()
        if not articles:
            raise ValueError("No articles to index")

        self.articles = articles
        self.model_name = model_name
        self.rrf_k = rrf_k
        self.model = SentenceTransformer(model_name)

        # Slug and title are repeated so slug-like terms (e.g. "returns within 30 days")
        # weigh more in BM25 than they would in the body alone.
        self.doc_texts = [
            f"{a['slug'].replace('-', ' ')} {a['title']} {a['title']} {a['body']}"
            for a in articles
        ]
        self.bm25 = BM25Okapi([tokenize(t) for t in self.doc_texts])
        self.doc_emb = self._load_or_encode(cache)

    def _load_or_encode(self, cache: bool) -> np.ndarray:
        # Key on model name and article content, so a model swap or article edit
        # invalidates the cache.
        key = hashlib.sha256(
            (self.model_name + json.dumps(self.articles, sort_keys=True)).encode()
        ).hexdigest()[:16]
        path = CACHE_DIR / f"emb_{key}.npy"

        if cache and path.exists():
            return np.load(path)

        emb = self.model.encode(
            self.doc_texts, normalize_embeddings=True, show_progress_bar=False
        )
        if cache:
            CACHE_DIR.mkdir(exist_ok=True)
            np.save(path, emb)
        return emb

    def search(self, query: str, top_k: int = 4) -> list[ScoredArticle]:
        if not query.strip():
            return []

        bm25_scores = self.bm25.get_scores(tokenize(query))
        q = self.model.encode(query, normalize_embeddings=True)
        dense_scores = self.doc_emb @ q

        fused = np.zeros(len(self.articles))
        for scores in (bm25_scores, dense_scores):
            order = np.argsort(-scores)
            # rank r (1-based) contributes 1 / (k + r)
            fused[order] += 1.0 / (self.rrf_k + np.arange(1, len(order) + 1))

        top = np.argsort(-fused)[:top_k]
        return [
            ScoredArticle(
                slug=self.articles[i]["slug"],
                title=self.articles[i]["title"],
                body=self.articles[i]["body"],
                score=float(fused[i]),
            )
            for i in top
        ]


def build_query(latest_message: str, order: dict) -> str:
    facts = []
    keys = (
        "product_type",
        "delivered_days_ago",
        "subscription_age_days",
        "opened",
        "license_revealed",
        "customized",
        "damage_reported",
    )
    for key in keys:
        value = order.get(key)
        if value is not None:
            facts.append(f"{key} {value}")
    return " ".join([latest_message, *facts]).strip()