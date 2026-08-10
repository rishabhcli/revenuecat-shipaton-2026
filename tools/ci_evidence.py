#!/usr/bin/env python3
"""Record the exact hosted verification result for one commit, or refuse.

A green local run proves nothing about the hosted clean-checkout contract, and a
run URL pasted into a document is not regenerable.  This tool asks GitHub for the
verification runs of one exact commit and writes an artifact only when a single
completed run for that commit succeeded on the required workflow.  Every other
state, including "still running", is a refusal with a stable code.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Sequence


ROOT: Final = Path(__file__).resolve().parent.parent
REQUIRED_WORKFLOW_PATH: Final = ".github/workflows/verify.yml"
REQUIRED_WORKFLOW_NAME: Final = "verify"
COMMIT_RE: Final = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE: Final = re.compile(r"^[A-Za-z0-9._-]{1,100}/[A-Za-z0-9._-]{1,100}$")
GIT_TIMEOUT_SECONDS: Final = 10.0
API_TIMEOUT_SECONDS: Final = 60.0
MAX_API_BYTES: Final = 4_194_304
RECORDED_FIELDS: Final = (
    "id",
    "name",
    "path",
    "head_sha",
    "head_branch",
    "event",
    "status",
    "conclusion",
    "run_attempt",
    "html_url",
    "created_at",
    "updated_at",
)


class EvidenceError(RuntimeError):
    """The hosted verification result could not be proven for this commit."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_bounded(command: Sequence[str], *, timeout_seconds: float) -> str:
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise EvidenceError("command_timeout", f"{command[0]} exceeded {timeout_seconds:g}s") from error
    except (OSError, subprocess.SubprocessError) as error:
        raise EvidenceError("command_unavailable", f"could not run {command[0]}") from error
    if completed.returncode != 0:
        raise EvidenceError(
            "command_failed",
            f"{command[0]} exited {completed.returncode}: {completed.stderr.strip()[:200]}",
        )
    if len(completed.stdout) > MAX_API_BYTES:
        raise EvidenceError("response_too_large", f"{command[0]} returned an unbounded response")
    return completed.stdout


def resolve_commit(reference: str) -> str:
    if COMMIT_RE.fullmatch(reference):
        return reference
    resolved = run_bounded(
        ["git", "rev-parse", "--verify", f"{reference}^{{commit}}"],
        timeout_seconds=GIT_TIMEOUT_SECONDS,
    ).strip()
    if not COMMIT_RE.fullmatch(resolved):
        raise EvidenceError("commit_unresolved", f"{reference} is not a full commit identifier")
    return resolved


def repository_slug() -> str:
    slug = run_bounded(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        timeout_seconds=API_TIMEOUT_SECONDS,
    ).strip()
    if not REPOSITORY_RE.fullmatch(slug):
        raise EvidenceError("repository_unresolved", "could not identify the hosted repository")
    return slug


def verification_runs(slug: str, commit: str) -> list[dict[str, Any]]:
    payload = run_bounded(
        ["gh", "api", f"repos/{slug}/actions/runs?head_sha={commit}&per_page=100"],
        timeout_seconds=API_TIMEOUT_SECONDS,
    )
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise EvidenceError("response_invalid", "the runs response was not valid JSON") from error
    runs = document.get("workflow_runs") if isinstance(document, dict) else None
    if not isinstance(runs, list):
        raise EvidenceError("response_invalid", "the runs response had no workflow_runs array")
    return [
        run
        for run in runs
        if isinstance(run, dict)
        and run.get("path") == REQUIRED_WORKFLOW_PATH
        and run.get("name") == REQUIRED_WORKFLOW_NAME
        and run.get("head_sha") == commit
    ]


def select_successful_run(runs: Sequence[dict[str, Any]], commit: str) -> dict[str, Any]:
    if not runs:
        raise EvidenceError(
            "run_absent", f"no {REQUIRED_WORKFLOW_PATH} run exists for commit {commit}"
        )
    incomplete = [run for run in runs if run.get("status") != "completed"]
    if incomplete:
        raise EvidenceError(
            "run_incomplete",
            f"{len(incomplete)} verification run(s) for {commit} have not completed",
        )
    failed = [run for run in runs if run.get("conclusion") != "success"]
    if failed:
        conclusions = ", ".join(sorted({str(run.get("conclusion")) for run in failed}))
        raise EvidenceError(
            "run_not_successful",
            f"verification for {commit} concluded {conclusions}",
        )
    return max(runs, key=lambda run: (int(run.get("run_attempt") or 0), int(run.get("id") or 0)))


def render(commit: str, slug: str, run: dict[str, Any], run_count: int) -> str:
    lines = [
        "# Hosted clean-checkout verification evidence",
        f"generated_at={utc_now()}",
        f"command=make ci-evidence COMMIT={commit}",
        f"repository={slug}",
        f"source_commit={commit}",
        f"required_workflow={REQUIRED_WORKFLOW_PATH}",
        f"matching_runs={run_count}",
        "scope=hosted repository verification contract only "
        "(not app, device, provider, or production evidence)",
        "--- run ---",
    ]
    for field in RECORDED_FIELDS:
        lines.append(f"{field}={run.get(field)}")
    return "\n".join(lines) + "\n"


def write_artifact(output: Path, content: str) -> None:
    if output.is_symlink():
        raise EvidenceError("output_symlink", f"refusing symlink output at {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence" / "tier0" / "ci-verify.txt")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(sys.argv[1:] if argv is None else argv)
    try:
        commit = resolve_commit(arguments.commit)
        slug = repository_slug()
        runs = verification_runs(slug, commit)
        run = select_successful_run(runs, commit)
        write_artifact(arguments.output, render(commit, slug, run, len(runs)))
    except EvidenceError as error:
        print(f"ci-evidence:error [{error.code}] {error}", file=sys.stderr)
        return 2
    print(f"ci-evidence:ok commit={commit} run={run.get('id')} path={arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
