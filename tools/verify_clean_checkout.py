#!/usr/bin/env python3
"""Run the canonical gate from a bounded detached clean worktree."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TIMEOUT_SECONDS = 1_200
TERMINATION_GRACE_SECONDS = 10


class CleanVerificationError(RuntimeError):
    """The clean-check harness cannot safely proceed."""


class VerificationTimeout(CleanVerificationError):
    def __init__(self, timeout_seconds: float, output: str) -> None:
        super().__init__(f"canonical verification exceeded {timeout_seconds:g} seconds")
        self.timeout_seconds = timeout_seconds
        self.output = output


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str


def command_output(root: Path, *command: str) -> str:
    try:
        return subprocess.run(
            command,
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise CleanVerificationError(f"command failed ({' '.join(command)}): {error}") from error


def require_clean_source(root: Path = ROOT) -> None:
    status = command_output(
        root,
        "git",
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status:
        preview = " | ".join(status.splitlines()[:10])
        raise CleanVerificationError(
            "source repository has staged, unstaged, or untracked changes; "
            f"commit/reconcile them before clean verification ({preview})"
        )


def terminate_process_group(
    process: subprocess.Popen[str], grace_seconds: float = TERMINATION_GRACE_SECONDS
) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError as error:
        raise CleanVerificationError(f"cannot terminate verification process group: {error}") from error

    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=grace_seconds)


def run_bounded(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout_seconds: float,
    termination_grace_seconds: float = TERMINATION_GRACE_SECONDS,
) -> CommandResult:
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    except OSError as error:
        raise CleanVerificationError(f"cannot start {' '.join(command)}: {error}") from error

    try:
        output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        terminate_process_group(process, termination_grace_seconds)
        output, _ = process.communicate(timeout=termination_grace_seconds)
        raise VerificationTimeout(timeout_seconds, output) from None
    except BaseException:
        terminate_process_group(process, termination_grace_seconds)
        raise
    return CommandResult(returncode=process.returncode, output=output)


def positive_seconds(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout must be an integer") from error
    if not 1 <= value <= 1_800:
        raise argparse.ArgumentTypeError("timeout must be between 1 and 1800 seconds")
    return value


def clean_environment(worktree: Path, revision: str) -> dict[str, str]:
    environment = os.environ.copy()
    for variable in ("GNUMAKEFLAGS", "MAKEFLAGS", "MAKELEVEL", "MAKEOVERRIDES", "MFLAGS"):
        environment.pop(variable, None)
    environment.update(
        {
            "CLEAN_CHECKOUT": "1",
            "SOURCE_COMMIT": revision,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(worktree),
            "NPM_CONFIG_CACHE": str(worktree / ".dev" / "cache" / "npm"),
            "npm_config_cache": str(worktree / ".dev" / "cache" / "npm"),
            "PLAYWRIGHT_BROWSERS_PATH": str(worktree / ".dev" / "cache" / "ms-playwright"),
            "TMPDIR": str(worktree / ".dev" / "tmp"),
        }
    )
    return environment


def append_output(lines: list[str], output: str) -> None:
    if output:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
        lines.extend(output.rstrip("\n").splitlines())


def stop_worktree_services(
    worktree: Path, environment: dict[str, str], timeout_seconds: float = 30
) -> str | None:
    controller = worktree / "scripts" / "devctl.py"
    if not controller.is_file():
        return "detached worktree has no ownership-safe service controller"
    try:
        result = run_bounded(
            [sys.executable, "scripts/devctl.py", "down"],
            cwd=worktree,
            environment=environment,
            timeout_seconds=timeout_seconds,
        )
    except CleanVerificationError as error:
        return f"detached service shutdown failed: {error}"
    if result.returncode != 0:
        return (
            f"detached service shutdown exited {result.returncode}: {result.output.strip()}"
        )
    return None


def cleanup_worktree(
    root: Path, worktree: Path, environment: dict[str, str]
) -> list[str]:
    failures: list[str] = []
    shutdown_failure = stop_worktree_services(worktree, environment)
    if shutdown_failure is not None:
        return [shutdown_failure + f"; retained worktree and PID evidence at {worktree}"]

    try:
        result = run_bounded(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=root,
            timeout_seconds=60,
        )
        if result.returncode != 0:
            failures.append(
                f"git worktree remove exited {result.returncode}: {result.output.strip()}"
            )
    except CleanVerificationError as error:
        failures.append(str(error))

    if worktree.exists():
        try:
            shutil.rmtree(worktree)
        except OSError as error:
            failures.append(f"cannot remove worktree directory: {error}")

    try:
        result = run_bounded(
            ["git", "worktree", "prune"], cwd=root, timeout_seconds=30
        )
        if result.returncode != 0:
            failures.append(f"git worktree prune exited {result.returncode}: {result.output.strip()}")
    except CleanVerificationError as error:
        failures.append(str(error))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/tier0/verify-all-clean.txt"),
        help="repository-relative evidence path",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=positive_seconds,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="hard deadline for make verify-all",
    )
    args = parser.parse_args()
    output_path = (ROOT / args.output).resolve()
    if output_path == ROOT or ROOT not in output_path.parents:
        parser.error("--output must remain inside the repository")

    try:
        require_clean_source()
        revision = command_output(ROOT, "git", "rev-parse", "HEAD")
    except CleanVerificationError as error:
        print(f"clean-verify:error:{error}", file=sys.stderr)
        return 1
    if re.fullmatch(r"[0-9a-f]{40,64}", revision) is None:
        print("clean-verify:error:invalid HEAD revision", file=sys.stderr)
        return 1

    worktree_parent = ROOT / ".dev" / "tmp"
    worktree = Path(tempfile.mkdtemp(prefix=f"clean-{revision[:12]}-", dir=worktree_parent))
    shutil.rmtree(worktree)
    timestamp = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    command = ["make", "verify-all"]
    environment = clean_environment(worktree, revision)

    lines = [
        "# Clean-checkout verification evidence",
        f"generated_at={timestamp}",
        f"source_commit={revision}",
        "source_precondition=clean (no staged, unstaged, or untracked paths)",
        "dirty_tree=false (detached worktree)",
        "seed=not-applicable (deterministic suites declare their own seeds)",
        "command=make verify-all",
        f"timeout_seconds={args.timeout_seconds}",
        "--- output ---",
    ]
    exit_code = 1
    worktree_added = False
    try:
        add_result = run_bounded(
            ["git", "worktree", "add", "--detach", str(worktree), revision],
            cwd=ROOT,
            timeout_seconds=60,
        )
        if add_result.returncode != 0:
            raise CleanVerificationError(
                f"git worktree add exited {add_result.returncode}: {add_result.output.strip()}"
            )
        worktree_added = True
        result = run_bounded(
            command,
            cwd=worktree,
            environment=environment,
            timeout_seconds=args.timeout_seconds,
        )
        append_output(lines, result.output)
        exit_code = result.returncode
        lines.append(f"exit_code={exit_code}")
    except VerificationTimeout as error:
        append_output(lines, error.output)
        exit_code = 124
        lines.append(f"harness_timeout_seconds={error.timeout_seconds:g}")
        lines.append(f"exit_code={exit_code}")
        print(f"clean-verify:error:{error}", file=sys.stderr)
    except KeyboardInterrupt:
        exit_code = 130
        lines.extend(("harness_error=KeyboardInterrupt", f"exit_code={exit_code}"))
        print("clean-verify:error:interrupted", file=sys.stderr)
    except CleanVerificationError as error:
        lines.extend((f"harness_error={type(error).__name__}: {error}", "exit_code=1"))
        print(f"clean-verify:error:{error}", file=sys.stderr)
    finally:
        cleanup_failures: list[str] = []
        if worktree_added:
            cleanup_failures.extend(cleanup_worktree(ROOT, worktree, environment))
        else:
            if worktree.exists():
                try:
                    shutil.rmtree(worktree)
                except OSError as error:
                    cleanup_failures.append(f"cannot remove incomplete worktree: {error}")
            try:
                prune_result = run_bounded(
                    ["git", "worktree", "prune"], cwd=ROOT, timeout_seconds=30
                )
                if prune_result.returncode != 0:
                    cleanup_failures.append(
                        "git worktree prune exited "
                        f"{prune_result.returncode}: {prune_result.output.strip()}"
                    )
            except CleanVerificationError as error:
                cleanup_failures.append(str(error))
        for cleanup_failure in cleanup_failures:
            lines.append(f"cleanup_error={cleanup_failure}")
            print(f"clean-verify:cleanup-error:{cleanup_failure}", file=sys.stderr)
        if cleanup_failures and exit_code == 0:
            exit_code = 1
            lines.append("exit_code=1 (cleanup failure overrides verification success)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(output_path)

    if exit_code != 0:
        print(f"clean-verify:failed evidence={output_path.relative_to(ROOT)}", file=sys.stderr)
        return exit_code
    print(
        f"clean-verify:ok source_commit={revision} evidence={output_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
