from __future__ import annotations

import copy
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from tools import (
    bootstrap,
    check_policy,
    check_text,
    init_workspace,
    repository_state,
    verify_clean_checkout,
)


STRICT_SETTINGS = [
    {
        "tool": "swift",
        "kind": {
            "unsafeFlags": {
                "_0": sorted(check_policy.REQUIRED_STRICT_SWIFT_FLAGS),
            }
        }
    }
]


def initialize_git_repository(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".gitignore").write_text(".dev/\n", encoding="utf-8")
    (root / "tracked.txt").write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "tracked.txt"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Repository Test",
            "-c",
            "user.email=repository-test@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        cwd=root,
        check=True,
    )


def foundation_manifest_fixture(root: Path) -> dict[str, object]:
    targets: list[dict[str, object]] = []
    for name, dependencies in check_policy.EXPECTED_FOUNDATION_DEPENDENCIES.items():
        source_directory = root / "Sources" / name
        source_directory.mkdir(parents=True)
        (source_directory / "Contract.swift").write_text("public enum Contract {}\n", encoding="utf-8")
        targets.append(
            {
                "name": name,
                "type": "regular",
                "dependencies": [
                    {"byName": [dependency, None]} for dependency in sorted(dependencies)
                ],
                "settings": copy.deepcopy(STRICT_SETTINGS),
            }
        )
    test_directory = root / "Tests" / "FoundationPropertyTests"
    test_directory.mkdir(parents=True)
    (test_directory / "ContractTests.swift").write_text(
        "import XCTest\n", encoding="utf-8"
    )
    targets.append(
        {
            "name": "FoundationPropertyTests",
            "type": "test",
            "dependencies": [
                {"byName": [dependency, None]}
                for dependency in sorted(check_policy.EXPECTED_FOUNDATION_DEPENDENCIES)
            ],
            "settings": copy.deepcopy(STRICT_SETTINGS),
        }
    )
    return {"dependencies": [], "targets": targets, "swiftLanguageVersions": ["6"]}


class BootstrapParsingTests(unittest.TestCase):
    def test_semantic_version_accepts_patchless_version(self) -> None:
        self.assertEqual(bootstrap.semantic_version("Swift version 6.4", "Swift"), (6, 4, 0))

    def test_semantic_version_rejects_unversioned_output(self) -> None:
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.semantic_version("main", "example")


class PolicyContractTests(unittest.TestCase):
    def test_exclusive_allocated_ports_are_exact(self) -> None:
        self.assertEqual(check_policy.parse_ports(), check_policy.EXPECTED_PORTS)
        self.assertTrue(all(4220 <= port <= 4229 for port in check_policy.parse_ports().values()))

    def test_forbidden_port_set_does_not_overlap_repository_block(self) -> None:
        self.assertFalse(
            check_policy.FORBIDDEN_RUNTIME_PORTS.intersection(range(4220, 4230))
        )

    def test_access_modified_and_selective_imports_are_detected(self) -> None:
        source = """
// import Photos
@_exported import SwiftUI
public import UIKit
import class RevenueCat.CustomerInfo
let marker = 1; import Network
let harmless = "import Metal"
"""
        self.assertEqual(
            check_policy.swift_imports(source),
            [(3, "SwiftUI"), (4, "UIKit"), (5, "RevenueCat"), (6, "Network")],
        )

    def test_foundation_boundary_rejects_external_import_and_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_directory = root / "Sources" / "CaptureDomain"
            source_directory.mkdir(parents=True)
            (source_directory / "Contract.swift").write_text(
                "@_exported import SwiftUI\n", encoding="utf-8"
            )
            manifest = {
                "dependencies": [{"sourceControl": [{"identity": "provider"}]}],
                "targets": [
                    {
                        "name": "CaptureDomain",
                        "type": "regular",
                        "dependencies": [{"product": ["Purchases", "provider", None, None]}],
                        "settings": STRICT_SETTINGS,
                    }
                ],
            }
            failures = check_policy.validate_foundation_boundaries(manifest, root)
            self.assertTrue(any("external package dependencies" in item for item in failures))
            self.assertTrue(any("non-foundation dependency" in item for item in failures))
            self.assertTrue(any("external module SwiftUI" in item for item in failures))

    def test_dependency_allowlist_rejects_cross_domain_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = foundation_manifest_fixture(root)
            purchases = next(
                target
                for target in manifest["targets"]
                if target["name"] == "PurchasesDomain"
            )
            purchases["dependencies"].append({"byName": ["CameraDomain", None]})
            failures = check_policy.validate_foundation_boundaries(manifest, root)
            self.assertTrue(
                any(
                    "PurchasesDomain dependency set differs from ADR allowlist" in item
                    for item in failures
                )
            )

    def test_test_target_rejects_external_import_and_missing_strict_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = foundation_manifest_fixture(root)
            test_target = next(
                target
                for target in manifest["targets"]
                if target["name"] == "FoundationPropertyTests"
            )
            test_target["settings"] = []
            (root / "Tests" / "FoundationPropertyTests" / "ContractTests.swift").write_text(
                "@_exported import AVFoundation\n", encoding="utf-8"
            )
            failures = check_policy.validate_foundation_boundaries(manifest, root)
            self.assertTrue(any("test target FoundationPropertyTests lacks strict flag" in item for item in failures))
            self.assertTrue(any("foundation test imports undeclared/external module AVFoundation" in item for item in failures))

    def test_make_npm_target_requires_safe_workspace_prerequisite(self) -> None:
        makefile = (check_policy.ROOT / "Makefile").read_text(encoding="utf-8")
        weakened = makefile.replace(
            "locked-install: workspace-init", "locked-install:", 1
        )
        failures = check_policy.validate_make_writable_scope(weakened)
        self.assertIn(
            "Make target locked-install runs npm/browser tooling without workspace-init prerequisite",
            failures,
        )


