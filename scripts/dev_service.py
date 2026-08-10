#!/usr/bin/env python3
"""Loopback-only development services for the repository's exclusive port block.

The services intentionally expose local operational surfaces, not fabricated product
results.  Every readiness document states its scope, and the RevenueCat receiver
never reports that provider delivery has been verified.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import itertools
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import signal
import socketserver
import stat
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any, Final, Mapping
from urllib.parse import parse_qs, urlsplit


REPOSITORY_NAME: Final = "revenuecat-shipaton-2026"
BIND_HOST: Final = "127.0.0.1"
PORT_MIN: Final = 4220
PORT_MAX: Final = 4229
MAX_REQUEST_TARGET_BYTES: Final = 2_048
MAX_WEBHOOK_BYTES: Final = 65_536
MAX_EVALUATION_BYTES: Final = 1_048_576
MAX_LEDGER_BYTES: Final = 8_388_608
MAX_ARTIFACT_FILES: Final = 2_000
MAX_ARTIFACT_ENTRIES: Final = 4_000
MAX_CONCURRENT_REQUESTS: Final = 16
REQUEST_TIMEOUT_SECONDS: Final = 5.0
OVERLOAD_WRITE_TIMEOUT_SECONDS: Final = 0.25
MAX_LOG_BYTES: Final = 1_048_576
LOG_BACKUP_COUNT: Final = 3
MAX_LOG_EVENT_BYTES: Final = 8_192
WEBHOOK_TOKEN_MIN_BYTES: Final = 16
WEBHOOK_TOKEN_MAX_BYTES: Final = 256
TOKEN_RE: Final = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
EVENT_TYPE_RE: Final = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
SHA256_RE: Final = re.compile(r"^[0-9a-f]{64}$")
SAFE_EVIDENCE_PATH_RE: Final = re.compile(r"^[A-Za-z0-9._/-]{1,512}$")
UTC_TIMESTAMP_RE: Final = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$"
)
DEVCTL_TOKEN_HEADER: Final = "X-Devctl-Instance-Token"
SERVICE_LOGGER = logging.getLogger("revenuecat_shipaton_2026.dev_service")
SERVICE_LOGGER.propagate = False


class LoggingUnavailable(RuntimeError):
    """Required repository-local structured logging is unhealthy."""


class JSONBoundaryError(ValueError):
    """JSON contained duplicate object keys or non-standard constants."""


class LoggerHealth:
    """Latch logging failures until an explicit logger reconfiguration."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._healthy = False
        self._failure_code = "logging_not_configured"

    def reset_healthy(self) -> None:
        with self._lock:
            self._healthy = True
            self._failure_code = "none"

    def fail(self, code: str) -> None:
        with self._lock:
            self._healthy = False
            self._failure_code = code

    def snapshot(self) -> tuple[bool, str]:
        with self._lock:
            return self._healthy, self._failure_code


LOGGER_HEALTH = LoggerHealth()


class FailClosedRotatingFileHandler(RotatingFileHandler):
    """Make a structured-log write failure visible to the serving path."""

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802 - logging API
        del record
        raise RuntimeError("structured log write failed") from sys.exc_info()[1]


def utc_now() -> str:
    """Return a timezone-explicit timestamp suitable for structured output."""

    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def strict_json_loads(text: str) -> Any:
    """Decode standards-compliant JSON while refusing ambiguous duplicate keys."""

    def object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        document: dict[str, Any] = {}
        for key, value in pairs:
            if key in document:
                raise JSONBoundaryError("duplicate JSON object key")
            document[key] = value
        return document

    def reject_constant(_value: str) -> None:
        raise JSONBoundaryError("non-standard JSON numeric constant")

    return json.loads(
        text,
        object_pairs_hook=object_from_pairs,
        parse_constant=reject_constant,
    )


