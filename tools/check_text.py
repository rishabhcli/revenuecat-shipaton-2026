#!/usr/bin/env python3
"""Check repository text hygiene and high-signal secret patterns."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_PARTS = {".build", ".dev", ".git", "node_modules"}
BINARY_SUFFIXES = {
    ".gif",
    ".heic",
    ".ico",
    ".jpg",
    ".jpeg",
    ".metallib",
    ".mov",
    ".mp4",
    ".pdf",
    ".png",
    ".xcassets",
    ".zip",
}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{30,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "stripe-live-key": re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"),
    "revenuecat-secret": re.compile(r"\bsk_[A-Za-z0-9]{24,}\b"),
}
# The imported Devpost dossier intentionally preserves irregular whitespace from the
# captured external form. Normalizing thousands of untouched lines would create an
# unrelated diff and weaken provenance; newly authored files remain strict.
LEGACY_WHITESPACE_FILES = {Path("HACKATHON.md")}


def candidate_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    paths: list[Path] = []
    for relative in completed.stdout.splitlines():
        path = ROOT / relative
        if not path.is_file() or EXCLUDED_PARTS.intersection(path.parts):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        paths.append(path)
    return sorted(paths)


def main() -> int:
    failures: list[str] = []
    for path in candidate_files():
        relative = path.relative_to(ROOT)
        payload = path.read_bytes()
        if b"\x00" in payload:
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            failures.append(f"{relative}: is not valid UTF-8")
            continue
        if text and not text.endswith("\n"):
            failures.append(f"{relative}: missing final newline")
        if "\r" in text:
            failures.append(f"{relative}: contains CR/CRLF line endings")
        if relative not in LEGACY_WHITESPACE_FILES:
            for number, line in enumerate(text.splitlines(), start=1):
                if line.rstrip(" \t") != line:
                    failures.append(f"{relative}:{number}: trailing whitespace")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{relative}: contains possible {label}")

    if failures:
        print("text-check:error", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"text-check:ok files={len(candidate_files())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
