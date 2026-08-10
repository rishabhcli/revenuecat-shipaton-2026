#!/usr/bin/env python3
"""Validate the pinned local toolchain without modifying global state."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class BootstrapError(RuntimeError):
    """Raised when the executable contract cannot be satisfied."""


def require_lsof() -> str:
    """Require the listener-inspection tool used by fail-closed dev preflight."""

    located = shutil.which("lsof")
    if located is None:
        fallback = Path("/usr/sbin/lsof")
        located = str(fallback) if fallback.is_file() else None
    if located is None:
        raise BootstrapError("lsof is required for fail-closed local listener ownership checks")
    return located


def run(*command: str) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise BootstrapError(f"tool check failed: {' '.join(command)}: {error}") from error
    return f"{completed.stdout}\n{completed.stderr}".strip()


def semantic_version(text: str, label: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if match is None:
        raise BootstrapError(f"could not parse {label} version from {text!r}")
    return tuple(int(value or 0) for value in match.groups())


def validate() -> list[str]:
    facts: list[str] = []

    lsof_path = require_lsof()
    facts.append(f"lsof={lsof_path}")

    python_version = sys.version_info[:3]
    if not ((3, 11, 0) <= python_version < (3, 15, 0)):
        raise BootstrapError(
            f"Python 3.11 through 3.14 is required, found {sys.version.split()[0]}"
        )
    facts.append(f"python={sys.version.split()[0]}")

    swift_output = run("xcrun", "swift", "--version")
    swift_version = semantic_version(swift_output, "Swift")
    if swift_version[0] != 6:
        raise BootstrapError(f"Swift language toolchain major 6 is required, found {swift_version}")
    facts.append(f"swift={'.'.join(map(str, swift_version))}")

    xcode_output = run("xcodebuild", "-version")
    xcode_version = semantic_version(xcode_output, "Xcode")
    if xcode_version[0] < 26:
        raise BootstrapError(f"Xcode 26 or newer is required, found {xcode_version}")
    facts.append(f"xcode={'.'.join(map(str, xcode_version))}")

    format_output = run("xcrun", "swift-format", "--version")
    if not format_output:
        raise BootstrapError("xcrun swift-format returned no version identifier")
    facts.append(f"swift-format={format_output.splitlines()[0]}")

    metal_path = run("xcrun", "--find", "metal")
    if not Path(metal_path).is_file():
        raise BootstrapError(f"Metal compiler is not installed at reported path {metal_path!r}")
    facts.append("metal-toolchain=installed")

    declared_swift = (ROOT / ".swift-version").read_text(encoding="utf-8").strip()
    if semantic_version(declared_swift, ".swift-version")[0] != 6:
        raise BootstrapError(".swift-version must declare Swift major 6")

    expected_node = (ROOT / ".node-version").read_text(encoding="utf-8").strip()
    node_output = run("node", "--version").lstrip("v")
    if semantic_version(node_output, "Node") != semantic_version(expected_node, ".node-version"):
        raise BootstrapError(
            f"Node {expected_node} is required by .node-version, found {node_output}"
        )
    facts.append(f"node={node_output}")

    npm_output = run("npm", "--version")
    npm_version = semantic_version(npm_output, "npm")
    if npm_version[0] != 11:
        raise BootstrapError(f"npm major 11 is required, found {npm_output}")
    facts.append(f"npm={npm_output}")

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    if lock.get("lockfileVersion") != 3:
        raise BootstrapError("package-lock.json must use lockfileVersion 3")
    if lock.get("packages", {}).get("", {}).get("devDependencies") != package.get(
        "devDependencies"
    ):
        raise BootstrapError("package.json and package-lock.json direct dependencies differ")
    facts.append("npm-lock=consistent")

    return facts


def main() -> int:
    try:
        facts = validate()
    except (BootstrapError, json.JSONDecodeError, OSError) as error:
        print(f"bootstrap:error:{error}", file=sys.stderr)
        return 1
    print("bootstrap:ok " + " ".join(facts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
