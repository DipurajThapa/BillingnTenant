# ruff: noqa: E501
"""Local-only dashboard boundary for the deterministic reference engine."""

from __future__ import annotations

import html
import re
import secrets
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from preflight.config import CoreConfig, load_config, resolve_suites
from preflight.engine import execute, write_artifacts
from preflight.models import RunResult

RUN_ID = re.compile(r"[0-9a-f]{32}")
MAX_FORM_BYTES = 4096


@dataclass(frozen=True)
class RunRecord:
    result: RunResult
    directory: Path


class DashboardService:
    """Framework-neutral application service retained for a later hosted shell."""

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.config_path = self.workspace / ".preflight" / "core.yml"
        self._run_lock = threading.Lock()

    def config(self) -> CoreConfig:
        return load_config(self.config_path)

    def list_runs(self) -> list[RunRecord]:
        try:
            root = (self.workspace / self.config().artifact_directory).resolve()
        except (OSError, ValueError):
            return []
        if not root.is_relative_to(self.workspace) or not root.exists():
            return []
        records: list[RunRecord] = []
        for path in root.iterdir():
            if not path.is_dir() or not RUN_ID.fullmatch(path.name):
                continue
            try:
                result = RunResult.model_validate_json(
                    (path / "run.json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                continue
            if result.run_id == path.name:
                records.append(RunRecord(result, path))
        return sorted(records, key=lambda item: item.result.started_at, reverse=True)

    def get_run(self, run_id: str) -> RunRecord | None:
        if not RUN_ID.fullmatch(run_id):
            return None
        return next((item for item in self.list_runs() if item.result.run_id == run_id), None)

    def run(self, suites: list[str] | None = None) -> RunRecord:
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("DASH_RUN_BUSY")
        try:
            config = self.config()
            selected = resolve_suites(suites, config.features.metered_usage) if suites else None
            result = execute(config, suites=selected)
            directory = write_artifacts(result, self.workspace / config.artifact_directory)
            return RunRecord(result, directory.resolve())
        finally:
            self._run_lock.release()


def _layout(title: str, body: str) -> bytes:
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>{html.escape(title)} · SaaS Preflight</title>
<style>
:root{{--ink:#172033;--muted:#526078;--line:#d8dee9;--paper:#f6f4ef;--card:#fff;--accent:#4c1d68;
--pass:#176b3a;--warn:#7a4b00;--fail:#a51d2d}}*{{box-sizing:border-box}}body{{margin:0;
font:1rem/1.55 system-ui,sans-serif;color:var(--ink);background:var(--paper)}}header,main,footer{{
max-width:72rem;margin:auto;padding:1rem}}header{{display:flex;justify-content:space-between;align-items:center;
gap:1rem}}a{{color:#005fcc}}.card{{background:var(--card);border:1px solid var(--line);border-radius:.75rem;
padding:1rem;margin-bottom:1rem}}h1{{font-size:clamp(1.6rem,4vw,2.4rem)}}h2{{font-size:1.2rem}}
button{{background:var(--accent);color:#fff;border:0;border-radius:.4rem;padding:.65rem 1rem;font:inherit;
cursor:pointer}}button:focus-visible,a:focus-visible{{outline:3px solid #005fcc;outline-offset:3px}}
.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse}}th,td{{padding:.65rem;text-align:left;
border-bottom:1px solid var(--line)}}.PASS{{color:var(--pass)}}.WARN{{color:var(--warn)}}
.FAIL,.INCOMPLETE{{color:var(--fail)}}.muted{{color:var(--muted)}}.error{{border-left:4px solid var(--fail)}}
fieldset{{border:0;padding:0;margin:0 0 1rem}}label{{display:inline-block;margin:.25rem .8rem .25rem 0}}
@media(max-width:37.5rem){{header{{display:block}}th,td{{white-space:nowrap}}}}
</style></head><body><header><strong>SaaS Preflight</strong><nav aria-label="Primary"><a href="/">Runs</a></nav>
</header><main><h1>{html.escape(title)}</h1>{body}</main><footer class="muted">Local reference dashboard · External
providers are not implied by reference results.</footer></body></html>"""
    return document.encode()


def _home(service: DashboardService, csrf_token: str, message: str = "") -> bytes:
    try:
        config = service.config()
        suite_inputs = "".join(
            f'<label><input type="checkbox" name="suite" value="{html.escape(name)}"> '
            f"{html.escape(name)}</label>"
            for name in config.suites.enabled
        )
        form = f"""<section class="card"><h2>Run reference verification</h2>
<p>Leave every suite unchecked to use the approved configuration.</p><form method="post" action="/runs">
<input type="hidden" name="csrf" value="{csrf_token}"><fieldset><legend>Optional suite override</legend>
{suite_inputs}</fieldset><button type="submit">Start verification</button></form></section>"""
    except (OSError, ValueError) as exc:
        form = f'<section class="card error"><h2>Configuration unavailable</h2><p>{html.escape(str(exc))}</p>' \
            '<p>Run <code>preflight init</code>, correct the configuration, and reload.</p></section>'
    rows = "".join(
        f'<tr><td><a href="/runs/{item.result.run_id}">{item.result.run_id[:8]}</a></td>'
        f'<td class="{item.result.gate_status}">{item.result.gate_status}</td>'
        f"<td>{item.result.summary.passed}</td><td>{item.result.summary.failed}</td>"
        f"<td>{html.escape(item.result.started_at.isoformat())}</td></tr>"
        for item in service.list_runs()
    ) or '<tr><td colspan="5">No completed runs yet.</td></tr>'
    notice = f'<p class="card">{html.escape(message)}</p>' if message else ""
    body = f"""{notice}{form}<section class="card"><h2>Run history</h2><div class="table-wrap">
<table><caption>Verified reference runs in this workspace</caption><thead><tr><th>Run</th><th>Gate</th>
<th>Passed</th><th>Failed</th><th>Started</th></tr></thead><tbody>{rows}</tbody></table></div></section>"""
    return _layout("Verification dashboard", body)


def _run_detail(record: RunRecord) -> bytes:
    result = record.result
    rows = "".join(
        f"<tr><th scope=\"row\">{html.escape(row.test_id)}</th><td>{html.escape(row.suite)}</td>"
        f'<td>{html.escape(row.status)}</td><td>{html.escape(row.severity)}</td></tr>'
        for row in result.results
    )
    scopes = ", ".join(html.escape(value) for value in result.unverified_scopes) or "None"
    body = f"""<section class="card"><p class="{result.gate_status}"><strong>Decision:
{result.gate_status}</strong></p><dl><dt>Run ID</dt><dd><code>{result.run_id}</code></dd>
<dt>Verification level</dt><dd>{html.escape(result.verification_level)}</dd><dt>Unverified scopes</dt>
<dd>{scopes}</dd></dl><p><a href="/runs/{result.run_id}/report">Open standalone HTML report</a></p></section>
<section class="card"><h2>Scenario results</h2><div class="table-wrap"><table><caption>Scenario outcomes</caption>
<thead><tr><th>Scenario</th><th>Suite</th><th>Status</th><th>Severity</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>"""
    return _layout(f"Run {result.run_id[:8]}", body)


def make_handler(service: DashboardService, csrf_token: str):
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "SaaSPreflightDashboard/0.1"

        def _send(self, status: int, body: bytes, content_type: str = "text/html; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
                "form-action 'self'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                self._send(HTTPStatus.OK, _home(service, csrf_token))
                return
            match = re.fullmatch(r"/runs/([0-9a-f]{32})(/report)?", path)
            record = service.get_run(match.group(1)) if match else None
            if record is None:
                self._send(HTTPStatus.NOT_FOUND, _layout("Not found", "<p>Run not found.</p>"))
                return
            if match and match.group(2):
                try:
                    report = (record.directory / "preflight-report.html").read_bytes()
                except OSError:
                    self._send(HTTPStatus.NOT_FOUND, _layout("Not found", "<p>Report not found.</p>"))
                    return
                self._send(HTTPStatus.OK, report)
                return
            self._send(HTTPStatus.OK, _run_detail(record))

        def do_POST(self):
            if urlsplit(self.path).path != "/runs":
                self._send(HTTPStatus.NOT_FOUND, _layout("Not found", "<p>Action not found.</p>"))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            origin = self.headers.get("Origin")
            allowed_origin = f"http://127.0.0.1:{self.server.server_port}"
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
            rejection = None
            if length < 1 or length > MAX_FORM_BYTES:
                rejection = "DASH_REQUEST_SIZE_INVALID"
            elif content_type != "application/x-www-form-urlencoded":
                rejection = "DASH_CONTENT_TYPE_INVALID"
            elif origin and origin != allowed_origin:
                rejection = "DASH_ORIGIN_INVALID"
            if rejection:
                self._send(
                    HTTPStatus.BAD_REQUEST,
                    _layout("Invalid request", f"<p>{rejection}: request rejected.</p>"),
                )
                return
            try:
                values = parse_qs(self.rfile.read(length).decode("utf-8", "strict"))
            except UnicodeDecodeError:
                self._send(HTTPStatus.BAD_REQUEST, _layout("Invalid request", "<p>Request rejected.</p>"))
                return
            if values.get("csrf") != [csrf_token]:
                self._send(HTTPStatus.FORBIDDEN, _layout("Forbidden", "<p>Invalid form token.</p>"))
                return
            try:
                record = service.run(values.get("suite"))
            except RuntimeError as exc:
                status = HTTPStatus.CONFLICT if str(exc) == "DASH_RUN_BUSY" else HTTPStatus.BAD_REQUEST
                self._send(status, _home(service, csrf_token, str(exc)))
                return
            except (OSError, ValueError) as exc:
                self._send(HTTPStatus.BAD_REQUEST, _home(service, csrf_token, str(exc)))
                return
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", f"/runs/{record.result.run_id}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            return

    return DashboardHandler


def serve_dashboard(workspace: Path, port: int) -> None:
    service = DashboardService(workspace)
    csrf_token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(service, csrf_token))
    print(f"Dashboard: http://127.0.0.1:{server.server_port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
