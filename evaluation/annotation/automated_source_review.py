"""Validate and report saved automated source observations; never submit reviews.

This is an offline replay of a web-assisted inspection, not a URL fetcher, NLI
classifier, human approval tool, or independent annotation process.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from evaluation.annotation.candidate_review import candidate_checksum, load_candidates
from evaluation.annotation.validate_pilot import _validate_schema


def validate_assessments(rows, candidates):
    if not isinstance(rows, list):
        raise ValueError("Assessments must be an array")
    seen = set()
    for row in rows:
        _validate_schema(row, "automated_source_assessment.schema.json", "automated assistance")
        candidate_id = row["candidate_id"]
        if candidate_id in seen or candidate_id not in candidates:
            raise ValueError("Duplicate or unknown candidate ID")
        seen.add(candidate_id)
        candidate = candidates[candidate_id]
        if (row["candidate_sha256"] != candidate_checksum(candidate)
                or row["claim"] != candidate["claim_text"]):
            raise ValueError("Stale candidate checksum or claim")
        expected = {item["evidence_id"]: item for item in candidate["evidence"]}
        checks = row["evidence_checks"]
        if (len(checks) != len(expected)
                or {item["evidence_id"] for item in checks} != set(expected)):
            raise ValueError("Evidence coverage must match the candidate exactly once")
        for check in checks:
            evidence = expected[check["evidence_id"]]
            if check["source_url"] != evidence["source_url"]:
                raise ValueError("Source URL differs from candidate")
            if check["access_status"] == "inaccessible":
                if (check["excerpt_match"] != "incomplete"
                        or check["publication_date_status"] != "incomplete"
                        or check["observed_title"] is not None
                        or check["observed_publisher"] is not None
                        or check["observed_publication_date"] is not None):
                    raise ValueError("Inaccessible source cannot be reported as verified")
                if row["recommended_action"] == "suitable for human approval":
                    raise ValueError("Incomplete source verification requires human attention")
            elif (not check["observed_title"] or not check["observed_publisher"]
                  or check["excerpt_match"] == "incomplete"):
                raise ValueError("Opened source requires observed metadata and excerpt status")
            date = check["observed_publication_date"]
            if check["publication_date_status"] == "matched_existing_date":
                if date is None or date != evidence["publication_date"]:
                    raise ValueError("Publication date must match the saved candidate")
            elif date is not None:
                raise ValueError("Unestablished publication day must remain null")
    if seen != set(candidates):
        raise ValueError("Assessment coverage must include every candidate")


def summarize(rows, candidates):
    validate_assessments(rows, candidates)
    checks = [check for row in rows for check in row["evidence_checks"]]
    opened = {check["source_url"] for check in checks if check["access_status"] == "opened"}
    unavailable = {check["source_url"] for check in checks if check["access_status"] == "inaccessible"}
    return {
        "record_type": "automated_preliminary_summary",
        "candidate_count": len(rows), "evidence_count": len(checks),
        "distinct_source_urls": len({check["source_url"] for check in checks}),
        "distinct_sources_opened": len(opened),
        "inaccessible_source_urls": sorted(unavailable),
        "passages_located": sum(check["excerpt_match"] != "incomplete" for check in checks),
        "excerpt_status_counts": dict(Counter(check["excerpt_match"] for check in checks)),
        "candidates_with_inaccessible_sources": [row["candidate_id"] for row in rows
            if any(check["access_status"] == "inaccessible" for check in row["evidence_checks"])],
        "missing_candidate_publication_dates": sum(e["publication_date"] is None
            for candidate in candidates.values() for e in candidate["evidence"]),
        "publication_status_counts": dict(Counter(check["publication_date_status"] for check in checks)),
        "recommendation_counts": dict(Counter(row["recommended_action"] for row in rows)),
        "human_approval_status": "Not established by this report; all recommendations require a real reviewer.",
    }


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_report(rows, candidates):
    summary = summarize(rows, candidates)
    lines = ["# Automated preliminary candidate source review", "",
             "AI-generated assistance, not independent human review, approval, or gold labels.",
             "Recommendations concern inclusion quality, not claim truth. A disputed or false claim can be a valid annotation candidate.",
             "", "## Actual inspection totals", "", "```json",
             json.dumps(summary, indent=2, ensure_ascii=False), "```", "",
             "Opened means readable content returned through the web tool. It does not mean measured HTTP 200, an uncached origin response, full DOM inspection, or authenticated archival capture.",
             "Located means the saved excerpt was found as a fragment, with documented formatting normalization or table/bullet assembly. It does not establish truth, sufficient context, or source independence.",
             "No new evidence, dates, or candidate text were imported. See [inspection notes](../README.md) for methods and remaining human steps.",
             "", "## All candidates", "",
             "| Candidate | Claim | Passage checks | Priority | Preliminary recommendation | Reason |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        status = "; ".join("[{}]({}): {}".format(check["evidence_id"], check["source_url"],
                                                check["excerpt_match"])
                           for check in row["evidence_checks"])
        lines.append("| " + " | ".join(_cell(value) for value in (
            row["candidate_id"], row["claim"], status, row["human_review_priority"],
            row["recommended_action"], row["recommendation_reason"])) + " |")
    lines.extend(["", "## Per-candidate context, dates and provenance", ""])
    for row in rows:
        lines.extend(["### " + row["candidate_id"], "",
                      "- Claim/evidence interpretation: " + row["claim_evidence_interpretation"],
                      "- Clarity: " + row["claim_clarity_assessment"],
                      "- Dates: " + row["date_assessment"],
                      "- Provenance: " + row["provenance_assessment"],
                      "- Research concerns: " + "; ".join(row["research_concerns"]), ""])
        for check in row["evidence_checks"]:
            lines.extend(["- [{}]({}): **{} / {}**".format(check["evidence_id"], check["source_url"],
                          check["access_status"], check["excerpt_match"]),
                          "  - Observed title/publisher: {} / {}".format(
                              check["observed_title"] or "not established", check["observed_publisher"] or "not established"),
                          "  - Source role: " + check["source_role"],
                          "  - Locator/method: " + check["locator"],
                          "  - Date status: {}; original day: {}; {}".format(check["publication_date_status"],
                              check["observed_publication_date"] or "unknown", check["other_date_notes"]),
                          "  - Context: " + check["context_notes"]])
        lines.append("")
    return "\n".join(lines).rstrip()


def write_reports(rows, candidates, output_dir):
    """Exclusive report copies only; never write into human review packets."""
    summary = summarize(rows, candidates)
    output_dir = Path(output_dir)
    # A new directory makes accidental reruns fail before any output is replaced.
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "worksheets").mkdir()
    for row in rows:
        with (output_dir / "worksheets" / (row["candidate_id"] + ".json")).open("x", encoding="utf-8") as stream:
            json.dump(row, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    with (output_dir / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with (output_dir / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(render_report(rows, candidates) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessments", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, help="New directory only; otherwise print summary")
    args = parser.parse_args()
    try:
        rows = json.loads(args.assessments.read_text(encoding="utf-8"))
        candidates = load_candidates()
        result = (write_reports(rows, candidates, args.output_dir) if args.output_dir
                  else summarize(rows, candidates))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError) as error:
        parser.exit(1, "Automated assistance validation failed: {}\n".format(error))


if __name__ == "__main__":
    main()
