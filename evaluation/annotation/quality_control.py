"""Read-only quality audit for the claim/evidence bundle before annotation."""
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from jsonschema import Draft202012Validator, FormatChecker

from evaluation.annotation.validate_pilot import DEFAULT_PILOT, SCHEMAS, _load_json


DEFAULT_JSON_REPORT = Path("evaluation/annotation/pilot_90_quality_report.json")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NEAR_DUPLICATE_THRESHOLD = 0.85


def _finding(findings, severity, code, message, **details):
    findings.append({"severity": severity, "code": code, "message": message, **details})


def _valid_https_url(value):
    if not isinstance(value, str) or not value or value != value.strip() or any(ch.isspace() for ch in value):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
        return (parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None
                and parsed.password is None and (port is None or 1 <= port <= 65535))
    except ValueError:
        return False


def _valid_date(value):
    if not isinstance(value, str) or not _ISO_DATE_RE.fullmatch(value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _source_reference_key(source_url, source_identifier):
    if source_url and _valid_https_url(source_url):
        parts = urlsplit(source_url)
        query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                 if not key.casefold().startswith("utm_") and key.casefold() not in {"fbclid", "gclid"}]
        return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(),
                           parts.path.rstrip("/") or "/", urlencode(sorted(query)), "")).casefold()
    return str(source_identifier).strip().casefold() if source_identifier else None


def _schema_errors(record, schema, label):
    errors = []
    for error in Draft202012Validator(
            schema, format_checker=FormatChecker()).iter_errors(record):
        location = ".".join(str(part) for part in error.absolute_path) or "<record>"
        errors.append("{0}.{1}: {2}".format(label, location, error.message))
    return errors


