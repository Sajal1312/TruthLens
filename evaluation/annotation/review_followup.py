"""Offline, version-bound human review preparation; never submit or import."""
import argparse
from collections import Counter
import json
from pathlib import Path

from evaluation.annotation.automated_source_review import validate_assessments
from evaluation.annotation.candidate_review import candidate_checksum, load_candidates
from evaluation.annotation.validate_pilot import _validate_schema


def validate_followup(bundle, candidates, previous):
    _validate_schema(bundle, "source_review_followup.schema.json", "automated follow-up")
    validate_assessments(previous, candidates)
    checks = bundle["source_checks"]
    if (len({c["check_id"] for c in checks}) != len(checks)
            or len({c["url"] for c in checks}) != len(checks)):
        raise ValueError("Duplicate source check ID or URL")
    by_id = {c["check_id"]: c for c in checks}
    for check in checks:
        if check["access_status"] == "inaccessible":
            if check["publication_date"] is not None:
                raise ValueError("Inaccessible source cannot establish a publication date")
        if (check["publication_precision"] == "day") != (check["publication_date"] is not None):
            raise ValueError("Only a verified publication day may populate publication_date")
    notes = bundle["candidate_followups"]
    if len({n["candidate_id"] for n in notes}) != len(notes):
        raise ValueError("Duplicate candidate follow-up")
    flagged = {row["candidate_id"] for row in previous
               if row["recommended_action"] != "suitable for human approval"}
    if {n["candidate_id"] for n in notes} != flagged:
        raise ValueError("Follow-up must cover the exact previously flagged set")
    for note in notes:
        candidate = candidates[note["candidate_id"]]
        if note["candidate_sha256"] != candidate_checksum(candidate):
            raise ValueError("Stale follow-up candidate checksum")
        if any(key not in by_id for key in note["source_check_ids"]):
            raise ValueError("Unknown source check reference")
        if note["status"] in {"resolved_context_gap", "authoritative_replacement_available"}:
            if not any(by_id[key]["access_status"] == "opened" for key in note["source_check_ids"]):
                raise ValueError("A remedy requires an accessible checked source")
            if not note["proposed_context_note"]:
                raise ValueError("Resolved context requires an explicit proposed remedy")
    expected = {e["evidence_id"]: e for c in candidates.values() for e in c["evidence"]
                if e["publication_date"] is None}
    date_rows = bundle["missing_date_checks"]
    if (len(date_rows) != len(expected)
            or {r["evidence_id"] for r in date_rows} != set(expected)):
        raise ValueError("Missing-date checks must cover every unknown publication date once")
    for row in date_rows:
        if row["source_check_id"] not in by_id:
            raise ValueError("Unknown publication source reference")
        if by_id[row["source_check_id"]]["url"] != expected[row["evidence_id"]]["source_url"]:
            raise ValueError("Date check URL differs from saved evidence")


def summarize(bundle, candidates, previous):
    validate_followup(bundle, candidates, previous)
    statuses = Counter(n["status"] for n in bundle["candidate_followups"])
    return {
        "record_type": "automated_followup_summary",
        "candidate_count": len(candidates),
        "previous_recommendations": dict(Counter(r["recommended_action"] for r in previous)),
        "followup_issue_counts": dict(statuses),
        "updated_preliminary_routes": {
            "review_current_candidate": len(candidates) - len(bundle["candidate_followups"]),
            "versioned_context_or_source_revision_prepared": statuses["resolved_context_gap"] + statuses["authoritative_replacement_available"],
            "hold_for_scope_or_evidence_review": statuses["unresolved"],
        },
        "source_checks": len(bundle["source_checks"]),
        "source_access": dict(Counter(c["access_status"] for c in bundle["source_checks"])),
        "unknown_publication_dates_checked": len(bundle["missing_date_checks"]),
        "new_original_publication_days_established": sum(
            next(c for c in bundle["source_checks"] if c["check_id"] == row["source_check_id"])["publication_date"] is not None
            for row in bundle["missing_date_checks"]),
        "note": "Context remedies are proposals only; no candidate, review packet or pilot was changed. No human approval is inferred.",
    }


