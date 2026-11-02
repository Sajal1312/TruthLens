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


def test_short_claim_is_rejected_before_key_lookup_or_search(monkeypatch):
    calls = []
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: calls.append("key"))
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: calls.append("search"))

    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value("Sun orbits.")
    app.button[0].click()
    app.run()

    assert not app.exception, [error.message for error in app.exception]
    assert any("at least 12 characters" in item.value for item in app.warning)
    assert calls == []


def test_unexpected_search_exception_is_safely_reported(monkeypatch):
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")

    def fail_search(*_args):
        raise RuntimeError("internal detail should not reach the user")

    monkeypatch.setattr(verifier, "search_evidence", fail_search)
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value("The Eiffel Tower is located in Paris.")
    app.button[0].click()
    app.run()

    assert not app.exception, [error.message for error in app.exception]
    errors = "\n".join(item.value for item in app.error)
    assert "RuntimeError" in errors
    assert "internal detail should not reach the user" not in errors


def test_assessment_groups_evidence_roles_and_shows_provenance_notes(monkeypatch):
    claim = "The Eiffel Tower is located in Paris."
    results = [
        {"title": "Support source", "url": "https://example.com/support",
         "content": "The Eiffel Tower is located in Paris, France.", "published_date": "2025-01-01",
         "publisher": "Example publisher", "retrieved_at": "2026-11-01T10:00:00+00:00"},
        {"title": "Contradiction source", "url": "https://example.org/contradiction",
         "content": "The Eiffel Tower is not located in Paris.", "published_date": "", "retrieved_at": "2026-11-01T10:00:00+00:00"},
        {"title": "Unmatched source", "url": "https://example.net/unmatched",
         "content": "The tower attracts visitors from around the world.", "published_date": "",
         "retrieved_at": "2026-11-01T10:00:00+00:00"},
    ]
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda _claim, _key: results)

    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.button[0].click()
    app.run()

    assert not app.exception, [error.message for error in app.exception]
    assert "Evidence by assessment role" in [item.label for item in app.expander]
    assert "Source provenance notes" in [item.label for item in app.expander]
    displayed = "\n".join([str(item.value) for item in app.markdown] + [item.value for item in app.text])
    assert "Supporting passages" in displayed
    assert "Contradicting passages" in displayed
    assert "Excluded or not matched" in displayed
    assert "Publisher: Example publisher" in displayed


def test_explanation_section_uses_real_assessment_trace_and_escaped_highlights(monkeypatch):
    import nli_assessor

    claim = "The Eiffel Tower is located in Paris."
    results = [{
        "title": '<img src=x onerror="alert(1)"> Synthetic source',
        "url": "https://source-one.example/evidence",
        "content": 'The Eiffel Tower is located in Paris <script>alert("x")</script>, France.',
        "published_date": "", "updated_date": "2026-10-01",
    }, {
        "title": "Another synthetic source", "url": "https://source-two.example/guide",
        "content": "The Eiffel Tower is located in Paris near the Champ de Mars.",
        "published_date": "2025-02-01",
    }]
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: results)
    monkeypatch.setattr(nli_assessor, "load_local_nli_model", lambda: lambda *_args: {
        "label": "SUPPORTS", "confidence": .92, "margin": .60})

    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.checkbox[0].check()
    app.button[0].click()
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    text = "\n".join(item.value for item in why.text)
    assert "Verdict: Supported" in text
    assert "Raw NLI prediction: SUPPORTS" in text
    assert "Counted toward aggregation" in text
    assert "Publication date: Not returned" in text and "Update date: 2026-10-01" in text
    assert "URL: " + results[0]["url"] in text
    html_values = [item.value for item in why.markdown]
    assert any('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;' in value for value in html_values)
    assert not any("<script>" in value or "<img " in value for value in html_values)
    assert any('class="evidence-support"' in value for value in html_values)
    assert any("not calibrated probabilities" in item.value for item in why.caption)


def test_empty_search_explanation_keeps_claim_and_explains_absence(monkeypatch):
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: [])
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value("The Eiffel Tower is located in Paris.")
    app.checkbox[0].check()
    app.button[0].click()
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    text = "\n".join(item.value for item in why.text)
    assert "Claim: The Eiffel Tower is located in Paris." in text
    assert "Verdict: Inconclusive" in text
    assert any("Absence of evidence does not establish" in item.value for item in why.info)
    assert "Categories: Insufficient evidence" in text
    assert "Retrieved entries: 0" in text


def test_temporal_panel_warns_about_old_data_without_overriding_verdict(monkeypatch):
    claim = "Demo Lab currently employs 100 researchers."
    results = [{"title": "Synthetic dated source " + str(index),
                "url": "https://source-{0}.example/page".format(index),
                "content": "In 2019, Demo Lab currently employs 100 researchers, " + suffix,
                "published_date": "2026-01-01", "updated_date": "2026-10-01"}
               for index, suffix in enumerate(["according to this archived staffing list.",
                                              "according to a fictional old institutional record."])]
    expected = verifier.assess_evidence(claim, results)
    assert expected["verdict"] == "Supported"
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: results)
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.button[0].click()
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    assert any("Temporal Evidence Analysis" in item.value for item in why.markdown)
    text = "\n".join(item.value for item in why.text)
    assert "Verdict: Supported" in text
    assert "Claim temporal classification: current status" in text
    assert "may not establish current status" in text
    assert "Publication date: 2026-01-01" in text
    assert "Updated date: 2026-10-01" in text
    assert any("do not override the verdict" in item.value for item in why.caption)


