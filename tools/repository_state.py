#!/usr/bin/env python3
"""Capture and compare repository state around the canonical verification run.

Tracked and untracked source content is immutable during verification. Generated
state may change only inside the repository-local ignored namespaces enumerated
below; each ignored path is recorded in the snapshot rather than silently
disappearing behind ``git status``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
MAX_GIT_LIST_BYTES = 64 * 1024 * 1024
MAX_GIT_COMMAND_SECONDS = 30
MAX_TRACKED_PATHS = 50_000
MAX_UNTRACKED_PATHS = 50_000
MAX_IGNORED_PATHS = 250_000
MAX_INDEX_ENTRIES = 100_000
MAX_SOURCE_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 2 * 1024 * 1024 * 1024
IGNORED_NAMESPACE_ROOTS = (
    ".build",
    ".dev",
    ".swiftpm",
    "DerivedData",
    "node_modules",
    "playwright-report",
    "test-results",
)
REPOSITORY_LOCAL_NAMESPACE_PATHS = (
    PurePosixPath(".dev"),
    PurePosixPath(".dev/artifacts"),
    PurePosixPath(".dev/cache"),
    PurePosixPath(".dev/cache/ms-playwright"),
    PurePosixPath(".dev/cache/npm"),
    PurePosixPath(".dev/logs"),
    PurePosixPath(".dev/pids"),
    PurePosixPath(".dev/playwright-results"),
    PurePosixPath(".dev/pw-profile"),
    PurePosixPath(".dev/tmp"),
)


class RepositoryStateError(RuntimeError):
    """The repository cannot be snapshotted or changed during verification."""


def terminate_git_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


def git_bytes(root: Path, *arguments: str) -> bytes:
    try:
        process = subprocess.Popen(
            ["git", *arguments],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as error:
        raise RepositoryStateError(f"git {' '.join(arguments)} failed: {error}") from error
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    payload = bytearray()
    deadline = time.monotonic() + MAX_GIT_COMMAND_SECONDS
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                terminate_git_process(process)
                raise RepositoryStateError(
                    f"git {' '.join(arguments)} exceeded {MAX_GIT_COMMAND_SECONDS} seconds"
                )
            events = selector.select(remaining)
            if not events:
                terminate_git_process(process)
                raise RepositoryStateError(
                    f"git {' '.join(arguments)} exceeded {MAX_GIT_COMMAND_SECONDS} seconds"
                )
            chunk = os.read(process.stdout.fileno(), 64 * 1024)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > MAX_GIT_LIST_BYTES:
                terminate_git_process(process)
                raise RepositoryStateError(
                    f"git {' '.join(arguments)} output exceeds byte limit {MAX_GIT_LIST_BYTES}"
                )
        return_code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired as error:
        terminate_git_process(process)
        raise RepositoryStateError(
            f"git {' '.join(arguments)} exceeded {MAX_GIT_COMMAND_SECONDS} seconds"
        ) from error
    finally:
        selector.close()
        process.stdout.close()
    if return_code != 0:
        raise RepositoryStateError(
            f"git {' '.join(arguments)} exited with status {return_code}"
        )
    return bytes(payload)


def decode_git_paths(payload: bytes, *, label: str, max_paths: int) -> list[str]:
    paths: list[str] = []
    start = 0
    while start < len(payload):
        end = payload.find(b"\0", start)
        if end == -1:
            end = len(payload)
        if end > start:
            paths.append(os.fsdecode(payload[start:end]))
            if len(paths) > max_paths:
                raise RepositoryStateError(
                    f"{label} path count exceeds limit {max_paths}"
                )
        start = end + 1
    return paths


def sha256_file(path: Path, *, label: str, relative: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    total_bytes = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            total_bytes += len(chunk)
            if total_bytes > MAX_SOURCE_FILE_BYTES:
                raise RepositoryStateError(
                    f"{label} file exceeds per-file byte limit {MAX_SOURCE_FILE_BYTES}: {relative}"
                )
            digest.update(chunk)
    return digest.hexdigest(), total_bytes


def path_record(root: Path, relative: str, *, label: str) -> dict[str, Any]:
    path = root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing", "mode": None, "sha256": None, "size_bytes": None}

    mode = f"{stat.S_IMODE(metadata.st_mode):04o}"
    if stat.S_ISLNK(metadata.st_mode):
        target = os.fsencode(os.readlink(path))
        return {
            "kind": "symlink",
            "mode": mode,
            "sha256": hashlib.sha256(target).hexdigest(),
            "size_bytes": len(target),
        }
    if stat.S_ISREG(metadata.st_mode):
        if metadata.st_size > MAX_SOURCE_FILE_BYTES:
            raise RepositoryStateError(
                f"{label} file exceeds per-file byte limit {MAX_SOURCE_FILE_BYTES}: {relative}"
            )
        digest, bytes_read = sha256_file(path, label=label, relative=relative)
        if bytes_read != metadata.st_size:
            raise RepositoryStateError(f"{label} file changed size while hashing: {relative}")
        return {
            "kind": "file",
            "mode": mode,
            "sha256": digest,
            "size_bytes": bytes_read,
        }
    if stat.S_ISDIR(metadata.st_mode):
        return {"kind": "directory", "mode": mode, "sha256": None, "size_bytes": 0}
    raise RepositoryStateError(f"unsupported filesystem object: {relative}")


def ignored_path_record(root: Path, relative: str) -> dict[str, Any]:
    """Inventory ignored state without hashing large generated binaries."""

    path = root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing", "size_bytes": None}
    if stat.S_ISLNK(metadata.st_mode):
        return {"kind": "symlink", "size_bytes": len(os.fsencode(os.readlink(path)))}
    if stat.S_ISREG(metadata.st_mode):
        return {"kind": "file", "size_bytes": metadata.st_size}
    if stat.S_ISDIR(metadata.st_mode):
        return {"kind": "directory", "size_bytes": 0}
    raise RepositoryStateError(f"unsupported ignored filesystem object: {relative}")


def classify_ignored_path(relative: str) -> str | None:
    """Return the explicit generated-state class for an ignored path."""

    parts = PurePosixPath(relative).parts
    if not parts:
        return None
    root_name = parts[0]
    root_categories = {
        ".build": "swift-build",
        ".dev": "repository-local-dev-state",
        ".swiftpm": "swiftpm-metadata",
        "node_modules": "locked-node-install",
        "playwright-report": "playwright-report",
        "test-results": "test-results",
    }
    if root_name in root_categories:
        return root_categories[root_name]
    if "DerivedData" in parts:
        return "xcode-derived-data"
    if "xcuserdata" in parts:
        return "xcode-user-data"
    if "__pycache__" in parts or relative.endswith((".pyc", ".pyo")):
        return "python-bytecode"
    if parts[-1] == ".DS_Store":
        return "macos-metadata"
    return None


def content_records(
    root: Path, paths: list[str], *, label: str, byte_budget: int
) -> tuple[dict[str, dict[str, Any]], int]:
    records: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    for relative in sorted(paths):
        record = path_record(root, relative, label=label)
        size = record.get("size_bytes")
        if isinstance(size, int):
            total_bytes += size
        if total_bytes > byte_budget:
            raise RepositoryStateError(
                f"tracked and untracked source bytes exceed total limit {MAX_TOTAL_SOURCE_BYTES}"
            )
        records[relative] = record
    return records, total_bytes


def validate_ignored_namespace_roots(root: Path) -> None:
    for name in IGNORED_NAMESPACE_ROOTS:
        path = root / name
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RepositoryStateError(
                f"ignored namespace root must be a real repository-local directory: {name}"
            )
    for relative in REPOSITORY_LOCAL_NAMESPACE_PATHS:
        path = root / relative
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RepositoryStateError(
                "repository-local writable namespace must be a real directory: " + str(relative)
            )


def capture_repository(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    validate_ignored_namespace_roots(root)
    tracked_paths = decode_git_paths(
        git_bytes(root, "ls-files", "-z"),
        label="tracked",
        max_paths=MAX_TRACKED_PATHS,
    )
    untracked_paths = decode_git_paths(
        git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z"),
        label="untracked",
        max_paths=MAX_UNTRACKED_PATHS,
    )
    ignored_paths = decode_git_paths(
        git_bytes(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"),
        label="ignored",
        max_paths=MAX_IGNORED_PATHS,
    )

    ignored_inventory: list[dict[str, Any]] = []
    for relative in sorted(ignored_paths):
        category = classify_ignored_path(relative)
        if category is None:
            raise RepositoryStateError(
                "ignored path is outside the generated-state allowlist: " + relative
            )
        ignored_inventory.append(
            {"path": relative, "category": category, **ignored_path_record(root, relative)}
        )

    index_payload = git_bytes(root, "ls-files", "--stage", "-z")
    index_entry_count = index_payload.count(b"\0")
    if index_entry_count > MAX_INDEX_ENTRIES:
        raise RepositoryStateError(
            f"index entry count exceeds limit {MAX_INDEX_ENTRIES}"
        )
    tracked_records, tracked_bytes = content_records(
        root,
        tracked_paths,
        label="tracked",
        byte_budget=MAX_TOTAL_SOURCE_BYTES,
    )
    untracked_records, untracked_bytes = content_records(
        root,
        untracked_paths,
        label="untracked",
        byte_budget=MAX_TOTAL_SOURCE_BYTES - tracked_bytes,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "repository_root": str(root),
        "tracked_worktree": tracked_records,
        "index_sha256": hashlib.sha256(index_payload).hexdigest(),
        "index_entry_count": index_entry_count,
        "source_bytes": tracked_bytes + untracked_bytes,
        "untracked_worktree": untracked_records,
        "ignored_inventory": ignored_inventory,
    }


def changed_paths(
    before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]
) -> list[str]:
    paths = sorted(set(before) | set(after))
    return [path for path in paths if before.get(path) != after.get(path)]


def compare_repository_states(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if before.get("schema_version") != SCHEMA_VERSION:
        failures.append("baseline snapshot has an unsupported schema version")
    if after.get("schema_version") != SCHEMA_VERSION:
        failures.append("after snapshot has an unsupported schema version")
    if before.get("repository_root") != after.get("repository_root"):
        failures.append("snapshot repository roots differ")
    if before.get("index_sha256") != after.get("index_sha256"):
        failures.append("Git index content changed")

    tracked = changed_paths(
        before.get("tracked_worktree", {}), after.get("tracked_worktree", {})
    )
    if tracked:
        failures.append("tracked worktree content changed: " + ", ".join(tracked))
    untracked = changed_paths(
        before.get("untracked_worktree", {}), after.get("untracked_worktree", {})
    )
    if untracked:
        failures.append("untracked worktree content changed: " + ", ".join(untracked))
    return failures


def write_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise RepositoryStateError(f"snapshot output may not be a symlink: {path}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    payload = (json.dumps(snapshot, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
    except OSError as error:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise RepositoryStateError(f"cannot write snapshot {path}: {error}") from error


def read_snapshot(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise RepositoryStateError(f"baseline snapshot may not be a symlink: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RepositoryStateError(f"cannot read baseline snapshot {path}: {error}") from error
    if not isinstance(value, dict):
        raise RepositoryStateError(f"baseline snapshot must be a JSON object: {path}")
    return value


def ignored_summary(snapshot: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for entry in snapshot.get("ignored_inventory", []):
        category = str(entry["category"])
        counts[category] = counts.get(category, 0) + 1
    return ",".join(f"{category}:{counts[category]}" for category in sorted(counts)) or "none"


def repository_relative_output(raw_path: Path) -> Path:
    output = Path(os.path.abspath(ROOT / raw_path))
    if output == ROOT or ROOT not in output.parents:
        raise RepositoryStateError("snapshot output must remain inside the repository")
    current = ROOT
    relative = output.relative_to(ROOT)
    for component in relative.parts[:-1]:
        current = current / component
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RepositoryStateError(
                f"snapshot parent must be a real repository-local directory: {current}"
            )
    if output.is_symlink():
        raise RepositoryStateError(f"snapshot output may not be a symlink: {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--output", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--before", type=Path, required=True)
    compare_parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "capture":
            output = repository_relative_output(args.output)
            snapshot = capture_repository()
            write_snapshot(output, snapshot)
            print(
                "repository-state:capture:ok "
                f"tracked={len(snapshot['tracked_worktree'])} "
                f"untracked={len(snapshot['untracked_worktree'])} "
                f"ignored={ignored_summary(snapshot)}"
            )
            return 0

        before_path = repository_relative_output(args.before)
        after_path = repository_relative_output(args.after)
        before = read_snapshot(before_path)
        after = capture_repository()
        write_snapshot(after_path, after)
        failures = compare_repository_states(before, after)
        if failures:
            print("repository-state:error", file=sys.stderr)
            for failure in failures:
                print(f"- {failure}", file=sys.stderr)
            return 1
        print(
            "repository-state:compare:ok tracked-content=stable index=stable "
            f"untracked-content=stable ignored-before={ignored_summary(before)} "
            f"ignored-after={ignored_summary(after)}"
        )
        return 0
    except RepositoryStateError as error:
        print(f"repository-state:error:{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
