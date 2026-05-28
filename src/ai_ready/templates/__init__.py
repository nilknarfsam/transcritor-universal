"""Templates semânticos para Markdown AI-ready."""

from src.ai_ready.templates.base import TemplateContext, extract_sections
from src.ai_ready.templates.course_template import render_course
from src.ai_ready.templates.generic_template import render_generic
from src.ai_ready.templates.podcast_template import render_podcast
from src.ai_ready.templates.sermon_template import render_sermon

TEMPLATE_RENDERERS = {
    "generic": render_generic,
    "sermon": render_sermon,
    "podcast": render_podcast,
    "course": render_course,
}

__all__ = [
    "TEMPLATE_RENDERERS",
    "TemplateContext",
    "extract_sections",
    "render_course",
    "render_generic",
    "render_podcast",
    "render_sermon",
]
