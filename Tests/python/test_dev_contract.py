from __future__ import annotations

import hashlib
import http.client
import json
import logging
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest import mock

from scripts import dev_service, devctl
from tools import bootstrap, probe_services


REPO_ROOT = Path(__file__).resolve().parents[2]


class RepositoryLocalTempCase(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = REPO_ROOT / ".dev" / "tmp"
        temp_parent.mkdir(parents=True, exist_ok=True)
        self._temporary = tempfile.TemporaryDirectory(prefix="contract-test-", dir=temp_parent)
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name) / devctl.REPOSITORY_NAME
        self.root.mkdir()

    def write_ports(self, text: str | None = None) -> Path:
        path = self.root / "ports.env"
        path.write_text(
            text
            or "# isolated test\nPORT_0=4220\nPORT_1=4221\nPORT_2=4222\nPORT_3=4223\n",
            encoding="utf-8",
        )
        return path


class PortConfigurationTests(RepositoryLocalTempCase):
    def test_exact_configuration_is_parsed_as_data(self) -> None:
        configuration = devctl.parse_ports_file(self.write_ports())
        self.assertEqual(configuration.ports, {"PORT_0": 4220, "PORT_1": 4221, "PORT_2": 4222, "PORT_3": 4223})

    def test_shell_syntax_is_refused_instead_of_executed(self) -> None:
        path = self.write_ports(
            "PORT_0=$(touch should-not-exist)\nPORT_1=4221\nPORT_2=4222\nPORT_3=4223\n"
        )
        with self.assertRaisesRegex(devctl.DevContractError, "line 1") as raised:
            devctl.parse_ports_file(path)
        self.assertEqual(raised.exception.code, "ports_file_invalid")
        self.assertFalse((self.root / "should-not-exist").exists())

    def test_port_outside_exclusive_block_is_refused(self) -> None:
        path = self.write_ports("PORT_0=3000\nPORT_1=4221\nPORT_2=4222\nPORT_3=4223\n")
        with self.assertRaises(devctl.DevContractError) as raised:
            devctl.parse_ports_file(path)
        self.assertEqual(raised.exception.code, "port_outside_block")

    def test_duplicate_service_ports_are_refused(self) -> None:
        path = self.write_ports("PORT_0=4220\nPORT_1=4220\nPORT_2=4222\nPORT_3=4223\n")
        with self.assertRaises(devctl.DevContractError) as raised:
            devctl.parse_ports_file(path)
        self.assertEqual(raised.exception.code, "ports_file_duplicate_port")

    def test_missing_service_port_is_refused(self) -> None:
        path = self.write_ports("PORT_0=4220\nPORT_1=4221\nPORT_2=4222\n")
        with self.assertRaises(devctl.DevContractError) as raised:
            devctl.parse_ports_file(path)
        self.assertEqual(raised.exception.code, "ports_file_missing_key")


class PidOwnershipTests(RepositoryLocalTempCase):
    def setUp(self) -> None:
        super().setUp()
        self.write_ports()
        devctl.ensure_dev_directories(self.root)
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "dev_service.py").write_text("# test\n", encoding="utf-8")

    def record(self, **changes: object) -> devctl.PidRecord:
        values: dict[str, object] = {
            "schema_version": 1,
            "repository": devctl.REPOSITORY_NAME,
            "repo_root": str(self.root.resolve()),
            "pid": 424242,
            "service": "evaluation",
            "host": devctl.BIND_HOST,
            "port": 4220,
            "instance_token": "a" * 32,
            "script": str((self.root / "scripts" / "dev_service.py").resolve()),
            "log_file": str((self.root / ".dev" / "logs" / "evaluation.log").absolute()),
            "started_at": "2026-08-10T00:00:00.000Z",
        }
        values.update(changes)
        return devctl.PidRecord(**values)  # type: ignore[arg-type]

    def process_arguments(self, record: devctl.PidRecord) -> list[str]:
        return [
            "/usr/bin/python3",
            "-u",
            record.script,
            "--service",
            record.service,
            "--host",
            record.host,
            "--port",
            str(record.port),
            "--repo-root",
            record.repo_root,
            "--instance-token",
            record.instance_token,
            "--log-file",
            record.log_file,
        ]

    def test_pid_record_round_trip_is_strict(self) -> None:
        record = self.record()
        devctl.write_pid_record(self.root, record)
        self.assertEqual(devctl.read_pid_record(self.root, record.service), record)

    def test_pid_record_symlink_is_refused(self) -> None:
        target = self.root / ".dev" / "tmp" / "record.json"
        target.write_text(json.dumps(self.record().to_document()), encoding="utf-8")
        devctl.pid_path(self.root, "evaluation").symlink_to(target)
        with self.assertRaises(devctl.DevContractError) as raised:
            devctl.read_pid_record(self.root, "evaluation")
        self.assertEqual(raised.exception.code, "pid_record_symlink")

    def test_pid_record_symlink_swap_is_refused_by_descriptor_open(self) -> None:
        record = self.record()
        devctl.write_pid_record(self.root, record)
        record_path = devctl.pid_path(self.root, "evaluation")
        outside = self.root / ".dev" / "tmp" / "outside-record.json"
        outside.write_text(json.dumps(record.to_document()), encoding="utf-8")
        real_open = os.open
        swapped = False

        def racing_open(path: object, flags: int, mode: int = 0o777) -> int:
            nonlocal swapped
            if Path(path) == record_path and not swapped:  # type: ignore[arg-type]
                swapped = True
                record_path.unlink()
                record_path.symlink_to(outside)
            return real_open(path, flags, mode)  # type: ignore[arg-type]

        with mock.patch.object(devctl.os, "open", side_effect=racing_open):
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.read_pid_record(self.root, "evaluation")
        self.assertTrue(swapped)
        self.assertEqual(raised.exception.code, "pid_record_symlink")

    def test_process_identity_requires_every_owned_argument(self) -> None:
        record = self.record()
        arguments = self.process_arguments(record)
        self.assertTrue(devctl.process_matches_record(record, arguments))
        arguments[-1] = str(self.root / ".dev" / "logs" / "other.log")
        self.assertFalse(devctl.process_matches_record(record, arguments))

    def test_stop_refuses_unproven_pid_without_signalling(self) -> None:
        record = self.record()
        with (
            mock.patch.object(devctl, "process_is_alive", return_value=True),
            mock.patch.object(devctl, "process_matches_record", return_value=False),
            mock.patch.object(devctl, "request_owned_shutdown") as shutdown,
            mock.patch.object(devctl.os, "kill") as kill,
        ):
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.stop_owned_record(self.root, record)
        self.assertEqual(raised.exception.code, "stop_ownership_unproven")
        shutdown.assert_not_called()
        kill.assert_not_called()

    def test_shutdown_endpoint_failure_never_falls_back_to_pid_signal(self) -> None:
        record = self.record()
        devctl.write_pid_record(self.root, record)
        with (
            mock.patch.object(devctl, "process_is_alive", return_value=True),
            mock.patch.object(devctl, "process_matches_record", return_value=True),
            mock.patch.object(
                devctl,
                "request_owned_shutdown",
                side_effect=devctl.DevContractError("stop_shutdown_refused", "refused"),
            ),
            mock.patch.object(devctl.os, "kill") as kill,
        ):
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.stop_owned_record(self.root, record)
        self.assertEqual(raised.exception.code, "stop_shutdown_refused")
        kill.assert_not_called()
        self.assertEqual(devctl.read_pid_record(self.root, record.service), record)

    def test_pid_identity_change_after_shutdown_is_refused_without_signal(self) -> None:
        record = self.record()
        devctl.write_pid_record(self.root, record)
        with (
            mock.patch.object(devctl, "process_is_alive", return_value=True),
            mock.patch.object(devctl, "process_matches_record", side_effect=[True, False]),
            mock.patch.object(devctl, "process_arguments", return_value=["/foreign/process"]),
            mock.patch.object(devctl, "request_owned_shutdown") as shutdown,
            mock.patch.object(devctl.time, "monotonic", side_effect=[0.0, 6.0]),
            mock.patch.object(devctl.os, "kill") as kill,
        ):
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.stop_owned_record(self.root, record)
        self.assertEqual(raised.exception.code, "stop_pid_reused")
        shutdown.assert_called_once_with(record)
        kill.assert_not_called()
        self.assertEqual(devctl.read_pid_record(self.root, record.service), record)

    def test_authenticated_self_shutdown_removes_only_the_same_record(self) -> None:
        record = self.record()
        devctl.write_pid_record(self.root, record)
        with (
            mock.patch.object(devctl, "process_is_alive", side_effect=[True, False]),
            mock.patch.object(devctl, "process_matches_record", return_value=True),
            mock.patch.object(devctl, "request_owned_shutdown") as shutdown,
            mock.patch.object(devctl.os, "kill") as kill,
        ):
            devctl.stop_owned_record(self.root, record)
        shutdown.assert_called_once_with(record)
        kill.assert_not_called()
        self.assertIsNone(devctl.read_pid_record(self.root, record.service))

    def test_changed_pid_record_is_never_removed(self) -> None:
        original = self.record()
        changed = self.record(pid=424243, instance_token="b" * 32)
        devctl.write_pid_record(self.root, changed)
        with self.assertRaises(devctl.DevContractError) as raised:
            devctl.remove_pid_record_if_same(self.root, original)
        self.assertEqual(raised.exception.code, "pid_record_changed")
        self.assertTrue(devctl.pid_path(self.root, "evaluation").exists())


