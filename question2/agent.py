from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from question1.retriever import ArticleRetriever, ScoredArticle, build_query
from question2.rules import Action, RuleResult, resolve_order
from shared.billing import CostSession
from shared.llm import ChatMessage, LlmClient
from shared.tools import format_thread, get_order, get_ticket


ALLOWED_ACTIONS = tuple(action.value for action in Action)


class TicketOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: Action
    kb_article: str
    evidence: list[str] = Field(default_factory=list)
    customer_reply: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class TicketOutputError(ValueError):
    """Raised when the compose node does not return a valid ticket output."""


@dataclass(frozen=True)
class AuditResult:
    action: Action
    kb_article: str
    evidence: list[str]
    customer_reply: str
    confidence: float
    audited_at: datetime


SYSTEM_PROMPT = """You are ShopAssist, a Tier-1 customer support copilot.
Triage the ticket using the order snapshot and retrieved help-center articles.
Choose exactly one action from ALLOWED_ACTIONS: {allowed_actions}.
Cite one retrieved article slug in kb_article, or "none" if no article applies.
List the order or ticket facts supporting the decision in evidence. Draft a
concise customer_reply and return confidence from 0 to 1.
Return only JSON with: action, kb_article, evidence, customer_reply, confidence."""


def parse_resolution(text: str) -> TicketOutput:
    try:
        return TicketOutput.model_validate_json(text)
    except (ValidationError, ValueError, TypeError) as exc:
        raise TicketOutputError(f"Invalid ticket output: {exc}") from exc


def audit(
    res: RuleResult,
    order: dict,
    retrieved_slugs: Sequence[str],
    parsed: TicketOutput,
    now: datetime | None = None,
) -> AuditResult:
    """Apply citation, confidence, and article policy checks to a draft."""
    expected = resolve_order(order)
    retrieved = set(retrieved_slugs)
    action = parsed.action
    article = parsed.kb_article
    evidence = list(parsed.evidence)

    if action.value not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")

    if article != "none" and article not in retrieved:
        action = Action.ESCALATE_TIER2
        article = "none"
        evidence.append("The cited article was not retrieved.")

    if action != Action.ESCALATE_TIER2 and article == "none":
        action = Action.ESCALATE_TIER2
        evidence.append("A non-escalation action requires an article citation.")

    if parsed.confidence < 0.5:
        action = Action.ESCALATE_TIER2
        evidence.append("Confidence below 0.5 requires Tier 2 escalation.")

    if action == Action.ESCALATE_TIER2 and article == "none":
        for candidate in (expected.kb_article, res.kb_article):
            if candidate in retrieved:
                article = candidate
                break

    return AuditResult(
        action=action,
        kb_article=article,
        evidence=evidence,
        customer_reply=parsed.customer_reply,
        confidence=parsed.confidence,
        audited_at=now or datetime.now(timezone.utc),
    )


class SupportPipeline:
    """Retriever → compose → deterministic audit support pipeline."""

    _retriever: ArticleRetriever | None = None

    def __init__(self, session: CostSession | None = None):
        self.session = session or CostSession()
        self.llm = LlmClient(self.session)
        if SupportPipeline._retriever is None:
            SupportPipeline._retriever = ArticleRetriever()
        self.retriever = SupportPipeline._retriever

    def _retrieve(self, ticket: dict, order: dict) -> list[ScoredArticle]:
        customer_text = " ".join(
            message["text"]
            for message in ticket["messages"]
            if message["from"] == "customer"
        )
        return self.retriever.search(build_query(customer_text, order), top_k=2)

    def _compose(
        self,
        ticket_id: str,
        thread: str,
        snapshot: str,
        retrieved: Sequence[ScoredArticle],
    ) -> str:
        articles = "\n\n".join(
            f"--- {article.slug} ---\n{article.body}" for article in retrieved
        )
        messages = [
            ChatMessage(
                "system",
                SYSTEM_PROMPT.format(allowed_actions=", ".join(ALLOWED_ACTIONS)),
            ),
            ChatMessage(
                "user",
                "\n\n".join(
                    [
                        f"TICKET_ID: {ticket_id}",
                        f"THREAD:\n{thread}",
                        f"ORDER_SNAPSHOT:\n{snapshot}\nEND_SNAPSHOT",
                        f"RETRIEVED_ARTICLES:\n{articles}",
                    ]
                ),
            ),
        ]
        return self.llm.chat("compose", messages)

    def handle_ticket(self, ticket_id: str) -> AuditResult:
        ticket = get_ticket(ticket_id)
        order = get_order(ticket["order_id"])
        thread = format_thread(ticket)
        snapshot = json.dumps(order, indent=2)
        retrieved = self._retrieve(ticket, order)
        draft = self._compose(ticket_id, thread, snapshot, retrieved)
        parsed = parse_resolution(draft)
        return audit(
            resolve_order(order),
            order,
            [article.slug for article in retrieved],
            parsed,
            datetime.now(timezone.utc),
        )
