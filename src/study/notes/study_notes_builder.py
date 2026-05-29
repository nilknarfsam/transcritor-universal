"""Notas de estudo — aplicações, reflexões e perguntas."""

from __future__ import annotations


class StudyNotesBuilder:
    def build(
        self,
        *,
        title: str,
        topics: list[str],
        applications: list[str],
        reflections: list[str],
        review_questions: list[str],
        key_points: list[str],
    ) -> str:
        lines = [
            f"# Notas de Estudo — {title or 'Conteúdo'}",
            "",
        ]

        if key_points:
            lines.extend(["## Pontos importantes", ""])
            for p in key_points:
                lines.append(f"- {p}")
            lines.append("")

        lines.extend(["# Aplicações Práticas", ""])
        if applications:
            for a in applications:
                lines.append(f"- {a}")
        else:
            lines.append("- Como aplicar os conceitos no dia a dia?")
            lines.append("- Qual mudança prática este conteúdo sugere?")
        lines.append("")

        lines.extend(["# Reflexões", ""])
        if reflections:
            for r in reflections:
                lines.append(f"- {r}")
        else:
            for t in topics[:4]:
                lines.append(f"- O que «{t}» significa para mim neste contexto?")
        lines.append("")

        lines.extend(["# Perguntas para Revisão", ""])
        if review_questions:
            for q in review_questions:
                lines.append(f"- {q}")
        else:
            for t in topics[:5]:
                lines.append(f"- Explique «{t}» sem consultar o material.")
        lines.append("")

        return "\n".join(lines)

    def build_applications(self, topics: list[str], template: str = "generic") -> list[str]:
        apps: list[str] = []
        for t in topics[:6]:
            if template == "sermon":
                apps.append(f"Aplicar o ensino sobre «{t}» na vida comunitária e pessoal.")
            elif template == "course":
                apps.append(f"Exercício: elaborar um exemplo real sobre «{t}».")
            elif template == "podcast":
                apps.append(f"Discutir em grupo os pontos relacionados a «{t}».")
            else:
                apps.append(f"Identificar uma situação atual onde «{t}» se aplica.")
        if not apps:
            apps.append("Registrar uma ação concreta nas próximas 24 horas com base no conteúdo.")
        return apps

    def build_reflections(self, topics: list[str], highlights: list[str]) -> list[str]:
        refs: list[str] = []
        for h in highlights[:3]:
            refs.append(f"Por que esta frase é relevante? «{h[:80]}…»" if len(h) > 80 else f"Por que esta frase é relevante? «{h}»")
        for t in topics[:4]:
            refs.append(f"Que dúvidas ainda tenho sobre «{t}»?")
        return refs

    def build_review_questions(
        self,
        topics: list[str],
        *,
        flashcard_count: int = 0,
        quiz_count: int = 0,
    ) -> list[str]:
        qs: list[str] = []
        for t in topics[:6]:
            qs.append(f"Defina e exemplifique: {t}.")
        if flashcard_count:
            qs.append(f"Revise os {flashcard_count} flashcards gerados.")
        if quiz_count:
            qs.append(f"Responda o quiz de {quiz_count} questões sem consultar as notas.")
        return qs
