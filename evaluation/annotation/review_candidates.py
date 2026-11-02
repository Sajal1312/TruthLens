"""Offline review report for staged, unannotated source-derived candidates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from evaluation.annotation.quality_control import audit_pilot
from evaluation.annotation.validate_pilot import DEFAULT_PILOT, _load_json, _validate_schema


DEFAULT_CANDIDATES = Path(__file__).resolve().parent / "candidates" / "phase1_15"


def review_candidates(directory=DEFAULT_CANDIDATES):
    directory = Path(directory)
    records = _load_json(directory / "claim_records.json")
    manifest = _load_json(directory / "collection_manifest.json")
    return _review_loaded(records, manifest)


def _review_loaded(records, manifest):
    if not isinstance(records, list):
        raise ValueError("Candidate records must be a JSON array")
    for index, record in enumerate(records):
        _validate_schema(record, "claim_record.schema.json", "candidate[{0}]".format(index))
        if record["annotation_status"] != "unannotated":
            raise ValueError("Staged candidates must remain unannotated")
    topics = manifest["topics_by_claim"]
    checks = manifest["source_checks"]
    ids = {record["claim_id"] for record in records}
    evidence = {item["evidence_id"]: item for record in records for item in record["evidence"]}
    if set(topics) != ids or set(checks) != set(evidence):
        raise ValueError("Topic/source-check references must match candidate claim and evidence IDs")
    for record in records:
        for item in record["evidence"]:
            check = checks[item["evidence_id"]]
            if check["claim_id"] != record["claim_id"] or check["source_url"] != item["source_url"]:
                raise ValueError("Source-check references do not match the evidence record")
            if check["passage_sha256"] != hashlib.sha256(item["passage"].encode("utf-8")).hexdigest():
                raise ValueError("Collected excerpt changed: source check must be repeated")
            if check["human_review_status"] != "pending":
                raise ValueError("This collection report must not imply completed human review")
    if any(topic not in manifest["target_topics"] for topic in topics.values()):
        raise ValueError("Unknown collection topic")

    # Reuse the existing read-only QC, with only temporary preparation files.
    # Its fixed 90-claim sampling plan is not a candidate verdict target.
    with tempfile.TemporaryDirectory(prefix="truthlens-candidate-qc-") as temporary:
        temporary = Path(temporary)
        pilot_manifest = _load_json(DEFAULT_PILOT / "manifest.json")
        pilot_manifest["status"] = "collecting"
        (temporary / "manifest.json").write_text(json.dumps(pilot_manifest), encoding="utf-8")
        (temporary / "claim_records.json").write_text(json.dumps(records), encoding="utf-8")
        qc = audit_pilot(temporary)
    findings = [item for item in qc["findings"]
                if item["code"] not in {"partial_pilot", "target_distribution_is_sampling_plan"}]
    if len(records) != manifest["target_claim_count"]:
        findings.append({"severity": "error", "code": "candidate_count_shortfall",
                         "message": "Candidate count does not match the collection target."})
    topic_counts = Counter(topics.values())
    for topic, target in manifest["target_topics"].items():
        if topic_counts[topic] != target:
            findings.append({"severity": "warning", "code": "topic_target_mismatch",
                             "message": "Collection topic target is not met: " + topic})
    counts = Counter(item["severity"] for item in findings)
    publisher_documents = {}
    shared_sources = {}
    groups = {}
    for record in records:
        for item in record["evidence"]:
            publisher_documents.setdefault(item["publisher_id"], set()).add(item["source_url"])
            shared_sources.setdefault(item["source_url"], set()).add(record["claim_id"])
            group = item["provenance_group_id"]
            if group:
                groups.setdefault(group, []).append({
                    "claim_id": record["claim_id"], "evidence_id": item["evidence_id"],
                    "source_url": item["source_url"], "relation": item["provenance_relation"],
                    "basis": item["provenance_basis"]})
    return {
        "collection_id": manifest["collection_id"],
        "collected_on": manifest["collected_on"],
        "claim_count": len(records), "evidence_count": qc["evidence_count"],
        "topic_distribution": dict(sorted(topic_counts.items())),
        "challenge_category_distribution": qc["challenge_category_distribution"],
        "evidence_count_per_claim": {record["claim_id"]: len(record["evidence"]) for record in records},
        "metadata_completeness": qc["metadata_completeness"],
        "duplicate_flags": [item for item in findings if item["code"] in {
            "duplicate_claim_id", "duplicate_evidence_id", "duplicate_claim_text", "near_duplicate_claim_text"}],
        "provenance_flags": [item for item in findings if item["code"] in {
            "source_in_multiple_provenance_groups", "cross_split_group", "provenance_basis_missing"}],
        "publisher_document_counts": {publisher: len(urls) for publisher, urls in publisher_documents.items()},
        "publisher_evidence_counts": dict(Counter(item["publisher_id"] for item in evidence.values())),
        "unique_source_url_count": len(shared_sources),
        "source_domain_counts": dict(Counter(urlsplit(url).hostname for url in shared_sources if url)),
        "shared_source_references": {url: sorted(claim_ids) for url, claim_ids in shared_sources.items()
                                     if len(claim_ids) > 1},
        "shared_provenance_groups": {group: members for group, members in groups.items() if len(members) > 1},
        "collector_source_review": {
            "method": "Opened-page excerpt checks recorded by collector; offline QC only verifies saved hashes and joins.",
            "independent_human_review_completed": False,
            "source_checks_with_recheck_date": sum(bool(check.get("rechecked_on")) for check in checks.values()),
        },
        "findings": findings,
        "finding_counts": {severity: counts[severity] for severity in ("error", "warning", "informational")},
        "human_review_status": "pending_for_all_candidates",
        "candidates_requiring_human_review": sorted(ids),
        "candidates_without_collector_located_passages": sorted({
            check["claim_id"] for check in checks.values()
            if check["passage_match"] != "collector_located_in_opened_page"}),
        "selection_limitations": manifest["selection_limitations"],
        "retrieval_failures": manifest["retrieval_failures"],
        "offline_check_limitation": "Schema, hashes and QC were checked offline; this command does not refetch pages or establish truth or human approval.",
    }


def _combined_inputs(directories):
    records, topics, checks, targets, limitations, failures = [], {}, {}, Counter(), [], []
    claim_ids, evidence_ids, collection_ids, dates = set(), set(), [], []
    for directory in directories:
        directory = Path(directory)
        batch = _load_json(directory / "claim_records.json")
        manifest = _load_json(directory / "collection_manifest.json")
        _review_loaded(batch, manifest)
        new_ids = {row["claim_id"] for row in batch}
        new_evidence_ids = {item["evidence_id"] for row in batch for item in row["evidence"]}
        if claim_ids & new_ids or evidence_ids & new_evidence_ids:
            raise ValueError("Duplicate claim or evidence IDs across candidate collections")
        claim_ids.update(new_ids)
        evidence_ids.update(new_evidence_ids)
        records.extend(batch)
        topics.update(manifest["topics_by_claim"])
        checks.update(manifest["source_checks"])
        targets.update(manifest["target_topics"])
        limitations.extend(manifest["selection_limitations"])
        failures.extend(manifest["retrieval_failures"])
        collection_ids.append(manifest["collection_id"])
        dates.append(manifest["collected_on"])
    return records, {
        "collection_id": "+".join(collection_ids), "collection_ids": collection_ids,
        "collected_on": ", ".join(sorted(set(dates))),
        "target_claim_count": sum(targets.values()), "target_topics": dict(targets),
        "topics_by_claim": topics, "source_checks": checks,
        "selection_limitations": list(dict.fromkeys(limitations)), "retrieval_failures": failures,
    }


def review_collections(directories):
    """QC the union, including cross-batch duplication and provenance links."""
    records, manifest = _combined_inputs(directories)
    report = _review_loaded(records, manifest)
    report["collection_ids"] = manifest["collection_ids"]
    return report


def render_review(report, records, manifest):
    lines = ["# Candidate collection review", "", "Collection: " + report["collection_id"], "",
             "All candidates await independent human review. No gold labels or model predictions were created.", "",
             "Collected: {0}. Claims: {1}. Evidence passages: {2}.".format(
                 report["collected_on"], report["claim_count"], report["evidence_count"]), "",
             "## Topic distribution", ""]
    lines.extend("- {0}: {1}".format(topic, count) for topic, count in report["topic_distribution"].items())
    lines.extend(["", "## Candidate claims and source provenance", ""])
    for record in records:
        lines.extend(["### " + record["claim_id"], "", record["claim_text"], "",
                      "- Topic: " + manifest["topics_by_claim"][record["claim_id"]],
                      "- Challenge tags: " + ", ".join(record["claim_category"]), ""])
        for item in record["evidence"]:
            check = manifest["source_checks"][item["evidence_id"]]
            lines.extend([
                      "- Source: [{0}]({1}) ({2}; {3}).".format(
                          item["source_title"], item["source_url"], item["publisher_id"], check["source_role"]),
                      "- Passage locator: " + check["locator"],
                      "- Publication date: {0}; event date: {1}; access date: {2}.".format(
                          item["publication_date"] or "unknown", item["event_date"] or "not recorded / partial precision",
                          item["checked_on"]),
                      "- Review: " + check["review_notes"], ""])
            if check.get("date_verification_note"):
                lines.extend(["- Date check: " + check["date_verification_note"], ""])
    lines.extend(["## Candidate QC", "",
                  "Errors: {error}; warnings: {warning}; informational: {informational}.".format(**report["finding_counts"]),
                  "", "Duplicate flags: {0}; provenance overlap flags: {1}.".format(
                      len(report["duplicate_flags"]), len(report["provenance_flags"])), "",
                  "Missing metadata: " + json.dumps(report["metadata_completeness"]["missing_counts_by_field"]), "",
                  "Publisher document counts: " + json.dumps(report["publisher_document_counts"]), "",
                  "Repeated publishers show concentration; they do not establish shared reporting chains or source independence.", "",
                  "Unique source URLs: {0}; shared source references across claims: {1}; shared provenance groups: {2}.".format(
                      report["unique_source_url_count"], len(report["shared_source_references"]),
                      len(report["shared_provenance_groups"])), "",
                  "Challenge distribution: " + json.dumps(report["challenge_category_distribution"]), ""])
    for group, members in report["shared_provenance_groups"].items():
        lines.append("- Provenance group {0}: {1}. Relationships: {2}. Keep linked material together in future splits; independence is not inferred.".format(
            group, ", ".join(member["evidence_id"] for member in members),
            ", ".join(sorted({member["relation"] for member in members}))))
    lines.extend("- {0}: {1}".format(item["severity"], item["message"]) for item in report["findings"])
    lines.extend(["", "## Research limitations and collection follow-up", ""])
    lines.extend("- " + item for item in report["selection_limitations"])
    lines.append("- " + report["offline_check_limitation"])
    lines.extend("- Retrieval attempt: {0} — {1}".format(item["url"], item["outcome"])
                 for item in report["retrieval_failures"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--combined", action="store_true", help="Review Phase 1 and Phase 2 together")
    parser.add_argument("--output-directory", type=Path, help="Folder for generated reports")
    args = parser.parse_args(argv)
    if args.combined:
        records, manifest = _combined_inputs([DEFAULT_CANDIDATES, DEFAULT_CANDIDATES.parent / "phase2_15"])
        report = _review_loaded(records, manifest)
        report["collection_ids"] = manifest["collection_ids"]
        output = args.output_directory or DEFAULT_CANDIDATES.parent / "combined_review"
    else:
        manifest = _load_json(args.directory / "collection_manifest.json")
        records = _load_json(args.directory / "claim_records.json")
        report = _review_loaded(records, manifest)
        output = args.output_directory or args.directory
    output.mkdir(parents=True, exist_ok=True)
    (output / "review_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "review_report.md").write_text(render_review(report, records, manifest), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "claim_count", "evidence_count", "topic_distribution", "finding_counts", "human_review_status")}, indent=2))
    return 1 if report["finding_counts"]["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
