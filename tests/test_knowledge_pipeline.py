"""Testes da feature flag ``features.knowledge_pipeline``."""

from __future__ import annotations

import unittest

from src.core.settings_service import (
    DEFAULT_FEATURES,
    DEFAULT_SETTINGS,
    EXPORT_MODES_REQUIRING_KNOWLEDGE,
    SettingsService,
)


def _settings_service(*, knowledge_pipeline: bool, export_mode: str = "raw") -> SettingsService:
    """Instância isolada sem I/O de disco."""
    service = SettingsService.__new__(SettingsService)
    service._history = []
    service._settings = dict(DEFAULT_SETTINGS)
    service._settings["features"] = dict(DEFAULT_FEATURES)
    service._settings["features"]["knowledge_pipeline"] = knowledge_pipeline
    service._settings["export_mode"] = export_mode
    return service


class TestShouldRunKnowledgePipeline(unittest.TestCase):
    """Valida ``SettingsService.should_run_knowledge_pipeline``."""

    def test_flag_off_raw_and_clean_do_not_run(self) -> None:
        for mode in ("raw", "clean"):
            with self.subTest(mode=mode):
                service = _settings_service(knowledge_pipeline=False, export_mode=mode)
                self.assertFalse(service.should_run_knowledge_pipeline(mode))
                self.assertFalse(service.should_run_knowledge_pipeline())

    def test_flag_off_advanced_modes_run_temporarily(self) -> None:
        for mode in sorted(EXPORT_MODES_REQUIRING_KNOWLEDGE):
            with self.subTest(mode=mode):
                service = _settings_service(knowledge_pipeline=False, export_mode=mode)
                self.assertTrue(service.should_run_knowledge_pipeline(mode))
                self.assertTrue(service.knowledge_pipeline_auto_enabled(mode))

    def test_flag_on_all_modes_run(self) -> None:
        modes = ("raw", "clean", "ai_ready", "notebooklm", "study_mode")
        for mode in modes:
            with self.subTest(mode=mode):
                service = _settings_service(knowledge_pipeline=True, export_mode=mode)
                self.assertTrue(service.should_run_knowledge_pipeline(mode))
                self.assertFalse(service.knowledge_pipeline_auto_enabled(mode))

    def test_export_mode_needs_knowledge_pipeline(self) -> None:
        service = _settings_service(knowledge_pipeline=False)
        self.assertFalse(service.export_mode_needs_knowledge_pipeline("raw"))
        self.assertFalse(service.export_mode_needs_knowledge_pipeline("clean"))
        for mode in EXPORT_MODES_REQUIRING_KNOWLEDGE:
            with self.subTest(mode=mode):
                self.assertTrue(service.export_mode_needs_knowledge_pipeline(mode))

    def test_default_export_mode_used_when_argument_omitted(self) -> None:
        service = _settings_service(knowledge_pipeline=False, export_mode="notebooklm")
        self.assertTrue(service.should_run_knowledge_pipeline())
        service = _settings_service(knowledge_pipeline=False, export_mode="raw")
        self.assertFalse(service.should_run_knowledge_pipeline())

    def test_knowledge_pipeline_property_persists_in_memory(self) -> None:
        service = _settings_service(knowledge_pipeline=False)
        self.assertFalse(service.knowledge_pipeline)
        service.knowledge_pipeline = True
        self.assertTrue(service._settings["features"]["knowledge_pipeline"])
        self.assertTrue(service.should_run_knowledge_pipeline("raw"))


if __name__ == "__main__":
    unittest.main()
