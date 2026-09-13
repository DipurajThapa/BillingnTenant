"""Render and verify the offline report in native Chromium viewports."""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import ConsoleMessage, Request, sync_playwright

from preflight.config import example_config
from preflight.engine import execute, write_artifacts

VIEWPORTS = (320, 375, 768, 1440)
BROWSERS = ("chromium", "firefox")
REQUIRED_HEADINGS = (
    "Run provenance",
    "Decision summary",
    "Incomplete causes",
    "Findings",
    "Scenario coverage",
    "Fixture and cleanup",
    "Limitations",
)


def build_report(output: Path) -> Path:
    workspace = output / "workspace"
    workspace.mkdir()
    previous = Path.cwd()
    try:
        os.chdir(workspace)
        run_dir = write_artifacts(execute(example_config()), Path("artifacts"))
        return (workspace / run_dir / "preflight-report.html").resolve()
    finally:
        os.chdir(previous)


def verify(output: Path) -> list[dict[str, object]]:
    report = build_report(output)
    evidence: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        for browser_name in BROWSERS:
            browser_type = getattr(playwright, browser_name)
            browser = browser_type.launch()
            for width in VIEWPORTS:
                evidence.append(check_page(browser, browser_name, width, report, output))
            evidence.append(check_page(browser, browser_name, 320, report, output, enhanced=True))
            browser.close()

    failures = [row for row in evidence if not row["passed"]]
    (output / "browser-matrix.json").write_text(json.dumps(evidence, indent=2) + "\n")
    if failures:
        raise SystemExit(f"browser report verification failed: {json.dumps(failures)}")
    return evidence


def check_page(browser, browser_name, width, report, output, *, enhanced=False):
    context = browser.new_context(
        viewport={"width": width, "height": 900},
        forced_colors="active" if enhanced else "none",
    )
    page = context.new_page()
    console_errors: list[str] = []
    external_requests: list[str] = []

    def record_console(message: ConsoleMessage, errors: list[str] = console_errors) -> None:
        if message.type == "error":
            errors.append(message.text)

    def record_request(request: Request, requests: list[str] = external_requests) -> None:
        if not request.url.startswith(("file:", "data:", "blob:")):
            requests.append(request.url)

    page.on("console", record_console)
    page.on("request", record_request)
    page.goto(report.as_uri(), wait_until="load")
    if enhanced:
        page.add_style_tag(
            content="*{line-height:1.5!important;letter-spacing:.12em!important;"
            "word-spacing:.16em!important}p{margin-bottom:2em!important}"
        )

    headings = page.locator("h2").all_text_contents()
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in headings]
    overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    banner_visible = page.get_by_text("Reference verification only.", exact=True).is_visible()
    table_visible = page.get_by_role("table").is_visible()

    page.locator("body").press("Home")
    page.keyboard.press("Tab")
    first_focus = page.evaluate("document.activeElement.className")
    page.keyboard.press("Enter")
    skip_target = page.evaluate("document.activeElement.id")
    page.keyboard.press("Tab")
    next_focus = page.evaluate("document.activeElement.className")

    mode = "enhanced" if enhanced else "normal"
    screenshot = output / f"report-{browser_name}-{width}px-{mode}.png"
    page.screenshot(path=screenshot, full_page=True)
    result = {
        "browser": browser_name,
        "width": width,
        "mode": mode,
        "pageOverflow": overflow,
        "missingHeadings": missing,
        "bannerVisible": banner_visible,
        "tableVisible": table_visible,
        "firstFocus": first_focus,
        "skipTarget": skip_target,
        "nextFocus": next_focus,
        "consoleErrors": console_errors,
        "externalRequests": external_requests,
        "screenshot": screenshot.name,
    }
    result["passed"] = not (
        result["pageOverflow"]
        or result["missingHeadings"]
        or not result["bannerVisible"]
        or not result["tableVisible"]
        or result["firstFocus"] != "skip"
        or result["skipTarget"] != "main"
        or result["nextFocus"] != "table-wrap"
        or result["consoleErrors"]
        or result["externalRequests"]
    )
    page.close()
    context.close()
    return result


def main() -> None:
    output = Path(os.environ.get("PREFLIGHT_BROWSER_EVIDENCE", "browser-artifacts")).resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence = verify(output)
    print(f"browser report verification passed: {len(evidence)} browser/viewport modes")


if __name__ == "__main__":
    main()
