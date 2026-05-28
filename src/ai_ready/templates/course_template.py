"""Template para aulas e cursos."""

from __future__ import annotations

from src.ai_ready.templates.base import TemplateContext, _bullet_list, _section, extract_sections


def _extract_reflections(text: str, *, limit: int = 5) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if any(kw in lower for kw in ("exerc", "reflex", "pergunta", "atividade", "desafio", "tarefa")):
            cleaned = line.strip()
            if len(cleaned) > 15:
                items.append(cleaned)
        if len(items) >= limit:
            break
    if not items:
        items = [p for p in text.split("\n\n") if "?" in p][:limit]
    return items


def render_course(ctx: TemplateContext) -> str:
    sections = extract_sections(ctx)
    reflections = _extract_reflections(ctx.content)
    parts = [
        _section("Resumo", str(sections["summary"])),
        _section("Conteúdo Estruturado", str(sections["structured_body"])),
        _section("Pontos Principais", _bullet_list(sections["main_points"])),  # type: ignore[arg-type]
        _section("Exercícios e Reflexões", _bullet_list(reflections)),
        _section("Frases Marcantes", _bullet_list(sections["quotes"])),  # type: ignore[arg-type]
        _section("Referências", _bullet_list(sections["references"])),  # type: ignore[arg-type]
        _section("Tags", _bullet_list(sections["tags"])),  # type: ignore[arg-type]
    ]
    return "\n".join(parts).strip()
