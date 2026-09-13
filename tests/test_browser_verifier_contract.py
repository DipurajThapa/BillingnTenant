import ast
from pathlib import Path


def test_browser_verifier_covers_required_matrix_and_checks() -> None:
    path = Path("scripts/verify_report_browser.py")
    source = path.read_text()
    ast.parse(source)
    assert "VIEWPORTS = (320, 375, 768, 1440)" in source
    for check in (
        "pageOverflow",
        "missingHeadings",
        "bannerVisible",
        "tableVisible",
        "firstFocus",
        "skipTarget",
        "consoleErrors",
        "externalRequests",
    ):
        assert check in source


def test_browser_dependency_is_not_a_core_requirement() -> None:
    project = Path("pyproject.toml").read_text()
    dependencies = project.split("[project.optional-dependencies]", 1)[0]
    assert "playwright" not in dependencies.lower()