class PreflightRefusalTests(RepositoryLocalTempCase):
    def setUp(self) -> None:
        super().setUp()
        self.write_ports()

    @staticmethod
    def empty_listener_map() -> dict[int, list[devctl.Listener]]:
        return {port: [] for port in devctl.PORT_BLOCK}

    def test_preflight_creates_only_isolated_dev_state(self) -> None:
        with (
            mock.patch.object(devctl, "dev_is_git_ignored", return_value=True),
            mock.patch.object(
                devctl, "discover_listeners_for_ports", return_value=self.empty_listener_map()
            ),
        ):
            state = devctl.preflight(self.root)
        self.assertFalse(state.active_records)
        for name in ("pids", "logs", "tmp", "cache", "pw-profile"):
            self.assertTrue((self.root / ".dev" / name).is_dir())
        storage = json.loads(
            (self.root / ".dev" / "pw-profile" / "storage-state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(storage, {"cookies": [], "origins": []})

    def test_any_foreign_listener_in_reserved_block_fails_loudly(self) -> None:
        listeners = self.empty_listener_map()
        listeners[4229] = [devctl.Listener(9191, "foreign-python", "127.0.0.1:4229")]
        with (
            mock.patch.object(devctl, "dev_is_git_ignored", return_value=True),
            mock.patch.object(devctl, "discover_listeners_for_ports", return_value=listeners),
        ):
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.preflight(self.root)
        self.assertEqual(raised.exception.code, "foreign_port_holder")
        self.assertIn("no process was killed", str(raised.exception))

    def test_preflight_refuses_when_dev_is_not_ignored(self) -> None:
        with mock.patch.object(devctl, "dev_is_git_ignored", return_value=False):
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.preflight(self.root)
        self.assertEqual(raised.exception.code, "dev_not_ignored")

    def test_listener_inspection_never_accepts_out_of_block_port(self) -> None:
        with self.assertRaises(devctl.DevContractError) as raised:
            devctl.discover_listeners_for_ports((3000,))
        self.assertEqual(raised.exception.code, "port_probe_invalid")

    def test_lsof_machine_output_is_mapped_to_the_exact_port(self) -> None:
        completed = SimpleNamespace(
            returncode=0,
            stdout="p123\ncPython\ntIPv4\nn127.0.0.1:4222\n",
            stderr="",
        )
        with (
            mock.patch.object(devctl.shutil, "which", return_value="/usr/sbin/lsof"),
            mock.patch.object(devctl.subprocess, "run", return_value=completed),
        ):
            listeners = devctl.discover_listeners_for_ports(devctl.PORT_BLOCK)
        self.assertEqual(listeners[4222], [devctl.Listener(123, "Python", "127.0.0.1:4222")])
        self.assertFalse(listeners[4220])

    def test_lsof_absence_fails_closed_with_stable_code(self) -> None:
        with mock.patch.object(devctl, "lsof_executable", return_value=None):
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.discover_listeners_for_ports(devctl.PORT_BLOCK)
        self.assertEqual(raised.exception.code, "lsof_unavailable")
        self.assertIn("IPv4 and IPv6", str(raised.exception))

    def test_bootstrap_requires_lsof(self) -> None:
        with (
            mock.patch.object(bootstrap.shutil, "which", return_value=None),
            mock.patch.object(bootstrap.Path, "is_file", return_value=False),
        ):
            with self.assertRaisesRegex(bootstrap.BootstrapError, "lsof is required"):
                bootstrap.require_lsof()

    def test_real_foreign_listener_is_discovered_without_being_killed(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            listener.bind((devctl.BIND_HOST, 4229))
            listener.listen(1)
            with mock.patch.object(devctl, "dev_is_git_ignored", return_value=True):
                with self.assertRaises(devctl.DevContractError) as raised:
                    devctl.preflight(self.root)
            self.assertEqual(raised.exception.code, "foreign_port_holder")
            self.assertIn("port 4229", str(raised.exception))
            self.assertEqual(listener.getsockname(), (devctl.BIND_HOST, 4229))
        finally:
            listener.close()


class SpawnEnvironmentTests(RepositoryLocalTempCase):
    def test_service_environment_is_allowlisted_and_drops_inherited_secrets(self) -> None:
        devctl.ensure_dev_directories(self.root)
        with mock.patch.dict(
            os.environ,
            {
                "REVENUECAT_WEBHOOK_AUTH_TOKEN": "must-not-cross-boundary",
                "AWS_SECRET_ACCESS_KEY": "must-not-cross-boundary",
                "HTTP_PROXY": "http://attacker.invalid",
                "PATH": "/attacker/bin",
            },
            clear=True,
        ):
            environment = devctl.sanitized_service_environment(self.root)
        self.assertNotIn("REVENUECAT_WEBHOOK_AUTH_TOKEN", environment)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", environment)
        self.assertNotIn("HTTP_PROXY", environment)
        self.assertEqual(environment["PATH"], "/usr/bin:/bin:/usr/sbin:/sbin")
        self.assertEqual(environment["HOME"], str(self.root / ".dev" / "tmp" / "service-home"))
        self.assertEqual(
            set(environment),
            {
                "GIT_CONFIG_NOSYSTEM",
                "GIT_OPTIONAL_LOCKS",
                "GIT_TERMINAL_PROMPT",
                "HOME",
                "LANG",
                "LC_ALL",
                "PATH",
                "PYTHONUNBUFFERED",
                "PYTHONUTF8",
                "TMPDIR",
            },
        )


class ReadinessValidationTests(RepositoryLocalTempCase):
    def setUp(self) -> None:
        super().setUp()
        self.record = devctl.PidRecord(
            schema_version=1,
            repository=devctl.REPOSITORY_NAME,
            repo_root=str(self.root.resolve()),
            pid=111,
            service="test-patterns",
            host=devctl.BIND_HOST,
            port=4222,
            instance_token="c" * 32,
            script=str(self.root / "scripts" / "dev_service.py"),
            log_file=str(self.root / ".dev" / "logs" / "test-patterns.log"),
            started_at="2026-08-10T00:00:00.000Z",
        )

    def valid_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "service": "test-patterns",
            "bind_host": "127.0.0.1",
            "port": 4222,
            "instance_token_sha256": hashlib.sha256(("c" * 32).encode("ascii")).hexdigest(),
            "readiness_scope": "local_development_surface",
            "production_verified": False,
            "ready": True,
            "checks": {"timing_calibrated": False},
        }

    def response(self, payload: object, content_type: str = "application/json") -> object:
        body = json.dumps(payload).encode("utf-8")

        class Headers:
            def get_content_type(self) -> str:
                return content_type

        class Response:
            status = 200
            headers = Headers()

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, _limit: int) -> bytes:
                return body

        return Response()

    def test_semantic_owned_readiness_is_accepted(self) -> None:
        with mock.patch.object(
            devctl, "open_loopback_request", return_value=self.response(self.valid_payload())
        ):
            self.assertEqual(devctl.readiness_probe(self.record), (True, "ready"))

    def test_tcp_or_http_acceptance_without_json_contract_is_not_ready(self) -> None:
        with mock.patch.object(
            devctl,
            "open_loopback_request",
            return_value=self.response("not readiness", content_type="text/plain"),
        ):
            ready, detail = devctl.readiness_probe(self.record)
        self.assertFalse(ready)
        self.assertIn("content type", detail)

    def test_wrong_instance_token_is_not_ready(self) -> None:
        payload = self.valid_payload()
        payload["instance_token_sha256"] = "0" * 64
        with mock.patch.object(devctl, "open_loopback_request", return_value=self.response(payload)):
            ready, detail = devctl.readiness_probe(self.record)
        self.assertFalse(ready)
        self.assertIn("instance_token_sha256", detail)

    def test_test_pattern_service_must_disclaim_calibration(self) -> None:
        payload = self.valid_payload()
        payload["checks"] = {"timing_calibrated": True}
        with mock.patch.object(devctl, "open_loopback_request", return_value=self.response(payload)):
            ready, detail = devctl.readiness_probe(self.record)
        self.assertFalse(ready)
        self.assertIn("must not be implied", detail)


class LoopbackHTTPClientTests(unittest.TestCase):
    @contextmanager
    def server(
        self, port: int, handler: type[BaseHTTPRequestHandler]
    ) -> Iterator[ThreadingHTTPServer]:
        class IsolatedServer(ThreadingHTTPServer):
            allow_reuse_address = False

        instance = IsolatedServer(("127.0.0.1", port), handler)
        thread = threading.Thread(target=instance.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        try:
            yield instance
        finally:
            instance.shutdown()
            instance.server_close()
            thread.join(timeout=2.0)
            self.assertFalse(thread.is_alive())

    def test_devctl_ignores_hostile_proxy_environment(self) -> None:
        target_hits: list[str] = []
        proxy_hits: list[str] = []

        class TargetHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                target_hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *_args: object) -> None:
                pass

        class ProxyHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                proxy_hits.append(self.path)
                self.send_response(502)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args: object) -> None:
                pass

        with self.server(4227, TargetHandler), self.server(0, ProxyHandler) as proxy:
            proxy_port = int(proxy.server_address[1])
            hostile_environment = {
                "HTTP_PROXY": f"http://127.0.0.1:{proxy_port}",
                "http_proxy": f"http://127.0.0.1:{proxy_port}",
                "NO_PROXY": "",
                "no_proxy": "",
            }
            request = devctl.urlrequest.Request("http://127.0.0.1:4227/exact", method="GET")
            with mock.patch.dict(os.environ, hostile_environment, clear=False):
                with devctl.open_loopback_request(request, timeout=1.0) as response:
                    self.assertEqual(response.read(), b"ok")
        self.assertEqual(target_hits, ["/exact"])
        self.assertEqual(proxy_hits, [])

    def test_devctl_refuses_redirect_without_contacting_destination(self) -> None:
        destination_hits: list[str] = []

        class DestinationHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                destination_hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args: object) -> None:
                pass

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:4229/stolen")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args: object) -> None:
                pass

        with self.server(4229, DestinationHandler), self.server(4228, RedirectHandler):
            request = devctl.urlrequest.Request("http://127.0.0.1:4228/start", method="GET")
            with self.assertRaises(devctl.DevContractError) as raised:
                devctl.open_loopback_request(request, timeout=1.0)
        self.assertEqual(raised.exception.code, "loopback_redirect_refused")
        self.assertEqual(destination_hits, [])

    def test_probe_builds_proxy_disabled_redirect_refusing_opener(self) -> None:
        class Response:
            def geturl(self) -> str:
                return "http://127.0.0.1:4220/health/ready"

            def close(self) -> None:
                pass

        class Opener:
            def open(self, _request: object, timeout: float) -> Response:
                self.timeout = timeout
                return Response()

        captured: list[object] = []

        def build_opener(*handlers: object) -> Opener:
            captured.extend(handlers)
            return Opener()

        request = probe_services.urlrequest.Request(
            "http://127.0.0.1:4220/health/ready", method="GET"
        )
        with mock.patch.object(probe_services.urlrequest, "build_opener", side_effect=build_opener):
            opened = probe_services.open_exact_loopback(request, 1.0)
        opened.close()
        proxy_handlers = [item for item in captured if isinstance(item, probe_services.urlrequest.ProxyHandler)]
        self.assertEqual(len(proxy_handlers), 1)
        self.assertEqual(proxy_handlers[0].proxies, {})
        self.assertTrue(
            any(isinstance(item, probe_services.RedirectRefusingHandler) for item in captured)
        )

    def test_probe_refuses_redirect_response(self) -> None:
        url = "http://127.0.0.1:4220/health/ready"

        class Opener:
            def open(self, _request: object, timeout: float) -> object:
                del timeout
                raise probe_services.urlerror.HTTPError(url, 302, "redirect", {}, None)

        request = probe_services.urlrequest.Request(url, method="GET")
        with mock.patch.object(probe_services.urlrequest, "build_opener", return_value=Opener()):
            with self.assertRaisesRegex(probe_services.ProbeFailure, "change its exact URL"):
                probe_services.open_exact_loopback(request, 1.0)

    def test_probe_readiness_digest_must_match_validated_pid_record(self) -> None:
        records: dict[str, devctl.PidRecord] = {}
        for key, port in probe_services.EXPECTED_PORTS.items():
            service = probe_services.SERVICE_BY_KEY[key]
            records[service] = devctl.PidRecord(
                schema_version=1,
                repository=devctl.REPOSITORY_NAME,
                repo_root=str(REPO_ROOT),
                pid=10_000 + port,
                service=service,
                host="127.0.0.1",
                port=port,
                instance_token=(key.lower().replace("_", "") + "x" * 32)[:32],
                script=str(REPO_ROOT / "scripts" / "dev_service.py"),
                log_file=str(REPO_ROOT / ".dev" / "logs" / f"{service}.log"),
                started_at="2026-08-10T00:00:00.000Z",
            )

        def json_response(
            _method: str, port: int, path: str, _body: bytes | None = None
        ) -> tuple[int, object]:
            if path != "/health/ready":
                raise AssertionError("digest mismatch must stop before unrelated probes")
            service = next(item for item in records.values() if item.port == port)
            return 200, {
                "schema_version": 1,
                "service": service.service,
                "bind_host": service.host,
                "port": service.port,
                "ready": True,
                "readiness_scope": "local_development_surface",
                "production_verified": False,
                "instance_token_sha256": "0" * 64,
            }

        with (
            mock.patch.object(
                probe_services.devctl,
                "read_pid_record",
                side_effect=lambda _root, service: records[service],
            ),
            mock.patch.object(probe_services.devctl, "process_is_alive", return_value=True),
            mock.patch.object(probe_services.devctl, "process_matches_record", return_value=True),
            mock.patch.object(probe_services, "json_response", side_effect=json_response),
        ):
            with self.assertRaisesRegex(probe_services.ProbeFailure, "readiness digest"):
                probe_services.run()


