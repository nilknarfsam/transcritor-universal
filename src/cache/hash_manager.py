"""SHA256 fingerprint para identificação de arquivos processados."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class FileFingerprint:
    sha256: str
    size_bytes: int
    file_name: str


def file_fingerprint(path: str) -> FileFingerprint:
    """Calcula SHA256 e metadados básicos do arquivo."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while True:
            block = f.read(CHUNK_SIZE)
            if not block:
                break
            digest.update(block)
            size += len(block)
    return FileFingerprint(
        sha256=digest.hexdigest(),
        size_bytes=size,
        file_name=os.path.basename(path),
    )
