from pathlib import Path

from preflight.config import example_config
from preflight.engine import execute, render_html


def test_core_source_has_no_external_provider_or_network_dependency() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("src").rglob("*.py"))
    imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
    forbidden = ("stripe", "supabase", "requests", "httpx", "socket")
    assert not any(name in line.lower() for line in imports for name in forbidden)


def test_report_is_offline_responsive_and_escapes_rendered_text() -> None:
    result = execute(example_config())
    result.results[0].test_id = "<script>alert(1)</script>"
    html = render_html(result)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "max-width:600px" in html
    assert "width=device-width" in html
    assert "http://" not in html and "https://" not in html


def test_every_deferred_scope_is_explicitly_unverified() -> None:
    result = execute(example_config())
    assert set(result.unverified_scopes) == {
        "stripe",
        "supabase",
        "remote_http",
        "github_actions",
        "formal_accessibility",
        "cpanel",
    }
    assert result.execution_profile == "reference"