class ServiceTruthfulnessTests(RepositoryLocalTempCase):
    def test_absent_evaluation_file_is_a_truthful_empty_state(self) -> None:
        result = dev_service.load_evaluation(self.root)
        self.assertEqual(result["data_status"], "not_yet_available")
        self.assertEqual(result["matrix_cells"], 0)
        self.assertIn("no results are claimed", result["message"].lower())

    def test_invalid_present_evaluation_file_fails_closed(self) -> None:
        path = self.root / "evidence" / "evaluation" / "device-matrix.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"schema_version":1,"cells":[{"device":"only-one-field"}]}', encoding="utf-8")
        with self.assertRaises(dev_service.DataValidationError):
            dev_service.load_evaluation(self.root)

    def test_well_formed_but_uncommitted_evaluation_is_refused(self) -> None:
        path = self.root / "evidence" / "evaluation" / "device-matrix.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "evidence_kind": "physical_device_capture_matrix",
                    "metric_schema_version": 1,
                    "provenance": {},
                    "cells": [],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(dev_service.DataValidationError, "not committed"):
            dev_service.load_evaluation(self.root)

    def test_committed_matrix_is_quarantined_without_empirical_numbers_or_rows(self) -> None:
        matrix_path = self.root / "evidence" / "evaluation" / "device-matrix.json"
        matrix_path.parent.mkdir(parents=True)
        secret_label = "DO-NOT-SURFACE-DEVICE"
        matrix = {
            "schema_version": 2,
            "cells": [
                {
                    "device": secret_label,
                    "status": "supported",
                    "banding_reduction_fraction": 0.987654321,
                }
            ],
        }
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
        for arguments in (
            ("init", "--quiet"),
            ("config", "user.name", "Contract Test"),
            ("config", "user.email", "contract@example.invalid"),
            ("add", "evidence/evaluation/device-matrix.json"),
            ("commit", "--quiet", "-m", "committed unreplayed matrix"),
        ):
            subprocess.run(["git", *arguments], cwd=self.root, check=True, capture_output=True)

        result = dev_service.load_evaluation(self.root)
        encoded_result = json.dumps(result, sort_keys=True)
        self.assertEqual(result["data_status"], "quarantined_unreplayed_evidence")
        self.assertIs(result["generator_replayed"], False)
        self.assertEqual(result["quarantine_reason"], "no_committed_replay_verifier")
        self.assertEqual(result["matrix_cells"], 0)
        self.assertEqual(result["cells"], [])
        self.assertNotIn(secret_label, encoded_result)
        self.assertNotIn("supported", encoded_result)
        self.assertNotIn("0.987654321", encoded_result)

        matrix_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(dev_service.DataValidationError, "does not match|differs"):
            dev_service.load_evaluation(self.root)

    def test_evaluation_quarantine_has_constant_git_work_for_many_rows(self) -> None:
        matrix_path = self.root / "evidence" / "evaluation" / "device-matrix.json"
        matrix_path.parent.mkdir(parents=True)
        matrix_path.write_text(
            json.dumps({"cells": [{"value": index} for index in range(10_000)]}),
            encoding="utf-8",
        )
        for arguments in (
            ("init", "--quiet"),
            ("config", "user.name", "Contract Test"),
            ("config", "user.email", "contract@example.invalid"),
            ("add", "evidence/evaluation/device-matrix.json"),
            ("commit", "--quiet", "-m", "large quarantined matrix"),
        ):
            subprocess.run(["git", *arguments], cwd=self.root, check=True, capture_output=True)
        original_git_run = dev_service._git_run
        with mock.patch.object(dev_service, "_git_run", wraps=original_git_run) as git_run:
            result = dev_service.load_evaluation(self.root)
        self.assertEqual(git_run.call_count, 2)
        self.assertEqual(result["cells"], [])
        self.assertEqual(result["matrix_cells"], 0)

    def test_oversized_evaluation_is_refused_before_git_work(self) -> None:
        matrix_path = self.root / "evidence" / "evaluation" / "device-matrix.json"
        matrix_path.parent.mkdir(parents=True)
        with matrix_path.open("wb") as handle:
            handle.truncate(dev_service.MAX_EVALUATION_BYTES + 1)
        with mock.patch.object(dev_service, "_git_run") as git_run:
            with self.assertRaisesRegex(dev_service.DataValidationError, "exceeds"):
                dev_service.load_evaluation(self.root)
        git_run.assert_not_called()

    def test_evaluation_refuses_intermediate_directory_symlink(self) -> None:
        outside = self.root / "outside-evidence" / "evaluation"
        outside.mkdir(parents=True)
        (outside / "device-matrix.json").write_text("{}", encoding="utf-8")
        (self.root / "evidence").symlink_to(outside.parent, target_is_directory=True)
        with self.assertRaisesRegex(dev_service.DataValidationError, "directory component evidence"):
            dev_service.load_evaluation(self.root)

    def test_artifact_inventory_does_not_claim_uploads(self) -> None:
        result = dev_service.artifact_metadata(self.root)
        self.assertEqual(result["artifact_count"], 0)
        self.assertEqual(result["testflight_status"], "not_configured")
        self.assertEqual(result["store_submission_status"], "not_configured")

    def test_artifact_file_limit_is_enforced_before_sorting(self) -> None:
        artifact_root = self.root / "artifacts"
        artifact_root.mkdir()
        for name in ("z", "a", "m"):
            (artifact_root / name).write_text(name, encoding="utf-8")
        with mock.patch.object(dev_service, "MAX_ARTIFACT_FILES", 2):
            with self.assertRaisesRegex(dev_service.DataValidationError, "2-file"):
                dev_service.artifact_metadata(self.root)

    def test_artifact_inventory_refuses_file_and_nested_directory_symlinks(self) -> None:
        artifact_root = self.root / "artifacts"
        artifact_root.mkdir()
        target_file = self.root / "target.txt"
        target_file.write_text("target", encoding="utf-8")
        file_link = artifact_root / "linked-file"
        file_link.symlink_to(target_file)
        with self.assertRaisesRegex(dev_service.DataValidationError, "refuses symlink"):
            dev_service.artifact_metadata(self.root)
        file_link.unlink()

        target_directory = self.root / "target-directory"
        target_directory.mkdir()
        (target_directory / "payload").write_text("target", encoding="utf-8")
        nested = artifact_root / "nested"
        nested.mkdir()
        (nested / "linked-directory").symlink_to(target_directory, target_is_directory=True)
        with self.assertRaisesRegex(dev_service.DataValidationError, "refuses symlink"):
            dev_service.artifact_metadata(self.root)

    def test_artifact_inventory_refuses_non_regular_entry(self) -> None:
        artifact_root = self.root / "artifacts"
        artifact_root.mkdir()
        fifo = artifact_root / "unexpected-fifo"
        os.mkfifo(fifo, 0o600)
        with self.assertRaisesRegex(dev_service.DataValidationError, "non-regular"):
            dev_service.artifact_metadata(self.root)

    def test_artifact_inventory_refuses_directory_symlink_swap(self) -> None:
        artifact_root = self.root / "artifacts"
        artifact_root.mkdir()
        swapped_directory = artifact_root / "swap"
        swapped_directory.mkdir()
        (swapped_directory / "inside").write_text("inside", encoding="utf-8")
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret-name").write_text("outside", encoding="utf-8")
        real_open = os.open
        swapped = False

        def racing_open(
            path: object,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            nonlocal swapped
            if path == "swap" and dir_fd is not None and not swapped:
                swapped = True
                shutil.rmtree(swapped_directory)
                swapped_directory.symlink_to(outside, target_is_directory=True)
            return real_open(path, flags, mode, dir_fd=dir_fd)  # type: ignore[arg-type]

        with mock.patch.object(dev_service.os, "open", side_effect=racing_open):
            with self.assertRaisesRegex(dev_service.DataValidationError, "replaced directory"):
                dev_service.artifact_metadata(self.root)
        self.assertTrue(swapped)

    def test_original_patterns_are_deterministic_and_bounded(self) -> None:
        first = dev_service.moire_svg(4, 17)
        self.assertEqual(first, dev_service.moire_svg(4, 17))
        self.assertIn("Original moire line target", first)
        with self.assertRaises(ValueError):
            dev_service.moire_svg(1, 17)
        flicker = dev_service.flicker_document(60.0, 0.5)
        self.assertIn("not calibrated", flicker)

    def test_webhook_schema_refuses_non_sandbox_events(self) -> None:
        document = {
            "api_version": "1.0",
            "event": {"id": "event-1", "type": "INITIAL_PURCHASE", "environment": "PRODUCTION"},
        }
        with self.assertRaisesRegex(dev_service.WebhookValidationError, "SANDBOX"):
            dev_service.validate_webhook(document)

    def test_webhook_ledger_is_idempotent_and_does_not_store_raw_event_id(self) -> None:
        ledger = dev_service.WebhookLedger(self.root)
        event_id = "sensitive-customer-correlatable-event-id"
        self.assertTrue(ledger.accept(event_id, "INITIAL_PURCHASE"))
        self.assertFalse(ledger.accept(event_id, "INITIAL_PURCHASE"))
        contents = ledger.path.read_text(encoding="utf-8")
        self.assertNotIn(event_id, contents)
        self.assertEqual(len(contents.splitlines()), 1)
        snapshot = json.loads(contents)
        self.assertEqual(set(snapshot), {"schema_version", "records"})
        self.assertEqual(len(snapshot["records"]), 1)
        self.assertEqual(
            set(snapshot["records"][0]),
            dev_service.WebhookLedger.RECORD_KEYS,
        )
        ledger.close()

        restarted = dev_service.WebhookLedger(self.root)
        self.assertFalse(restarted.accept(event_id, "INITIAL_PURCHASE"))
        restarted.close()

    def test_webhook_ledger_refuses_same_id_with_different_payload_identity(self) -> None:
        ledger = dev_service.WebhookLedger(self.root)
        ledger.accept("same-event", "TEST", "1" * 64)
        before = ledger.path.read_bytes()
        with self.assertRaises(dev_service.WebhookIdentityConflict):
            ledger.accept("same-event", "TEST", "2" * 64)
        with self.assertRaises(dev_service.WebhookIdentityConflict):
            ledger.accept("same-event", "INITIAL_PURCHASE", "1" * 64)
        self.assertEqual(ledger.path.read_bytes(), before)
        ledger.close()

    def test_webhook_ledger_refuses_partial_and_non_exact_snapshots(self) -> None:
        snapshot_path = (
            self.root / ".dev" / "tmp" / dev_service.WebhookLedger.SNAPSHOT_NAME
        )
        snapshot_path.parent.mkdir(parents=True)
        invalid_documents: tuple[bytes, ...] = (
            b'{"schema_version":1,"records":[',
            b'{"schema_version":1,"schema_version":1,"records":[]}',
            json.dumps(
                {
                    "schema_version": 1,
                    "records": [
                        {
                            "schema_version": 1,
                            "event_id_sha256": "a" * 64,
                            "event_payload_sha256": "b" * 64,
                            "event_type": "TEST",
                            "environment": "SANDBOX",
                            "received_at": "2026-08-10T00:00:00.000Z",
                            "unexpected": True,
                        }
                    ],
                }
            ).encode("utf-8"),
            json.dumps(
                {
                    "schema_version": 1,
                    "records": [
                        {
                            "schema_version": 1,
                            "event_id_sha256": "a" * 64,
                            "event_payload_sha256": "b" * 64,
                            "event_type": "TEST",
                            "environment": "SANDBOX",
                            "received_at": "yesterday",
                        }
                    ],
                }
            ).encode("utf-8"),
        )
        for payload in invalid_documents:
            with self.subTest(payload=payload[:40]):
                snapshot_path.write_bytes(payload)
                with self.assertRaises(dev_service.ConfigurationError):
                    dev_service.WebhookLedger(self.root)
                snapshot_path.unlink()

    def test_webhook_ledger_write_and_file_fsync_failures_leave_no_partial_state(self) -> None:
        for failed_method in ("_write_all", "_fsync_file"):
            with self.subTest(failed_method=failed_method):
                ledger = dev_service.WebhookLedger(self.root)
                with mock.patch.object(ledger, failed_method, side_effect=OSError("injected")):
                    with self.assertRaises(OSError):
                        ledger.accept(f"event-{failed_method}", "TEST")
                self.assertFalse(ledger.path.exists())
                temporary_names = [
                    entry.name
                    for entry in ledger.path.parent.iterdir()
                    if entry.name.startswith(dev_service.WebhookLedger.TEMP_PREFIX)
                ]
                self.assertEqual(temporary_names, [])
                self.assertTrue(ledger.accept(f"recovered-{failed_method}", "TEST"))
                ledger.close()
                ledger.path.unlink()

    def test_webhook_ledger_directory_fsync_failure_reconciles_on_restart(self) -> None:
        ledger = dev_service.WebhookLedger(self.root)
        with mock.patch.object(ledger, "_fsync_directory", side_effect=OSError("injected")):
            with self.assertRaises(dev_service.LedgerPersistenceUncertain):
                ledger.accept("uncertain-event", "TEST")
        self.assertTrue(ledger.path.is_file())
        ledger.close()
        restarted = dev_service.WebhookLedger(self.root)
        self.assertFalse(restarted.accept("uncertain-event", "TEST"))
        restarted.close()

    def test_webhook_ledger_fails_closed_at_retention_bound(self) -> None:
        ledger = dev_service.WebhookLedger(self.root)
        with ledger.path.open("wb") as handle:
            handle.truncate(dev_service.MAX_LEDGER_BYTES)
        with self.assertRaises(OSError):
            ledger.accept("event-after-limit", "INITIAL_PURCHASE")

    def test_webhook_readiness_explicitly_disclaims_provider_verification(self) -> None:
        log_path = self.root / ".dev" / "logs" / "revenuecat-webhook.log"
        log_path.parent.mkdir(parents=True)
        dev_service.configure_service_logging(log_path, self.root, "revenuecat-webhook")
        with mock.patch.dict(os.environ, {}, clear=True):
            state = dev_service.ServiceState(
                dev_service.SERVICE_SPECS["revenuecat-webhook"],
                self.root,
                "127.0.0.1",
                4221,
                "d" * 32,
            )
        ready, payload = state.readiness()
        self.assertTrue(ready)
        verification = payload["checks"]["provider_verification"]
        self.assertIs(verification["verified"], False)
        self.assertEqual(verification["status"], "not_performed")
        state.webhook_ledger.close()  # type: ignore[union-attr]


class WebhookConfigurationTests(RepositoryLocalTempCase):
    def test_configured_webhook_token_rejects_non_printable_or_unbounded_values(self) -> None:
        invalid_values = (
            "",
            "too-short",
            "x" * 15,
            "contains space token",
            "contains\ttab-token",
            "contains\nnewline-token",
            "unicode-token-💳",
            "x" * 257,
        )
        for value in invalid_values:
            with self.subTest(value_length=len(value)):
                with mock.patch.dict(
                    os.environ, {"REVENUECAT_WEBHOOK_AUTH_TOKEN": value}, clear=True
                ):
                    with self.assertRaises(dev_service.ConfigurationError):
                        dev_service.ServiceState(
                            dev_service.SERVICE_SPECS["revenuecat-webhook"],
                            self.root,
                            "127.0.0.1",
                            4221,
                            "d" * 32,
                        )

    def test_configured_webhook_token_accepts_bounded_printable_ascii(self) -> None:
        token = "configured-token!"
        with mock.patch.dict(
            os.environ, {"REVENUECAT_WEBHOOK_AUTH_TOKEN": token}, clear=True
        ):
            state = dev_service.ServiceState(
                dev_service.SERVICE_SPECS["revenuecat-webhook"],
                self.root,
                "127.0.0.1",
                4221,
                "d" * 32,
            )
        self.assertEqual(state.webhook_auth_token, token)
        state.webhook_ledger.close()  # type: ignore[union-attr]


class HTTPServiceContractTests(RepositoryLocalTempCase):
    def tearDown(self) -> None:
        for handler in tuple(dev_service.SERVICE_LOGGER.handlers):
            handler.close()
            dev_service.SERVICE_LOGGER.removeHandler(handler)
        super().tearDown()

    @contextmanager
    def running_service(
        self,
        service_name: str,
        *,
        webhook_auth_token: str | None = None,
        instance_token: str = "e" * 32,
    ) -> Iterator[tuple[dev_service.ServiceState, int, Path]]:
        log_path = self.root / ".dev" / "logs" / f"{service_name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        dev_service.configure_service_logging(log_path, self.root, service_name)
        service_environment = (
            {"REVENUECAT_WEBHOOK_AUTH_TOKEN": webhook_auth_token}
            if webhook_auth_token is not None
            else {}
        )
        with mock.patch.dict(os.environ, service_environment, clear=True):
            state = dev_service.ServiceState(
                dev_service.SERVICE_SPECS[service_name],
                self.root,
                "127.0.0.1",
                0,
                instance_token,
            )
        server = dev_service.BoundedThreadingHTTPServer(
            ("127.0.0.1", 0), dev_service.RequestHandler, state
        )
        port = int(server.server_address[1])
        state.port = port
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
        thread.start()
        try:
            yield state, port, log_path
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)
            self.assertFalse(thread.is_alive())
            if state.webhook_ledger is not None:
                state.webhook_ledger.close()

    def json_request(
        self,
        port: int,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, object], dict[str, str]]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2.0)
        request_headers = dict(headers or {})
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        payload = response.read()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        status = response.status
        connection.close()
        return status, json.loads(payload.decode("utf-8")), response_headers

    def test_webhook_is_deterministically_unconfigured_without_explicit_adapter_config(self) -> None:
        body = json.dumps(
            {
                "api_version": "1.0",
                "event": {"id": "event-unconfigured", "type": "TEST", "environment": "SANDBOX"},
            }
        ).encode("utf-8")
        with self.running_service("revenuecat-webhook") as (_state, port, _log_path):
            status, document, _headers = self.json_request(
                port,
                "POST",
                "/webhooks/revenuecat",
                body=body,
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(status, 503)
        self.assertEqual(document["error"]["code"], "webhook_auth_not_configured")  # type: ignore[index]

    def test_configured_webhook_auth_accepts_and_deduplicates_sandbox_event(self) -> None:
        event_id = "configured-idempotency-event"
        body = json.dumps(
            {
                "api_version": "1.0",
                "event": {"id": event_id, "type": "TEST", "environment": "SANDBOX"},
            }
        ).encode("utf-8")
        headers = {
            "Authorization": "Bearer configured-secret",
            "Content-Type": "application/json",
        }
        with self.running_service(
            "revenuecat-webhook", webhook_auth_token="configured-secret"
        ) as (state, port, _log_path):
            first_status, first, _ = self.json_request(
                port, "POST", "/webhooks/revenuecat", body=body, headers=headers
            )
            second_status, second, _ = self.json_request(
                port, "POST", "/webhooks/revenuecat", body=body, headers=headers
            )
        self.assertEqual(first_status, 202)
        self.assertEqual(first["duplicate"], False)
        self.assertEqual(second_status, 200)
        self.assertEqual(second["duplicate"], True)
        self.assertIsNotNone(state.webhook_ledger)
        ledger = state.webhook_ledger.path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        self.assertNotIn(event_id, ledger)
        self.assertEqual(len(ledger.splitlines()), 1)

    def test_shutdown_requires_raw_token_but_readiness_exposes_only_digest(self) -> None:
        raw_token = "raw-control-token-must-not-be-logged"
        with self.running_service(
            "test-patterns", instance_token=raw_token
        ) as (_state, port, log_path):
            ready_status, readiness, _ = self.json_request(port, "GET", "/health/ready")
            self.assertEqual(ready_status, 200)
            self.assertNotIn("instance_token", readiness)
            self.assertEqual(
                readiness["instance_token_sha256"],
                hashlib.sha256(raw_token.encode("ascii")).hexdigest(),
            )
            refused_status, refused, _ = self.json_request(
                port,
                "POST",
                "/__devctl/shutdown",
                body=b"",
                headers={dev_service.DEVCTL_TOKEN_HEADER: "wrong-token-value"},
            )
            self.assertEqual(refused_status, 401)
            self.assertEqual(refused["error"]["code"], "shutdown_auth_failed")  # type: ignore[index]
            accepted_status, accepted, _ = self.json_request(
                port,
                "POST",
                "/__devctl/shutdown",
                body=b"",
                headers={dev_service.DEVCTL_TOKEN_HEADER: raw_token},
            )
            self.assertEqual(accepted_status, 202)
            self.assertIs(accepted["shutdown_requested"], True)
        log_contents = log_path.read_text(encoding="utf-8")
        self.assertNotIn(raw_token, log_contents)
        self.assertNotIn("wrong-token-value", log_contents)

    def test_request_logs_include_safe_outcome_and_refusal_fields(self) -> None:
        with self.running_service("test-patterns") as (_state, port, log_path):
            status, _document, response_headers = self.json_request(
                port, "GET", "/patterns/flicker?hz=500"
            )
            self.assertEqual(status, 400)
            request_id = response_headers["x-request-id"]
        records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
        record = records[-1]
        self.assertEqual(record["event"], "local_http_request")
        self.assertEqual(record["correlation_id"], request_id)
        self.assertRegex(record["correlation_id"], r"^[0-9a-f]{32}$")
        self.assertEqual(record["status"], 400)
        self.assertEqual(record["refusal_code"], "invalid_request")
        self.assertEqual(record["route_id"], "pattern_flicker")
        self.assertNotIn("path", record)
        self.assertGreaterEqual(record["duration_ms"], 0.0)
        self.assertNotIn("hz=500", json.dumps(record))

    def test_unmatched_secret_path_and_query_are_never_persisted(self) -> None:
        secret = "raw-secret-path-value-never-log"
        with self.running_service("test-patterns") as (_state, port, log_path):
            status, _document, _headers = self.json_request(
                port, "GET", f"/{secret}?token={secret}"
            )
            self.assertEqual(status, 404)
        log_contents = log_path.read_text(encoding="utf-8")
        self.assertNotIn(secret, log_contents)
        record = json.loads(log_contents.splitlines()[-1])
        self.assertEqual(record["route_id"], "unmatched")
        self.assertNotIn("path", record)

    def test_logger_failure_latches_readiness_unhealthy_until_reconfiguration(self) -> None:
        with self.running_service("test-patterns") as (state, port, log_path):
            with mock.patch.object(
                dev_service.SERVICE_LOGGER, "info", side_effect=OSError("injected")
            ):
                status, first, _ = self.json_request(port, "GET", "/health/ready")
            self.assertEqual(status, 503)
            self.assertEqual(first["checks"]["status"], "logging_unavailable")  # type: ignore[index]
            second_status, second, _ = self.json_request(port, "GET", "/health/ready")
            self.assertEqual(second_status, 503)
            self.assertEqual(second["checks"]["status"], "logging_unavailable")  # type: ignore[index]
            dev_service.configure_service_logging(log_path, self.root, "test-patterns")
            ready, recovered = state.readiness()
            self.assertTrue(ready)
            self.assertIs(recovered["ready"], True)

    def test_webhook_audit_failure_returns_uncertain_and_degrades_readiness(self) -> None:
        event_id = "audit-failure-event-id"
        body = json.dumps(
            {
                "api_version": "1.0",
                "event": {"id": event_id, "type": "TEST", "environment": "SANDBOX"},
            }
        ).encode("utf-8")
        headers = {
            "Authorization": "Bearer configured-secret",
            "Content-Type": "application/json",
        }
        with self.running_service(
            "revenuecat-webhook", webhook_auth_token="configured-secret"
        ) as (state, port, _log_path):
            with mock.patch.object(
                dev_service.SERVICE_LOGGER, "info", side_effect=OSError("injected")
            ):
                status, response, _ = self.json_request(
                    port, "POST", "/webhooks/revenuecat", body=body, headers=headers
                )
            self.assertEqual(status, 503)
            self.assertIs(response["accepted"], False)
            self.assertEqual(response["persistence_state"], "committed_audit_uncertain")
            self.assertEqual(response["error"]["code"], "webhook_audit_uncertain")  # type: ignore[index]
            readiness_status, readiness, _ = self.json_request(port, "GET", "/health/ready")
            self.assertEqual(readiness_status, 503)
            self.assertEqual(readiness["checks"]["status"], "logging_unavailable")  # type: ignore[index]
            self.assertIsNotNone(state.webhook_ledger)
            ledger_document = json.loads(state.webhook_ledger.path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
            self.assertEqual(len(ledger_document["records"]), 1)
            self.assertNotIn(event_id, json.dumps(ledger_document))

    def test_concurrency_saturation_returns_and_logs_bounded_503(self) -> None:
        log_path = self.root / ".dev" / "logs" / "test-patterns.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        dev_service.configure_service_logging(log_path, self.root, "test-patterns")
        state = dev_service.ServiceState(
            dev_service.SERVICE_SPECS["test-patterns"], self.root, "127.0.0.1", 0, "f" * 32
        )
        server = dev_service.BoundedThreadingHTTPServer(
            ("127.0.0.1", 0), dev_service.RequestHandler, state
        )

        class FakeSocket:
            def __init__(self) -> None:
                self.payload = b""
                self.timeout = 0.0

            def settimeout(self, timeout: float) -> None:
                self.timeout = timeout

            def sendall(self, payload: bytes) -> None:
                self.payload += payload

        fake = FakeSocket()
        for _ in range(dev_service.MAX_CONCURRENT_REQUESTS):
            self.assertTrue(server._request_slots.acquire(blocking=False))
        try:
            with mock.patch.object(server, "shutdown_request") as shutdown_request:
                server.process_request(fake, ("127.0.0.1", 12345))
            self.assertTrue(fake.payload.startswith(b"HTTP/1.1 503 Service Unavailable\r\n"))
            self.assertIn(b'"code":"concurrency_limit"', fake.payload)
            shutdown_request.assert_called_once_with(fake)
            log_record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(log_record["status"], 503)
            self.assertEqual(log_record["refusal_code"], "concurrency_limit")
            self.assertRegex(log_record["correlation_id"], r"^[0-9a-f]{32}$")
        finally:
            for _ in range(dev_service.MAX_CONCURRENT_REQUESTS):
                server._request_slots.release()
            server.server_close()


class LogRetentionTests(RepositoryLocalTempCase):
    def tearDown(self) -> None:
        for handler in tuple(dev_service.SERVICE_LOGGER.handlers):
            handler.close()
            dev_service.SERVICE_LOGGER.removeHandler(handler)
        super().tearDown()

    def log_path(self) -> Path:
        path = self.root / ".dev" / "logs" / "evaluation.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def test_structured_logs_rotate_with_a_hard_backup_count(self) -> None:
        path = self.log_path()
        dev_service.configure_service_logging(path, self.root, "evaluation")
        payload = "x" * 900
        for index in range(1_400):
            dev_service.emit_log({"event": "rotation_test", "index": index, "payload": payload})
        for handler in dev_service.SERVICE_LOGGER.handlers:
            handler.flush()
        retained = sorted(path.parent.glob("evaluation.log*"))
        self.assertGreaterEqual(len(retained), 2)
        self.assertLessEqual(len(retained), dev_service.LOG_BACKUP_COUNT + 1)
        self.assertTrue(all(item.stat().st_size <= dev_service.MAX_LOG_BYTES for item in retained))
        self.assertFalse(Path(f"{path}.{dev_service.LOG_BACKUP_COUNT + 1}").exists())

    def test_oversized_existing_log_fails_closed(self) -> None:
        path = self.log_path()
        with path.open("wb") as handle:
            handle.truncate(dev_service.MAX_LOG_BYTES + 1)
        with self.assertRaisesRegex(dev_service.ConfigurationError, "exceeds"):
            dev_service.configure_service_logging(path, self.root, "evaluation")

    def test_oversized_log_event_fails_closed(self) -> None:
        path = self.log_path()
        dev_service.configure_service_logging(path, self.root, "evaluation")
        with self.assertRaisesRegex(RuntimeError, "size bound"):
            dev_service.emit_log({"event": "oversized", "payload": "x" * dev_service.MAX_LOG_EVENT_BYTES})

    def test_log_symlink_is_refused(self) -> None:
        path = self.log_path()
        target = self.root / ".dev" / "tmp" / "target.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        path.symlink_to(target)
        with self.assertRaisesRegex(dev_service.ConfigurationError, "symlink"):
            dev_service.configure_service_logging(path, self.root, "evaluation")


class CommittedSurfaceTests(unittest.TestCase):
    def test_gitignore_contains_dev_directory_rule(self) -> None:
        lines = [line for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual(lines.count(".dev/"), 1)

    def test_playwright_uses_devctl_owned_complete_block_without_reuse(self) -> None:
        config = (REPO_ROOT / "playwright.config.ts").read_text(encoding="utf-8")
        self.assertIn("const testHarnessPort = 4222", config)
        self.assertIn("127.0.0.1", config)
        self.assertIn("testDir: './Tests/e2e'", config)
        self.assertIn("browserName: 'chromium'", config)
        self.assertIn("./.dev/pw-profile/storage-state.json", config)
        self.assertIn("python3 scripts/devctl.py e2e-server", config)
        self.assertIn("reuseExistingServer: false", config)
        self.assertIn("gracefulShutdown: { signal: 'SIGTERM'", config)
        self.assertIn("timeout: 45_000", config)
        self.assertGreaterEqual(
            45_000,
            int((len(devctl.SERVICES) * devctl.STOP_TIMEOUT_SECONDS + 5) * 1_000),
        )
        self.assertNotIn("TEST_WORKER_INDEX", config)
        self.assertNotIn("scripts/dev_service.py", config)
        self.assertNotIn("reuseExistingServer: true", config)
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("override PLAYWRIGHT_BROWSERS_PATH := $(DEV_CACHE_DIR)/ms-playwright", makefile)
        self.assertIn("playwright install chromium", makefile)

    def test_no_broad_process_kill_commands_exist(self) -> None:
        source = (REPO_ROOT / "scripts" / "devctl.py").read_text(encoding="utf-8")
        for prohibited in ("pkill", "killall", "docker system prune", "docker kill"):
            self.assertNotIn(prohibited, source)
        self.assertNotIn("os.kill(record.pid, signal.SIG", source)
        self.assertNotIn("signal.SIGKILL", source)


if __name__ == "__main__":
    unittest.main()
