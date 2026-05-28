"""Template para sermões e mensagens bíblicas."""

from __future__ import annotations

import re

from src.ai_ready.templates.base import TemplateContext, _bullet_list, _section, extract_sections


def _extract_biblical_context(text: str) -> str:
    refs = re.findall(
        r"\b(?:[1-3]\s)?[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)*\s+\d{1,3}(?::\d{1,3}(?:-\d{1,3})?)?",
        text,
    )
    if not refs:
        return "_Contexto bíblico não identificado automaticamente._"
    unique = list(dict.fromkeys(refs))
    return _bullet_list(unique)


def _extract_applications(text: str, *, limit: int = 5) -> list[str]:
    apps: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if any(kw in lower for kw in ("aplic", "prátic", "hoje", "devemos", "precisamos", "exort")):
            cleaned = line.strip()
            if len(cleaned) > 20:
                apps.append(cleaned)
        if len(apps) >= limit:
            break
    return apps


def render_sermon(ctx: TemplateContext) -> str:
    sections = extract_sections(ctx)
    applications = _extract_applications(ctx.content)
    parts = [
        _section("Resumo", str(sections["summary"])),
        _section("Estrutura da Mensagem", _bullet_list(sections["main_points"])),  # type: ignore[arg-type]
        _section("Contexto Bíblico", _extract_biblical_context(ctx.content)),
        _section("Conteúdo Estruturado", str(sections["structured_body"])),
        _section("Aplicações", _bullet_list(applications)),
        _section("Frases Marcantes", _bullet_list(sections["quotes"])),  # type: ignore[arg-type]
        _section("Referências Bíblicas", _bullet_list(sections["references"])),  # type: ignore[arg-type]
        _section("Tags", _bullet_list(sections["tags"])),  # type: ignore[arg-type]
    ]
    return "\n".join(parts).strip()
