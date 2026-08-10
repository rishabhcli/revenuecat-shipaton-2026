#!/usr/bin/env python3
"""Enforce repository, writable-scope, architecture, and supply-chain boundaries."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = {
    ".github/workflows/verify.yml",
    ".gitignore",
    "AGENTS.md",
    "ASSUMPTIONS.md",
    "BLOCKED.md",
    "GOAL.md",
    "HACKATHON.md",
    "Makefile",
    "Package.swift",
    "PROGRESS.md",
    "README.md",
    "SUPPORT_MATRIX.md",
    "WINNING_IDEA.md",
    "adr/0001-toolchain-and-module-boundaries.md",
    "adr/0002-local-development-services-threat-model.md",
    "docs/dependency-register.md",
    "evidence/README.md",
    "package-lock.json",
    "package.json",
    "playwright.config.ts",
    "ports.env",
    "tools/repository_state.py",
    "tools/init_workspace.py",
    "tools/verify_clean_checkout.py",
}
EXPECTED_PORTS = {"PORT_0": 4220, "PORT_1": 4221, "PORT_2": 4222, "PORT_3": 4223}
FORBIDDEN_RUNTIME_PORTS = {3000, 3001, 4200, 5000, 5173, 5432, 6379, 8000, 8080, 9000, 9090}
APP_ONLY_NAME_MARKERS = ("Adapter", "Application", "Cloud", "Provider", "Transport")
ALLOWED_FOUNDATION_IMPORTS = {"Swift", "_Concurrency"}
ALLOWED_TEST_IMPORTS = {"Swift", "_Concurrency", "XCTest"}
EXPECTED_FOUNDATION_DEPENDENCIES = {
    "CaptureDomain": set(),
    "RuntimeConfiguration": {"CaptureDomain"},
    "CameraDomain": {"CaptureDomain"},
    "AnalysisDomain": {"CaptureDomain", "CameraDomain"},
    "MetalDomain": {"CaptureDomain"},
    "PurchasesDomain": {"CaptureDomain"},
    "ExportDomain": {"CaptureDomain", "MetalDomain", "PurchasesDomain"},
    "EvaluationDomain": {"CaptureDomain"},
    "UIDomain": {"CaptureDomain", "AnalysisDomain", "PurchasesDomain"},
}
EXPECTED_TEST_DEPENDENCIES = {
    "FoundationPropertyTests": set(EXPECTED_FOUNDATION_DEPENDENCIES),
}
REQUIRED_STRICT_SWIFT_FLAGS = {
    "-warnings-as-errors",
    "-strict-concurrency=complete",
    "-warn-concurrency",
}
IMPORT_DECLARATION = re.compile(
    r"(?:^|;)[ \t]*(?:(?:@[_A-Za-z][_A-Za-z0-9]*(?:\([^\n)]*\))?[ \t]+)|"
    r"(?:(?:public|internal|package|private|fileprivate)[ \t]+))*"
    r"import[ \t]+(?:(?:typealias|struct|class|enum|protocol|let|var|func)[ \t]+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)\b",
    re.MULTILINE,
)


def parse_ports(root: Path = ROOT) -> dict[str, int]:
    values: dict[str, int] = {}
    for raw_line in (root / "ports.env").read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"(PORT_[0-9]+)=(\d+)", line)
        if match is None:
            raise ValueError(f"invalid ports.env line: {raw_line!r}")
        values[match.group(1)] = int(match.group(2))
    return values


def mask_swift_comments_and_strings(source: str) -> str:
    """Mask non-code while preserving line offsets for import diagnostics."""

    result: list[str] = []
    index = 0
    block_depth = 0
    string_delimiter: str | None = None
    while index < len(source):
        if block_depth:
            if source.startswith("/*", index):
                block_depth += 1
                result.extend("  ")
                index += 2
            elif source.startswith("*/", index):
                block_depth -= 1
                result.extend("  ")
                index += 2
            else:
                result.append("\n" if source[index] == "\n" else " ")
                index += 1
            continue

        if string_delimiter is not None:
            if source.startswith(string_delimiter, index):
                result.extend(" " * len(string_delimiter))
                index += len(string_delimiter)
                string_delimiter = None
            elif source[index] == "\\" and string_delimiter == '"' and index + 1 < len(source):
                result.extend("  ")
                index += 2
            else:
                result.append("\n" if source[index] == "\n" else " ")
                index += 1
            continue

        if source.startswith("//", index):
            end = source.find("\n", index)
            if end == -1:
                result.extend(" " * (len(source) - index))
                break
            result.extend(" " * (end - index))
            index = end
            continue
        if source.startswith("/*", index):
            block_depth = 1
            result.extend("  ")
            index += 2
            continue
        if source.startswith('"""', index):
            string_delimiter = '"""'
            result.extend("   ")
            index += 3
            continue
        if source[index] == '"':
            string_delimiter = '"'
            result.append(" ")
            index += 1
            continue
        result.append(source[index])
        index += 1
    return "".join(result)


