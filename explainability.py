"""Read-only explanation views of recorded decisions; never infer new verdicts.

Sentence selection uses word overlap only to help readers navigate retrieved text.
It is neither a stance classifier nor an attribution of internal model reasoning.
"""
import html
import re

from evidence_quality import provenance_diagnostics, source_context
from temporal_reasoning import temporal_evidence_analysis
from evidence_independence import analyze_evidence_independence
from numerical_reasoning import analyze_numerical_evidence
from uncertainty_analysis import analyze_uncertainty


def _text(value):
    return value if isinstance(value, str) else ""


def evidence_excerpt(content, claim, preferred=None, limit=360):
    """Return a short, exact source substring and its selection basis.

    Prefer the assessor's recorded window, tolerating whitespace normalization
    by the window builder. Otherwise select a sentence as a reading aid only.
    A missing recorded window is reported rather than attributed to other text.
    """
    content, claim, preferred = _text(content), _text(claim), _text(preferred)
    start, end = 0, len(content)
    located = False
    if preferred.strip():
        pattern = r"\s+".join(re.escape(word) for word in preferred.split())
        match = re.search(pattern, content)
        if match:
            start, end = match.span()
            located = True
        basis = ("Excerpt from the assessor's recorded passage" if located else
                 "Recorded passage not located in the retrieved snippet; showing a reading aid only")
    else:
        basis = "Sentence selected from the retrieved snippet as a reading aid only"

    region = content[start:end]
    if not located or len(region) > limit:
        terms = set(re.findall(r"\w+", claim.casefold()))
        sentences = list(re.finditer(r"\S.*?(?:[.!?](?=\s|$)|\n|$)", region, re.S))
        if sentences:
            sentence = max(sentences, key=lambda item: len(
                terms & set(re.findall(r"\w+", item.group().casefold()))))
            start, end = start + sentence.start(), start + sentence.end()
    if end - start > limit:
        end = start + limit
        boundary = content.rfind(" ", start, end)
        if boundary > start + limit // 2:
            end = boundary
    excerpt = content[start:end].strip()
    return {"text": excerpt, "basis": basis, "recorded_passage_located": located,
            "shortened": bool(content[:start].strip() or content[end:].strip())}


def highlighted_evidence(text, tone="neutral"):
    """Escape all source text BEFORE adding fixed, presentation-only markup."""
    tone = tone if tone in {"support", "contradiction", "neutral"} else "neutral"
    escaped = html.escape(_text(text), quote=True)
    return ('<div class="evidence-excerpt"><mark class="evidence-{0}">{1}</mark></div>'
            .format(tone, escaped))


def build_explanation(claim, results, assessment, *, reference_date=None):
    """Join real retrieved sources to their recorded source/component decisions.

    No scores, votes, relevance labels or verdicts are recalculated. In
    particular, a raw directional NLI label is not a counted directional vote.
    """
    rows = assessment.get("per_source") or []
    provenance = provenance_diagnostics(results)
    entries = []
    for index, source in enumerate(results):
        row = rows[index] if index < len(rows) else {}
        if row.get("url") and row["url"] != source.get("url"):
            row = {"status": "Assessment/source URL mismatch; no decision attributed"}
        warnings = []
        for key in ("relevance", "date_relevance", "publication_date_signal", "independence"):
            if row.get(key):
                warnings.append(key.replace("_", " ").capitalize() + ": " + str(row[key]))
        context = row.get("source_context") or source_context(source.get("url", ""))
        if context.get("note"):
            warnings.append(context["note"])
        for relation in provenance[index]["relationships"]:
            for observation in relation.get("observations", []):
                warnings.append("Source {0}: {1}".format(relation["other_index"] + 1, observation["label"]))
        warnings.append(provenance[index]["independence"])

        for part in row.get("part_assessments") or [row]:
            # Within-source conflicts retain both recorded passages. Neither is
            # reintroduced as a vote after the pipeline excluded that conflict.
            for window in part.get("passages") or [part]:
                part_claim = _text(part.get("claim_part")) or _text(claim)
                preferred = window.get("text") if window is not part else part.get("passage")
                excerpt = evidence_excerpt(source.get("content"), part_claim, preferred)
                label = _text(part.get("label")) or "Not assessed"
                contributed = part.get("contributed") if isinstance(part.get("contributed"), bool) else None
                tone = {"SUPPORTS": "support", "CONTRADICTS": "contradiction"}.get(label, "neutral") if contributed else "neutral"
                if preferred and not excerpt["recorded_passage_located"]:
                    tone = "neutral"
                entries.append({
                    "source_index": index, "title": _text(source.get("title")) or "Untitled source",
                    "url": _text(source.get("url")), "claim_part": part_claim,
                    "publisher": provenance[index]["publisher"],
                    "published_date": _text(source.get("published_date")),
                    # Only explicitly supplied update metadata is displayed. Never
                    # infer an update from a publication or retrieval timestamp.
                    "updated_date": _text(source.get("updated_date")) or _text(source.get("last_updated")),
                    "label": label, "passage_label": _text(window.get("label")) or label,
                    "model_label": _text(window.get("model_label")),
                    "contributed": contributed,
                    "status": _text(part.get("status")) or _text(row.get("status")) or "No passage decision was recorded",
                    "confidence": window.get("confidence"), "margin": window.get("margin"),
                    "excerpt": excerpt, "tone": tone, "warnings": list(warnings),
                })
    explanation = {
        "claim": _text(assessment.get("original_claim")) or _text(claim),
        "verdict": _text(assessment.get("verdict")) or "Not recorded",
        "method": _text(assessment.get("method")),
        "reasoning": _text(assessment.get("reasoning")) or "No aggregation reason was recorded.",
        "limitations": _text(assessment.get("limitations")),
        "evidence_used": list(assessment.get("evidence_used") or []),
        "components": [dict(part) for part in assessment.get("part_outcomes") or []],
        "entries": entries,
        "has_nli_decisions": any(row.get("part_assessments") for row in rows),
        "temporal": temporal_evidence_analysis(
            _text(assessment.get("original_claim")) or _text(claim), results, reference_date),
        "independence": analyze_evidence_independence(results),
        "numerical": analyze_numerical_evidence(
            _text(assessment.get("original_claim")) or _text(claim), results, reference_date),
    }
    explanation["uncertainty"] = analyze_uncertainty(
        assessment, results, independence=explanation["independence"],
        temporal=explanation["temporal"], numerical=explanation["numerical"])
    return explanation
