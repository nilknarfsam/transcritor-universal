from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "historico_transcricoes.json"
LEGACY_HISTORY_FILE = PROJECT_ROOT / "historico_transcricoes.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "System",
    "language": "auto",
    "output_folder": "",
    "default_export_format": "txt",
    "export_mode": "raw",
    "content_template": "generic",
    "whisper_model": "base",
    "max_history": 10,
    "workspace_id": "ws-default",
    "collection_id": "",
    "collection_name": "",
    "library_author": "",
    "library_speaker": "",
    "library_category": "",
    "library_tags": "",
    "knowledge_type": "document",
    "ui_last_tab": "Pipeline",
    "ui_last_search_query": "",
    "ui_search_filter_workspace": "(todos)",
    "ui_search_filter_collection": "(todas)",
    "ui_search_filter_node_type": "(todos)",
    "ui_search_filter_template": "(todos)",
    "ui_search_filter_export_mode": "(todos)",
    "ui_search_filter_difficulty": "(todos)",
}


class SettingsService:
    def __init__(self) -> None:
        self._settings = dict(DEFAULT_SETTINGS)
        self._history: list[dict[str, str]] = []
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_history()
        self.load()

    def _migrate_legacy_history(self) -> None:
        if LEGACY_HISTORY_FILE.exists() and not HISTORY_FILE.exists():
            shutil.copy2(LEGACY_HISTORY_FILE, HISTORY_FILE)

    def load(self) -> None:
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    loaded = json.load(f)
                self._settings.update({k: loaded[k] for k in DEFAULT_SETTINGS if k in loaded})
            except (json.JSONDecodeError, OSError):
                pass
        self._history = self._load_history_file()

    def save_settings(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, ensure_ascii=False, indent=2)

    def _load_history_file(self) -> list[dict[str, str]]:
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def save_history(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._history, f, ensure_ascii=False, indent=2)

    @property
    def theme(self) -> str:
        return str(self._settings["theme"])

    @theme.setter
    def theme(self, value: str) -> None:
        self._settings["theme"] = value
        self.save_settings()

    @property
    def language(self) -> str:
        return str(self._settings["language"])

    @language.setter
    def language(self, value: str) -> None:
        self._settings["language"] = value
        self.save_settings()

    @property
    def output_folder(self) -> str:
        return str(self._settings["output_folder"])

    @output_folder.setter
    def output_folder(self, value: str) -> None:
        self._settings["output_folder"] = value
        self.save_settings()

    @property
    def default_export_format(self) -> str:
        return str(self._settings["default_export_format"])

    @default_export_format.setter
    def default_export_format(self, value: str) -> None:
        self._settings["default_export_format"] = value
        self.save_settings()

    @property
    def export_mode(self) -> str:
        return str(self._settings.get("export_mode", "raw"))

    @export_mode.setter
    def export_mode(self, value: str) -> None:
        self._settings["export_mode"] = value
        self.save_settings()

    @property
    def content_template(self) -> str:
        return str(self._settings.get("content_template", "generic"))

    @content_template.setter
    def content_template(self, value: str) -> None:
        self._settings["content_template"] = value
        self.save_settings()

    @property
    def whisper_model(self) -> str:
        return str(self._settings["whisper_model"])

    @whisper_model.setter
    def whisper_model(self, value: str) -> None:
        self._settings["whisper_model"] = value
        self.save_settings()

    @property
    def max_history(self) -> int:
        return int(self._settings["max_history"])

    @property
    def workspace_id(self) -> str:
        return str(self._settings.get("workspace_id", "ws-default"))

    @workspace_id.setter
    def workspace_id(self, value: str) -> None:
        self._settings["workspace_id"] = value
        self.save_settings()

    @property
    def collection_id(self) -> str:
        return str(self._settings.get("collection_id", ""))

    @collection_id.setter
    def collection_id(self, value: str) -> None:
        self._settings["collection_id"] = value
        self.save_settings()

    @property
    def collection_name(self) -> str:
        return str(self._settings.get("collection_name", ""))

    @collection_name.setter
    def collection_name(self, value: str) -> None:
        self._settings["collection_name"] = value
        self.save_settings()

    @property
    def library_author(self) -> str:
        return str(self._settings.get("library_author", ""))

    @library_author.setter
    def library_author(self, value: str) -> None:
        self._settings["library_author"] = value
        self.save_settings()

    @property
    def library_speaker(self) -> str:
        return str(self._settings.get("library_speaker", ""))

    @library_speaker.setter
    def library_speaker(self, value: str) -> None:
        self._settings["library_speaker"] = value
        self.save_settings()

    @property
    def library_category(self) -> str:
        return str(self._settings.get("library_category", ""))

    @library_category.setter
    def library_category(self, value: str) -> None:
        self._settings["library_category"] = value
        self.save_settings()

    @property
    def library_tags(self) -> str:
        return str(self._settings.get("library_tags", ""))

    @library_tags.setter
    def library_tags(self, value: str) -> None:
        self._settings["library_tags"] = value
        self.save_settings()

    @property
    def knowledge_type(self) -> str:
        return str(self._settings.get("knowledge_type", "document"))

    @knowledge_type.setter
    def knowledge_type(self, value: str) -> None:
        self._settings["knowledge_type"] = value
        self.save_settings()

    @property
    def ui_last_tab(self) -> str:
        return str(self._settings.get("ui_last_tab", "Pipeline"))

    @ui_last_tab.setter
    def ui_last_tab(self, value: str) -> None:
        self._settings["ui_last_tab"] = value
        self.save_settings()

    @property
    def ui_last_search_query(self) -> str:
        return str(self._settings.get("ui_last_search_query", ""))

    @ui_last_search_query.setter
    def ui_last_search_query(self, value: str) -> None:
        self._settings["ui_last_search_query"] = value
        self.save_settings()

    @property
    def ui_search_filter_workspace(self) -> str:
        return str(self._settings.get("ui_search_filter_workspace", "(todos)"))

    @ui_search_filter_workspace.setter
    def ui_search_filter_workspace(self, value: str) -> None:
        self._settings["ui_search_filter_workspace"] = value
        self.save_settings()

    @property
    def ui_search_filter_collection(self) -> str:
        return str(self._settings.get("ui_search_filter_collection", "(todas)"))

    @ui_search_filter_collection.setter
    def ui_search_filter_collection(self, value: str) -> None:
        self._settings["ui_search_filter_collection"] = value
        self.save_settings()

    @property
    def ui_search_filter_node_type(self) -> str:
        return str(self._settings.get("ui_search_filter_node_type", "(todos)"))

    @ui_search_filter_node_type.setter
    def ui_search_filter_node_type(self, value: str) -> None:
        self._settings["ui_search_filter_node_type"] = value
        self.save_settings()

    @property
    def ui_search_filter_template(self) -> str:
        return str(self._settings.get("ui_search_filter_template", "(todos)"))

    @ui_search_filter_template.setter
    def ui_search_filter_template(self, value: str) -> None:
        self._settings["ui_search_filter_template"] = value
        self.save_settings()

    @property
    def ui_search_filter_export_mode(self) -> str:
        return str(self._settings.get("ui_search_filter_export_mode", "(todos)"))

    @ui_search_filter_export_mode.setter
    def ui_search_filter_export_mode(self, value: str) -> None:
        self._settings["ui_search_filter_export_mode"] = value
        self.save_settings()

    @property
    def ui_search_filter_difficulty(self) -> str:
        return str(self._settings.get("ui_search_filter_difficulty", "(todos)"))

    @ui_search_filter_difficulty.setter
    def ui_search_filter_difficulty(self, value: str) -> None:
        self._settings["ui_search_filter_difficulty"] = value
        self.save_settings()

    def parse_library_tags(self) -> list[str]:
        raw = self.library_tags.replace(";", ",")
        return [t.strip() for t in raw.split(",") if t.strip()]

    def library_context_for_export(
        self,
        *,
        workspace_name: str = "",
        collection_name: str = "",
        semantic_score: float = 0.0,
        chunk_count: int = 0,
        topics: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "workspace": workspace_name,
            "collection": collection_name,
            "category": self.library_category,
            "knowledge_type": self.knowledge_type,
            "speaker": self.library_speaker,
            "author": self.library_author,
            "tags": self.parse_library_tags(),
            "semantic_score": semantic_score,
            "chunk_count": chunk_count,
            "topics": topics,
        }

    @property
    def history(self) -> list[dict[str, str]]:
        return list(self._history)

    def add_history_entry(
        self,
        file_name: str,
        file_type: str,
        *,
        status: str = "concluído",
        message: str = "",
        output_path: str = "",
        export_mode: str = "",
        template_usado: str = "",
        pipeline_stage: str = "",
        tipo_documento: str = "",
        referencias: str = "",
        highlights: str = "",
        chunks: str = "",
        topicos: str = "",
        cache_hit: str = "",
        recovery_used: str = "",
        restored_queue: str = "",
        processing_time: str = "",
        reused_pipeline: str = "",
        tempo_whisper: str = "",
        tempo_ocr: str = "",
        tempo_semantic: str = "",
        workspace: str = "",
        collection: str = "",
        catalog_id: str = "",
        semantic_relationships: str = "",
        flashcards_count: str = "",
        quizzes_count: str = "",
        study_mode: str = "",
        difficulty: str = "",
        study_exports: str = "",
        graph_node_id: str = "",
        related_documents_count: str = "",
        semantic_search_hits: str = "",
        graph_updated_at: str = "",
        knowledge_readiness_score: str = "",
        dataset_id: str = "",
    ) -> None:
        entry: dict[str, str] = {
            "arquivo": file_name,
            "tipo": file_type,
            "status": status,
        }
        if message:
            entry["mensagem"] = message
        if output_path:
            entry["saida"] = output_path
        if export_mode:
            entry["export_mode"] = export_mode
        if template_usado:
            entry["template_usado"] = template_usado
        if pipeline_stage:
            entry["pipeline_stage"] = pipeline_stage
        if tipo_documento:
            entry["tipo_documento"] = tipo_documento
        if referencias:
            entry["referencias"] = referencias
        if highlights:
            entry["highlights"] = highlights
        if chunks:
            entry["chunks"] = chunks
        if topicos:
            entry["topicos"] = topicos
        if cache_hit:
            entry["cache_hit"] = cache_hit
        if recovery_used:
            entry["recovery_used"] = recovery_used
        if restored_queue:
            entry["restored_queue"] = restored_queue
        if processing_time:
            entry["processing_time"] = processing_time
        if reused_pipeline:
            entry["reused_pipeline"] = reused_pipeline
        if tempo_whisper:
            entry["tempo_whisper"] = tempo_whisper
        if tempo_ocr:
            entry["tempo_ocr"] = tempo_ocr
        if tempo_semantic:
            entry["tempo_semantic"] = tempo_semantic
        if workspace:
            entry["workspace"] = workspace
        if collection:
            entry["collection"] = collection
        if catalog_id:
            entry["catalog_id"] = catalog_id
        if semantic_relationships:
            entry["semantic_relationships"] = semantic_relationships
        if flashcards_count:
            entry["flashcards_count"] = flashcards_count
        if quizzes_count:
            entry["quizzes_count"] = quizzes_count
        if study_mode:
            entry["study_mode"] = study_mode
        if difficulty:
            entry["difficulty"] = difficulty
        if study_exports:
            entry["study_exports"] = study_exports
        if graph_node_id:
            entry["graph_node_id"] = graph_node_id
        if related_documents_count:
            entry["related_documents_count"] = related_documents_count
        if semantic_search_hits:
            entry["semantic_search_hits"] = semantic_search_hits
        if graph_updated_at:
            entry["graph_updated_at"] = graph_updated_at
        if knowledge_readiness_score:
            entry["knowledge_readiness_score"] = knowledge_readiness_score
        if dataset_id:
            entry["dataset_id"] = dataset_id
        self._history.append(entry)
        max_items = self.max_history
        if len(self._history) > max_items:
            self._history = self._history[-max_items:]
        self.save_history()

    def add_partial_queue_history(
        self,
        completed: int,
        errors: int,
        cancelled: int,
        total: int,
        *,
        reason: str = "cancelada",
        recovery_used: bool = False,
        restored_queue: bool = False,
    ) -> None:
        self.add_history_entry(
            f"Fila ({completed}/{total})",
            "sessão",
            status="parcial",
            message=(
                f"Fila {reason}: {completed} concluído(s), "
                f"{errors} erro(s), {cancelled} não processado(s)."
            ),
            recovery_used="sim" if recovery_used else "",
            restored_queue="sim" if restored_queue else "",
        )

    def resolve_output_dir(self, source_path: str) -> str:
        folder = self.output_folder.strip()
        if folder and os.path.isdir(folder):
            return folder
        return os.path.dirname(os.path.abspath(source_path))
