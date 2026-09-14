import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from typer.testing import CliRunner

from preflight.cli import app
from preflight.dashboard import DashboardService, make_handler


def initialize(tmp_path: Path, monkeypatch) -> DashboardService:
    monkeypatch.chdir(tmp_path)
    assert CliRunner().invoke(app, ["init", "--non-interactive"]).exit_code == 0
    return DashboardService(tmp_path)


def test_dashboard_service_runs_and_lists_reference_results(tmp_path: Path, monkeypatch) -> None:
    service = initialize(tmp_path, monkeypatch)
    assert service.list_runs() == []
    record = service.run()
    assert record.result.gate_status == "PASS"
    assert record.result.verification_level == "reference_verified"
    loaded = service.get_run(record.result.run_id)
    assert loaded is not None
    assert loaded.result.model_dump() == record.result.model_dump()
    assert loaded.directory == record.directory
    assert service.get_run("../invalid") is None


def test_dashboard_http_flow_and_security_boundary(tmp_path: Path, monkeypatch) -> None:
    service = initialize(tmp_path, monkeypatch)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service, "known-token"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base) as response:
            home = response.read().decode()
            assert response.status == 200
            assert "Run reference verification" in home
            assert "No completed runs yet" in home
            assert "@media(max-width:37.5rem)" in home
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Referrer-Policy"] == "same-origin"
            assert "default-src 'none'" in response.headers["Content-Security-Policy"]

        invalid = urllib.request.Request(
            f"{base}/runs",
            data=urllib.parse.urlencode({"csrf": "invalid"}).encode(),
            method="POST",
        )
        try:
            urllib.request.urlopen(invalid)
            raise AssertionError("invalid CSRF token was accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403

        foreign = urllib.request.Request(
            f"{base}/runs",
            data=urllib.parse.urlencode({"csrf": "known-token"}).encode(),
            headers={"Origin": "https://example.invalid"},
            method="POST",
        )
        try:
            urllib.request.urlopen(foreign)
            raise AssertionError("foreign Origin was accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        request = urllib.request.Request(
            f"{base}/runs",
            data=urllib.parse.urlencode({"csrf": "known-token"}).encode(),
            headers={"Origin": base},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            detail = response.read().decode()
            assert response.status == 200
            assert "Decision:" in detail
            assert "reference_verified" in detail
            assert "Open standalone HTML report" in detail
            report_url = response.url + "/report"
        with urllib.request.urlopen(report_url) as response:
            report = response.read().decode()
            assert response.status == 200
            assert "Reference verification only" in report
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_dashboard_missing_config_and_invalid_suite_are_observable(
    tmp_path: Path, monkeypatch
) -> None:
    missing = DashboardService(tmp_path)
    handler = make_handler(missing, "token")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}") as response:
            assert "Configuration unavailable" in response.read().decode()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    service = initialize(tmp_path, monkeypatch)
    try:
        service.run(["unknown"])
        raise AssertionError("unknown suite was accepted")
    except ValueError as exc:
        assert str(exc) == "CORE_EXTERNAL_NOT_ENABLED"
