from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from rank_bm25 import BM25Okapi

from app.core.config import INDEX_DIR, ensure_directories

INDEX_FILE = INDEX_DIR / "index.json"


@dataclass
class IndexedDocument:
    doc_id: str
    title: str
    tags: str
    content: str
    tokens: list[str] = field(default_factory=list)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def ensure_index() -> None:
    ensure_directories()
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text(json.dumps({"documents": []}), encoding="utf-8")


def _load_index() -> list[IndexedDocument]:
    ensure_index()
    payload = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    documents = []
    for item in payload.get("documents", []):
        documents.append(
            IndexedDocument(
                doc_id=item["doc_id"],
                title=item["title"],
                tags=item.get("tags", ""),
                content=item["content"],
                tokens=item.get("tokens", []),
            )
        )
    return documents


def _save_index(documents: list[IndexedDocument]) -> None:
    payload = {
        "documents": [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "tags": doc.tags,
                "content": doc.content,
                "tokens": doc.tokens,
            }
            for doc in documents
        ]
    }
    INDEX_FILE.write_text(json.dumps(payload), encoding="utf-8")


def index_document(doc_id: str, title: str, content: str, tags: str) -> None:
    documents = _load_index()
    tokens = _tokenize(f"{title} {tags} {content}")
    updated = IndexedDocument(doc_id=doc_id, title=title, tags=tags, content=content, tokens=tokens)
    documents = [doc for doc in documents if doc.doc_id != doc_id]
    documents.append(updated)
    _save_index(documents)


def _apply_boolean_filter(documents: Iterable[IndexedDocument], query: str) -> list[IndexedDocument]:
    tokens = query.split()
    if not tokens:
        return []

    normalized = [token.upper() for token in tokens]
    terms = [token for token in tokens if token.upper() not in {"AND", "OR", "NOT"}]
    if not terms:
        return []

    def matches(doc: IndexedDocument) -> bool:
        doc_text = f"{doc.title} {doc.tags} {doc.content}".lower()
        include = True
        current_op = "OR"
        pending_not = False
        for raw in tokens:
            token = raw.upper()
            if token in {"AND", "OR"}:
                current_op = token
                continue
            if token == "NOT":
                pending_not = True
                continue
            term = raw.lower()
            term_match = term in doc_text
            if pending_not:
                term_match = not term_match
                pending_not = False
            if current_op == "AND":
                include = include and term_match
            else:
                include = include or term_match
        return include

    if any(token in {"AND", "OR", "NOT"} for token in normalized):
        return [doc for doc in documents if matches(doc)]
    return list(documents)


def _highlight_snippet(content: str, terms: list[str]) -> str:
    if not content:
        return ""
    lower = content.lower()
    for term in terms:
        idx = lower.find(term.lower())
        if idx != -1:
            start = max(idx - 50, 0)
            end = min(idx + 150, len(content))
            snippet = content[start:end]
            return re.sub(
                re.escape(term),
                lambda match: f"<strong>{match.group(0)}</strong>",
                snippet,
                flags=re.IGNORECASE,
            )
    return content[:200]


def search_documents(query: str, limit: int = 10, allowed_ids: list[int] | None = None):
    documents = _load_index()
    if allowed_ids is not None:
        allowed_set = {str(doc_id) for doc_id in allowed_ids}
        documents = [doc for doc in documents if doc.doc_id in allowed_set]

    filtered = _apply_boolean_filter(documents, query)
    if not filtered:
        return []

    corpus = [doc.tokens for doc in filtered]
    bm25 = BM25Okapi(corpus)
    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)
    ranked = sorted(zip(filtered, scores), key=lambda pair: pair[1], reverse=True)[:limit]

    results_payload = []
    for doc, _score in ranked:
        results_payload.append(
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "tags": doc.tags,
                "highlight": _highlight_snippet(doc.content, query_tokens),
            }
        )
    return results_payload