def render_sheet(bundle, candidates, previous):
    summary = summarize(bundle, candidates, previous)
    notes = {n["candidate_id"]: n for n in bundle["candidate_followups"]}
    old = {r["candidate_id"]: r for r in previous}
    lines = ["# TruthLens — human inclusion review sheet", "",
             "Automated assistance prepared on " + bundle["automated_checked_on"] + ". No decisions are preselected.",
             "This is a scratch worksheet, not a submittable review packet. Decisions belong to a real human.",
             "Original claims/evidence remain unchanged. Proposed context and replacement sources below are NOT part of the frozen candidate.",
             "Prior excerpt checks are dated 2026-11-01; this follow-up rechecks flagged issues and all missing-date URLs, not every original passage.",
             "Do not share these interpretive notes with later blinded annotators.", "",
             "Reviewer's own alias: ____________________    Actual review date/time and timezone: ____________________", "",
             "## Preparation summary", "", "```json", json.dumps(summary, indent=2), "```", "",
             "For each row, choose your own inclusion decision: approved / revision_required / rejected. No option is selected.",
             "Unknown publication days are not proof of an invalid source. Month/year, update, event and access dates must remain distinct.", ""]
    for cid, candidate in candidates.items():
        prior = old[cid]
        note = notes.get(cid)
        lines += ["## " + cid, "", "**Exact claim:** " + candidate["claim_text"], "",
                  "Version SHA-256: `" + candidate_checksum(candidate) + "`", ""]
        for e in candidate["evidence"]:
            lines += ["- [{}]({}) — {}. Saved publication day: {}.".format(
                e["evidence_id"], e["source_url"], e["source_title"], e["publication_date"] or "unknown")]
        lines += ["", "**Prior automated finding:** " + prior["claim_evidence_interpretation"]]
        if note:
            lines += ["**Follow-up:** " + note["findings"],
                      "**Remaining concerns:** " + "; ".join(note["remaining_concerns"]),
                      "**Proposed context (not adopted):** " + note["proposed_context_note"],
                      "**Recommendation:** " + note["recommended_inclusion_action"]]
            for check_id in note["source_check_ids"]:
                check = next(c for c in bundle["source_checks"] if c["check_id"] == check_id)
                lines += ["- Follow-up [{}]({}): {}. {}".format(
                    check_id, check["url"], check["access_status"], check["finding"])]
        else:
            lines += ["**Remaining concerns:** " + "; ".join(prior["research_concerns"]),
                      "**Recommendation:** Review the current candidate personally; previous preliminary route was suitable for human approval review. This is not approval."]
        lines += ["**Date / provenance caution:** " + prior["provenance_assessment"], "",
                  "**Human decision (leave blank until you decide):** ____________________",
                  "**Human rationale / required revisions:** ________________________________________",
                  "Rationale continued: __________________________________________________________", ""]
    lines += ["## Missing publication dates — follow-up", "",
              "All original unknown dates remain null. The checks below concern visible source metadata; they are not exhaustive HTML/archive audits.", ""]
    for row in bundle["missing_date_checks"]:
        lines += ["- {}: {} ({})".format(row["evidence_id"], row["finding"], row["source_check_id"])]
    lines += ["", "## Source-check log", "",
              "Only requested/opened pages below count as checked sources. Search-result snippets alone were not used as verified evidence.", ""]
    for check in bundle["source_checks"]:
        lines += ["- [{}]({}) — **{}**. {} Locator: {}. Publication metadata: {}.".format(
            check["check_id"], check["url"], check["access_status"], check["finding"],
            check["locator"], check["publication_label"])]
    spaced = []
    for line in lines:
        if line.startswith("**") and spaced and spaced[-1]:
            spaced.append("")
        spaced.append(line)
    return "\n".join(spaced).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--followup", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, help="New directory only; omit to validate and print summary")
    args = parser.parse_args()
    try:
        bundle = json.loads(args.followup.read_text(encoding="utf-8"))
        previous = json.loads(args.previous.read_text(encoding="utf-8"))
        candidates = load_candidates()
        summary = summarize(bundle, candidates, previous)
        sheet = render_sheet(bundle, candidates, previous)
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            with (args.output_dir / "human_review_sheet.md").open("x", encoding="utf-8") as stream:
                stream.write(sheet)
            with (args.output_dir / "summary.json").open("x", encoding="utf-8") as stream:
                json.dump(summary, stream, indent=2)
                stream.write("\n")
        print(json.dumps(summary, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, "Follow-up validation failed: {}\n".format(error))


if __name__ == "__main__":
    main()
