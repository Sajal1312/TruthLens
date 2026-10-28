"""Offline UI regression tests for untrusted retrieved webpage text."""
from streamlit.testing.v1 import AppTest

import verifier


def test_retrieved_markdown_and_html_are_rendered_as_plain_text(monkeypatch):
    claim = "The Eiffel Tower is located in Paris."
    title = "### Channel: Insane Curiosity **Source Title**"
    published_date = "## Published **today**"
    content = (
        "Why Does The Earth Orbit Around The Sun? ## Channel: Insane Curiosity ### Description 2023-01-17\n"
        "### Revolution of Earth Earth revolves in orbit around the Sun.\n\n"
        + ("Retrieved plain text. " * 45)
        + "\n<script>alert('not executed')</script> **bold text**"
    )
    ordinary_content = "An ordinary sentence with punctuation, dates, and numbers: 2026-10-25."
    results = [{
        "title": title,
        "url": "https://example.com/page",
        "content": content,
        "published_date": published_date,
    }, {
        "title": "Ordinary source title",
        "url": "https://example.org/ordinary",
        "content": ordinary_content,
        "published_date": "2025-06-01",
    }]
    assessed_content = []
    original_assess = verifier.assess_evidence

    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda _claim, _key: results)

    def record_assessment(source_claim, source_results):
        assessed_content.extend(item["content"] for item in source_results)
        return original_assess(source_claim, source_results)

    monkeypatch.setattr(verifier, "assess_evidence", record_assessment)

    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.button[0].click()
    app.run()

    assert not app.exception, [error.message for error in app.exception]
    plain_text_values = [element.value for element in app.text]
    assert "Channel: Insane Curiosity Source Title" in plain_text_values
    assert "Published: Published today" in plain_text_values
    displayed_text = "\n".join(plain_text_values)
    assert "Why Does The Earth Orbit Around The Sun? Channel: Insane Curiosity Description 2023-01-17" in displayed_text
    assert "Revolution of Earth Earth revolves in orbit around the Sun." in displayed_text
    assert "###" not in displayed_text and "##" not in displayed_text
    assert "**bold text**" not in "\n".join(plain_text_values)
    assert "<script>alert('not executed')</script> bold text" in "\n".join(plain_text_values)
    assert ordinary_content in plain_text_values
    assert "Ordinary source title" in plain_text_values
    short_text = next(value for value in plain_text_values if value.startswith("Why Does The Earth"))
    assert len(short_text) < len(content)
    assert any(item.label == "Show full retrieved snippet" for item in app.expander)
    assert assessed_content == [content, ordinary_content]

    markdown_values = [str(element.value) for element in app.markdown]
    assert not any("Channel: Insane Curiosity" in value or "### Revolution" in value for value in markdown_values)


def test_missing_tavily_key_shows_configuration_help_without_search(monkeypatch):
    claim = "The Eiffel Tower is located in Paris."
    searches = []
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: None)
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: searches.append(True))

    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.button[0].click()
    app.run()

    assert not app.exception, [error.message for error in app.exception]
    assert any("Tavily API key not found" in element.value for element in app.error)
    assert searches == []


def test_search_service_error_is_shown_as_friendly_message(monkeypatch):
    claim = "The Eiffel Tower is located in Paris."
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")

    def fail_search(*_args):
        raise verifier.VerificationError("Tavily search limit reached. Wait a little and try again.")

    monkeypatch.setattr(verifier, "search_evidence", fail_search)

    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.button[0].click()
    app.run()

    assert not app.exception, [error.message for error in app.exception]
    assert any("Tavily search limit reached" in element.value for element in app.error)
