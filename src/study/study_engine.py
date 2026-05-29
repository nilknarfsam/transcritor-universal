"""Orquestrador Study Intelligence — flashcards, quizzes, resumos e notas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.study.difficulty.difficulty_classifier import classify_difficulty
from src.study.flashcards.flashcard_generator import FlashcardGenerator
from src.study.notes.study_notes_builder import StudyNotesBuilder
from src.study.quizzes.quiz_generator import QuizGenerator
from src.study.revisions.revision_builder import RevisionBuilder
from src.study.summaries.study_summary_builder import StudySummaryBuilder


@dataclass
class StudyResult:
    difficulty: str = "básico"
    flashcards: list[dict[str, str]] = field(default_factory=list)
    quizzes: list[dict[str, Any]] = field(default_factory=list)
    quick_review_md: str = ""
    study_notes_md: str = ""
    markdown_sections: str = ""
    concepts: list[str] = field(default_factory=list)
    applications: list[str] = field(default_factory=list)
    reflections: list[str] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)
    revision_plan_md: str = ""
    flashcards_count: int = 0
    quizzes_count: int = 0
    study_ready: bool = False

    def to_metadata(self) -> dict[str, Any]:
        return {
            "difficulty": self.difficulty,
            "flashcards_count": self.flashcards_count,
            "quizzes_count": self.quizzes_count,
            "study_ready": self.study_ready,
            "study_mode": True,
            "concepts": self.concepts[:10],
        }

    def to_package(self) -> dict[str, Any]:
        return {
            "difficulty": self.difficulty,
            "flashcards": self.flashcards,
            "quizzes": self.quizzes,
            "quick_review_md": self.quick_review_md,
            "study_notes_md": self.study_notes_md,
            "markdown_sections": self.markdown_sections,
            "concepts": self.concepts,
            "applications": self.applications,
            "reflections": self.reflections,
            "review_questions": self.review_questions,
            "revision_plan_md": self.revision_plan_md,
            "flashcards_count": self.flashcards_count,
            "quizzes_count": self.quizzes_count,
            "study_ready": self.study_ready,
        }

    @classmethod
    def from_package(cls, data: dict[str, Any]) -> "StudyResult":
        return cls(
            difficulty=str(data.get("difficulty", "básico")),
            flashcards=list(data.get("flashcards") or []),
            quizzes=list(data.get("quizzes") or []),
            quick_review_md=str(data.get("quick_review_md", "")),
            study_notes_md=str(data.get("study_notes_md", "")),
            markdown_sections=str(data.get("markdown_sections", "")),
            concepts=list(data.get("concepts") or []),
            applications=list(data.get("applications") or []),
            reflections=list(data.get("reflections") or []),
            review_questions=list(data.get("review_questions") or []),
            revision_plan_md=str(data.get("revision_plan_md", "")),
            flashcards_count=int(data.get("flashcards_count", 0)),
            quizzes_count=int(data.get("quizzes_count", 0)),
            study_ready=bool(data.get("study_ready")),
        )

    def to_history_fields(self) -> dict[str, str]:
        return {
            "flashcards_count": str(self.flashcards_count),
            "quizzes_count": str(self.quizzes_count),
            "study_mode": "sim",
            "difficulty": self.difficulty,
        }


class StudyEngine:
    def __init__(self) -> None:
        self._flashcards = FlashcardGenerator()
        self._quizzes = QuizGenerator()
        self._summary = StudySummaryBuilder()
        self._notes = StudyNotesBuilder()
        self._revision = RevisionBuilder()

    def build(
        self,
        text: str,
        *,
        title: str = "",
        content_template: str = "generic",
        semantic_metadata: dict[str, Any] | None = None,
        chunks: list[dict[str, Any]] | None = None,
        highlights: list[str] | None = None,
        topics: list[str] | None = None,
        references: list[Any] | None = None,
    ) -> StudyResult:
        meta = semantic_metadata or {}
        chunk_list = list(chunks or meta.get("chunks") or [])
        hi_list = list(highlights or [])
        if not hi_list and isinstance(meta.get("highlights"), list):
            hi_list = meta["highlights"]
        topic_list = list(topics or meta.get("topics") or [])
        ref_list = list(references or meta.get("bible_references") or [])

        ref_count = int(meta.get("reference_count", 0) or len(ref_list))
        chunk_count = int(meta.get("chunk_count", 0) or len(chunk_list))

        difficulty = classify_difficulty(
            text,
            topics=topic_list,
            reference_count=ref_count,
            chunk_count=chunk_count,
        )

        flashcards = self._flashcards.generate(
            chunks=chunk_list,
            highlights=hi_list,
            topics=topic_list,
            references=ref_list,
            difficulty=difficulty,
        )
        quizzes = self._quizzes.generate(
            chunks=chunk_list,
            highlights=hi_list,
            topics=topic_list,
            difficulty=difficulty,
        )

        concepts = self._summary.extract_concepts(
            topics=topic_list, chunks=chunk_list, highlights=hi_list
        )
        key_points = self._summary.key_points(hi_list, chunk_list)
        applications = self._notes.build_applications(topic_list, content_template)
        reflections = self._notes.build_reflections(topic_list, hi_list)
        review_questions = self._notes.build_review_questions(
            topic_list,
            flashcard_count=len(flashcards),
            quiz_count=len(quizzes),
        )

        quick_review = self._summary.build_quick_review(
            title=title,
            topics=topic_list,
            highlights=hi_list,
            concepts=concepts,
            difficulty=difficulty,
        )
        study_notes = self._notes.build(
            title=title,
            topics=topic_list,
            applications=applications,
            reflections=reflections,
            review_questions=review_questions,
            key_points=key_points,
        )
        revision_plan = self._revision.build_revision_plan(
            title=title,
            difficulty=difficulty,
            flashcards_count=len(flashcards),
            quizzes_count=len(quizzes),
        )

        sections = self._build_markdown_sections(
            quick_review=quick_review,
            concepts=concepts,
            review_questions=review_questions,
            applications=applications,
            reflections=reflections,
            flashcards_count=len(flashcards),
            quizzes_count=len(quizzes),
            difficulty=difficulty,
        )

        return StudyResult(
            difficulty=difficulty,
            flashcards=flashcards,
            quizzes=quizzes,
            quick_review_md=quick_review,
            study_notes_md=study_notes,
            markdown_sections=sections,
            concepts=concepts,
            applications=applications,
            reflections=reflections,
            review_questions=review_questions,
            revision_plan_md=revision_plan,
            flashcards_count=len(flashcards),
            quizzes_count=len(quizzes),
            study_ready=bool(flashcards or quizzes or concepts),
        )

    @staticmethod
    def _build_markdown_sections(
        *,
        quick_review: str,
        concepts: list[str],
        review_questions: list[str],
        applications: list[str],
        reflections: list[str],
        flashcards_count: int,
        quizzes_count: int,
        difficulty: str,
    ) -> str:
        lines = [
            "---",
            "",
            quick_review,
            "",
            "## Conceitos Principais",
            "",
        ]
        for c in concepts[:12]:
            lines.append(f"- {c}")
        lines.extend([
            "",
            "## Perguntas para Revisão",
            "",
        ])
        for q in review_questions[:10]:
            lines.append(f"- {q}")
        lines.extend([
            "",
            "# Aplicações Práticas",
            "",
        ])
        for a in applications[:8]:
            lines.append(f"- {a}")
        lines.extend([
            "",
            "# Reflexões",
            "",
        ])
        for r in reflections[:8]:
            lines.append(f"- {r}")
        lines.extend([
            "",
            f"*Study Intelligence · {flashcards_count} flashcards · "
            f"{quizzes_count} quiz · dificuldade: {difficulty}*",
            "",
        ])
        return "\n".join(lines)
