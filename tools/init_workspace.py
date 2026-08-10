#!/usr/bin/env python3
"""Create repository-local writable namespaces without following symlinks."""

from __future__ import annotations

import os
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
WRITABLE_DIRECTORIES = (
    PurePosixPath(".dev/cache/npm"),
    PurePosixPath(".dev/cache/ms-playwright"),
    PurePosixPath(".dev/tmp"),
    PurePosixPath(".dev/logs"),
)


class WorkspaceInitializationError(RuntimeError):
    """A writable namespace is unsafe or cannot be initialized."""


def ensure_directory_without_symlinks(root: Path, relative: PurePosixPath) -> None:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise WorkspaceInitializationError(f"unsafe writable path: {relative}")

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(root, flags)
    except OSError as error:
        raise WorkspaceInitializationError(f"repository root is not a safe directory: {error}") from error

    try:
        for component in relative.parts:
            try:
                os.mkdir(component, mode=0o700, dir_fd=directory_fd)
            except FileExistsError:
                pass
            except OSError as error:
                raise WorkspaceInitializationError(
                    f"cannot create writable directory {relative}: {error}"
                ) from error

            try:
                child_fd = os.open(component, flags, dir_fd=directory_fd)
            except OSError as error:
                raise WorkspaceInitializationError(
                    f"writable path component is a symlink or non-directory: {relative}"
                ) from error
            os.close(directory_fd)
            directory_fd = child_fd
    finally:
        os.close(directory_fd)


def initialize_workspace(root: Path = ROOT) -> None:
    for relative in WRITABLE_DIRECTORIES:
        ensure_directory_without_symlinks(root, relative)


def main() -> int:
    try:
        initialize_workspace()
    except WorkspaceInitializationError as error:
        print(f"workspace-init:error:{error}", file=sys.stderr)
        return 1
    print("workspace-init:ok writable_scope=.dev cache=npm,playwright tmp=repository-local")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