def _normalized_claim(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def _claim_similarity(left, right):
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    jaccard = len(left_tokens & right_tokens) / float(len(left_tokens | right_tokens))
    length_ratio = min(len(left_tokens), len(right_tokens)) / float(max(len(left_tokens), len(right_tokens)))
    return jaccard if length_ratio >= 0.8 else 0.0


def audit_pilot(directory=DEFAULT_PILOT, *, full_pilot=False):
    """Audit a prepared claim/evidence bundle; never writes or labels pilot data."""
    directory = Path(directory)
    findings = []
    try:
        manifest = _load_json(directory / "manifest.json")
        Draft202012Validator.check_schema(_load_json(SCHEMAS / "pilot_manifest.schema.json"))
        manifest_errors = _schema_errors(
            manifest, _load_json(SCHEMAS / "pilot_manifest.schema.json"), "manifest")
        for message in manifest_errors:
            _finding(findings, "error", "invalid_manifest", message)
        # Do not follow a tampered manifest path; the schema fixes this file name.
        records_name = manifest.get("claim_records_file")
        if records_name != "claim_records.json":
            _finding(findings, "error", "invalid_claim_records_path",
                     "Manifest claim_records_file must be the pilot-local claim_records.json file.")
            records_name = "claim_records.json"
        records_path = directory / records_name
        claim_records = _load_json(records_path)
        if not isinstance(claim_records, list):
            _finding(findings, "error", "invalid_claim_records", "Claim records must be a JSON array.")
            claim_records = []
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        _finding(findings, "error", "unreadable_pilot", "Could not read pilot preparation files: " + str(error))
        return _assemble_report(None, [], findings, full_pilot)

    claim_schema = _load_json(SCHEMAS / "claim_record.schema.json")
    Draft202012Validator.check_schema(claim_schema)
    target_count = manifest.get("target_claim_count", 90)
    if full_pilot and len(claim_records) != target_count:
        _finding(findings, "error", "wrong_claim_count",
                 "Full-pilot mode requires exactly {0} claim records; found {1}.".format(
                     target_count, len(claim_records)), expected=target_count, actual=len(claim_records))
    elif not claim_records:
        _finding(findings, "informational", "empty_preparation",
                 "The pilot is an empty preparation state; no annotation records are expected yet.")
    elif len(claim_records) != target_count:
        _finding(findings, "warning", "partial_pilot",
                 "The preparation set is partial ({0} of {1} claims).".format(
                     len(claim_records), target_count), expected=target_count, actual=len(claim_records))

    planned_value = manifest.get("challenge_categories", [])
    planned_categories = set(planned_value) if isinstance(planned_value, list) else set()
    claim_ids = Counter()
    evidence_ids = Counter()
    family_splits = defaultdict(set)
    event_splits = defaultdict(set)
    provenance_splits = defaultdict(set)
    source_group_map = defaultdict(set)
    family_members = defaultdict(list)
    provenance_members = defaultdict(list)
    category_counts = Counter({category: 0 for category in planned_categories})
    evidence_count = 0
    claims_with_evidence = 0
    metadata_missing = Counter()
    claims_for_similarity = []

    for index, record in enumerate(claim_records):
        label = "claim[{0}]".format(index)
        if not isinstance(record, dict):
            _finding(findings, "error", "invalid_claim_record", label + " must be a JSON object.")
            continue
        for message in _schema_errors(record, claim_schema, label):
            _finding(findings, "error", "schema_violation", message)
        claim_id = record.get("claim_id")
        if isinstance(claim_id, str) and claim_id:
            claim_ids[claim_id] += 1
        elif claim_id is not None:
            _finding(findings, "error", "invalid_claim_id", label + " has an invalid claim ID.")
        text = record.get("claim_text")
        if isinstance(text, str) and text.strip():
            claims_for_similarity.append((claim_id or label, text))
        else:
            _finding(findings, "error", "missing_claim_text", label + " has no claim text.")

        family_id = record.get("claim_family_id")
        if not isinstance(family_id, str) or not _ID_RE.fullmatch(family_id):
            _finding(findings, "error", "invalid_claim_family", label + " has an invalid claim-family reference.")
        else:
            family_members[family_id].append(claim_id or label)
            if record.get("split"):
                family_splits[family_id].add(record["split"])
        event_id = record.get("event_group_id")
        if event_id is not None:
            if not isinstance(event_id, str) or not _ID_RE.fullmatch(event_id):
                _finding(findings, "error", "invalid_event_group", label + " has an invalid event-group reference.")
            else:
                if record.get("split"):
                    event_splits[event_id].add(record["split"])

        tags = record.get("claim_category", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    category_counts[tag] += 1
                if not isinstance(tag, str) or tag not in planned_categories:
                    _finding(findings, "error", "unknown_challenge_tag",
                             "Claim {0} uses a category outside the pilot manifest.".format(claim_id),
                             claim_id=claim_id, category=tag)

        evidence = record.get("evidence", [])
        if not isinstance(evidence, list):
            _finding(findings, "error", "invalid_evidence_list",
                     "Claim {0} evidence must be a list.".format(claim_id), claim_id=claim_id)
            evidence = []
        if evidence:
            claims_with_evidence += 1
        else:
            _finding(findings, "error", "missing_evidence",
                     "Claim {0} has no evidence passage.".format(claim_id), claim_id=claim_id)

        for evidence_index, item in enumerate(evidence):
            evidence_count += 1
            evidence_label = "claim {0} evidence[{1}]".format(claim_id, evidence_index)
            if not isinstance(item, dict):
                _finding(findings, "error", "invalid_evidence_record",
                         evidence_label + " must be a JSON object.")
                continue
            evidence_id = item.get("evidence_id")
            if isinstance(evidence_id, str) and evidence_id:
                evidence_ids[evidence_id] += 1
            source_identifier = item.get("source_identifier")
            source_url = item.get("source_url")
            if source_identifier is not None and (
                    not isinstance(source_identifier, str) or not source_identifier.strip()
                    or any(char.isspace() or ord(char) < 32 for char in source_identifier)):
                _finding(findings, "error", "invalid_source_identifier",
                         evidence_label + " has an invalid source identifier.", evidence_id=evidence_id)
            if source_url is not None and not _valid_https_url(source_url):
                _finding(findings, "error", "invalid_source_url",
                         evidence_label + " has an invalid HTTPS URL.", evidence_id=evidence_id)
            if not (isinstance(source_identifier, str) and source_identifier.strip()) and not source_url:
                _finding(findings, "error", "untraceable_source",
                         evidence_label + " has neither a source identifier nor a URL.", evidence_id=evidence_id)
            elif not source_url:
                _finding(findings, "warning", "missing_source_url",
                         evidence_label + " has an identifier but no direct source URL.", evidence_id=evidence_id)

            for field in ("source_identifier", "source_title", "publisher_id", "publication_date", "checked_on"):
                value = item.get(field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    metadata_missing[field] += 1
                    _finding(findings, "warning", "missing_metadata",
                             evidence_label + " is missing optional metadata: " + field + ".",
                             evidence_id=evidence_id, field=field)
            for field in ("publication_date", "event_date", "checked_on"):
                value = item.get(field)
                if value is not None and not _valid_date(value):
                    _finding(findings, "error", "invalid_date",
                             evidence_label + " has a non-ISO or invalid " + field + ".",
                             evidence_id=evidence_id, field=field, value=value)
            if not isinstance(item.get("passage"), str) or not item.get("passage", "").strip():
                _finding(findings, "error", "empty_passage", evidence_label + " has an empty passage.")

            group_id = item.get("provenance_group_id")
            relation = item.get("provenance_relation", "unknown")
            if not isinstance(relation, str):
                relation = "unknown"  # Schema violation already records malformed values.
            basis = item.get("provenance_basis")
            if group_id is not None and (not isinstance(group_id, str) or not _ID_RE.fullmatch(group_id)):
                _finding(findings, "error", "invalid_provenance_group",
                         evidence_label + " has an invalid provenance-group reference.", evidence_id=evidence_id)
            elif group_id is not None:
                provenance_members[group_id].append(evidence_id or evidence_label)
                if record.get("split"):
                    provenance_splits[group_id].add(record["split"])
            if relation in {"same_origin", "syndicated", "independent_verified", "related_suspected"} and not group_id:
                _finding(findings, "warning", "provenance_group_missing",
                         evidence_label + " declares a provenance relationship without a group ID.",
                         evidence_id=evidence_id, relation=relation)
            if group_id and (not isinstance(basis, str) or not basis.strip()):
                _finding(findings, "warning", "provenance_basis_missing",
                         evidence_label + " has a provenance group without a documented basis.",
                         evidence_id=evidence_id, provenance_group_id=group_id)
            source_key = _source_reference_key(source_url, source_identifier)
            if source_key and group_id:
                source_group_map[str(source_key).casefold()].add(group_id)

    for claim_id, count in claim_ids.items():
        if count > 1:
            _finding(findings, "error", "duplicate_claim_id",
                     "Claim ID appears more than once: {0}.".format(claim_id), claim_id=claim_id, count=count)
    for evidence_id, count in evidence_ids.items():
        if count > 1:
            _finding(findings, "error", "duplicate_evidence_id",
                     "Evidence ID is not globally unique: {0}.".format(evidence_id),
                     evidence_id=evidence_id, count=count)

    for left in range(len(claims_for_similarity)):
        left_id, left_text = claims_for_similarity[left]
        normalized_left = _normalized_claim(left_text)
        for right in range(left + 1, len(claims_for_similarity)):
            right_id, right_text = claims_for_similarity[right]
            normalized_right = _normalized_claim(right_text)
            similarity = _claim_similarity(normalized_left, normalized_right)
            if similarity >= _NEAR_DUPLICATE_THRESHOLD:
                exact = normalized_left == normalized_right
                _finding(findings, "warning", "duplicate_claim_text" if exact else "near_duplicate_claim_text",
                         "Claim texts require human duplicate/leakage review.",
                         claim_ids=[left_id, right_id], token_jaccard=round(similarity, 4), exact=exact)

    for group_label, groups in (("claim_family", family_splits), ("event", event_splits),
                                ("provenance", provenance_splits)):
        for group_id, splits in groups.items():
            if len(splits) > 1:
                _finding(findings, "warning", "cross_split_group",
                         "Related {0} group spans multiple split labels; keep it together in any future split.".format(group_label),
                         group_id=group_id, group_type=group_label, splits=sorted(splits))
    for source_key, groups in source_group_map.items():
        if len(groups) > 1:
            _finding(findings, "warning", "source_in_multiple_provenance_groups",
                     "The same source identifier or URL is assigned to multiple provenance groups; review grouping.",
                     source_reference=source_key, provenance_group_ids=sorted(groups))

    for field, count in sorted(metadata_missing.items()):
        _finding(findings, "informational", "metadata_completeness",
                 "Metadata completeness summary for {0}.".format(field), field=field,
                 missing_count=count, evidence_count=evidence_count)
    _finding(findings, "informational", "target_distribution_is_sampling_plan",
             "Target verdict counts are sampling goals only; this audit does not create or infer gold labels.",
             target_distribution=manifest.get("target_verdict_distribution", {}))
    _finding(findings, "informational", "dates_checked_separately",
             "Publication dates and event dates are checked as separate fields; an event date is never inferred from a publication date.")
    for category in sorted(planned_categories):
        if category_counts[category] == 0:
            _finding(findings, "warning" if claim_records else "informational",
                     "challenge_category_unrepresented",
                     "No current claim is tagged with planned challenge category {0}.".format(category),
                     category=category)
    _finding(findings, "informational", "future_split_grouping",
             "For future development/diagnostic/final-test splits, keep claim-family, event, and documented provenance groups together; do not create a split in this audit.")

    return _assemble_report(manifest, claim_records, findings, full_pilot,
                            evidence_count=evidence_count, claims_with_evidence=claims_with_evidence,
                            category_counts=category_counts, metadata_missing=metadata_missing,
                            family_members=family_members, provenance_members=provenance_members)


def _assemble_report(manifest, records, findings, full_pilot, *, evidence_count=0,
                     claims_with_evidence=0, category_counts=None, metadata_missing=None,
                     family_members=None, provenance_members=None):
    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    informational = sum(item["severity"] == "informational" for item in findings)
    target = (manifest or {}).get("target_claim_count", 90)
    if not records and errors == 0:
        readiness = "empty_preparation"
    elif errors:
        readiness = "blocked_errors"
    elif len(records) != target:
        readiness = "incomplete"
    elif warnings:
        readiness = "human_review_required"
    else:
        readiness = "ready_for_distribution"
    return {
        "pilot_id": (manifest or {}).get("pilot_id"),
        "mode": "full_pilot" if full_pilot else "preparation",
        "claim_count": len(records),
        "target_claim_count": target,
        "evidence_count": evidence_count,
        "claims_with_evidence": claims_with_evidence,
        "challenge_category_distribution": dict(sorted((category_counts or {}).items())),
        "metadata_completeness": {
            "evidence_count": evidence_count,
            "missing_counts_by_field": dict(sorted((metadata_missing or {}).items())),
        },
        "claim_family_groups": {key: len(value) for key, value in sorted((family_members or {}).items())},
        "provenance_groups": {key: len(value) for key, value in sorted((provenance_members or {}).items())},
        "sampling_target_distribution": {
            "counts": (manifest or {}).get("target_verdict_distribution", {}),
            "status": "sampling_plan_only_not_gold_labels",
        },
        "findings": findings,
        "finding_counts": {"errors": errors, "warnings": warnings, "informational": informational},
        "distribution_readiness": readiness,
        "ready_for_distribution": readiness == "ready_for_distribution",
        "limitations": [
            "Near-duplicate detection uses token Jaccard (0.85 threshold) and only flags candidates for human review.",
            "Valid URLs and metadata are structural checks; they do not verify source contents or truth.",
            "Provenance overlap findings are based on recorded identifiers and URLs, not proof of source independence.",
            "This audit does not assign verdicts, fetch sources, access secrets, or create future dataset splits.",
        ],
    }


def render_markdown(report):
    lines = ["# TruthLens pilot quality-control audit", "",
             "**Readiness:** `{0}`".format(report["distribution_readiness"]), "",
             "## Counts", "",
             "- Claims: {0} / {1}".format(report["claim_count"], report["target_claim_count"]),
             "- Evidence passages: {0}".format(report["evidence_count"]),
             "- Claims with evidence: {0}".format(report["claims_with_evidence"]),
             "- Findings: {errors} errors, {warnings} warnings, {informational} informational".format(
                 **report["finding_counts"]), "",
             "## Challenge-category distribution", ""]
    lines.extend("- {0}: {1}".format(category, count)
                 for category, count in report["challenge_category_distribution"].items())
    lines.extend(["", "## Sampling targets", "",
                  "Targets are sampling goals only; no gold verdicts are generated.", "",
                  "```json", json.dumps(report["sampling_target_distribution"]["counts"], indent=2), "```", "",
                  "## Findings", ""])
    if not report["findings"]:
        lines.append("No findings.")
    else:
        for finding in report["findings"]:
            lines.append("- **{0} / {1}:** {2}".format(
                finding["severity"].upper(), finding["code"], finding["message"]))
    lines.extend(["", "## Limitations", ""])
    lines.extend("- " + item for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default=str(DEFAULT_PILOT), help="Pilot preparation folder")
    parser.add_argument("--full-pilot", action="store_true", help="Require exactly the planned 90 claims")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_REPORT),
                        help="Path for machine-readable JSON report")
    parser.add_argument("--markdown-output", help="Optional path to save the human-readable report")
    args = parser.parse_args(argv)
    report = audit_pilot(args.directory, full_pilot=args.full_pilot)
    markdown = render_markdown(report)
    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print("JSON report saved to: {0}".format(json_path))
    if args.markdown_output:
        print("Markdown report saved to: {0}".format(args.markdown_output))
    return 1 if report["finding_counts"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
