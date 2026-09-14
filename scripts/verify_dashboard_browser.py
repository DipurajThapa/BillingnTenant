"""Verify the local dashboard journey in native Chromium and Firefox."""

from __future__ import annotations

import json
import os
import secrets
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import yaml
from playwright.sync_api import ConsoleMessage, Request, sync_playwright

from preflight.config import ReferenceOverrides, example_config
from preflight.dashboard import DashboardService, make_handler

VIEWPORTS = (320, 375, 768, 1440)
BROWSERS = ("chromium", "firefox")


def build_workspace(output: Path) -> Path:
    workspace = output / "dashboard-workspace"
    config_root = workspace / ".preflight"
    config_root.mkdir(parents=True)
    (config_root / "core.yml").write_text(
        yaml.safe_dump(example_config().model_dump(mode="json", by_alias=True), sort_keys=False)
    )
    (config_root / "reference.yml").write_text(
        yaml.safe_dump(
            ReferenceOverrides().model_dump(mode="json", by_alias=True), sort_keys=False
        )
    )
    return workspace


def verify(output: Path) -> list[dict[str, object]]:
    workspace = build_workspace(output)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(DashboardService(workspace), secrets.token_urlsafe(32)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    evidence: list[dict[str, object]] = []
    try:
        with sync_playwright() as playwright:
            for browser_name in BROWSERS:
                browser = getattr(playwright, browser_name).launch()
                evidence.extend(check_browser(browser, browser_name, base_url, output))
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    failures = [row for row in evidence if not row["passed"]]
    (output / "dashboard-browser-matrix.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    if failures:
        raise SystemExit(f"dashboard browser verification failed: {json.dumps(failures)}")
    return evidence


def check_browser(browser, browser_name: str, base_url: str, output: Path):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    console_errors: list[str] = []
    prohibited_requests: list[str] = []

    def record_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            console_errors.append(message.text)

    def record_request(request: Request) -> None:
        if not request.url.startswith((base_url, "data:", "blob:")):
            prohibited_requests.append(request.url)

    page.on("console", record_console)
    page.on("request", record_request)
    page.goto(base_url, wait_until="load")
    page.get_by_role("button", name="Start verification").click()
    page.wait_for_url(f"{base_url}/runs/*", wait_until="load")
    run_url = page.url
    gate_visible = page.get_by_text("Decision: PASS", exact=False).is_visible()
    report_link_visible = page.get_by_role(
        "link", name="Open standalone HTML report"
    ).is_visible()
    results: list[dict[str, object]] = []
    for width in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": 900})
        page.goto(run_url, wait_until="load")
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        table_visible = page.get_by_role("table").is_visible()
        page.screenshot(
            path=output / f"dashboard-{browser_name}-{width}px.png", full_page=True
        )
        row = {
            "browser": browser_name,
            "width": width,
            "pageOverflow": overflow,
            "gateVisible": gate_visible,
            "reportLinkVisible": report_link_visible,
            "tableVisible": table_visible,
            "consoleErrors": list(console_errors),
            "prohibitedRequests": list(prohibited_requests),
            "screenshot": f"dashboard-{browser_name}-{width}px.png",
        }
        row["passed"] = not (
            overflow
            or not gate_visible
            or not report_link_visible
            or not table_visible
            or console_errors
            or prohibited_requests
        )
        results.append(row)
    page.close()
    context.close()
    return results


def main() -> None:
    output = Path(os.environ.get("PREFLIGHT_BROWSER_EVIDENCE", "browser-artifacts")).resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence = verify(output)
    print(f"dashboard browser verification passed: {len(evidence)} browser/viewport modes")


if __name__ == "__main__":
    main()
