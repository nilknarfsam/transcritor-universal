"""Captura de progresso do tqdm (Whisper) via redirecionamento de ``sys.stderr``."""

from __future__ import annotations

import re
import sys
from contextlib import contextmanager
from typing import Callable, Iterator, TextIO

_TQDM_PERCENT = re.compile(r"(\d+(?:\.\d+)?)%\|")


class TqdmStderrCapture:
    """Proxy de ``stderr`` que repassa a saída e extrai a porcentagem do tqdm."""

    def __init__(
        self,
        stream: TextIO,
        on_fraction: Callable[[float], None],
        *,
        min_delta: float = 0.01,
    ) -> None:
        self._stream = stream
        self._on_fraction = on_fraction
        self._min_delta = min_delta
        self._last = -1.0

    def write(self, data: str) -> int:
        if not data:
            return 0
        self._stream.write(data)
        match = _TQDM_PERCENT.search(data)
        if match:
            fraction = max(0.0, min(1.0, float(match.group(1)) / 100.0))
            if fraction - self._last >= self._min_delta or fraction >= 1.0:
                self._last = fraction
                self._on_fraction(fraction)
        return len(data)

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str):
        return getattr(self._stream, name)


@contextmanager
def capture_tqdm_progress(
    on_fraction: Callable[[float], None],
    *,
    min_delta: float = 0.01,
) -> Iterator[None]:
    """Substitui ``sys.stderr`` durante a transcrição; restaura no ``finally``."""
    original = sys.stderr
    sys.stderr = TqdmStderrCapture(original, on_fraction, min_delta=min_delta)  # type: ignore[assignment]
    try:
        yield
    finally:
        sys.stderr = original