def test_independence_panel_preserves_verdict_links_and_renders_untrusted_text_safely(monkeypatch):
    claim = "The Eiffel Tower is located in Paris."
    payload = "<script>alert(1)</script>"
    results = [{"title": '<img src=x onerror="alert(1)"> Synthetic source',
                "url": "https://one.example/article?utm_source=test",
                "content": 'The Eiffel Tower is located in Paris, France. According to NASA, a report titled "' + payload + '" is at https://reports.example/survey.'},
               {"title": "Another synthetic source", "url": "https://two.example/guide",
                "content": 'The Eiffel Tower is located in Paris near the Champ de Mars. Reuters reported a discussion of a report titled "' + payload + '" at https://reports.example/survey.'}]
    expected = verifier.assess_evidence(claim, results)
    assert expected["verdict"] == "Supported"
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: results)
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.button[0].click()
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    assert any("Evidence Independence Analysis" in item.value for item in why.markdown)
    displayed = "\n".join(item.value for item in why.text)
    assert "Verdict: Supported" in displayed and expected["reasoning"] in displayed
    assert "Distinct valid source URLs: 2" in displayed
    assert "Explicit shared-reference pairs: 1" in displayed
    table = why.dataframe[0].value
    assert {"observed", "heuristic"} <= set(table["Basis type"])
    assert any(payload in value for value in table["Recorded basis"])
    assert not any("<script>" in item.value or "<img " in item.value for item in app.markdown)
    assert any('href="https://one.example/article?utm_source=test"' in item.value for item in why.markdown)
    assert any("No independence is established" in item.value for item in why.caption)


def test_independence_panel_does_not_call_unrelated_sources_independent(monkeypatch):
    results = [{"title": "Synthetic source", "url": "https://one.example/a", "content": "A fictional budget committee met."},
               {"title": "Other synthetic source", "url": "https://two.example/b", "content": "An invented telescope schedule was archived."}]
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: results)
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value("The Eiffel Tower is located in Paris.")
    app.button[0].click()
    app.run()
    assert not app.exception
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    assert any("No dependency signal was detected. This does not establish independence." in item.value for item in why.caption)


def test_numerical_panel_shows_mismatch_and_compatible_values_without_overriding_nli(monkeypatch):
    import nli_assessor

    claim = "Class A pass rate in 2025 is 30%."
    results = [{"title": '<script>alert("title")</script> Synthetic record',
                "url": "https://one.example/record", "content": 'Class A pass rate in 2025 is 3%. <script>alert(1)</script>'},
               {"title": "Other synthetic record", "url": "https://two.example/record",
                "content": "Class A pass rate in 2025 is 30%."}]
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: results)
    # Deliberately imperfect mocked NLI: diagnostics must not replace its verdict.
    monkeypatch.setattr(nli_assessor, "load_local_nli_model", lambda: lambda *_args: {
        "label": "SUPPORTS", "confidence": .92, "margin": .60})
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.checkbox[0].check()
    app.button[0].click()
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    assert any("Numerical and Quantifier Analysis" in item.value for item in why.markdown)
    text = "\n".join(item.value for item in why.text)
    assert "Verdict: Supported" in text
    assert "Potential mismatch:" in text and "Compatible:" in text
    assert "Time expressions kept separate from quantities: 2025" in text
    assert "Claim Q1 · Evidence Q1" in text
    assert not any("<script>" in item.value for item in app.markdown)
    assert any("Diagnostic comparisons only" in item.value for item in why.caption)
    assert any("Evidence Sufficiency and Uncertainty" in item.value for item in why.markdown)
    assert "Primary uncertainty reason from the decision trace: Not determined" in text
    assert "Numerical ambiguity" in text
    assert any("Additional warnings are not asserted causes of the verdict" in item.value for item in why.caption)


def test_quantifier_panel_explains_some_does_not_disprove_all(monkeypatch):
    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: [{
        "title": "Synthetic class record", "url": "https://one.example/record",
        "content": "Some students in Class A passed."}])
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value("All students in Class A passed.")
    app.button[0].click()
    app.run()
    assert not app.exception
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    text = "\n".join(item.value for item in why.text)
    assert "neither establishes nor disproves all" in text
    assert "Comparison unresolved:" in text


def test_uncertainty_primary_reason_and_source_html_are_plain_text(monkeypatch):
    claim = "The Eiffel Tower is located in Paris."
    payload = '<script>alert("source")</script>'
    results = [{"title": '<img src=x onerror="bad"> Synthetic source', "url": "https://one.example/record",
                "content": "The Eiffel Tower is located in Paris, France."}]
    original = verifier.assess_evidence
    recorded = []

    def snapshot_reason(source_claim, sources):
        result = original(source_claim, sources)
        result["reasoning"] = payload + " " + result["reasoning"]
        recorded.append(result["reasoning"])
        return result

    monkeypatch.setattr(verifier, "get_tavily_key", lambda: "mock-key")
    monkeypatch.setattr(verifier, "search_evidence", lambda *_args: results)
    monkeypatch.setattr(verifier, "assess_evidence", snapshot_reason)
    app = AppTest.from_file("app.py", default_timeout=20).run()
    app.text_area[0].set_value(claim)
    app.button[0].click()
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    why = next(item for item in app.expander if item.label == "Why did TruthLens reach this verdict?")
    text = "\n".join(item.value for item in why.text)
    assert "Primary uncertainty reason from the decision trace: " + recorded[0] in text
    assert "Verdict: Inconclusive" in text
    assert any("What additional evidence would help?" in item.value for item in why.markdown)
    assert not any("<script>" in item.value or "<img " in item.value for item in why.markdown)