def configure_service_logging(log_path: Path, root: Path, service_name: str) -> None:
    """Configure bounded repository-local rotation after validating ownership."""

    expected = root / ".dev" / "logs" / f"{service_name}.log"
    if log_path.expanduser().absolute() != expected.absolute():
        raise ConfigurationError(f"log path must be exactly {expected}")
    if log_path.is_symlink():
        raise ConfigurationError("service log may not be a symlink")
    try:
        parent_stat = log_path.parent.stat()
    except OSError as error:
        raise ConfigurationError("service log directory is unavailable") from error
    if not stat.S_ISDIR(parent_stat.st_mode) or log_path.parent.is_symlink():
        raise ConfigurationError("service log directory must be a real directory")
    allowed_names = {log_path.name} | {
        f"{log_path.name}.{index}" for index in range(1, LOG_BACKUP_COUNT + 1)
    }
    for candidate in log_path.parent.glob(f"{log_path.name}*"):
        if candidate.name not in allowed_names:
            raise ConfigurationError(f"unexpected log retention file {candidate.name}")
        if candidate.is_symlink():
            raise ConfigurationError(f"log retention file {candidate.name} may not be a symlink")
        candidate_stat = candidate.stat()
        if not stat.S_ISREG(candidate_stat.st_mode) or candidate_stat.st_size > MAX_LOG_BYTES:
            raise ConfigurationError(
                f"log retention file {candidate.name} exceeds the {MAX_LOG_BYTES}-byte bound"
            )
    for handler in tuple(SERVICE_LOGGER.handlers):
        handler.close()
        SERVICE_LOGGER.removeHandler(handler)
    handler = FailClosedRotatingFileHandler(
        log_path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
        delay=False,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    SERVICE_LOGGER.addHandler(handler)
    SERVICE_LOGGER.setLevel(logging.INFO)
    LOGGER_HEALTH.reset_healthy()


def emit_log(record: Mapping[str, Any]) -> None:
    """Write one structured event through the bounded rotating handler."""

    try:
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
        if len(encoded.encode("utf-8")) + 1 > MAX_LOG_EVENT_BYTES:
            raise LoggingUnavailable("structured log event exceeds its size bound")
        if not SERVICE_LOGGER.handlers:
            raise LoggingUnavailable("structured logger has no bounded handler")
        SERVICE_LOGGER.info(encoded)
    except Exception as error:
        LOGGER_HEALTH.fail("structured_log_write_failed")
        if isinstance(error, LoggingUnavailable):
            raise
        raise LoggingUnavailable("structured log write failed") from error


def verify_logging(service_name: str) -> None:
    """Actively prove that a bounded audit event can be persisted."""

    healthy, code = LOGGER_HEALTH.snapshot()
    if not healthy:
        raise LoggingUnavailable(code)
    emit_log(
        {
            "timestamp": utc_now(),
            "event": "local_logging_readiness_probe",
            "service": service_name,
        }
    )


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    title: str


SERVICE_SPECS: Final[dict[str, ServiceSpec]] = {
    "evaluation": ServiceSpec("evaluation", "Evaluation dashboard"),
    "revenuecat-webhook": ServiceSpec(
        "revenuecat-webhook", "RevenueCat sandbox webhook receiver"
    ),
    "test-patterns": ServiceSpec("test-patterns", "Original test-pattern server"),
    "artifacts": ServiceSpec("artifacts", "Build and artifact metadata server"),
}


class ConfigurationError(RuntimeError):
    """The service cannot start without violating the local contract."""


class DataValidationError(RuntimeError):
    """A local data source is present but does not satisfy its declared schema."""


class WebhookValidationError(ValueError):
    """A webhook body is syntactically valid JSON but violates the receiver schema."""


class WebhookIdentityConflict(WebhookValidationError):
    """An event ID was retried with a different validated payload identity."""


class LedgerPersistenceUncertain(OSError):
    """A ledger write reached an outcome that must be reconciled on retry."""


def _safe_relative_path(value: Any, field: str, required_prefix: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise DataValidationError(f"{field} must be a non-empty string of at most 512 chars")
    text = value
    if SAFE_EVIDENCE_PATH_RE.fullmatch(text) is None:
        raise DataValidationError(f"{field} contains unsupported path characters")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != text:
        raise DataValidationError(f"{field} must be a normalized repository-relative path")
    if not text.startswith(required_prefix):
        raise DataValidationError(f"{field} must be under {required_prefix}")
    return text


def _regular_file_bytes_at(root: Path, relative_path: str, maximum_bytes: int) -> bytes:
    """Read a relative regular file without following any path-component symlink."""

    components = PurePosixPath(relative_path).parts
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
    try:
        root_descriptor = os.open(root, directory_flags)
    except OSError as error:
        raise DataValidationError("cannot securely open the repository root") from error
    current_directory = root_descriptor
    descriptor = -1
    try:
        for component in components[:-1]:
            try:
                next_directory = os.open(
                    component,
                    directory_flags,
                    dir_fd=current_directory,
                )
            except OSError as error:
                raise DataValidationError(
                    f"cannot securely open directory component {component}"
                ) from error
            if current_directory != root_descriptor:
                os.close(current_directory)
            current_directory = next_directory
        file_flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            file_flags |= os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            file_flags |= os.O_CLOEXEC
        try:
            descriptor = os.open(components[-1], file_flags, dir_fd=current_directory)
        except OSError as error:
            raise DataValidationError(
                f"cannot securely open regular file {components[-1]}"
            ) from error
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise DataValidationError(f"{components[-1]} is not a regular file")
        if file_stat.st_size > maximum_bytes:
            raise DataValidationError(f"{components[-1]} exceeds {maximum_bytes} bytes")
        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > maximum_bytes:
            raise DataValidationError(f"{components[-1]} exceeds {maximum_bytes} bytes")
        return payload
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if current_directory != root_descriptor:
            os.close(current_directory)
        os.close(root_descriptor)


def _git_run(root: Path, arguments: list[str], *, text: bool = False) -> subprocess.CompletedProcess[Any]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            capture_output=True,
            text=text,
            timeout=2.0,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise DataValidationError("committed evidence identity could not be verified") from error


def _committed_file_bytes(root: Path, relative_path: str, maximum_bytes: int) -> bytes:
    """Return bytes only when the worktree file is identical to the file in HEAD."""

    normalized = _safe_relative_path(relative_path, "committed evidence path", "evidence/")
    worktree_bytes = _regular_file_bytes_at(root, normalized, maximum_bytes)
    object_name = f"HEAD:{normalized}"
    size_result = _git_run(root, ["cat-file", "-s", object_name], text=True)
    if size_result.returncode != 0:
        raise DataValidationError(f"{normalized} is not committed in HEAD")
    try:
        committed_size = int(size_result.stdout.strip())
    except ValueError as error:
        raise DataValidationError(f"Git returned an invalid size for {normalized}") from error
    if committed_size > maximum_bytes or committed_size != len(worktree_bytes):
        raise DataValidationError(f"{normalized} does not match its bounded committed blob")
    show_result = _git_run(root, ["show", object_name])
    if show_result.returncode != 0 or show_result.stdout != worktree_bytes:
        raise DataValidationError(f"{normalized} differs from the committed HEAD version")
    return worktree_bytes


def load_evaluation(root: Path) -> dict[str, Any]:
    """Quarantine committed matrix bytes until a committed replay verifier exists."""

    relative_matrix_path = "evidence/evaluation/device-matrix.json"
    path = root / relative_matrix_path
    if not path.exists() and not path.is_symlink():
        return {
            "schema_version": 3,
            "data_status": "not_yet_available",
            "matrix_cells": 0,
            "cells": [],
            "source": relative_matrix_path,
            "generator_replayed": False,
            "message": "No committed evaluation matrix is present; no results are claimed.",
        }

    raw_matrix = _committed_file_bytes(root, relative_matrix_path, MAX_EVALUATION_BYTES)
    return {
        "schema_version": 3,
        "data_status": "quarantined_unreplayed_evidence",
        "matrix_cells": 0,
        "cells": [],
        "source": relative_matrix_path,
        "source_sha256": hashlib.sha256(raw_matrix).hexdigest(),
        "generator_replayed": False,
        "quarantine_reason": "no_committed_replay_verifier",
        "message": (
            "Committed matrix bytes are quarantined: no committed replay verifier exists, "
            "so no empirical rows, statuses, or metrics are displayed."
        ),
    }


def source_revision(root: Path) -> dict[str, Any]:
    """Read current Git identity while exposing only a revision and dirty boolean."""

    try:
        revision = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=1.0,
        ).stdout.strip()
        status_output = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=1.0,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {"revision": None, "dirty": None, "status": "unavailable"}
    if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
        return {"revision": None, "dirty": None, "status": "invalid_git_output"}
    return {"revision": revision, "dirty": bool(status_output), "status": "observed"}


def _directory_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _file_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _same_file_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


def _open_relative_artifact_root(
    repository_fd: int, components: tuple[str, ...]
) -> int | None:
    """Open a declared artifact root without ever reopening a queued pathname."""

    current = os.dup(repository_fd)
    try:
        for component in components:
            try:
                next_descriptor = os.open(
                    component, _directory_open_flags(), dir_fd=current
                )
            except FileNotFoundError:
                os.close(current)
                return None
            except OSError as error:
                raise DataValidationError(
                    f"artifact inventory cannot securely open {'/'.join(components)}"
                ) from error
            opened_stat = os.fstat(next_descriptor)
            if not stat.S_ISDIR(opened_stat.st_mode):
                os.close(next_descriptor)
                raise DataValidationError(
                    f"{'/'.join(components)} must be a real directory, not a symlink"
                )
            os.close(current)
            current = next_descriptor
        return current
    except BaseException:
        try:
            os.close(current)
        except OSError:
            pass
        raise


def artifact_metadata(
    root: Path,
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Inventory declared trees solely through retained no-follow directory FDs."""

    declared_roots = (("artifacts",), ("evidence", "store-assets"))
    artifacts: list[dict[str, Any]] = []
    entries_seen = 0
    try:
        repository_fd = os.open(root, _directory_open_flags())
    except OSError as error:
        raise DataValidationError("artifact inventory cannot securely open repository root") from error
    try:
        for components in declared_roots:
            artifact_root_fd = _open_relative_artifact_root(repository_fd, components)
            if artifact_root_fd is None:
                continue
            pending: list[tuple[int, tuple[str, ...]]] = [(artifact_root_fd, components)]
            try:
                while pending:
                    directory_fd, relative_components = pending.pop()
                    try:
                        try:
                            with os.scandir(directory_fd) as directory_entries:
                                remaining_entry_budget = MAX_ARTIFACT_ENTRIES - entries_seen + 1
                                entries = list(
                                    itertools.islice(directory_entries, remaining_entry_budget)
                                )
                        except OSError as error:
                            raise DataValidationError(
                                f"artifact inventory cannot scan {'/'.join(relative_components)}"
                            ) from error
                        for entry in entries:
                            entries_seen += 1
                            if entries_seen > MAX_ARTIFACT_ENTRIES:
                                raise DataValidationError(
                                    "artifact inventory exceeds the "
                                    f"{MAX_ARTIFACT_ENTRIES}-entry traversal limit"
                                )
                            entry_relative = relative_components + (entry.name,)
                            display_path = "/".join(entry_relative)
                            try:
                                observed_stat = entry.stat(follow_symlinks=False)
                            except OSError as error:
                                raise DataValidationError(
                                    f"artifact inventory cannot stat {display_path}"
                                ) from error
                            if stat.S_ISLNK(observed_stat.st_mode):
                                raise DataValidationError(
                                    f"artifact inventory refuses symlink {display_path}"
                                )
                            if stat.S_ISDIR(observed_stat.st_mode):
                                try:
                                    child_fd = os.open(
                                        entry.name,
                                        _directory_open_flags(),
                                        dir_fd=directory_fd,
                                    )
                                except OSError as error:
                                    raise DataValidationError(
                                        f"artifact inventory refuses replaced directory {display_path}"
                                    ) from error
                                child_stat = os.fstat(child_fd)
                                if (
                                    not stat.S_ISDIR(child_stat.st_mode)
                                    or not _same_file_identity(observed_stat, child_stat)
                                ):
                                    os.close(child_fd)
                                    raise DataValidationError(
                                        f"artifact inventory refuses changed directory {display_path}"
                                    )
                                pending.append((child_fd, entry_relative))
                                continue
                            if not stat.S_ISREG(observed_stat.st_mode):
                                raise DataValidationError(
                                    f"artifact inventory refuses non-regular entry {display_path}"
                                )
                            if len(artifacts) >= MAX_ARTIFACT_FILES:
                                raise DataValidationError(
                                    "artifact inventory exceeds the "
                                    f"{MAX_ARTIFACT_FILES}-file safety limit"
                                )
                            try:
                                file_fd = os.open(
                                    entry.name, _file_open_flags(), dir_fd=directory_fd
                                )
                            except OSError as error:
                                raise DataValidationError(
                                    f"artifact inventory refuses replaced file {display_path}"
                                ) from error
                            try:
                                file_stat = os.fstat(file_fd)
                                if (
                                    not stat.S_ISREG(file_stat.st_mode)
                                    or not _same_file_identity(observed_stat, file_stat)
                                ):
                                    raise DataValidationError(
                                        f"artifact inventory refuses changed file {display_path}"
                                    )
                            finally:
                                os.close(file_fd)
                            artifacts.append(
                                {
                                    "path": display_path,
                                    "size_bytes": file_stat.st_size,
                                    "modified_at": datetime.fromtimestamp(file_stat.st_mtime, UTC)
                                    .isoformat(timespec="seconds")
                                    .replace("+00:00", "Z"),
                                }
                            )
                    finally:
                        os.close(directory_fd)
            except BaseException:
                for descriptor, _relative in pending:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
                raise
    finally:
        os.close(repository_fd)

    artifacts.sort(key=lambda artifact: artifact["path"])
    return {
        "schema_version": 1,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "source": dict(source_metadata) if source_metadata is not None else source_revision(root),
        "testflight_status": "not_configured",
        "store_submission_status": "not_configured",
        "message": (
            "No build artifacts are present; nothing is claimed as uploaded."
            if not artifacts
            else "Inventory reflects files currently present in declared artifact directories."
        ),
    }


def flicker_document(hz: float, duty_cycle: float) -> str:
    """Generate an original browser-sampled square-wave display pattern."""

    if not (0.5 <= hz <= 240.0):
        raise ValueError("hz must be between 0.5 and 240")
    if not (0.05 <= duty_cycle <= 0.95):
        raise ValueError("duty must be between 0.05 and 0.95")
    hz_text = format(hz, ".6g")
    duty_text = format(duty_cycle, ".6g")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Original flicker pattern — requested {hz_text} Hz</title>
<style>
html,body{{margin:0;width:100%;height:100%;background:#000;color:#fff;font:16px system-ui,sans-serif}}
#field{{position:fixed;inset:0;background:#000}}
#status{{position:fixed;left:1rem;bottom:1rem;padding:.7rem .9rem;max-width:42rem;
background:rgba(0,0,0,.76);border:1px solid #aaa;border-radius:.35rem}}
</style></head><body><main id="field" aria-label="Animated black and white flicker field"></main>
<p id="status" role="status">Requested square wave: {hz_text} Hz, duty {duty_text}. Actual emitted timing is browser/display dependent and is not calibrated.</p>
<script>
"use strict";
const requestedHz={hz_text}; const duty={duty_text}; const start=performance.now();
const field=document.getElementById("field"); let previous=null; let transitions=0; let frames=0;
function draw(now){{
  const phase=((now-start)*requestedHz/1000)%1; const bright=phase<duty;
  if(bright!==previous){{transitions+=1;previous=bright;}}
  field.style.background=bright?"#fff":"#000"; frames+=1;
  if(frames%120===0){{document.getElementById("status").textContent=
    `Requested square wave: ${{requestedHz}} Hz, duty ${{duty}}. Browser frames observed: ${{frames}}; transitions rendered: ${{transitions}}. Actual emitted timing remains display dependent.`;}}
  requestAnimationFrame(draw);
}}
requestAnimationFrame(draw);
</script></body></html>"""


def moire_svg(spacing_px: int, angle_degrees: int) -> str:
    """Generate an original high-frequency line target as SVG."""

    if not 2 <= spacing_px <= 64:
        raise ValueError("spacing must be between 2 and 64")
    if not -89 <= angle_degrees <= 89:
        raise ValueError("angle must be between -89 and 89")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200" role="img" aria-labelledby="title desc">
<title id="title">Original moire line target</title>
<desc id="desc">Alternating black and white lines, {spacing_px} pixels apart, rotated {angle_degrees} degrees.</desc>
<defs><pattern id="lines" width="{spacing_px * 2}" height="{spacing_px * 2}" patternUnits="userSpaceOnUse" patternTransform="rotate({angle_degrees})">
<rect width="{spacing_px}" height="{spacing_px * 2}" fill="#050505"/><rect x="{spacing_px}" width="{spacing_px}" height="{spacing_px * 2}" fill="#fafafa"/>
</pattern></defs><rect width="1200" height="1200" fill="url(#lines)"/>
<path d="M0 600H1200M600 0V1200" stroke="#ff2d55" stroke-width="2"/>
</svg>"""


def checkerboard_svg(cell_px: int) -> str:
    """Generate an original checkerboard/detail-preservation target as SVG."""

    if not 2 <= cell_px <= 128:
        raise ValueError("cell must be between 2 and 128")
    double = cell_px * 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200" role="img" aria-labelledby="title desc">
<title id="title">Original checkerboard target</title><desc id="desc">Black and white checkerboard with {cell_px} pixel cells.</desc>
<defs><pattern id="checks" width="{double}" height="{double}" patternUnits="userSpaceOnUse">
<rect width="{double}" height="{double}" fill="#fff"/><rect width="{cell_px}" height="{cell_px}" fill="#000"/>
<rect x="{cell_px}" y="{cell_px}" width="{cell_px}" height="{cell_px}" fill="#000"/>
</pattern></defs><rect width="1200" height="1200" fill="url(#checks)"/>
</svg>"""


class WebhookLedger:
    """Crash-consistent, privacy-minimised snapshot of authenticated sandbox receipts."""

    SNAPSHOT_NAME: Final = "revenuecat-webhook-receipts.json"
    LEGACY_NAME: Final = "revenuecat-webhook-receipts.jsonl"
    TEMP_PREFIX: Final = ".revenuecat-webhook-receipts."
    MAX_RECORDS: Final = 20_000
    RECORD_KEYS: Final = {
        "schema_version",
        "event_id_sha256",
        "event_payload_sha256",
        "event_type",
        "environment",
        "received_at",
    }

    def __init__(self, root: Path) -> None:
        self.path = root / ".dev" / "tmp" / self.SNAPSHOT_NAME
        self._lock = threading.Lock()
        self._directory_fd = self._open_directory(root)
        self._records: dict[str, dict[str, Any]] = {}
        try:
            self._validate_directory_entries()
            self._records = self._load_snapshot()
        except BaseException:
            os.close(self._directory_fd)
            self._directory_fd = -1
            raise

    @staticmethod
    def _open_directory(root: Path) -> int:
        try:
            current = os.open(root, _directory_open_flags())
        except OSError as error:
            raise ConfigurationError("cannot securely open webhook ledger repository root") from error
        try:
            for component in (".dev", "tmp"):
                try:
                    next_descriptor = os.open(
                        component, _directory_open_flags(), dir_fd=current
                    )
                except FileNotFoundError:
                    try:
                        os.mkdir(component, 0o700, dir_fd=current)
                    except FileExistsError:
                        pass
                    try:
                        next_descriptor = os.open(
                            component, _directory_open_flags(), dir_fd=current
                        )
                    except OSError as error:
                        raise ConfigurationError(
                            "webhook ledger directory is not a real directory"
                        ) from error
                except OSError as error:
                    raise ConfigurationError(
                        "webhook ledger directory is not a real directory"
                    ) from error
                os.close(current)
                current = next_descriptor
            return current
        except BaseException:
            try:
                os.close(current)
            except OSError:
                pass
            raise

    def close(self) -> None:
        descriptor = self._directory_fd
        if descriptor >= 0:
            self._directory_fd = -1
            os.close(descriptor)

    def __del__(self) -> None:
        try:
            self.close()
        except OSError:
            pass

    def _validate_directory_entries(self) -> None:
        inspected = 0
        try:
            with os.scandir(self._directory_fd) as entries:
                for entry in entries:
                    inspected += 1
                    if inspected > 4_096:
                        raise ConfigurationError(
                            "webhook ledger directory exceeds its entry inspection bound"
                        )
                    if entry.name == self.LEGACY_NAME:
                        raise ConfigurationError(
                            "legacy append-only webhook ledger is refused; remove isolated .dev state"
                        )
                    if entry.name.startswith(self.TEMP_PREFIX):
                        raise ConfigurationError(
                            "stale webhook ledger temporary file requires reconciliation"
                        )
        except ConfigurationError:
            raise
        except OSError as error:
            raise ConfigurationError("cannot inspect webhook ledger directory") from error

    def _read_snapshot_bytes(self) -> bytes | None:
        try:
            descriptor = os.open(
                self.SNAPSHOT_NAME, _file_open_flags(), dir_fd=self._directory_fd
            )
        except FileNotFoundError:
            return None
        except OSError as error:
            raise ConfigurationError("webhook receipt snapshot cannot be securely opened") from error
        try:
            file_stat = os.fstat(descriptor)
            if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > MAX_LEDGER_BYTES:
                raise ConfigurationError("webhook receipt snapshot is not a bounded regular file")
            chunks: list[bytes] = []
            remaining = MAX_LEDGER_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            if len(payload) > MAX_LEDGER_BYTES:
                raise ConfigurationError("webhook receipt snapshot exceeds its retention bound")
            return payload
        finally:
            os.close(descriptor)

    @staticmethod
    def _validate_timestamp(value: Any) -> str:
        if not isinstance(value, str) or UTC_TIMESTAMP_RE.fullmatch(value) is None:
            raise ConfigurationError("webhook receipt timestamp must be canonical UTC")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ConfigurationError("webhook receipt timestamp is invalid") from error
        if parsed.tzinfo != UTC:
            raise ConfigurationError("webhook receipt timestamp must be UTC")
        return value

    def _parse_record(self, value: Any, index: int) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != self.RECORD_KEYS:
            raise ConfigurationError(f"webhook receipt record {index} has an invalid schema")
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise ConfigurationError(f"webhook receipt record {index} has an invalid version")
        event_digest = value.get("event_id_sha256")
        payload_digest = value.get("event_payload_sha256")
        if not isinstance(event_digest, str) or SHA256_RE.fullmatch(event_digest) is None:
            raise ConfigurationError(f"webhook receipt record {index} has an invalid event digest")
        if not isinstance(payload_digest, str) or SHA256_RE.fullmatch(payload_digest) is None:
            raise ConfigurationError(f"webhook receipt record {index} has an invalid payload digest")
        event_type = value.get("event_type")
        if not isinstance(event_type, str) or EVENT_TYPE_RE.fullmatch(event_type) is None:
            raise ConfigurationError(f"webhook receipt record {index} has an invalid event type")
        if value.get("environment") != "SANDBOX":
            raise ConfigurationError(f"webhook receipt record {index} has an invalid environment")
        received_at = self._validate_timestamp(value.get("received_at"))
        return {
            "schema_version": 1,
            "event_id_sha256": event_digest,
            "event_payload_sha256": payload_digest,
            "event_type": event_type,
            "environment": "SANDBOX",
            "received_at": received_at,
        }

    def _load_snapshot(self) -> dict[str, dict[str, Any]]:
        payload = self._read_snapshot_bytes()
        if payload is None:
            return {}
        try:
            document = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, JSONBoundaryError) as error:
            raise ConfigurationError("webhook receipt snapshot is not valid UTF-8 JSON") from error
        if not isinstance(document, dict) or set(document) != {"schema_version", "records"}:
            raise ConfigurationError("webhook receipt snapshot has an invalid schema")
        if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
            raise ConfigurationError("webhook receipt snapshot has an invalid version")
        values = document.get("records")
        if not isinstance(values, list) or len(values) > self.MAX_RECORDS:
            raise ConfigurationError("webhook receipt snapshot record count is invalid")
        records: dict[str, dict[str, Any]] = {}
        for index, value in enumerate(values):
            record = self._parse_record(value, index)
            digest = record["event_id_sha256"]
            if digest in records:
                raise ConfigurationError("webhook receipt snapshot repeats an event digest")
            records[digest] = record
        return records

    @staticmethod
    def _encode_snapshot(records: Mapping[str, Mapping[str, Any]]) -> bytes:
        document = {
            "schema_version": 1,
            "records": [records[digest] for digest in sorted(records)],
        }
        encoded = (
            json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        if len(encoded) > MAX_LEDGER_BYTES:
            raise OSError("webhook receipt snapshot reached its retention bound")
        return encoded

    @staticmethod
    def _write_all(descriptor: int, payload: bytes) -> None:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write to webhook receipt snapshot")
            view = view[written:]

    @staticmethod
    def _fsync_file(descriptor: int) -> None:
        os.fsync(descriptor)

    def _replace(self, temporary_name: str) -> None:
        os.replace(
            temporary_name,
            self.SNAPSHOT_NAME,
            src_dir_fd=self._directory_fd,
            dst_dir_fd=self._directory_fd,
        )

    def _fsync_directory(self) -> None:
        os.fsync(self._directory_fd)

    def _store_snapshot(self, candidate: dict[str, dict[str, Any]]) -> None:
        encoded = self._encode_snapshot(candidate)
        temporary_name = f"{self.TEMP_PREFIX}{os.getpid()}.{uuid.uuid4().hex}.tmp"
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        descriptor = -1
        cleanup_failed = False
        try:
            descriptor = os.open(
                temporary_name, flags, 0o600, dir_fd=self._directory_fd
            )
            self._write_all(descriptor, encoded)
            self._fsync_file(descriptor)
            os.close(descriptor)
            descriptor = -1
            self._replace(temporary_name)
            self._fsync_directory()
            return
        except Exception as original_error:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    cleanup_failed = True
            try:
                os.unlink(temporary_name, dir_fd=self._directory_fd)
            except FileNotFoundError:
                pass
            except OSError:
                cleanup_failed = True
            try:
                observed = self._load_snapshot()
            except ConfigurationError as reconciliation_error:
                raise LedgerPersistenceUncertain(
                    "webhook receipt persistence failed and disk state is unreadable"
                ) from reconciliation_error
            if observed == candidate:
                self._records = observed
                raise LedgerPersistenceUncertain(
                    "webhook receipt was written but directory durability is uncertain"
                ) from original_error
            if observed != self._records or cleanup_failed:
                self._records = observed
                raise LedgerPersistenceUncertain(
                    "webhook receipt persistence failed with a changed disk state"
                ) from original_error
            raise

    @staticmethod
    def default_payload_identity(event_type: str) -> str:
        encoded = json.dumps(
            {"environment": "SANDBOX", "event_type": event_type},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def accept(
        self,
        event_id: str,
        event_type: str,
        event_payload_sha256: str | None = None,
    ) -> bool:
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 256:
            raise WebhookValidationError("event.id must be a non-empty string of at most 256 chars")
        if not isinstance(event_type, str) or EVENT_TYPE_RE.fullmatch(event_type) is None:
            raise WebhookValidationError("event.type must be an uppercase RevenueCat event token")
        payload_digest = event_payload_sha256 or self.default_payload_identity(event_type)
        if SHA256_RE.fullmatch(payload_digest) is None:
            raise WebhookValidationError("event payload identity must be lowercase SHA-256")
        digest = hashlib.sha256(event_id.encode("utf-8")).hexdigest()
        with self._lock:
            try:
                observed_records = self._load_snapshot()
            except ConfigurationError as error:
                raise LedgerPersistenceUncertain(
                    "webhook receipt snapshot changed or became unreadable"
                ) from error
            if observed_records != self._records:
                self._records = observed_records
                raise LedgerPersistenceUncertain(
                    "webhook receipt snapshot changed outside the active ledger"
                )
            existing = self._records.get(digest)
            if existing is not None:
                if (
                    existing["event_type"] != event_type
                    or existing["event_payload_sha256"] != payload_digest
                ):
                    raise WebhookIdentityConflict(
                        "event.id was already received with a different payload identity"
                    )
                return False
            if len(self._records) >= self.MAX_RECORDS:
                raise OSError("webhook receipt snapshot reached its record bound")
            record = {
                "schema_version": 1,
                "event_id_sha256": digest,
                "event_payload_sha256": payload_digest,
                "event_type": event_type,
                "environment": "SANDBOX",
                "received_at": utc_now(),
            }
            candidate = dict(self._records)
            candidate[digest] = record
            self._store_snapshot(candidate)
            self._records = candidate
            return True


def validate_webhook(document: Any) -> tuple[str, str, str]:
    if not isinstance(document, dict):
        raise WebhookValidationError("request body must be a JSON object")
    if document.get("api_version") != "1.0":
        raise WebhookValidationError("api_version must be 1.0")
    event = document.get("event")
    if not isinstance(event, dict):
        raise WebhookValidationError("event must be a JSON object")
    event_id = event.get("id")
    event_type = event.get("type")
    environment = event.get("environment")
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 256:
        raise WebhookValidationError("event.id must be a non-empty string of at most 256 chars")
    if not isinstance(event_type, str) or EVENT_TYPE_RE.fullmatch(event_type) is None:
        raise WebhookValidationError("event.type must be an uppercase RevenueCat event token")
    if environment != "SANDBOX":
        raise WebhookValidationError("only SANDBOX events are accepted by this local receiver")
    try:
        canonical_event = json.dumps(
            event,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise WebhookValidationError("event payload must be canonical JSON data") from error
    return event_id, event_type, hashlib.sha256(canonical_event).hexdigest()


def configured_webhook_auth_token() -> str | None:
    """Validate optional adapter configuration without retaining malformed secrets."""

    value = os.environ.get("REVENUECAT_WEBHOOK_AUTH_TOKEN")
    if value is None:
        return None
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ConfigurationError(
            "REVENUECAT_WEBHOOK_AUTH_TOKEN must be printable ASCII"
        ) from error
    if not WEBHOOK_TOKEN_MIN_BYTES <= len(encoded) <= WEBHOOK_TOKEN_MAX_BYTES:
        raise ConfigurationError(
            "REVENUECAT_WEBHOOK_AUTH_TOKEN must contain 16 through 256 bytes"
        )
    if any(byte < 0x21 or byte > 0x7E for byte in encoded):
        raise ConfigurationError(
            "REVENUECAT_WEBHOOK_AUTH_TOKEN must not contain whitespace or controls"
        )
    return value


class ServiceState:
    def __init__(
        self,
        spec: ServiceSpec,
        root: Path,
        host: str,
        port: int,
        instance_token: str,
    ) -> None:
        self.spec = spec
        self.root = root
        self.host = host
        self.port = port
        self.instance_token = instance_token
        self.instance_token_sha256 = hashlib.sha256(instance_token.encode("ascii")).hexdigest()
        self.started_at = utc_now()
        self.shutdown_requested = threading.Event()
        self.webhook_auth_token = configured_webhook_auth_token()
        self.webhook_ledger = WebhookLedger(root) if spec.name == "revenuecat-webhook" else None
        self._artifact_source: dict[str, Any] | None = None
        self._artifact_source_lock = threading.Lock()

    def common(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "service": self.spec.name,
            "service_title": self.spec.title,
            "bind_host": self.host,
            "port": self.port,
            "instance_token_sha256": self.instance_token_sha256,
            "readiness_scope": "local_development_surface",
            "production_verified": False,
        }

    def readiness(self) -> tuple[bool, dict[str, Any]]:
        payload = self.common()
        payload["checked_at"] = utc_now()
        try:
            verify_logging(self.spec.name)
            if self.spec.name == "evaluation":
                evaluation = load_evaluation(self.root)
                payload["checks"] = {
                    "http_surface": "ready",
                    "evaluation_data": evaluation["data_status"],
                    "matrix_cells": evaluation["matrix_cells"],
                }
            elif self.spec.name == "revenuecat-webhook":
                payload["checks"] = {
                    "receiver": "ready",
                    "authentication_configured": bool(self.webhook_auth_token),
                    "provider_verification": {
                        "verified": False,
                        "status": "not_performed",
                        "message": "Local readiness does not prove RevenueCat delivery.",
                    },
                }
            elif self.spec.name == "test-patterns":
                samples = (
                    flicker_document(60.0, 0.5),
                    moire_svg(4, 17),
                    checkerboard_svg(8),
                )
                payload["checks"] = {
                    "generator": "ready",
                    "sample_sha256": [
                        hashlib.sha256(sample.encode("utf-8")).hexdigest() for sample in samples
                    ],
                    "timing_calibrated": False,
                }
            else:
                metadata = self.artifacts()
                if metadata["source"]["status"] != "observed":
                    raise DataValidationError("Git source identity is unavailable")
                payload["checks"] = {
                    "inventory": "ready",
                    "artifact_count": metadata["artifact_count"],
                    "testflight_status": metadata["testflight_status"],
                    "store_submission_status": metadata["store_submission_status"],
                }
        except LoggingUnavailable as error:
            payload["ready"] = False
            payload["checks"] = {
                "status": "logging_unavailable",
                "error_code": "structured_log_write_failed",
                "message": str(error),
            }
            return False, payload
        except (DataValidationError, OSError) as error:
            payload["ready"] = False
            payload["checks"] = {"status": "invalid_local_data", "error": str(error)}
            return False, payload
        payload["ready"] = True
        return True, payload

    def artifacts(self) -> dict[str, Any]:
        if self.spec.name != "artifacts":
            raise DataValidationError("artifact metadata requested from the wrong service")
        with self._artifact_source_lock:
            if self._artifact_source is None:
                observed = source_revision(self.root)
                if observed.get("status") == "observed":
                    self._artifact_source = observed
                source = observed
            else:
                source = self._artifact_source
        return artifact_metadata(self.root, source)


def route_identifier(service_name: str, method: str, path: str) -> str:
    """Map request metadata to an exact non-sensitive allowlisted route ID."""

    if method in {"GET", "HEAD"}:
        common = {
            "/health/live": "health_live",
            "/health/ready": "health_ready",
        }
        if path in common:
            return common[path]
        routes = {
            "evaluation": {"/": "evaluation_index", "/api/evaluation": "evaluation_api"},
            "revenuecat-webhook": {"/": "webhook_index"},
            "test-patterns": {
                "/": "patterns_index",
                "/patterns/flicker": "pattern_flicker",
                "/patterns/moire.svg": "pattern_moire",
                "/patterns/checkerboard.svg": "pattern_checkerboard",
            },
            "artifacts": {"/": "artifacts_index", "/api/artifacts": "artifacts_api"},
        }
        return routes.get(service_name, {}).get(path, "unmatched")
    if method == "POST":
        if path == "/__devctl/shutdown":
            return "devctl_shutdown"
        if service_name == "revenuecat-webhook" and path == "/webhooks/revenuecat":
            return "webhook_revenuecat"
    return "unmatched"


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler], state: ServiceState):
        self.state = state
        self._request_slots = threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)
        super().__init__(address, handler)

    def server_bind(self) -> None:
        """Bind the loopback socket without an unbounded reverse-DNS lookup.

        ``http.server.HTTPServer.server_bind`` calls ``socket.getfqdn`` between
        ``bind`` and ``listen``.  That is a resolver call with no deadline placed
        directly in the startup path of a loopback-only service, so a slow or
        unreachable resolver leaves the socket bound but never listening while
        the controller can only observe a live process refusing connections.
        The literal bind host is already the exact identity this service serves.
        """

        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)

    def process_request(self, request: Any, client_address: Any) -> None:
        if not self._request_slots.acquire(blocking=False):
            request_id = uuid.uuid4().hex
            body = (
                json.dumps(
                    {
                        "schema_version": 1,
                        "service": self.state.spec.name,
                        "error": {
                            "code": "concurrency_limit",
                            "message": "The local service request limit is busy; retry later.",
                        },
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            response = (
                b"HTTP/1.1 503 Service Unavailable\r\n"
                b"Content-Type: application/json; charset=utf-8\r\n"
                + f"Content-Length: {len(body)}\r\n".encode("ascii")
                + f"X-Request-ID: {request_id}\r\n".encode("ascii")
                + b"Retry-After: 1\r\n"
                b"Cache-Control: no-store\r\n"
                b"Connection: close\r\n\r\n"
                + body
            )
            try:
                request.settimeout(OVERLOAD_WRITE_TIMEOUT_SECONDS)
                request.sendall(response)
            except OSError:
                pass
            finally:
                try:
                    try:
                        emit_log(
                            {
                            "timestamp": utc_now(),
                            "event": "local_http_request",
                            "service": self.state.spec.name,
                            "correlation_id": request_id,
                            "method": "unparsed",
                            "route_id": "unmatched",
                            "client": (
                                "127.0.0.1"
                                if client_address and client_address[0] == "127.0.0.1"
                                else "non_loopback_refused"
                            ),
                            "status": int(HTTPStatus.SERVICE_UNAVAILABLE),
                            "duration_ms": 0.0,
                            "refusal_code": "concurrency_limit",
                            }
                        )
                    except LoggingUnavailable:
                        pass
                finally:
                    self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._request_slots.release()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()

    def handle_error(self, request: Any, client_address: Any) -> None:
        del request, client_address
        exception_type = sys.exc_info()[0]
        error_type = exception_type.__name__ if exception_type is not None else "UnknownError"
        try:
            emit_log(
                {
                "timestamp": utc_now(),
                "event": "local_http_handler_failed",
                "service": self.state.spec.name,
                "error_type": error_type,
                }
            )
        except LoggingUnavailable:
            pass


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "RevenueCatShipatonLocal/1"
    sys_version = ""

    @property
    def state(self) -> ServiceState:
        server = self.server
        if not isinstance(server, BoundedThreadingHTTPServer):
            raise RuntimeError("handler attached to an unsupported server")
        return server.state

    def setup(self) -> None:
        self._request_started = time.monotonic()
        self._correlation_id = uuid.uuid4().hex
        self._response_status: int | None = None
        self._refusal_code: str | None = None
        self._route_id = "unmatched"
        self._request_log_emitted = False
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT_SECONDS)

    def _send_headers(self, status: int, content_type: str, length: int) -> None:
        self._response_status = int(status)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Request-ID", self._correlation_id)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'",
        )
        self.send_header("Connection", "close")
        self.end_headers()

    def _send_bytes(self, status: int, content_type: str, body: bytes, *, head: bool = False) -> None:
        self._send_headers(status, content_type, len(body))
        if not head:
            self.wfile.write(body)

    def _send_json(self, status: int, payload: Mapping[str, Any], *, head: bool = False) -> None:
        body = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", body, head=head)

    def _send_html(self, status: int, document: str, *, head: bool = False) -> None:
        self._send_bytes(status, "text/html; charset=utf-8", document.encode("utf-8"), head=head)

    def _error(self, status: int, code: str, message: str) -> None:
        self._refusal_code = code
        self._send_json(
            status,
            {
                "schema_version": 1,
                "error": {"code": code, "message": message},
                "service": self.state.spec.name,
            },
        )

    def _target(self) -> tuple[str, dict[str, list[str]]] | None:
        if len(self.path.encode("utf-8", errors="replace")) > MAX_REQUEST_TARGET_BYTES:
            self._error(HTTPStatus.REQUEST_URI_TOO_LONG, "request_target_too_long", "Request target is too long.")
            return None
        parsed = urlsplit(self.path)
        method = self.command if self.command in {"GET", "HEAD", "POST"} else "unmatched"
        self._route_id = route_identifier(self.state.spec.name, method, parsed.path)
        try:
            query = parse_qs(
                parsed.query,
                strict_parsing=True,
                keep_blank_values=True,
                max_num_fields=16,
            )
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_query", "Query parameters are invalid.")
            return None
        return parsed.path, query

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle_get(head=True)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle_get(head=False)

    def _handle_get(self, *, head: bool) -> None:
        target = self._target()
        if target is None:
            return
        path, query = target
        if path == "/health/live":
            payload = self.state.common()
            payload.update({"alive": True, "started_at": self.state.started_at, "checked_at": utc_now()})
            self._send_json(HTTPStatus.OK, payload, head=head)
            return
        if path == "/health/ready":
            ready, payload = self.state.readiness()
            self._send_json(HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE, payload, head=head)
            return

        try:
            if self.state.spec.name == "evaluation":
                self._evaluation_get(path, query, head)
            elif self.state.spec.name == "revenuecat-webhook":
                self._webhook_get(path, query, head)
            elif self.state.spec.name == "test-patterns":
                self._patterns_get(path, query, head)
            else:
                self._artifacts_get(path, query, head)
        except (ValueError, DataValidationError) as error:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_request", str(error))

    def _evaluation_get(self, path: str, query: dict[str, list[str]], head: bool) -> None:
        if query:
            raise ValueError("this endpoint does not accept query parameters")
        if path == "/api/evaluation":
            self._send_json(HTTPStatus.OK, load_evaluation(self.state.root), head=head)
            return
        if path != "/":
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found.")
            return
        self._send_html(HTTPStatus.OK, evaluation_dashboard_html(), head=head)

    def _webhook_get(self, path: str, query: dict[str, list[str]], head: bool) -> None:
        if path != "/" or query:
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found.")
            return
        ready, payload = self.state.readiness()
        self._send_json(HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE, payload, head=head)

    def _patterns_get(self, path: str, query: dict[str, list[str]], head: bool) -> None:
        if path == "/":
            if query:
                raise ValueError("pattern index does not accept query parameters")
            self._send_html(HTTPStatus.OK, patterns_index_html(), head=head)
            return
        if path == "/patterns/flicker":
            hz = single_float_query(query, "hz", default=60.0)
            duty = single_float_query(query, "duty", default=0.5)
            allowed = {"hz", "duty"}
            reject_unknown_query(query, allowed)
            self._send_html(HTTPStatus.OK, flicker_document(hz, duty), head=head)
            return
        if path == "/patterns/moire.svg":
            spacing = single_int_query(query, "spacing", default=4)
            angle = single_int_query(query, "angle", default=17)
            reject_unknown_query(query, {"spacing", "angle"})
            body = moire_svg(spacing, angle).encode("utf-8")
            self._send_bytes(HTTPStatus.OK, "image/svg+xml; charset=utf-8", body, head=head)
            return
        if path == "/patterns/checkerboard.svg":
            cell = single_int_query(query, "cell", default=8)
            reject_unknown_query(query, {"cell"})
            body = checkerboard_svg(cell).encode("utf-8")
            self._send_bytes(HTTPStatus.OK, "image/svg+xml; charset=utf-8", body, head=head)
            return
        self._error(HTTPStatus.NOT_FOUND, "not_found", "Pattern endpoint not found.")

    def _artifacts_get(self, path: str, query: dict[str, list[str]], head: bool) -> None:
        if query:
            raise ValueError("this endpoint does not accept query parameters")
        if path == "/api/artifacts":
            self._send_json(HTTPStatus.OK, self.state.artifacts(), head=head)
            return
        if path != "/":
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found.")
            return
        self._send_html(HTTPStatus.OK, artifacts_dashboard_html(), head=head)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        target = self._target()
        if target is None:
            return
        path, query = target
        if path == "/__devctl/shutdown":
            self._devctl_shutdown(query)
            return
        if self.state.spec.name != "revenuecat-webhook" or path != "/webhooks/revenuecat" or query:
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Webhook endpoint not found.")
            return
        expected_token = self.state.webhook_auth_token
        if not expected_token:
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "webhook_auth_not_configured",
                "Receiver authentication is not configured; provider events are refused.",
            )
            return
        supplied = self.headers.get("Authorization", "")
        prefix = "Bearer "
        supplied_token = supplied[len(prefix) :] if supplied.startswith(prefix) else ""
        if not supplied_token or not hmac.compare_digest(supplied_token, expected_token):
            self._error(HTTPStatus.UNAUTHORIZED, "webhook_auth_failed", "Webhook authentication failed.")
            return
        if self.headers.get("Transfer-Encoding"):
            self._error(HTTPStatus.BAD_REQUEST, "transfer_encoding_refused", "Chunked bodies are not accepted.")
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content_type_invalid", "Expected application/json.")
            return
        length_text = self.headers.get("Content-Length")
        try:
            length = int(length_text) if length_text is not None else -1
        except ValueError:
            length = -1
        if not 1 <= length <= MAX_WEBHOOK_BYTES:
            self._error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "body_size_invalid",
                f"Body must be between 1 and {MAX_WEBHOOK_BYTES} bytes.",
            )
            return
        try:
            body = self.rfile.read(length)
            document = strict_json_loads(body.decode("utf-8"))
            event_id, event_type, event_payload_sha256 = validate_webhook(document)
        except (UnicodeDecodeError, json.JSONDecodeError, JSONBoundaryError):
            self._error(HTTPStatus.BAD_REQUEST, "json_invalid", "Body must be valid UTF-8 JSON.")
            return
        except WebhookValidationError as error:
            self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "webhook_schema_invalid", str(error))
            return
        ledger = self.state.webhook_ledger
        if ledger is None:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "receiver_state_invalid", "Receiver is unavailable.")
            return
        try:
            created = ledger.accept(event_id, event_type, event_payload_sha256)
        except WebhookIdentityConflict as error:
            self._error(HTTPStatus.CONFLICT, "webhook_identity_conflict", str(error))
            return
        except LedgerPersistenceUncertain:
            self._refusal_code = "receipt_persist_uncertain"
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "schema_version": 1,
                    "accepted": False,
                    "persistence_state": "uncertain_requires_idempotent_retry",
                    "error": {
                        "code": "receipt_persist_uncertain",
                        "message": "Receipt durability is uncertain; retry the same event ID.",
                    },
                },
            )
            return
        except OSError:
            self._error(HTTPStatus.INSUFFICIENT_STORAGE, "receipt_persist_failed", "Event was not accepted.")
            return
        try:
            emit_log(
                {
                    "timestamp": utc_now(),
                    "event": "sandbox_webhook_receipt_audited",
                    "service": self.state.spec.name,
                    "correlation_id": self._correlation_id,
                    "event_id_sha256": hashlib.sha256(event_id.encode("utf-8")).hexdigest(),
                    "event_payload_sha256": event_payload_sha256,
                    "event_type": event_type,
                    "duplicate": not created,
                    "persistence_state": "committed",
                    "provider_delivery_verified": False,
                }
            )
        except LoggingUnavailable:
            self._refusal_code = "webhook_audit_uncertain"
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "schema_version": 1,
                    "accepted": False,
                    "duplicate": not created,
                    "persistence_state": "committed_audit_uncertain",
                    "error": {
                        "code": "webhook_audit_uncertain",
                        "message": "Receipt was committed but required audit logging failed; retry the same event ID.",
                    },
                },
            )
            return
        self._send_json(
            HTTPStatus.ACCEPTED if created else HTTPStatus.OK,
            {
                "schema_version": 1,
                "accepted": True,
                "duplicate": not created,
                "environment": "SANDBOX",
                "provider_delivery_verified": False,
            },
        )

    def _devctl_shutdown(self, query: dict[str, list[str]]) -> None:
        if query:
            self._error(
                HTTPStatus.BAD_REQUEST,
                "shutdown_query_refused",
                "The shutdown control endpoint does not accept query parameters.",
            )
            return
        supplied_token = self.headers.get(DEVCTL_TOKEN_HEADER, "")
        if not supplied_token or not hmac.compare_digest(supplied_token, self.state.instance_token):
            self._error(
                HTTPStatus.UNAUTHORIZED,
                "shutdown_auth_failed",
                "Shutdown control authentication failed.",
            )
            return
        if self.headers.get("Transfer-Encoding"):
            self._error(
                HTTPStatus.BAD_REQUEST,
                "shutdown_transfer_encoding_refused",
                "Shutdown control does not accept a transfer-encoded body.",
            )
            return
        content_length = self.headers.get("Content-Length")
        if content_length not in (None, "0"):
            self._error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "shutdown_body_refused",
                "Shutdown control does not accept a request body.",
            )
            return
        self.state.shutdown_requested.set()
        self._send_json(
            HTTPStatus.ACCEPTED,
            {
                "schema_version": 1,
                "service": self.state.spec.name,
                "instance_token_sha256": self.state.instance_token_sha256,
                "shutdown_requested": True,
            },
        )
        server = self.server
        if not isinstance(server, BoundedThreadingHTTPServer):
            raise RuntimeError("handler attached to an unsupported server")

        def shutdown_after_response() -> None:
            time.sleep(0.05)
            server.shutdown()

        threading.Thread(
            target=shutdown_after_response,
            name="authenticated-http-shutdown",
            daemon=True,
        ).start()

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        del size
        try:
            self._response_status = int(code)
        except (TypeError, ValueError):
            self._response_status = None

    def log_message(self, format_string: str, *args: Any) -> None:
        del format_string, args

    def finish(self) -> None:
        try:
            super().finish()
        finally:
            if not self._request_log_emitted:
                self._request_log_emitted = True
                command = getattr(self, "command", "")
                method = command if command in {"GET", "HEAD", "POST"} else "unparsed"
                status = self._response_status if self._response_status is not None else 0
                refusal_code = self._refusal_code
                if status >= 400 and refusal_code is None:
                    refusal_code = "http_error_unclassified"
                record = {
                    "timestamp": utc_now(),
                    "event": "local_http_request",
                    "service": self.state.spec.name,
                    "correlation_id": self._correlation_id,
                    "method": method,
                    "route_id": self._route_id,
                    "client": (
                        "127.0.0.1"
                        if self.client_address[0] == "127.0.0.1"
                        else "non_loopback_refused"
                    ),
                    "status": status,
                    "duration_ms": round(
                        max(0.0, (time.monotonic() - self._request_started) * 1000.0), 3
                    ),
                    "refusal_code": refusal_code,
                }
                try:
                    emit_log(record)
                except LoggingUnavailable:
                    pass


