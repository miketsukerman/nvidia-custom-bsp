"""SHA256 helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Compute a file SHA256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> None:
    """Raise ValueError when a file hash does not match."""

    actual = sha256_file(path)
    if actual != expected.lower():
        raise ValueError(f"SHA256 mismatch for {path}: expected {expected.lower()}, got {actual}")