def swift_imports(source: str) -> list[tuple[int, str]]:
    masked = mask_swift_comments_and_strings(source)
    return [
        (masked.count("\n", 0, match.start()) + 1, match.group(1))
        for match in IMPORT_DECLARATION.finditer(masked)
    ]


def dump_package(root: Path = ROOT) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["xcrun", "swift", "package", "dump-package"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        value = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot inspect Swift package graph: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("Swift package graph is not a JSON object")
    return value


def target_dependency_name(dependency: Any) -> str | None:
    if not isinstance(dependency, dict) or set(dependency) != {"byName"}:
        return None
    value = dependency["byName"]
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not isinstance(value[0], str)
        or value[1] is not None
    ):
        return None
    return value[0]


def contains_link_setting(value: Any) -> bool:
    if isinstance(value, dict):
        if any(key in {"linkedFramework", "linkedLibrary"} for key in value):
            return True
        return any(contains_link_setting(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_link_setting(item) for item in value)
    return False


def declared_swift_unsafe_flags(settings: Any) -> set[str]:
    flags: set[str] = set()
    if not isinstance(settings, list):
        return flags
    for setting in settings:
        if not isinstance(setting, dict) or setting.get("tool") != "swift":
            continue
        kind = setting.get("kind")
        if not isinstance(kind, dict):
            continue
        unsafe_flags = kind.get("unsafeFlags")
        if not isinstance(unsafe_flags, dict):
            continue
        values = unsafe_flags.get("_0")
        if isinstance(values, list):
            flags.update(value for value in values if isinstance(value, str))
    return flags


def graph_has_cycle(graph: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(dependency) for dependency in graph.get(node, set())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def validate_foundation_boundaries(
    manifest: dict[str, Any], root: Path = ROOT
) -> list[str]:
    failures: list[str] = []
    if manifest.get("dependencies"):
        failures.append(
            "portable foundation package may not declare external package dependencies; "
            "provider/framework adapters belong under App/"
        )

    targets = manifest.get("targets")
    if not isinstance(targets, list):
        return [*failures, "Swift package graph has no target list"]
    regular_targets = {
        target.get("name")
        for target in targets
        if isinstance(target, dict)
        and target.get("type") == "regular"
        and isinstance(target.get("name"), str)
    }
    if not regular_targets:
        return [*failures, "Swift package graph has no regular foundation targets"]
    if regular_targets != set(EXPECTED_FOUNDATION_DEPENDENCIES):
        failures.append(
            "foundation target set differs from ADR allowlist: "
            f"expected {sorted(EXPECTED_FOUNDATION_DEPENDENCIES)}, "
            f"found {sorted(regular_targets)}"
        )
    test_targets = {
        target.get("name")
        for target in targets
        if isinstance(target, dict)
        and target.get("type") == "test"
        and isinstance(target.get("name"), str)
    }
    if test_targets != set(EXPECTED_TEST_DEPENDENCIES):
        failures.append(
            "test target set differs from ADR allowlist: "
            f"expected {sorted(EXPECTED_TEST_DEPENDENCIES)}, found {sorted(test_targets)}"
        )
    unexpected_target_types = sorted(
        str(target.get("name"))
        for target in targets
        if isinstance(target, dict) and target.get("type") not in {"regular", "test"}
    )
    if unexpected_target_types:
        failures.append(
            "portable package contains unapproved target types: "
            + ", ".join(unexpected_target_types)
        )

    graph: dict[str, set[str]] = {name: set() for name in regular_targets}
    target_records = {
        target["name"]: target
        for target in targets
        if isinstance(target, dict) and target.get("name") in regular_targets
    }
    for name in sorted(regular_targets):
        target = target_records[name]
        if any(marker.lower() in name.lower() for marker in APP_ONLY_NAME_MARKERS):
            failures.append(f"app/adapter target may not live in portable Sources: {name}")
        if not (root / "Sources" / name).is_dir():
            failures.append(f"foundation target lacks Sources/{name}: {name}")

        dependencies = target.get("dependencies", [])
        if not isinstance(dependencies, list):
            failures.append(f"target dependencies are malformed: {name}")
            dependencies = []
        for dependency in dependencies:
            dependency_name = target_dependency_name(dependency)
            if dependency_name is None or dependency_name not in regular_targets:
                failures.append(
                    f"foundation target {name} has non-foundation dependency: {dependency!r}"
                )
                continue
            if name != "UIDomain" and dependency_name == "UIDomain":
                failures.append(f"foundation target {name} may not depend on UI domain state")
            graph[name].add(dependency_name)

        expected_dependencies = EXPECTED_FOUNDATION_DEPENDENCIES.get(name)
        if expected_dependencies is not None and graph[name] != expected_dependencies:
            failures.append(
                f"foundation target {name} dependency set differs from ADR allowlist: "
                f"expected {sorted(expected_dependencies)}, found {sorted(graph[name])}"
            )

        if contains_link_setting(target.get("settings", [])):
            failures.append(f"foundation target may not link a framework/library: {name}")
        swift_flags = declared_swift_unsafe_flags(target.get("settings", []))
        for required_flag in REQUIRED_STRICT_SWIFT_FLAGS:
            if required_flag not in swift_flags:
                failures.append(f"foundation target {name} lacks strict flag {required_flag}")
        unexpected_flags = swift_flags - REQUIRED_STRICT_SWIFT_FLAGS
        if unexpected_flags:
            failures.append(
                f"foundation target {name} has unapproved unsafe flags: {sorted(unexpected_flags)}"
            )

    if graph_has_cycle(graph):
        failures.append("foundation target dependency graph contains a cycle")

    test_records = {
        target["name"]: target
        for target in targets
        if isinstance(target, dict) and target.get("name") in test_targets
    }
    test_dependency_graph: dict[str, set[str]] = {}
    for name in sorted(test_targets):
        target = test_records[name]
        parsed_dependencies: set[str] = set()
        dependencies = target.get("dependencies", [])
        if not isinstance(dependencies, list):
            failures.append(f"test target dependencies are malformed: {name}")
            dependencies = []
        for dependency in dependencies:
            dependency_name = target_dependency_name(dependency)
            if dependency_name is None or dependency_name not in regular_targets:
                failures.append(f"test target {name} has non-foundation dependency: {dependency!r}")
                continue
            parsed_dependencies.add(dependency_name)
        test_dependency_graph[name] = parsed_dependencies
        expected_dependencies = EXPECTED_TEST_DEPENDENCIES.get(name)
        if expected_dependencies is not None and parsed_dependencies != expected_dependencies:
            failures.append(
                f"test target {name} dependency set differs from ADR allowlist: "
                f"expected {sorted(expected_dependencies)}, found {sorted(parsed_dependencies)}"
            )
        if contains_link_setting(target.get("settings", [])):
            failures.append(f"test target may not link an unapproved framework/library: {name}")
        swift_flags = declared_swift_unsafe_flags(target.get("settings", []))
        for required_flag in REQUIRED_STRICT_SWIFT_FLAGS:
            if required_flag not in swift_flags:
                failures.append(f"test target {name} lacks strict flag {required_flag}")
        unexpected_flags = swift_flags - REQUIRED_STRICT_SWIFT_FLAGS
        if unexpected_flags:
            failures.append(
                f"test target {name} has unapproved unsafe flags: {sorted(unexpected_flags)}"
            )

    for path in sorted((root / "Sources").glob("**/*.swift")):
        relative = path.relative_to(root)
        if len(relative.parts) < 3:
            failures.append(f"source file is not owned by a target directory: {relative}")
            continue
        target_name = relative.parts[1]
        if target_name not in regular_targets:
            failures.append(f"source directory is absent from the package graph: {relative}")
            continue
        if any(
            marker.lower() in component.lower()
            for component in relative.parts[1:-1]
            for marker in APP_ONLY_NAME_MARKERS
        ):
            failures.append(f"app/adapter implementation may not live under Sources: {relative}")

        allowed_imports = ALLOWED_FOUNDATION_IMPORTS | graph[target_name]
        source = path.read_text(encoding="utf-8")
        for line_number, module in swift_imports(source):
            if module not in allowed_imports:
                failures.append(
                    f"foundation source imports undeclared/external module {module}: "
                    f"{relative}:{line_number}"
                )

    test_root = root / "Tests" / "FoundationPropertyTests"
    for path in sorted(test_root.glob("**/*.swift")):
        relative = path.relative_to(root)
        allowed_imports = ALLOWED_TEST_IMPORTS | test_dependency_graph.get(
            "FoundationPropertyTests", set()
        )
        source = path.read_text(encoding="utf-8")
        for line_number, module in swift_imports(source):
            if module not in allowed_imports:
                failures.append(
                    f"foundation test imports undeclared/external module {module}: "
                    f"{relative}:{line_number}"
                )
    return failures


def make_target_graph(makefile: str) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    dependencies: dict[str, set[str]] = {}
    recipes: dict[str, list[str]] = {}
    current_targets: list[str] = []
    for line in makefile.splitlines():
        if line.startswith("\t"):
            for target in current_targets:
                recipes.setdefault(target, []).append(line[1:])
            continue
        current_targets = []
        match = re.match(
            r"^([A-Za-z0-9_\\:-]+(?:\s+[A-Za-z0-9_\\:-]+)*):(?!=)\s*(.*)$", line
        )
        if match is None:
            continue
        current_targets = match.group(1).split()
        prerequisites = {
            value for value in match.group(2).split() if not value.startswith("|")
        }
        for target in current_targets:
            dependencies.setdefault(target, set()).update(prerequisites)
    return dependencies, recipes


def target_depends_on(
    graph: dict[str, set[str]], target: str, required: str, seen: set[str] | None = None
) -> bool:
    if target == required:
        return True
    if seen is None:
        seen = set()
    if target in seen:
        return False
    seen.add(target)
    return any(
        target_depends_on(graph, dependency, required, seen.copy())
        for dependency in graph.get(target, set())
    )


def validate_make_writable_scope(makefile: str) -> list[str]:
    failures: list[str] = []
    required_fragments = (
        "override NPM_CONFIG_CACHE := $(DEV_CACHE_DIR)/npm",
        "override npm_config_cache := $(NPM_CONFIG_CACHE)",
        "override TMPDIR := $(DEV_TMP_DIR)",
        "override PLAYWRIGHT_BROWSERS_PATH := $(DEV_CACHE_DIR)/ms-playwright",
        "export NPM_CONFIG_CACHE",
        "export npm_config_cache",
        "export TMPDIR",
        "export PLAYWRIGHT_BROWSERS_PATH",
        "tools/init_workspace.py",
    )
    for fragment in required_fragments:
        if fragment not in makefile:
            failures.append(f"Makefile lacks repository-local writable-scope contract: {fragment}")
    if "~/.npm" in makefile or "$(HOME)/.npm" in makefile:
        failures.append("Makefile may not use the shared user npm cache")

    graph, recipes = make_target_graph(makefile)
    workspace_recipe = recipes.get("workspace-init", [])
    if not any("$(PYTHON) tools/init_workspace.py" in line for line in workspace_recipe):
        failures.append("workspace-init must invoke the symlink-refusing Python initializer")
    if any("mkdir" in line for line in workspace_recipe):
        failures.append("workspace-init may not use a symlink-following mkdir command")
    for target, lines in recipes.items():
        runs_npm_or_browser = any(
            re.search(r"(?:^|[\s@])npm(?:\s|$)|node_modules/\.bin/playwright", line)
            for line in lines
        )
        if runs_npm_or_browser and not target_depends_on(graph, target, "workspace-init"):
            failures.append(
                f"Make target {target} runs npm/browser tooling without workspace-init prerequisite"
            )
    return failures


def main() -> int:
    failures: list[str] = []
    for relative in sorted(REQUIRED_FILES):
        if not (ROOT / relative).is_file():
            failures.append(f"missing required file: {relative}")

    if failures:
        for failure in failures:
            print(f"policy:error:{failure}", file=sys.stderr)
        return 1

    try:
        ports = parse_ports()
    except (OSError, ValueError) as error:
        failures.append(str(error))
        ports = {}
    if ports != EXPECTED_PORTS:
        failures.append(f"ports.env must declare exactly {EXPECTED_PORTS}, found {ports}")
    if any(port < 4220 or port > 4229 for port in ports.values()):
        failures.append("an allocated port is outside 4220-4229")

    gitignore_lines = {
        line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    if not ({".dev/", "/.dev/"} & gitignore_lines):
        failures.append(".gitignore does not ignore .dev/")

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    if package.get("private") is not True:
        failures.append("development harness package must be private")
    dependency = package.get("devDependencies", {}).get("@playwright/test", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", dependency):
        failures.append("@playwright/test must be pinned to an exact semantic version")

    workflow = (ROOT / ".github/workflows/verify.yml").read_text(encoding="utf-8")
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = re.search(r"\buses:\s*([^\s]+)", line)
        if match and not re.fullmatch(r"[^@]+@[0-9a-f]{40}", match.group(1)):
            failures.append(
                f"verify workflow action is not pinned to a 40-character SHA at line {line_number}"
            )
    if "permissions:\n  contents: read" not in workflow:
        failures.append("verify workflow must explicitly minimize permissions")
    for fragment in (
        ".dev/cache/npm",
        ".dev/tmp",
        "npm_config_cache=",
        "TMPDIR=",
    ):
        if fragment not in workflow:
            failures.append(f"verify workflow lacks repository-local writable scope: {fragment}")
    if "DEVELOPER_DIR: /Applications/Xcode_26.6.app/Contents/Developer" not in workflow:
        failures.append("verify workflow must pin the installed Xcode 26.6 path")
    if "path: .dev/logs/verify-all.log" not in workflow:
        failures.append("verify workflow must archive only the exact canonical log path")
    if "include-hidden-files: true" not in workflow:
        failures.append("verify workflow must explicitly include the hidden .dev verification log")

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    failures.extend(validate_make_writable_scope(makefile))

    runtime_paths = [ROOT / "Makefile", ROOT / "playwright.config.ts"]
    runtime_paths.extend(sorted((ROOT / "scripts").glob("*.py")))
    for path in runtime_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "0.0.0.0" in text:
            failures.append(f"runtime config may not contain wildcard bind host: {path.relative_to(ROOT)}")
        for forbidden in FORBIDDEN_RUNTIME_PORTS:
            if re.search(rf"(?<!\d){forbidden}(?!\d)", text):
                failures.append(
                    f"runtime config contains forbidden port {forbidden}: {path.relative_to(ROOT)}"
                )

    try:
        manifest = dump_package()
    except ValueError as error:
        failures.append(str(error))
        manifest = {}
    if manifest.get("swiftLanguageVersions") != ["6"]:
        failures.append("Package.swift must select only Swift language mode 6")
    failures.extend(validate_foundation_boundaries(manifest))

    if failures:
        print("policy-check:error", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(
        "policy-check:ok "
        f"ports={','.join(str(port) for port in sorted(ports.values()))} "
        "ci_actions=sha-pinned writable_scope=repository-local "
        "foundation_dependencies=internal-only foundation_imports=allowlisted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