class WorkspaceInitializationTests(unittest.TestCase):
    def test_workspace_initialization_creates_real_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            init_workspace.ensure_directory_without_symlinks(
                root, PurePosixPath(".dev/cache/npm")
            )
            self.assertTrue((root / ".dev" / "cache" / "npm").is_dir())
            self.assertFalse((root / ".dev").is_symlink())

    def test_workspace_initialization_refuses_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            (root / ".dev").mkdir()
            os.symlink(outside, root / ".dev" / "cache")
            with self.assertRaises(init_workspace.WorkspaceInitializationError):
                init_workspace.ensure_directory_without_symlinks(
                    root, PurePosixPath(".dev/cache/npm")
                )
            self.assertFalse((Path(outside) / "npm").exists())


class RepositoryStateTests(unittest.TestCase):
    def test_content_hash_catches_second_change_to_already_dirty_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_git_repository(root)
            tracked = root / "tracked.txt"
            tracked.write_text("dirty-before\n", encoding="utf-8")
            before = repository_state.capture_repository(root)
            tracked.write_text("dirty-after\n", encoding="utf-8")
            after = repository_state.capture_repository(root)
            self.assertTrue(
                any(
                    "tracked worktree content changed: tracked.txt" in failure
                    for failure in repository_state.compare_repository_states(before, after)
                )
            )

    def test_unknown_ignored_namespace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_git_repository(root)
            (root / ".gitignore").write_text(".dev/\nprivate-cache/\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Repository Test",
                    "-c",
                    "user.email=repository-test@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "ignore fixture",
                ],
                cwd=root,
                check=True,
            )
            (root / "private-cache").mkdir()
            (root / "private-cache" / "hidden.txt").write_text("hidden\n", encoding="utf-8")
            with self.assertRaises(repository_state.RepositoryStateError):
                repository_state.capture_repository(root)

    def test_symlinked_ignored_namespace_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            initialize_git_repository(root)
            (root / ".dev").mkdir()
            os.symlink(outside, root / ".dev" / "cache")
            with self.assertRaises(repository_state.RepositoryStateError):
                repository_state.capture_repository(root)

    def test_snapshot_writer_refuses_symlink_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside.json"
            outside.write_text("unchanged\n", encoding="utf-8")
            output = root / "snapshot.json"
            output.symlink_to(outside)
            with self.assertRaises(repository_state.RepositoryStateError):
                repository_state.write_snapshot(output, {"schema_version": 1})
            self.assertEqual(outside.read_text(encoding="utf-8"), "unchanged\n")

    def test_huge_untracked_file_is_refused_before_hashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_git_repository(root)
            huge = root / "huge-untracked.bin"
            with huge.open("wb") as handle:
                handle.truncate(repository_state.MAX_SOURCE_FILE_BYTES + 1)
            with self.assertRaisesRegex(
                repository_state.RepositoryStateError,
                r"untracked file exceeds per-file byte limit",
            ):
                repository_state.capture_repository(root)

    def test_git_path_decoder_refuses_excessive_entry_count(self) -> None:
        with self.assertRaisesRegex(
            repository_state.RepositoryStateError,
            r"untracked path count exceeds limit 2",
        ):
            repository_state.decode_git_paths(
                b"one\0two\0three\0", label="untracked", max_paths=2
            )


