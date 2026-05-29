"""Revisões estruturadas — preparação para repetição espaçada futura."""

from __future__ import annotations


class RevisionBuilder:
    def build_revision_plan(
        self,
        *,
        title: str,
        difficulty: str,
        flashcards_count: int,
        quizzes_count: int,
    ) -> str:
        cycles = "3 dias → 7 dias → 14 dias" if difficulty == "avançado" else "1 dia → 3 dias → 7 dias"
        return (
            f"## Plano de Revisão — {title or 'Material'}\n\n"
            f"- **Dificuldade:** {difficulty}\n"
            f"- **Flashcards:** {flashcards_count}\n"
            f"- **Quiz:** {quizzes_count} questões\n"
            f"- **Ciclos sugeridos:** {cycles}\n"
        )
