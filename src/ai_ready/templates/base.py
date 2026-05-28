"""Utilitários compartilhados entre templates semânticos."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_BIBLE_REF = re.compile(
    r"\b(?:[1-3]\s)?[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)*\s+\d{1,3}(?::\d{1,3}(?:-\d{1,3})?)?",
)
_URL = re.compile(r"https?://\S+")
_TIMESTAMP = re.compile(r"(?:\[\d{1,2}:\d{2}(?::\d{2})?\]|\d{1,2}:\d{2}(?::\d{2})?\s*[-–—]\s*)")
_NUMBERED = re.compile(r"^\s*(?:\d+[\.)]\s+|[-*•]\s+)", re.MULTILINE)
_QUOTED = re.compile(r'"([^"\n]{10,120})"|\'([^\'\n]{10,120})\'')


@dataclass
class TemplateContext:
    content: str
    title: str = ""
    topics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text.strip()) if p.strip()]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]


def extract_summary(text: str, *, max_chars: int = 400) -> str:
    paragraphs = _paragraphs(text)
    if not paragraphs:
        return "_Conteúdo insuficiente para resumo automático._"
    summary = paragraphs[0]
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return summary


def extract_main_points(text: str, *, limit: int = 7) -> list[str]:
    points: list[str] = []
    for match in _NUMBERED.finditer(text):
        start = match.start()
        end = text.find("\n", start)
        line = text[start:end if end != -1 else None].strip()
        cleaned = re.sub(r"^\s*(?:\d+[\.)]\s+|[-*•]\s+)", "", line).strip()
        if cleaned and len(cleaned) > 10:
            points.append(cleaned)

    if not points:
        for sentence in _sentences(text):
            if len(sentence) > 40 and sentence.endswith((".", "!", "?")):
                points.append(sentence)
            if len(points) >= limit:
                break

    return points[:limit]


def extract_notable_quotes(text: str, *, limit: int = 5) -> list[str]:
    quotes: list[str] = []
    for m in _QUOTED.finditer(text):
        quote = m.group(1) or m.group(2) or ""
        if quote.strip():
            quotes.append(quote.strip())
    if not quotes:
        for sentence in _sentences(text):
            if 30 <= len(sentence) <= 120 and any(w in sentence.lower() for w in ("deve", "precis", "important", "sempre", "nunca", "vida", "deus")):
                quotes.append(sentence)
            if len(quotes) >= limit:
                break
    return quotes[:limit]


def extract_references(text: str) -> list[str]:
    refs = list(dict.fromkeys(_BIBLE_REF.findall(text)))
    refs.extend(u.rstrip(".,;") for u in _URL.findall(text))
    return refs[:12]


def extract_timestamps(text: str, *, limit: int = 20) -> list[str]:
    lines = text.splitlines()
    stamps: list[str] = []
    for line in lines:
        if _TIMESTAMP.search(line):
            stamps.append(line.strip())
        if len(stamps) >= limit:
            break
    return stamps


def extract_tags(text: str, topics: list[str] | None = None) -> list[str]:
    tags = list(topics or [])
    keywords = ("fé", "oração", "bíblia", "evangelho", "discipulado", "família", "santidade")
    lower = text.lower()
    for kw in keywords:
        if kw in lower and kw not in tags:
            tags.append(kw)
    return tags[:10]


def extract_sections(ctx: TemplateContext) -> dict[str, object]:
    content = ctx.content
    return {
        "summary": extract_summary(content),
        "main_points": extract_main_points(content),
        "quotes": extract_notable_quotes(content),
        "references": extract_references(content),
        "timestamps": extract_timestamps(content),
        "tags": extract_tags(content, ctx.topics or ctx.tags),
        "structured_body": content,
    }


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}\n"


def _bullet_list(items: list[str], *, empty_msg: str = "_Nenhum item identificado._") -> str:
    if not items:
        return empty_msg
    return "\n".join(f"- {item}" for item in items)
