#!/usr/bin/env python3
"""Exercise the four running development surfaces and their honest refusals."""

from __future__ import annotations

import json
import hashlib
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import devctl
from tools.check_policy import EXPECTED_PORTS


HOST = "127.0.0.1"
SERVICE_BY_KEY = {
    "PORT_0": "evaluation",
    "PORT_1": "revenuecat-webhook",
    "PORT_2": "test-patterns",
    "PORT_3": "artifacts",
}


class ProbeFailure(RuntimeError):
    """The integration surface did not honor its typed contract."""


class RedirectRefusingHandler(urlrequest.HTTPRedirectHandler):
    """Never forward a local probe or its headers across an HTTP redirect."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        return None


def open_exact_loopback(request: urlrequest.Request, timeout: float) -> Any:
    """Open an exact IPv4-loopback URL without environment proxy behavior."""

    parsed = urlsplit(request.full_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != HOST
        or parsed.port not in EXPECTED_PORTS.values()
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProbeFailure("probe URL is outside the repository's exact service allocation")
    opener = urlrequest.build_opener(urlrequest.ProxyHandler({}), RedirectRefusingHandler())
    try:
        opened = opener.open(request, timeout=timeout)
    except urlerror.HTTPError as error:
        if error.geturl() != request.full_url or 300 <= error.code < 400:
            error.close()
            raise ProbeFailure("probe response attempted to change its exact URL") from error
        opened = error
    if opened.geturl() != request.full_url:
        opened.close()
        raise ProbeFailure("probe response final URL changed")
    return opened


def response(method: str, port: int, path: str, body: bytes | None = None) -> tuple[int, str, bytes]:
    headers = {"Accept": "application/json", "Connection": "close"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urlrequest.Request(
        f"http://{HOST}:{port}{path}", data=body, headers=headers, method=method
    )
    opened = open_exact_loopback(request, timeout=2.0)
    with opened:
        payload = opened.read(1_048_577)
        if len(payload) > 1_048_576:
            raise ProbeFailure(f"{method} {path} exceeded response limit")
        return opened.status, opened.headers.get_content_type(), payload


def json_response(method: str, port: int, path: str, body: bytes | None = None) -> tuple[int, Any]:
    status, content_type, payload = response(method, port, path, body)
    if content_type != "application/json":
        raise ProbeFailure(f"{method} {path} returned {content_type}, expected application/json")
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProbeFailure(f"{method} {path} returned invalid JSON") from error
    return status, document


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeFailure(message)


def run() -> list[str]:
    outcomes: list[str] = []
    root = REPOSITORY_ROOT
    for key, port in EXPECTED_PORTS.items():
        service = SERVICE_BY_KEY[key]
        try:
            record = devctl.read_pid_record(root, service)
        except devctl.DevContractError as error:
            raise ProbeFailure(f"{service} PID record refused [{error.code}]") from error
        require(record is not None, f"{service} PID record is missing")
        assert record is not None
        require(record.host == HOST and record.port == port, f"{service} PID allocation mismatch")
        require(devctl.process_is_alive(record.pid), f"{service} recorded process is not alive")
        require(devctl.process_matches_record(record), f"{service} process ownership is unproven")
        expected_digest = hashlib.sha256(record.instance_token.encode("ascii")).hexdigest()
        status, document = json_response("GET", port, "/health/ready")
        require(status == HTTPStatus.OK, f"{service} readiness returned {status}")
        require(document.get("ready") is True, f"{service} did not report ready")
        require(document.get("service") == service, f"{service} identity mismatch")
        require(document.get("bind_host") == HOST, f"{service} bind host mismatch")
        require(document.get("port") == port, f"{service} port mismatch")
        require(
            document.get("readiness_scope") == "local_development_surface",
            f"{service} readiness scope is dishonest",
        )
        require(
            document.get("production_verified") is False,
            f"{service} must not report production verification",
        )
        require("instance_token" not in document, f"{service} leaked its raw ownership token")
        require(
            document.get("instance_token_sha256") == expected_digest,
            f"{service} readiness digest does not match its owned PID record",
        )
        outcomes.append(f"ready:{service}:{port}")

    status, evaluation = json_response("GET", EXPECTED_PORTS["PORT_0"], "/api/evaluation")
    require(status == HTTPStatus.OK, "evaluation API failed")
    require(
        evaluation.get("data_status")
        in {"not_yet_available", "quarantined_unreplayed_evidence"},
        "evaluation API returned an unknown provenance state",
    )
    cells = evaluation.get("cells")
    require(isinstance(cells, list), "evaluation cells are not an array")
    require(evaluation.get("matrix_cells") == len(cells), "evaluation count does not match rows")
    require(cells == [], "evaluation must not surface empirical rows before committed replay")
    require(evaluation.get("matrix_cells") == 0, "unreplayed evaluation must report zero cells")
    if evaluation.get("data_status") == "quarantined_unreplayed_evidence":
        require(evaluation.get("generator_replayed") is False, "quarantine must record no replay")
        require(
            evaluation.get("quarantine_reason") == "no_committed_replay_verifier",
            "evaluation quarantine reason is missing",
        )
    outcomes.append(f"evaluation:{evaluation.get('data_status')}:cells={len(cells)}")

    status, content_type, pattern = response(
        "GET", EXPECTED_PORTS["PORT_2"], "/patterns/moire.svg?spacing=4&angle=17"
    )
    require(status == HTTPStatus.OK, "moire pattern failed")
    require(content_type == "image/svg+xml", "moire pattern is not SVG")
    require(pattern.startswith(b"<svg"), "moire pattern has an unexpected body")
    outcomes.append("pattern:moire:original-svg")

    status, refusal = json_response(
        "GET", EXPECTED_PORTS["PORT_2"], "/patterns/flicker?hz=500"
    )
    require(status == HTTPStatus.BAD_REQUEST, "out-of-range flicker frequency was not refused")
    require(
        refusal.get("error", {}).get("code") == "invalid_request",
        "flicker refusal did not use the stable error code",
    )
    outcomes.append("refusal:flicker-frequency:400")

    status, artifacts = json_response("GET", EXPECTED_PORTS["PORT_3"], "/api/artifacts")
    require(status == HTTPStatus.OK, "artifact API failed")
    require(isinstance(artifacts.get("artifacts"), list), "artifact inventory is not an array")
    require(
        artifacts.get("artifact_count") == len(artifacts["artifacts"]),
        "artifact count does not match inventory",
    )
    outcomes.append(f"artifacts:observed:count={artifacts.get('artifact_count')}")

    webhook_body = json.dumps(
        {"event": {"id": "integration-event-0001", "type": "TEST"}}
    ).encode("utf-8")
    status, webhook_refusal = json_response(
        "POST",
        EXPECTED_PORTS["PORT_1"],
        "/webhooks/revenuecat",
        webhook_body,
    )
    require(
        status == HTTPStatus.SERVICE_UNAVAILABLE,
        "unconfigured webhook authentication did not fail closed",
    )
    require(
        webhook_refusal.get("error", {}).get("code") == "webhook_auth_not_configured",
        "webhook refusal did not use the stable error code",
    )
    outcomes.append("refusal:webhook-auth-unconfigured:503")

    return outcomes


def main() -> int:
    try:
        outcomes = run()
    except (OSError, ProbeFailure) as error:
        print(f"integration-probe:error:{error}", file=sys.stderr)
        return 1
    print("integration-probe:ok")
    for outcome in outcomes:
        print(f"  {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
