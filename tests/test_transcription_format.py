"""Testes de formatação de segmentos Whisper e captura de progresso tqdm."""

from __future__ import annotations

import io
import sys
import unittest

from src.core.transcription_service import (
    format_segments_to_text,
    format_timestamp_mmss,
    map_whisper_fraction_to_job,
)
from src.core.whisper_progress import TqdmStderrCapture, capture_tqdm_progress


class TestTranscriptionFormatting(unittest.TestCase):
    def test_format_timestamp_mmss(self) -> None:
        self.assertEqual(format_timestamp_mmss(0), "00:00")
        self.assertEqual(format_timestamp_mmss(45), "00:45")
        self.assertEqual(format_timestamp_mmss(125), "02:05")

    def test_format_segments_groups_by_block(self) -> None:
        segments = [
            {"start": 0.0, "text": " Olá, meus queridos alunos."},
            {"start": 12.0, "text": " Hoje falaremos de teologia."},
            {"start": 45.0, "text": " A teologia descobre fatos."},
            {"start": 70.0, "text": " Segundo bloco aqui."},
        ]
        text = format_segments_to_text(segments, block_seconds=60)
        self.assertIn("**[00:00]** Olá, meus queridos alunos. Hoje falaremos de teologia.", text)
        self.assertIn("**[00:45]** A teologia descobre fatos.", text)
        self.assertIn("**[01:10]** Segundo bloco aqui.", text)
        self.assertEqual(text.count("\n\n"), 2)

    def test_format_segments_empty(self) -> None:
        self.assertEqual(format_segments_to_text([]), "")

    def test_map_whisper_fraction_to_job(self) -> None:
        self.assertAlmostEqual(map_whisper_fraction_to_job(0.0), 0.05)
        self.assertAlmostEqual(map_whisper_fraction_to_job(1.0), 0.90)
        self.assertAlmostEqual(map_whisper_fraction_to_job(0.5), 0.475)


class TestTqdmCapture(unittest.TestCase):
    def test_stderr_capture_parses_percent(self) -> None:
        captured: list[float] = []
        buffer = io.StringIO()
        proxy = TqdmStderrCapture(buffer, captured.append, min_delta=0.0)
        proxy.write(" 15%|████          | 1/6 [00:01<00:05,  1.00it/s]\r")
        proxy.write("100%|██████████████| 6/6 [00:05<00:00,  1.20it/s]\n")
        self.assertEqual(captured[0], 0.15)
        self.assertEqual(captured[-1], 1.0)

    def test_capture_restores_stderr(self) -> None:
        original = sys.stderr
        seen: list[float] = []

        with capture_tqdm_progress(seen.append, min_delta=0.0):
            self.assertIsNot(sys.stderr, original)
            sys.stderr.write(" 50%|█████     | 3/6 [00:02<00:02,  1.50it/s]\r")

        self.assertIs(sys.stderr, original)
        self.assertEqual(seen, [0.5])


if __name__ == "__main__":
    unittest.main()
