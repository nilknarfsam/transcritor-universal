"""Exportações educacionais — sidecars junto ao markdown principal."""

from __future__ import annotations

import json
import os
from typing import Any

from src.study.study_engine import StudyResult


class StudyExporter:
    @staticmethod
    def base_paths(output_path: str) -> tuple[str, str]:
        folder = os.path.dirname(os.path.abspath(output_path))
        base = os.path.splitext(os.path.basename(output_path))[0]
        return folder, base

    @classmethod
    def write_exports(cls, output_path: str, study: StudyResult) -> dict[str, str]:
        """Salva flashcards.json, quizzes.json, study_notes.md, quick_review.md."""
        if not output_path:
            return {}
        folder, base = cls.base_paths(output_path)
        os.makedirs(folder, exist_ok=True)

        paths: dict[str, str] = {}
        fc_path = os.path.join(folder, f"{base}_flashcards.json")
        with open(fc_path, "w", encoding="utf-8") as f:
            json.dump({"flashcards": study.flashcards, "count": study.flashcards_count}, f, ensure_ascii=False, indent=2)
        paths["flashcards"] = fc_path

        quiz_path = os.path.join(folder, f"{base}_quizzes.json")
        with open(quiz_path, "w", encoding="utf-8") as f:
            json.dump({"quizzes": study.quizzes, "count": study.quizzes_count}, f, ensure_ascii=False, indent=2)
        paths["quizzes"] = quiz_path

        notes_path = os.path.join(folder, f"{base}_study_notes.md")
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(study.study_notes_md)
        paths["study_notes"] = notes_path

        review_path = os.path.join(folder, f"{base}_quick_review.md")
        with open(review_path, "w", encoding="utf-8") as f:
            f.write(study.quick_review_md)
        paths["quick_review"] = review_path

        return paths

    @staticmethod
    def paths_display(paths: dict[str, str]) -> str:
        return ", ".join(os.path.basename(p) for p in paths.values())