class CleanCheckoutHarnessTests(unittest.TestCase):
    def test_clean_source_precondition_rejects_staged_and_untracked_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_git_repository(root)
            verify_clean_checkout.require_clean_source(root)
            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
            with self.assertRaises(verify_clean_checkout.CleanVerificationError):
                verify_clean_checkout.require_clean_source(root)
            (root / "untracked.txt").unlink()
            (root / "tracked.txt").write_text("staged\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            with self.assertRaises(verify_clean_checkout.CleanVerificationError):
                verify_clean_checkout.require_clean_source(root)

    def test_bounded_runner_terminates_after_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(verify_clean_checkout.VerificationTimeout) as caught:
                verify_clean_checkout.run_bounded(
                    [
                        sys.executable,
                        "-c",
                        "import time; print('started', flush=True); time.sleep(60)",
                    ],
                    cwd=Path(temporary),
                    timeout_seconds=0.2,
                    termination_grace_seconds=0.2,
                )
        self.assertEqual(caught.exception.timeout_seconds, 0.2)

    def test_clean_environment_removes_inherited_make_bypass_flags(self) -> None:
        previous = os.environ.get("MAKEFLAGS")
        os.environ["MAKEFLAGS"] = "-i"
        try:
            environment = verify_clean_checkout.clean_environment(
                Path("/tmp/repository-clean-fixture"), "a" * 40
            )
        finally:
            if previous is None:
                os.environ.pop("MAKEFLAGS", None)
            else:
                os.environ["MAKEFLAGS"] = previous
        self.assertNotIn("MAKEFLAGS", environment)
        self.assertEqual(environment["TMPDIR"], "/tmp/repository-clean-fixture/.dev/tmp")
        self.assertEqual(environment["PYTHONPATH"], "/tmp/repository-clean-fixture")

    def test_detached_service_session_is_stopped_before_worktree_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worktree = Path(temporary)
            scripts = worktree / "scripts"
            pid_directory = worktree / ".dev" / "pids"
            scripts.mkdir()
            pid_directory.mkdir(parents=True)
            controller = scripts / "devctl.py"
            controller.write_text(
                """import os
import signal
from pathlib import Path

pid_file = Path('.dev/pids/service.pid')
pid = int(pid_file.read_text(encoding='utf-8'))
os.kill(pid, signal.SIGTERM)
pid_file.unlink()
""",
                encoding="utf-8",
            )
            service = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                start_new_session=True,
            )
            try:
                (pid_directory / "service.pid").write_text(
                    f"{service.pid}\n", encoding="utf-8"
                )
                failure = verify_clean_checkout.stop_worktree_services(
                    worktree, os.environ.copy(), timeout_seconds=5
                )
                self.assertIsNone(failure)
                self.assertEqual(service.wait(timeout=5), -signal.SIGTERM)
                self.assertFalse((pid_directory / "service.pid").exists())
            finally:
                if service.poll() is None:
                    service.kill()
                    service.wait(timeout=5)

    def test_failed_detached_shutdown_retains_pid_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worktree = root / "detached"
            (worktree / "scripts").mkdir(parents=True)
            pid_directory = worktree / ".dev" / "pids"
            pid_directory.mkdir(parents=True)
            (pid_directory / "service.pid").write_text("999999\n", encoding="utf-8")
            (worktree / "scripts" / "devctl.py").write_text(
                "raise SystemExit(7)\n", encoding="utf-8"
            )
            failures = verify_clean_checkout.cleanup_worktree(
                root, worktree, os.environ.copy()
            )
            self.assertTrue(any("retained worktree and PID evidence" in item for item in failures))
            self.assertTrue((pid_directory / "service.pid").is_file())


class SecretPatternTests(unittest.TestCase):
    def test_private_key_header_is_rejected(self) -> None:
        self.assertIsNotNone(
            check_text.SECRET_PATTERNS["private-key"].search(
                "-----BEGIN " + "PRIVATE KEY-----"
            )
        )

    def test_normal_source_text_does_not_match_secret_patterns(self) -> None:
        value = "correlation_id=fixture-0001 status=ready"
        self.assertTrue(
            all(pattern.search(value) is None for pattern in check_text.SECRET_PATTERNS.values())
        )


if __name__ == "__main__":
    unittest.main()