def single_float_query(query: dict[str, list[str]], name: str, *, default: float) -> float:
    values = query.get(name)
    if values is None:
        return default
    if len(values) != 1:
        raise ValueError(f"{name} must be supplied exactly once")
    try:
        return float(values[0])
    except ValueError as error:
        raise ValueError(f"{name} must be numeric") from error


def single_int_query(query: dict[str, list[str]], name: str, *, default: int) -> int:
    values = query.get(name)
    if values is None:
        return default
    if len(values) != 1 or not re.fullmatch(r"-?[0-9]+", values[0]):
        raise ValueError(f"{name} must be an integer supplied exactly once")
    return int(values[0])


def reject_unknown_query(query: dict[str, list[str]], allowed: set[str]) -> None:
    unknown = sorted(set(query) - allowed)
    if unknown:
        raise ValueError(f"unknown query parameter: {unknown[0]}")


def evaluation_dashboard_html() -> str:
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evaluation matrix</title>
<style>body{font:16px system-ui,sans-serif;background:#101216;color:#f4f5f7;margin:0;padding:2rem}main{max-width:70rem;margin:auto}table{border-collapse:collapse;width:100%}th,td{padding:.6rem;border:1px solid #59606b;text-align:left}.notice{padding:1rem;border-left:4px solid #f5a623;background:#24272d}</style></head>
<body><main><h1>Device × lens × format × source evaluation</h1><p class="notice" id="status" role="status">Loading validated local evidence…</p><table><thead><tr><th>Device</th><th>Lens</th><th>Format</th><th>Source</th><th>Status</th></tr></thead><tbody id="rows"></tbody></table></main>
<script>"use strict";fetch("/api/evaluation").then(r=>{if(!r.ok)throw new Error("read failed");return r.json()}).then(d=>{document.getElementById("status").textContent=d.message;const b=document.getElementById("rows");for(const c of d.cells){const tr=document.createElement("tr");for(const k of ["device","lens","format","source","status"]){const td=document.createElement("td");td.textContent=c[k];tr.appendChild(td)}b.appendChild(tr)}}).catch(()=>{document.getElementById("status").textContent="Evaluation evidence is unavailable; no results are shown."});</script></body></html>"""


def patterns_index_html() -> str:
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Original capture test patterns</title><style>body{font:17px system-ui,sans-serif;max-width:52rem;margin:3rem auto;padding:0 1rem;line-height:1.55}li{margin:.7rem 0}.warning{border-left:4px solid #a65f00;padding:.7rem 1rem;background:#fff5de}</style></head><body><main><h1>Original capture test patterns</h1><p class="warning">These generated targets are original repository content. Requested flicker timing is sampled by the browser and display; it is not a calibrated source measurement.</p><ul><li><a href="/patterns/flicker?hz=60&amp;duty=0.5">Browser-sampled flicker field</a></li><li><a href="/patterns/moire.svg?spacing=4&amp;angle=17">Moiré line target (SVG)</a></li><li><a href="/patterns/checkerboard.svg?cell=8">Checkerboard detail target (SVG)</a></li></ul></main></body></html>"""


def artifacts_dashboard_html() -> str:
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Build artifact metadata</title><style>body{font:16px system-ui,sans-serif;max-width:64rem;margin:3rem auto;padding:0 1rem}pre{white-space:pre-wrap;background:#111;color:#eee;padding:1rem;border-radius:.4rem}</style></head><body><main><h1>Build and store artifact metadata</h1><p id="status" role="status">Loading observed local metadata…</p><pre id="metadata"></pre></main><script>"use strict";fetch("/api/artifacts").then(r=>{if(!r.ok)throw new Error("read failed");return r.json()}).then(d=>{document.getElementById("status").textContent=d.message;document.getElementById("metadata").textContent=JSON.stringify(d,null,2)}).catch(()=>{document.getElementById("status").textContent="Artifact metadata is unavailable; no upload is claimed."});</script></body></html>"""


def parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, choices=sorted(SERVICE_SPECS))
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--instance-token", required=True)
    parser.add_argument("--log-file", required=True, type=Path)
    return parser.parse_args(argv)


def validated_root(path: Path) -> Path:
    root = path.expanduser().resolve(strict=True)
    if root.name != REPOSITORY_NAME or not (root / "ports.env").is_file():
        raise ConfigurationError(f"repo root must be the {REPOSITORY_NAME} checkout")
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(sys.argv[1:] if argv is None else argv)
    try:
        root = validated_root(arguments.repo_root)
        if arguments.host != BIND_HOST:
            raise ConfigurationError(f"host must be exactly {BIND_HOST}")
        if not PORT_MIN <= arguments.port <= PORT_MAX:
            raise ConfigurationError(f"port must be inside {PORT_MIN}-{PORT_MAX}")
        if not TOKEN_RE.fullmatch(arguments.instance_token):
            raise ConfigurationError("instance token has an invalid format")
        configure_service_logging(arguments.log_file, root, arguments.service)
        state = ServiceState(
            SERVICE_SPECS[arguments.service],
            root,
            arguments.host,
            arguments.port,
            arguments.instance_token,
        )
        # Emitted before bind so that a startup stall is observable as a phase
        # that began and never completed, rather than as silence.
        emit_log(
            {
                "event": "local_service_binding",
                "service": state.spec.name,
                "bind_host": state.host,
                "port": state.port,
                "timestamp": utc_now(),
            }
        )
        server = BoundedThreadingHTTPServer((arguments.host, arguments.port), RequestHandler, state)
    except (ConfigurationError, OSError) as error:
        record = {"event": "local_service_start_failed", "error": str(error), "timestamp": utc_now()}
        if SERVICE_LOGGER.handlers:
            emit_log(record)
        else:
            print(json.dumps(record, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2

    stop_once = threading.Event()

    def request_shutdown(signum: int, _frame: Any) -> None:
        if stop_once.is_set():
            return
        stop_once.set()
        state.shutdown_requested.set()
        emit_log(
            {
                "event": "local_service_shutdown_requested",
                "service": state.spec.name,
                "signal": signum,
                "timestamp": utc_now(),
            }
        )
        threading.Thread(target=server.shutdown, name="http-shutdown", daemon=True).start()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    emit_log(
        {
            "event": "local_service_started",
            "service": state.spec.name,
            "bind_host": state.host,
            "port": state.port,
            "production_verified": False,
            "timestamp": utc_now(),
        }
    )
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        if state.webhook_ledger is not None:
            state.webhook_ledger.close()
        for handler in tuple(SERVICE_LOGGER.handlers):
            handler.close()
            SERVICE_LOGGER.removeHandler(handler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
