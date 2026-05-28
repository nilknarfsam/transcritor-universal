"""Template genérico — estrutura padrão AI-ready."""

from __future__ import annotations

from src.ai_ready.templates.base import TemplateContext, _bullet_list, _section, extract_sections


def render_generic(ctx: TemplateContext) -> str:
    sections = extract_sections(ctx)
    parts = [
        _section("Resumo", str(sections["summary"])),
        _section("Conteúdo Estruturado", str(sections["structured_body"])),
        _section("Pontos Principais", _bullet_list(sections["main_points"])),  # type: ignore[arg-type]
        _section("Frases Marcantes", _bullet_list(sections["quotes"])),  # type: ignore[arg-type]
        _section("Referências", _bullet_list(sections["references"])),  # type: ignore[arg-type]
        _section("Tags", _bullet_list(sections["tags"])),  # type: ignore[arg-type]
    ]
    return "\n".join(parts).strip()
