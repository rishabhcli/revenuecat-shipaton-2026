#!/usr/bin/env python3
"""Safely manage this repository's loopback-only development services."""

from __future__ import annotations

import argparse
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Iterator, Mapping, Sequence
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlsplit


REPOSITORY_NAME: Final = "revenuecat-shipaton-2026"
BIND_HOST: Final = "127.0.0.1"
PORT_MIN: Final = 4220
PORT_MAX: Final = 4229
PORT_BLOCK: Final = tuple(range(PORT_MIN, PORT_MAX + 1))
DEFAULT_HEALTH_TIMEOUT_SECONDS: Final = 30.0
DEFAULT_DOWN_TIMEOUT_SECONDS: Final = 50.0
STOP_TIMEOUT_SECONDS: Final = 10.0
E2E_CLEANUP_TIMEOUT_SECONDS: Final = 45.0
CONTROLLER_LOCK_POLL_SECONDS: Final = 0.05
GIT_IGNORE_CHECK_TIMEOUT_SECONDS: Final = 2.0
PROCESS_INSPECTION_TIMEOUT_SECONDS: Final = 1.0
LISTENER_INSPECTION_TIMEOUT_SECONDS: Final = 10.0
READINESS_REQUEST_TIMEOUT_SECONDS: Final = 0.75
SHUTDOWN_REQUEST_TIMEOUT_SECONDS: Final = 1.5
STOP_FINAL_IDENTITY_RESERVE_SECONDS: Final = 1.0
MAX_PID_RECORD_BYTES: Final = 16_384
MAX_HEALTH_BYTES: Final = 65_536
DEVCTL_TOKEN_HEADER: Final = "X-Devctl-Instance-Token"
INSTANCE_TOKEN_RE: Final = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
PORT_LINE_RE: Final = re.compile(r"^(PORT_[0-3])\s*=\s*([0-9]+)\s*(?:#.*)?$")


@dataclass(frozen=True)
class ServiceDefinition:
    index: int
    name: str
    description: str

    @property
    def environment_key(self) -> str:
        return f"PORT_{self.index}"


SERVICES: Final[tuple[ServiceDefinition, ...]] = (
    ServiceDefinition(0, "evaluation", "Evaluation dashboard"),
    ServiceDefinition(1, "revenuecat-webhook", "RevenueCat sandbox webhook receiver"),
    ServiceDefinition(2, "test-patterns", "Original test-pattern server"),
    ServiceDefinition(3, "artifacts", "Build and artifact metadata server"),
)
SERVICE_BY_NAME: Final = {service.name: service for service in SERVICES}


class DevContractError(RuntimeError):
    """A requested action would violate or cannot prove the dev-server contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class OperationDeadline:
    """One monotonic absolute deadline shared by every phase of an operation."""

    expires_at: float
    timeout_code: str
    timeout_message: str
    cancelled: Any | None = None
    cancellation_code: str = "operation_cancelled"
    cancellation_message: str = "operation was cancelled"

    def remaining(self, maximum_seconds: float | None = None) -> float:
        if self.cancelled is not None and self.cancelled.is_set():
            raise DevContractError(self.cancellation_code, self.cancellation_message)
        remaining = self.expires_at - time.monotonic()
        if remaining <= 0:
            raise DevContractError(self.timeout_code, self.timeout_message)
        if maximum_seconds is not None:
            return min(remaining, maximum_seconds)
        return remaining

    def check(self) -> None:
        self.remaining()


def _deadline_after(
    timeout_seconds: float,
    *,
    timeout_code: str,
    timeout_message: str,
    cancelled: Any | None = None,
    cancellation_code: str = "operation_cancelled",
    cancellation_message: str = "operation was cancelled",
) -> OperationDeadline:
    return OperationDeadline(
        expires_at=time.monotonic() + timeout_seconds,
        timeout_code=timeout_code,
        timeout_message=timeout_message,
        cancelled=cancelled,
        cancellation_code=cancellation_code,
        cancellation_message=cancellation_message,
    )


def _check_deadline(deadline: OperationDeadline | None) -> None:
    if deadline is not None:
        deadline.check()


def _bounded_timeout(deadline: OperationDeadline | None, maximum_seconds: float) -> float:
    if deadline is None:
        return maximum_seconds
    return deadline.remaining(maximum_seconds)


@dataclass(frozen=True)
class PortConfiguration:
    ports: Mapping[str, int]

    def for_service(self, service: ServiceDefinition) -> int:
        return self.ports[service.environment_key]


@dataclass(frozen=True)
class PidRecord:
    schema_version: int
    repository: str
    repo_root: str
    pid: int
    service: str
    host: str
    port: int
    instance_token: str
    script: str
    log_file: str
    started_at: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repository": self.repository,
            "repo_root": self.repo_root,
            "pid": self.pid,
            "service": self.service,
            "host": self.host,
            "port": self.port,
            "instance_token": self.instance_token,
            "script": self.script,
            "log_file": self.log_file,
            "started_at": self.started_at,
        }


@dataclass(frozen=True)
class Listener:
    pid: int | None
    command: str
    endpoint: str


@dataclass(frozen=True)
class PreflightState:
    configuration: PortConfiguration
    active_records: Mapping[str, PidRecord]


@dataclass(frozen=True)
class SpawnedService:
    record: PidRecord
    process: subprocess.Popen[bytes]


class RedirectRefusingHandler(urlrequest.HTTPRedirectHandler):
    """Turn every HTTP redirect into an error instead of forwarding credentials."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        return None


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_ports_file(path: Path) -> PortConfiguration:
    """Parse ports.env as data, never by sourcing shell code."""

    if path.is_symlink():
        raise DevContractError("ports_file_symlink", "ports.env may not be a symlink")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise DevContractError("ports_file_unreadable", "ports.env must be readable UTF-8") from error
    values: dict[str, int] = {}
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = PORT_LINE_RE.fullmatch(line)
        if match is None:
            raise DevContractError(
                "ports_file_invalid",
                f"ports.env line {line_number} is not an allowed PORT_0..PORT_3 assignment",
            )
        key, value_text = match.groups()
        if key in values:
            raise DevContractError("ports_file_duplicate_key", f"ports.env repeats {key}")
        values[key] = int(value_text)

    expected_keys = {service.environment_key for service in SERVICES}
    if set(values) != expected_keys:
        missing = ", ".join(sorted(expected_keys - set(values))) or "none"
        raise DevContractError("ports_file_missing_key", f"ports.env is missing required keys: {missing}")
    if len(set(values.values())) != len(values):
        raise DevContractError("ports_file_duplicate_port", "every allocated service port must be unique")
    for key, port in values.items():
        if port not in PORT_BLOCK:
            raise DevContractError(
                "port_outside_block", f"{key}={port} is outside the exclusive {PORT_MIN}-{PORT_MAX} block"
            )
    return PortConfiguration(values)


