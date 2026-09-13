from html.parser import HTMLParser

from preflight.config import example_config
from preflight.engine import execute, render_html


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data: str) -> None:
        self.text.append(data.strip())


def report() -> tuple[str, StructureParser]:
    html = render_html(execute(example_config()))
    parser = StructureParser()
    parser.feed(html)
    return html, parser


def test_document_language_title_landmarks_and_skip_link() -> None:
    html, parser = report()
    assert ("html", {"lang": "en"}) in parser.tags
    assert any(tag == "title" for tag, _ in parser.tags)
    assert any(tag == "main" and attrs.get("id") == "main" for tag, attrs in parser.tags)
    assert any(tag == "a" and attrs.get("href") == "#main" for tag, attrs in parser.tags)
    assert html.count("<h1>") == 1


def test_table_has_caption_scoped_headers_and_keyboard_scroll_region() -> None:
    _html, parser = report()
    assert any(tag == "caption" for tag, _ in parser.tags)
    assert any(tag == "th" and attrs.get("scope") == "col" for tag, attrs in parser.tags)
    assert any(tag == "th" and attrs.get("scope") == "row" for tag, attrs in parser.tags)
    assert any(
        tag == "div" and attrs.get("role") == "region" and attrs.get("tabindex") == "0"
        for tag, attrs in parser.tags
    )


def test_status_and_scope_are_available_as_text_not_color_only() -> None:
    _html, parser = report()
    text = " ".join(value for value in parser.text if value)
    assert "Final gate: PASS" in text
    assert "Reference verification only." in text
    assert "PASSED" in text
    assert "Decision summary" in text
    assert "Incomplete causes" in text
    assert "Findings" in text
    assert "Fixture and cleanup" in text
    assert "Limitations" in text


def test_reflow_focus_contrast_and_user_spacing_compatibility_rules_exist() -> None:
    html, _parser = report()
    assert "@media(max-width:37.5rem)" in html
    assert ":focus-visible" in html
    assert "overflow-x:auto" in html
    assert "line-height" not in html
    assert "font:1rem/1.6" in html
    assert "user-scalable=no" not in html