def _ensure_real_directory(path: Path, mode: int = 0o700) -> None:
    if path.exists() and path.is_symlink():
        raise DevContractError("dev_directory_symlink", f"refusing symlink at {path}")
    try:
        path.mkdir(mode=mode, parents=True, exist_ok=True)
        file_stat = path.stat()
    except OSError as error:
        raise DevContractError("dev_directory_unavailable", f"cannot create {path}") from error
    if not stat.S_ISDIR(file_stat.st_mode):
        raise DevContractError("dev_directory_invalid", f"{path} is not a directory")
    try:
        path.chmod(mode)
    except OSError as error:
        raise DevContractError("dev_directory_permissions", f"cannot secure {path}") from error


def ensure_dev_directories(root: Path) -> None:
    dev = root / ".dev"
    _ensure_real_directory(dev)
    for name in ("pids", "logs", "tmp", "cache", "pw-profile"):
        _ensure_real_directory(dev / name)
    storage_state = dev / "pw-profile" / "storage-state.json"
    if storage_state.is_symlink():
        raise DevContractError("playwright_state_symlink", "refusing symlink Playwright storage state")
    if not storage_state.exists():
        temporary = storage_state.with_name(f".storage-state.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        temporary.write_text('{"cookies":[],"origins":[]}\n', encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, storage_state)
    try:
        state_stat = storage_state.stat()
        state_document = json.loads(storage_state.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DevContractError(
            "playwright_state_invalid", "Playwright storage state must be valid local JSON"
        ) from error
    if (
        not stat.S_ISREG(state_stat.st_mode)
        or state_stat.st_size > 1_048_576
        or not isinstance(state_document, dict)
        or not isinstance(state_document.get("cookies"), list)
        or not isinstance(state_document.get("origins"), list)
    ):
        raise DevContractError(
            "playwright_state_invalid", "Playwright storage state does not have cookies/origins arrays"
        )


def dev_is_git_ignored(
    root: Path, *, deadline: OperationDeadline | None = None
) -> bool:
    timeout_seconds = _bounded_timeout(deadline, GIT_IGNORE_CHECK_TIMEOUT_SECONDS)
    try:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", "--", ".dev/preflight-probe"],
            cwd=root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        _check_deadline(deadline)
        raise DevContractError(
            "git_ignore_check_failed", "git check-ignore exceeded its bounded inspection time"
        ) from error
    except (OSError, subprocess.SubprocessError) as error:
        raise DevContractError("git_ignore_check_failed", "could not verify .dev/ with git check-ignore") from error
    _check_deadline(deadline)
    return result.returncode == 0


def pid_path(root: Path, service_name: str) -> Path:
    if service_name not in SERVICE_BY_NAME:
        raise DevContractError("service_unknown", f"unknown service {service_name}")
    return root / ".dev" / "pids" / f"{service_name}.json"


def _parse_pid_document(document: Any, root: Path, expected_service: str) -> PidRecord:
    required = {
        "schema_version",
        "repository",
        "repo_root",
        "pid",
        "service",
        "host",
        "port",
        "instance_token",
        "script",
        "log_file",
        "started_at",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise DevContractError("pid_record_schema_invalid", f"PID record for {expected_service} has invalid keys")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise DevContractError("pid_record_schema_invalid", f"PID record for {expected_service} has invalid version")
    if document["repository"] != REPOSITORY_NAME:
        raise DevContractError("pid_record_repository_mismatch", f"PID record for {expected_service} has wrong owner")
    if document["repo_root"] != str(root.resolve()):
        raise DevContractError("pid_record_root_mismatch", f"PID record for {expected_service} points elsewhere")
    if type(document["pid"]) is not int or document["pid"] <= 1:
        raise DevContractError("pid_record_pid_invalid", f"PID record for {expected_service} has invalid PID")
    if document["service"] != expected_service or expected_service not in SERVICE_BY_NAME:
        raise DevContractError("pid_record_service_mismatch", f"PID record for {expected_service} has wrong service")
    if document["host"] != BIND_HOST:
        raise DevContractError("pid_record_host_mismatch", f"PID record for {expected_service} is not loopback-only")
    if type(document["port"]) is not int or document["port"] not in PORT_BLOCK:
        raise DevContractError("pid_record_port_invalid", f"PID record for {expected_service} has invalid port")
    token = document["instance_token"]
    if not isinstance(token, str) or INSTANCE_TOKEN_RE.fullmatch(token) is None:
        raise DevContractError("pid_record_token_invalid", f"PID record for {expected_service} has invalid token")
    expected_script = str((root / "scripts" / "dev_service.py").resolve())
    if document["script"] != expected_script:
        raise DevContractError("pid_record_script_mismatch", f"PID record for {expected_service} has wrong script")
    expected_log = str((root / ".dev" / "logs" / f"{expected_service}.log").absolute())
    if document["log_file"] != expected_log:
        raise DevContractError("pid_record_log_mismatch", f"PID record for {expected_service} has wrong log path")
    if not isinstance(document["started_at"], str) or len(document["started_at"]) > 64:
        raise DevContractError("pid_record_time_invalid", f"PID record for {expected_service} has invalid timestamp")
    return PidRecord(**document)


def read_pid_record(root: Path, service_name: str) -> PidRecord | None:
    """Read one bounded PID record through a no-follow file descriptor."""

    path = pid_path(root, service_name)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as error:
        code = "pid_record_symlink" if error.errno in {errno.ELOOP, errno.EMLINK} else "pid_record_unreadable"
        raise DevContractError(code, f"refusing unsafe PID record for {service_name}") from error
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > MAX_PID_RECORD_BYTES:
            raise DevContractError(
                "pid_record_file_invalid",
                f"PID record for {service_name} is not a bounded regular file",
            )
        chunks: list[bytes] = []
        remaining = MAX_PID_RECORD_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(8_192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > MAX_PID_RECORD_BYTES:
            raise DevContractError(
                "pid_record_file_invalid", f"PID record for {service_name} exceeds its size bound"
            )
    finally:
        os.close(descriptor)
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DevContractError(
            "pid_record_unreadable", f"PID record for {service_name} is invalid JSON"
        ) from error
    return _parse_pid_document(document, root, service_name)


def write_pid_record(root: Path, record: PidRecord) -> None:
    destination = pid_path(root, record.service)
    if destination.exists() or destination.is_symlink():
        raise DevContractError("pid_record_exists", f"refusing to overwrite PID record for {record.service}")
    temporary = destination.with_name(f".{record.service}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        encoded = (json.dumps(record.to_document(), sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        view = memoryview(encoded)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short PID record write")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, destination)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        with contextlib.suppress(OSError):
            temporary.unlink()
        raise


def remove_pid_record_if_same(root: Path, record: PidRecord) -> None:
    current = read_pid_record(root, record.service)
    if current is None:
        return
    if current.pid != record.pid or current.instance_token != record.instance_token:
        raise DevContractError(
            "pid_record_changed", f"PID record for {record.service} changed while operating; refusing removal"
        )
    pid_path(root, record.service).unlink()


def process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_arguments(
    pid: int, *, deadline: OperationDeadline | None = None
) -> list[str] | None:
    _check_deadline(deadline)
    proc_path = Path("/proc") / str(pid) / "cmdline"
    if proc_path.is_file():
        try:
            content = proc_path.read_bytes()
            _check_deadline(deadline)
            return [item.decode("utf-8", errors="strict") for item in content.split(b"\0") if item]
        except (OSError, UnicodeDecodeError):
            return None
    timeout_seconds = _bounded_timeout(deadline, PROCESS_INSPECTION_TIMEOUT_SECONDS)
    try:
        result = subprocess.run(
            ["ps", "-ww", "-p", str(pid), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        _check_deadline(deadline)
        return None
    except (OSError, subprocess.SubprocessError):
        return None
    _check_deadline(deadline)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return shlex.split(result.stdout.strip())
    except ValueError:
        return None


def _option(arguments: Sequence[str], name: str) -> str | None:
    for index, item in enumerate(arguments):
        if item == name and index + 1 < len(arguments):
            return arguments[index + 1]
        prefix = name + "="
        if item.startswith(prefix):
            return item[len(prefix) :]
    return None


def process_matches_record(
    record: PidRecord,
    arguments: Sequence[str] | None = None,
    *,
    deadline: OperationDeadline | None = None,
) -> bool:
    _check_deadline(deadline)
    args = process_arguments(record.pid, deadline=deadline) if arguments is None else list(arguments)
    if not args or record.script not in args:
        return False
    matches = (
        _option(args, "--service") == record.service
        and _option(args, "--host") == record.host
        and _option(args, "--port") == str(record.port)
        and _option(args, "--repo-root") == record.repo_root
        and _option(args, "--instance-token") == record.instance_token
        and _option(args, "--log-file") == record.log_file
    )
    _check_deadline(deadline)
    return matches


def lsof_executable() -> str | None:
    """Return the explicitly required listener-inspection executable, if available."""

    located = shutil.which("lsof")
    if located is not None:
        return located
    fallback = Path("/usr/sbin/lsof")
    return str(fallback) if fallback.is_file() else None


def discover_listeners_for_ports(
    ports: Sequence[int], *, deadline: OperationDeadline | None = None
) -> dict[int, list[Listener]]:
    """Identify every TCP listener on block ports in one bounded lsof snapshot."""

    inspected = tuple(ports)
    if not inspected or any(port not in PORT_BLOCK for port in inspected):
        raise DevContractError("port_probe_invalid", "listener inspection is limited to the exclusive port block")
    discovered: dict[int, list[Listener]] = {port: [] for port in inspected}
    lsof = lsof_executable()
    if lsof is None:
        raise DevContractError(
            "lsof_unavailable",
            "lsof is required to prove listener ownership across IPv4 and IPv6; refusing preflight",
        )
    port_selector = (
        str(inspected[0])
        if len(inspected) == 1
        else f"{min(inspected)}-{max(inspected)}"
    )
    timeout_seconds = _bounded_timeout(deadline, LISTENER_INSPECTION_TIMEOUT_SECONDS)
    try:
        result = subprocess.run(
            [lsof, "-nP", "-a", f"-iTCP:{port_selector}", "-sTCP:LISTEN", "-Fpctn"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        _check_deadline(deadline)
        raise DevContractError(
            "lsof_failed", f"listener inspection exceeded its bound on ports {port_selector}"
        ) from error
    except (OSError, subprocess.SubprocessError) as error:
        raise DevContractError("lsof_failed", f"could not identify listeners on ports {port_selector}") from error
    _check_deadline(deadline)
    if result.returncode not in (0, 1):
        raise DevContractError("lsof_failed", f"lsof failed while inspecting ports {port_selector}")
    current_pid: int | None = None
    current_command = "unknown"
    for line in result.stdout.splitlines():
        if not line:
            continue
        field, value = line[0], line[1:]
        if field == "p":
            current_pid = int(value) if value.isdigit() else None
            current_command = "unknown"
        elif field == "c":
            current_command = value[:128]
        elif field == "n":
            match = re.search(r":([0-9]+)(?:\s|$|->)", value)
            if match is None:
                continue
            port = int(match.group(1))
            if port in discovered:
                discovered[port].append(Listener(current_pid, current_command, value[:256]))
    _check_deadline(deadline)
    return discovered


def discover_listeners(
    port: int, *, deadline: OperationDeadline | None = None
) -> list[Listener]:
    """Identify every TCP listener on one block port."""

    return discover_listeners_for_ports((port,), deadline=deadline)[port]


def _record_map(
    root: Path, *, deadline: OperationDeadline | None = None
) -> dict[str, PidRecord]:
    _check_deadline(deadline)
    pids_dir = root / ".dev" / "pids"
    expected_names = {f"{service.name}.json" for service in SERVICES}
    for entry in pids_dir.iterdir():
        _check_deadline(deadline)
        if entry.name.startswith("."):
            continue
        if entry.name not in expected_names:
            raise DevContractError("unknown_pid_record", f"unexpected file in .dev/pids: {entry.name}")
    records: dict[str, PidRecord] = {}
    for service in SERVICES:
        _check_deadline(deadline)
        record = read_pid_record(root, service.name)
        _check_deadline(deadline)
        if record is None:
            continue
        _check_deadline(deadline)
        if not process_is_alive(record.pid):
            _check_deadline(deadline)
            remove_pid_record_if_same(root, record)
            _check_deadline(deadline)
            continue
        _check_deadline(deadline)
        if not process_matches_record(record, deadline=deadline):
            raise DevContractError(
                "pid_ownership_unproven",
                f"PID {record.pid} from {service.name} record does not match its unique instance token; refusing it",
            )
        records[service.name] = record
    _check_deadline(deadline)
    return records


def preflight(
    root: Path, *, deadline: OperationDeadline | None = None
) -> PreflightState:
    _check_deadline(deadline)
    if root.resolve().name != REPOSITORY_NAME:
        raise DevContractError("repository_mismatch", f"devctl must run in the {REPOSITORY_NAME} checkout")
    _check_deadline(deadline)
    configuration = parse_ports_file(root / "ports.env")
    _check_deadline(deadline)
    ensure_dev_directories(root)
    _check_deadline(deadline)
    if not dev_is_git_ignored(root, deadline=deadline):
        raise DevContractError("dev_not_ignored", ".dev/ is not ignored by Git")
    _check_deadline(deadline)
    records = _record_map(root, deadline=deadline)
    records_by_pid = {record.pid: record for record in records.values()}
    foreign: list[str] = []
    listeners_by_port = discover_listeners_for_ports(PORT_BLOCK, deadline=deadline)
    for port in PORT_BLOCK:
        for listener in listeners_by_port[port]:
            record = records_by_pid.get(listener.pid) if listener.pid is not None else None
            loopback_endpoint = listener.endpoint.startswith(f"{BIND_HOST}:")
            if record is None or record.port != port or not loopback_endpoint:
                foreign.append(
                    f"port {port} held by pid={listener.pid or 'unknown'} command={listener.command} endpoint={listener.endpoint}"
                )
    if foreign:
        raise DevContractError(
            "foreign_port_holder",
            "foreign listener(s) detected; no process was killed: " + "; ".join(foreign),
        )
    _check_deadline(deadline)
    return PreflightState(configuration, records)


@contextlib.contextmanager
def controller_lock(
    root: Path, *, deadline: OperationDeadline | None = None
) -> Iterator[None]:
    _check_deadline(deadline)
    ensure_dev_directories(root)
    _check_deadline(deadline)
    lock_path = root / ".dev" / "devctl.lock"
    if lock_path.is_symlink():
        raise DevContractError("controller_lock_symlink", "refusing symlink controller lock")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    acquired = False
    try:
        while not acquired:
            _check_deadline(deadline)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise DevContractError(
                        "controller_lock_failed", "could not acquire the devctl controller lock"
                    ) from error
                sleep_seconds = CONTROLLER_LOCK_POLL_SECONDS
                if deadline is not None:
                    sleep_seconds = min(sleep_seconds, deadline.remaining())
                time.sleep(sleep_seconds)
        _check_deadline(deadline)
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        _check_deadline(deadline)
        yield
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def sanitized_service_environment(root: Path) -> dict[str, str]:
    """Build a deterministic allowlisted environment for local service children."""

    temporary_root = root / ".dev" / "tmp"
    service_home = temporary_root / "service-home"
    _ensure_real_directory(temporary_root)
    _ensure_real_directory(service_home)
    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": str(service_home),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
        "TMPDIR": str(temporary_root),
    }


def _terminate_spawned_child(process: subprocess.Popen[bytes]) -> None:
    """Terminate only a still-owned Popen child; never signal a record-derived PID."""

    deadline = _deadline_after(
        STOP_TIMEOUT_SECONDS,
        timeout_code="spawn_cleanup_timeout",
        timeout_message=(
            f"newly spawned child pid {process.pid} did not exit within its total cleanup deadline; "
            "no unchecked PID escalation was sent"
        ),
    )
    deadline.check()
    if process.poll() is not None:
        return
    deadline.check()
    process.terminate()
    try:
        process.wait(timeout=deadline.remaining())
    except subprocess.TimeoutExpired as error:
        raise DevContractError(
            "spawn_cleanup_timeout",
            f"newly spawned child pid {process.pid} did not exit; no unchecked PID escalation was sent",
        ) from error


def spawn_service(root: Path, service: ServiceDefinition, port: int) -> SpawnedService:
    script = str((root / "scripts" / "dev_service.py").resolve())
    token = uuid.uuid4().hex
    log_path = (root / ".dev" / "logs" / f"{service.name}.log").absolute()
    if log_path.is_symlink():
        raise DevContractError("log_symlink", f"refusing symlink log at {log_path}")
    for backup_index in range(1, 4):
        backup = Path(f"{log_path}.{backup_index}")
        if backup.is_symlink():
            raise DevContractError("log_symlink", f"refusing symlink log backup at {backup}")
    command = [
        sys.executable,
        "-u",
        script,
        "--service",
        service.name,
        "--host",
        BIND_HOST,
        "--port",
        str(port),
        "--repo-root",
        str(root.resolve()),
        "--instance-token",
        token,
        "--log-file",
        str(log_path),
    ]
    environment = sanitized_service_environment(root)
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as error:
        raise DevContractError("service_spawn_failed", f"could not start {service.name}") from error
    record = PidRecord(
        schema_version=1,
        repository=REPOSITORY_NAME,
        repo_root=str(root.resolve()),
        pid=process.pid,
        service=service.name,
        host=BIND_HOST,
        port=port,
        instance_token=token,
        script=script,
        log_file=str(log_path),
        started_at=utc_now(),
    )
    try:
        write_pid_record(root, record)
    except BaseException:
        _terminate_spawned_child(process)
        raise
    return SpawnedService(record, process)


def open_loopback_request(request: urlrequest.Request, timeout: float) -> Any:
    """Open an exact loopback URL without proxies or redirect following."""

    parsed = urlsplit(request.full_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != BIND_HOST
        or parsed.port not in PORT_BLOCK
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise DevContractError("loopback_url_invalid", "request URL is outside the owned loopback block")
    opener = urlrequest.build_opener(urlrequest.ProxyHandler({}), RedirectRefusingHandler())
    try:
        response = opener.open(request, timeout=timeout)
    except urlerror.HTTPError as error:
        if error.geturl() != request.full_url or 300 <= error.code < 400:
            error.close()
            raise DevContractError(
                "loopback_redirect_refused",
                "loopback request attempted an HTTP redirect or changed its exact URL",
            ) from error
        raise
    if response.geturl() != request.full_url:
        response.close()
        raise DevContractError("loopback_final_url_mismatch", "loopback response final URL changed")
    return response


def readiness_probe(
    record: PidRecord, *, deadline: OperationDeadline | None = None
) -> tuple[bool, str]:
    request_timeout = _bounded_timeout(deadline, READINESS_REQUEST_TIMEOUT_SECONDS)
    request = urlrequest.Request(
        f"http://{BIND_HOST}:{record.port}/health/ready",
        headers={"Accept": "application/json", "Connection": "close"},
        method="GET",
    )
    try:
        with open_loopback_request(request, timeout=request_timeout) as response:
            if response.status != 200:
                return False, f"HTTP {response.status}"
            content_type = response.headers.get_content_type()
            if content_type != "application/json":
                return False, f"unexpected content type {content_type}"
            body = response.read(MAX_HEALTH_BYTES + 1)
    except urlerror.HTTPError as error:
        _check_deadline(deadline)
        return False, f"HTTP {error.code}"
    except DevContractError as error:
        _check_deadline(deadline)
        return False, f"{error.code}: exact loopback URL check failed"
    except (urlerror.URLError, TimeoutError, OSError):
        _check_deadline(deadline)
        return False, "readiness endpoint unavailable"
    _check_deadline(deadline)
    if len(body) > MAX_HEALTH_BYTES:
        return False, "readiness response exceeds size limit"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, "readiness response is not UTF-8 JSON"
    if not isinstance(payload, dict):
        return False, "readiness response is not an object"
    expected = {
        "schema_version": 1,
        "service": record.service,
        "bind_host": record.host,
        "port": record.port,
        "instance_token_sha256": hashlib.sha256(record.instance_token.encode("ascii")).hexdigest(),
        "readiness_scope": "local_development_surface",
        "production_verified": False,
        "ready": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            return False, f"readiness field {key} did not match the owned process"
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        return False, "readiness checks are missing"
    if record.service == "revenuecat-webhook":
        verification = checks.get("provider_verification")
        if not isinstance(verification, dict) or verification.get("verified") is not False:
            return False, "receiver must state that provider delivery is unverified"
    if record.service == "test-patterns" and checks.get("timing_calibrated") is not False:
        return False, "test-pattern timing calibration must not be implied"
    _check_deadline(deadline)
    return True, "ready"


def wait_for_record_health(
    record: PidRecord,
    timeout_seconds: float,
    *,
    cancelled: Any | None = None,
    deadline: OperationDeadline | None = None,
) -> None:
    if deadline is None:
        deadline = _deadline_after(
            timeout_seconds,
            timeout_code="health_timeout",
            timeout_message=f"{record.service} readiness did not pass within {timeout_seconds:g}s",
            cancelled=cancelled,
            cancellation_code="health_cancelled",
            cancellation_message=f"readiness cancelled for {record.service}",
        )
    detail = "not checked"
    while True:
        deadline.check()
        if not process_is_alive(record.pid):
            deadline.check()
            detail = "process exited"
        elif not process_matches_record(record, deadline=deadline):
            detail = "process ownership could not be proven"
        else:
            ready, detail = readiness_probe(record, deadline=deadline)
            if ready:
                return
        time.sleep(min(0.1, deadline.remaining()))


def wait_for_health(
    root: Path,
    configuration: PortConfiguration,
    timeout_seconds: float,
    *,
    require_every_record: bool = True,
    deadline: OperationDeadline | None = None,
) -> dict[str, str]:
    if deadline is None:
        deadline = _deadline_after(
            timeout_seconds,
            timeout_code="health_timeout",
            timeout_message=f"readiness did not pass within {timeout_seconds:g}s",
        )
    pending = {service.name for service in SERVICES}
    details: dict[str, str] = {}
    while pending:
        deadline.check()
        for service in SERVICES:
            if service.name not in pending:
                continue
            deadline.check()
            try:
                record = read_pid_record(root, service.name)
            except DevContractError as error:
                if error.code in {deadline.timeout_code, deadline.cancellation_code}:
                    raise
                details[service.name] = f"{error.code}: {error}"
                continue
            deadline.check()
            if record is None:
                details[service.name] = "PID record missing"
                if not require_every_record:
                    pending.remove(service.name)
                continue
            expected_port = configuration.for_service(service)
            if record.port != expected_port:
                details[service.name] = f"PID record uses {record.port}, expected {expected_port}"
                continue
            if not process_is_alive(record.pid):
                deadline.check()
                details[service.name] = "process exited"
                continue
            if not process_matches_record(record, deadline=deadline):
                details[service.name] = "process ownership could not be proven"
                continue
            ready, detail = readiness_probe(record, deadline=deadline)
            details[service.name] = detail
            if ready:
                pending.remove(service.name)
        if pending:
            time.sleep(min(0.1, deadline.remaining()))
    return details


def request_owned_shutdown(record: PidRecord, *, timeout_seconds: float) -> None:
    request = urlrequest.Request(
        f"http://{BIND_HOST}:{record.port}/__devctl/shutdown",
        data=b"",
        headers={
            "Accept": "application/json",
            "Connection": "close",
            DEVCTL_TOKEN_HEADER: record.instance_token,
        },
        method="POST",
    )
    try:
        with open_loopback_request(request, timeout=timeout_seconds) as response:
            if response.status != 202:
                raise DevContractError(
                    "stop_shutdown_refused",
                    f"{record.service} refused authenticated self-shutdown with HTTP {response.status}",
                )
            if response.headers.get_content_type() != "application/json":
                raise DevContractError(
                    "stop_shutdown_refused",
                    f"{record.service} returned a non-JSON shutdown response",
                )
            body = response.read(MAX_HEALTH_BYTES + 1)
    except urlerror.HTTPError as error:
        raise DevContractError(
            "stop_shutdown_refused",
            f"{record.service} refused authenticated self-shutdown with HTTP {error.code}",
        ) from error
    except DevContractError as error:
        raise DevContractError(
            "stop_shutdown_refused",
            f"{record.service} shutdown response changed its exact loopback URL",
        ) from error
    except (urlerror.URLError, TimeoutError, OSError) as error:
        raise DevContractError(
            "stop_shutdown_unavailable",
            f"{record.service} authenticated self-shutdown endpoint was unavailable; no signal was sent",
        ) from error
    if len(body) > MAX_HEALTH_BYTES:
        raise DevContractError("stop_shutdown_refused", "shutdown response exceeded its size limit")
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DevContractError("stop_shutdown_refused", "shutdown response was not UTF-8 JSON") from error
    expected_digest = hashlib.sha256(record.instance_token.encode("ascii")).hexdigest()
    if not isinstance(document, dict) or any(
        (
            document.get("schema_version") != 1,
            document.get("service") != record.service,
            document.get("instance_token_sha256") != expected_digest,
            document.get("shutdown_requested") is not True,
        )
    ):
        raise DevContractError(
            "stop_shutdown_refused",
            f"{record.service} shutdown response did not prove the owned instance",
        )


def _service_stop_deadline(
    service_name: str, parent_deadline: OperationDeadline | None
) -> OperationDeadline:
    started_at = time.monotonic()
    expires_at = started_at + STOP_TIMEOUT_SECONDS
    if parent_deadline is not None:
        expires_at = min(expires_at, parent_deadline.expires_at)
    return OperationDeadline(
        expires_at=expires_at,
        timeout_code="stop_timeout",
        timeout_message=(
            f"owned service {service_name} did not complete authenticated shutdown "
            "within its total deadline; no unchecked PID escalation was sent"
        ),
    )


def _process_alive_with_deadline(pid: int, deadline: OperationDeadline) -> bool:
    deadline.check()
    alive = process_is_alive(pid)
    deadline.check()
    return alive


def stop_owned_record(
    root: Path,
    record: PidRecord,
    *,
    parent_deadline: OperationDeadline | None = None,
) -> None:
    deadline = _service_stop_deadline(record.service, parent_deadline)
    if not _process_alive_with_deadline(record.pid, deadline):
        deadline.check()
        remove_pid_record_if_same(root, record)
        return
    if not process_matches_record(record, deadline=deadline):
        raise DevContractError(
            "stop_ownership_unproven",
            f"refusing shutdown for PID {record.pid}; ownership token for {record.service} does not match",
        )
    request_timeout = deadline.remaining(SHUTDOWN_REQUEST_TIMEOUT_SECONDS)
    request_owned_shutdown(record, timeout_seconds=request_timeout)
    deadline.check()
    while deadline.remaining() > STOP_FINAL_IDENTITY_RESERVE_SECONDS:
        if not _process_alive_with_deadline(record.pid, deadline):
            deadline.check()
            remove_pid_record_if_same(root, record)
            return
        wait_budget = deadline.remaining() - STOP_FINAL_IDENTITY_RESERVE_SECONDS
        if wait_budget > 0:
            time.sleep(min(0.05, wait_budget))
    if not _process_alive_with_deadline(record.pid, deadline):
        deadline.check()
        remove_pid_record_if_same(root, record)
        return
    final_arguments = process_arguments(record.pid, deadline=deadline)
    if final_arguments is not None and not process_matches_record(
        record, final_arguments, deadline=deadline
    ):
        raise DevContractError(
            "stop_pid_reused",
            f"PID {record.pid} identity changed after self-shutdown; no signal was sent",
        )
    raise DevContractError(
        "stop_timeout",
        f"owned service {record.service} did not self-terminate; no unchecked PID escalation was sent",
    )


def stop_spawned_service(
    root: Path,
    spawned: SpawnedService,
    *,
    parent_deadline: OperationDeadline | None = None,
) -> None:
    """Stop and reap a Popen child retained by the current controller."""

    record, process = spawned.record, spawned.process
    deadline = _service_stop_deadline(record.service, parent_deadline)
    deadline.check()
    if process.poll() is not None:
        deadline.check()
        remove_pid_record_if_same(root, record)
        return
    deadline.check()
    if not process_matches_record(record, deadline=deadline):
        raise DevContractError(
            "stop_ownership_unproven",
            f"retained child PID {record.pid} no longer matches {record.service}",
        )
    request_timeout = deadline.remaining(SHUTDOWN_REQUEST_TIMEOUT_SECONDS)
    request_owned_shutdown(record, timeout_seconds=request_timeout)
    deadline.check()
    remaining = deadline.remaining()
    wait_budget = max(0.0, remaining - STOP_FINAL_IDENTITY_RESERVE_SECONDS)
    try:
        if wait_budget <= 0:
            raise subprocess.TimeoutExpired(cmd=record.script, timeout=0.0)
        process.wait(timeout=wait_budget)
    except subprocess.TimeoutExpired as error:
        deadline.check()
        if process.poll() is not None:
            deadline.check()
            remove_pid_record_if_same(root, record)
            return
        deadline.check()
        final_arguments = process_arguments(record.pid, deadline=deadline)
        if final_arguments is not None and not process_matches_record(
            record, final_arguments, deadline=deadline
        ):
            raise DevContractError(
                "stop_pid_reused",
                f"retained child PID {record.pid} identity changed; no signal was sent",
            ) from error
        raise DevContractError(
            "stop_timeout",
            f"owned child {record.service} did not self-terminate; no PID signal escalation was sent",
        ) from error
    deadline.check()
    remove_pid_record_if_same(root, record)


def command_preflight(root: Path) -> None:
    with controller_lock(root):
        state = preflight(root)
    print(
        f"dev:preflight ok: .dev/ is isolated and ports {PORT_MIN}-{PORT_MAX} have no foreign listeners"
    )
    for service in SERVICES:
        print(f"  {service.name}: {BIND_HOST}:{state.configuration.for_service(service)}")


def command_up(root: Path, timeout_seconds: float) -> None:
    deadline = _deadline_after(
        timeout_seconds,
        timeout_code="up_timeout",
        timeout_message=f"dev:up did not complete within its total {timeout_seconds:g}s deadline",
    )
    started: list[SpawnedService] = []
    with controller_lock(root, deadline=deadline):
        try:
            state = preflight(root, deadline=deadline)
            # Reconcile only this repository's specifically identified processes if ports.env changed.
            for service in SERVICES:
                deadline.check()
                existing = state.active_records.get(service.name)
                if existing is not None:
                    expected_port = state.configuration.for_service(service)
                    ready, _detail = readiness_probe(existing, deadline=deadline)
                    if existing.port != expected_port or not ready:
                        stop_owned_record(root, existing, parent_deadline=deadline)
            for service in SERVICES:
                deadline.check()
                existing = read_pid_record(root, service.name)
                deadline.check()
                if existing is not None:
                    continue
                spawned = spawn_service(
                    root, service, state.configuration.for_service(service)
                )
                started.append(spawned)
                deadline.check()
            wait_for_health(
                root, state.configuration, timeout_seconds, deadline=deadline
            )
            deadline.check()
            records = []
            for service in SERVICES:
                deadline.check()
                records.append(read_pid_record(root, service.name))
                deadline.check()
        except BaseException:
            for spawned in reversed(started):
                with contextlib.suppress(DevContractError, OSError):
                    stop_spawned_service(root, spawned, parent_deadline=deadline)
            raise
    print("dev:up ok: every allocated service returned its owned readiness document")
    for record in records:
        if record is not None:
            print(f"  {record.service}: pid {record.pid}, http://{record.host}:{record.port}")


def command_health(root: Path, timeout_seconds: float) -> None:
    deadline = _deadline_after(
        timeout_seconds,
        timeout_code="health_timeout",
        timeout_message=f"dev:health did not complete within its total {timeout_seconds:g}s deadline",
    )
    deadline.check()
    configuration = parse_ports_file(root / "ports.env")
    deadline.check()
    details = wait_for_health(
        root, configuration, timeout_seconds, deadline=deadline
    )
    print("dev:health ok: all services are ready (TCP acceptance alone was not used)")
    for service in SERVICES:
        print(f"  {service.name}: {details[service.name]}")


def command_down(
    root: Path, timeout_seconds: float = DEFAULT_DOWN_TIMEOUT_SECONDS
) -> None:
    deadline = _deadline_after(
        timeout_seconds,
        timeout_code="down_timeout",
        timeout_message=f"dev:down did not complete within its total {timeout_seconds:g}s deadline",
    )
    stopped: list[tuple[str, int]] = []
    errors: list[str] = []
    with controller_lock(root, deadline=deadline):
        # PID records are the sole authority; listener discovery is deliberately not used to kill.
        for service in SERVICES:
            try:
                deadline.check()
                record = read_pid_record(root, service.name)
                deadline.check()
                if record is None:
                    continue
                stop_owned_record(root, record, parent_deadline=deadline)
                deadline.check()
                stopped.append((record.service, record.pid))
            except (DevContractError, OSError) as error:
                errors.append(f"{service.name}: {error}")
                if isinstance(error, DevContractError) and error.code == deadline.timeout_code:
                    break
    for service_name, pid in stopped:
        print(f"  stopped {service_name} pid {pid}")
    if errors:
        raise DevContractError(
            "down_incomplete",
            "one or more services did not complete authenticated self-shutdown: "
            + "; ".join(errors),
        )
    print("dev:down ok: only authenticated repository-owned services self-stopped")


def command_e2e_server(root: Path, timeout_seconds: float) -> None:
    """Own the complete service block for one Playwright coordinator lifecycle."""

    startup_expires_at = time.monotonic() + timeout_seconds
    stop_requested = threading.Event()
    startup_deadline = OperationDeadline(
        expires_at=startup_expires_at,
        timeout_code="e2e_start_timeout",
        timeout_message=f"E2E service startup did not complete within {timeout_seconds:g}s",
        cancelled=stop_requested,
        cancellation_code="e2e_start_cancelled",
        cancellation_message="E2E service startup was cancelled",
    )
    previous_handlers: dict[int, Any] = {}

    def handle_stop(_signum: int, _frame: Any) -> None:
        stop_requested.set()

    for signal_number in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[signal_number] = signal.getsignal(signal_number)
        signal.signal(signal_number, handle_stop)

    spawned_services: list[SpawnedService] = []
    cleanup_errors: list[str] = []
    try:
        startup_deadline.check()
        with controller_lock(root, deadline=startup_deadline):
            state = preflight(root, deadline=startup_deadline)
            if state.active_records:
                active = ", ".join(sorted(state.active_records))
                raise DevContractError(
                    "e2e_existing_service",
                    f"Playwright refuses to reuse already-running owned services: {active}",
                )
            def remaining_startup_seconds() -> float:
                return startup_deadline.remaining()

            # The Playwright readiness URL is on test-patterns. Start and prove the
            # other three services first so that 4222 cannot become a false gate.
            ordered_services = tuple(
                service for service in SERVICES if service.name != "test-patterns"
            ) + (SERVICE_BY_NAME["test-patterns"],)
            for service in ordered_services:
                remaining_startup_seconds()
                spawned = spawn_service(
                    root, service, state.configuration.for_service(service)
                )
                spawned_services.append(spawned)
                startup_deadline.check()
                wait_for_record_health(
                    spawned.record,
                    remaining_startup_seconds(),
                    cancelled=stop_requested,
                    deadline=startup_deadline,
                )
                startup_deadline.check()

        print("dev:e2e-server ready: all four owned services passed semantic readiness", flush=True)
        while not stop_requested.wait(0.1):
            for spawned in spawned_services:
                return_code = spawned.process.poll()
                if return_code is not None:
                    raise DevContractError(
                        "e2e_service_exited",
                        f"{spawned.record.service} exited unexpectedly with status {return_code}",
                    )
    finally:
        try:
            if spawned_services:
                cleanup_deadline = _deadline_after(
                    E2E_CLEANUP_TIMEOUT_SECONDS,
                    timeout_code="e2e_cleanup_timeout",
                    timeout_message=(
                        "E2E cleanup did not complete within its total "
                        f"{E2E_CLEANUP_TIMEOUT_SECONDS:g}s deadline"
                    ),
                )
                try:
                    with controller_lock(root, deadline=cleanup_deadline):
                        for spawned in reversed(spawned_services):
                            try:
                                cleanup_deadline.check()
                                stop_spawned_service(
                                    root,
                                    spawned,
                                    parent_deadline=cleanup_deadline,
                                )
                                cleanup_deadline.check()
                            except (DevContractError, OSError) as error:
                                cleanup_errors.append(f"{spawned.record.service}: {error}")
                except (DevContractError, OSError) as error:
                    cleanup_errors.append(f"controller-lock: {error}")
        finally:
            for signal_number, previous in previous_handlers.items():
                signal.signal(signal_number, previous)
    if cleanup_errors:
        raise DevContractError(
            "e2e_cleanup_incomplete",
            "E2E service cleanup was incomplete: " + "; ".join(cleanup_errors),
        )
    print("dev:e2e-server stopped: all four owned services self-stopped", flush=True)


def positive_bounded_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout must be numeric") from error
    if not 0.1 <= parsed <= 120.0:
        raise argparse.ArgumentTypeError("timeout must be between 0.1 and 120 seconds")
    return parsed


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight", help="validate namespace isolation and all block ports")
    up_parser = subparsers.add_parser("up", help="start every allocated service")
    up_parser.add_argument("--timeout", type=positive_bounded_float, default=DEFAULT_HEALTH_TIMEOUT_SECONDS)
    down_parser = subparsers.add_parser("down", help="stop only validated repository-owned PIDs")
    down_parser.add_argument(
        "--timeout", type=positive_bounded_float, default=DEFAULT_DOWN_TIMEOUT_SECONDS
    )
    health_parser = subparsers.add_parser("health", help="poll semantic readiness for every service")
    health_parser.add_argument(
        "--timeout", type=positive_bounded_float, default=DEFAULT_HEALTH_TIMEOUT_SECONDS
    )
    e2e_parser = subparsers.add_parser(
        "e2e-server", help="own all four services for one Playwright lifecycle"
    )
    e2e_parser.add_argument(
        "--timeout", type=positive_bounded_float, default=DEFAULT_HEALTH_TIMEOUT_SECONDS
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(sys.argv[1:] if argv is None else argv)
    root = repository_root()
    try:
        if arguments.command == "preflight":
            command_preflight(root)
        elif arguments.command == "up":
            command_up(root, arguments.timeout)
        elif arguments.command == "down":
            command_down(root, arguments.timeout)
        elif arguments.command == "health":
            command_health(root, arguments.timeout)
        elif arguments.command == "e2e-server":
            command_e2e_server(root, arguments.timeout)
        else:  # pragma: no cover - argparse prevents this branch.
            raise DevContractError("command_unknown", f"unknown command {arguments.command}")
    except DevContractError as error:
        print(f"dev:{arguments.command} failed [{error.code}]: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
