"""Offline QC audit tests using temporary synthetic records only."""
import json
from pathlib import Path
import shutil

from evaluation.annotation.quality_control import audit_pilot, main, render_markdown


ANNOTATION_ROOT = Path(__file__).parents[1] / "evaluation" / "annotation"
REAL_PILOT = ANNOTATION_ROOT / "pilot_90"


def _copy_pilot(tmp_path):
    target = tmp_path / "pilot_90"
    shutil.copytree(REAL_PILOT, target)
    return target


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _synthetic_claim(index, *, claim_id=None, text=None, category=None):
    colors = ["amber", "blue", "copper", "dawn", "emerald", "frost", "gold", "hazel", "indigo"]
    animals = ["badger", "crane", "dolphin", "falcon", "gecko", "heron", "ibis", "jaguar", "koala", "lemur"]
    actions = ["balances", "collects", "describes", "examines", "follows", "gathers", "holds", "identifies", "joins"]
    objects = ["beacons", "canvases", "dials", "engines", "forests", "gardens", "harbors", "instruments", "journals"]
    claim_id = claim_id or "qc-claim-{0:03d}".format(index)
    evidence_id = "qc-evidence-{0:03d}".format(index)
    category = category or ["ordinary_control"]
    text = text or "Synthetic audit-only assertion: {0} {1} {2} {3}.".format(
        colors[index // 100 % len(colors)], animals[index // 10 % len(animals)],
        actions[index // 3 % len(actions)], objects[index % len(objects)])
    return {
        "claim_id": claim_id,
        "claim_text": text,
        "claim_family_id": "qc-family-{0:03d}".format(index),
        "event_group_id": None,
        "claim_category": category,
        "split": "pilot",
        "annotation_status": "unannotated",
        "evidence": [{
            "evidence_id": evidence_id,
            "passage": "Synthetic QC passage {0}; not a real source or annotation.".format(index),
            "source_title": "Synthetic test source {0}".format(index),
            "source_identifier": "synthetic-source-{0:03d}".format(index),
            "source_url": "https://example.test/source/{0}".format(index),
            "publisher_id": "synthetic-publisher-{0:03d}".format(index),
            "publication_date": "2026-01-01",
            "event_date": None,
            "checked_on": "2026-01-02",
            "provenance_group_id": "qc-provenance-{0:03d}".format(index),
            "provenance_relation": "unknown",
            "provenance_basis": "Synthetic fixture; source independence not assessed.",
        }],
    }


def _write_records(directory, records, *, status="collecting"):
    manifest = _load(directory / "manifest.json")
    manifest["status"] = status
    _save(directory / "manifest.json", manifest)
    _save(directory / manifest["claim_records_file"], records)


def _codes(report):
    return {finding["code"] for finding in report["findings"]}


def test_empty_pilot_is_valid_empty_preparation_not_distribution_ready():
    report = audit_pilot(REAL_PILOT)
    assert report["claim_count"] == 0
    assert report["evidence_count"] == 0
    assert report["distribution_readiness"] == "empty_preparation"
    assert report["ready_for_distribution"] is False
    assert "empty_preparation" in _codes(report)
    assert report["finding_counts"]["warnings"] == 0


def test_full_90_synthetic_claim_bundle_can_be_ready_without_gold_labels(tmp_path):
    directory = _copy_pilot(tmp_path)
    manifest = _load(directory / "manifest.json")
    records = [
        _synthetic_claim(index, category=[manifest["challenge_categories"][index % 11]])
        for index in range(90)
    ]
    _write_records(directory, records)
    report = audit_pilot(directory, full_pilot=True)
    assert report["claim_count"] == 90
    assert report["evidence_count"] == 90
    assert report["distribution_readiness"] == "ready_for_distribution"
    assert report["ready_for_distribution"] is True
    assert report["sampling_target_distribution"]["status"] == "sampling_plan_only_not_gold_labels"
    assert not any("gold_verdict" in str(item) for item in report["findings"])


def test_full_pilot_mode_requires_exactly_90_claims(tmp_path):
    directory = _copy_pilot(tmp_path)
    _write_records(directory, [_synthetic_claim(0)])
    report = audit_pilot(directory, full_pilot=True)
    assert report["distribution_readiness"] == "blocked_errors"
    assert "wrong_claim_count" in _codes(report)


def test_unrepresented_planned_category_requires_human_review(tmp_path):
    directory = _copy_pilot(tmp_path)
    manifest = _load(directory / "manifest.json")
    _write_records(directory, [_synthetic_claim(0, category=[manifest["challenge_categories"][0]])])
    report = audit_pilot(directory)
    findings = [item for item in report["findings"] if item["code"] == "challenge_category_unrepresented"]
    assert findings
    assert all(item["severity"] == "warning" for item in findings)
    assert report["challenge_category_distribution"][manifest["challenge_categories"][0]] == 1
    assert all(category in report["challenge_category_distribution"]
               for category in manifest["challenge_categories"])


def test_duplicate_claim_and_evidence_ids_are_errors(tmp_path):
    directory = _copy_pilot(tmp_path)
    first = _synthetic_claim(0)
    second = _synthetic_claim(1)
    second["claim_id"] = first["claim_id"]
    second["evidence"][0]["evidence_id"] = first["evidence"][0]["evidence_id"]
    _write_records(directory, [first, second])
    report = audit_pilot(directory)
    assert {"duplicate_claim_id", "duplicate_evidence_id"} <= _codes(report)
    assert report["finding_counts"]["errors"] >= 2


def test_missing_evidence_is_an_error(tmp_path):
    directory = _copy_pilot(tmp_path)
    claim = _synthetic_claim(0)
    claim["evidence"] = []
    _write_records(directory, [claim])
    assert "missing_evidence" in _codes(audit_pilot(directory))


def test_invalid_urls_and_dates_are_errors(tmp_path):
    directory = _copy_pilot(tmp_path)
    claim = _synthetic_claim(0)
    claim["evidence"][0]["source_url"] = "javascript:alert(1)"
    claim["evidence"][0]["publication_date"] = "2026-02-30"
    claim["evidence"][0]["event_date"] = "01/02/2026"
    _write_records(directory, [claim])
    codes = _codes(audit_pilot(directory))
    assert "invalid_source_url" in codes
    assert "invalid_date" in codes


def test_unknown_challenge_tag_is_error(tmp_path):
    directory = _copy_pilot(tmp_path)
    _write_records(directory, [_synthetic_claim(0, category=["made_up_category"])])
    assert "unknown_challenge_tag" in _codes(audit_pilot(directory))


def test_exact_and_near_duplicate_claim_text_are_human_review_warnings(tmp_path):
    directory = _copy_pilot(tmp_path)
    first = _synthetic_claim(0, text="A synthetic example claim states the same proposition clearly.")
    second = _synthetic_claim(1, text="A synthetic example claim states the same proposition clearly.")
    third = _synthetic_claim(2, text="A synthetic example claim states the same proposition clearly today.")
    _write_records(directory, [first, second, third])
    report = audit_pilot(directory)
    assert "duplicate_claim_text" in _codes(report)
    assert "near_duplicate_claim_text" in _codes(report)
    assert report["distribution_readiness"] == "incomplete"


def test_provenance_overlap_and_cross_split_groups_are_warnings(tmp_path):
    directory = _copy_pilot(tmp_path)
    first = _synthetic_claim(0)
    second = _synthetic_claim(1)
    first["claim_family_id"] = second["claim_family_id"] = "shared-family"
    first["split"], second["split"] = "development", "final_test"
    first["evidence"][0]["source_url"] = "https://example.test/shared"
    second["evidence"][0]["source_url"] = "https://EXAMPLE.test/shared/?utm_source=qc"
    first["evidence"][0]["provenance_group_id"] = "origin-one"
    second["evidence"][0]["provenance_group_id"] = "origin-two"
    _write_records(directory, [first, second])
    report = audit_pilot(directory)
    codes = _codes(report)
    assert "cross_split_group" in codes
    assert "source_in_multiple_provenance_groups" in codes
    assert report["finding_counts"]["warnings"] >= 2


def test_missing_source_metadata_is_reported_as_warning(tmp_path):
    directory = _copy_pilot(tmp_path)
    claim = _synthetic_claim(0)
    evidence = claim["evidence"][0]
    evidence["source_title"] = None
    evidence["publisher_id"] = None
    evidence["publication_date"] = None
    evidence["checked_on"] = None
    _write_records(directory, [claim])
    report = audit_pilot(directory)
    assert "missing_metadata" in _codes(report)
    assert report["finding_counts"]["warnings"] >= 4
    assert report["metadata_completeness"]["missing_counts_by_field"]["source_title"] == 1


def test_audit_cli_writes_machine_and_human_reports(tmp_path, capsys):
    directory = _copy_pilot(tmp_path)
    json_path = tmp_path / "reports" / "audit.json"
    markdown_path = tmp_path / "reports" / "audit.md"
    code = main(["--directory", str(directory), "--json-output", str(json_path),
                 "--markdown-output", str(markdown_path)])
    output = capsys.readouterr().out
    assert code == 0  # Empty preparation has informational findings only.
    assert "empty_preparation" in output
    assert json.loads(json_path.read_text(encoding="utf-8"))["claim_count"] == 0
    assert "# TruthLens pilot quality-control audit" in markdown_path.read_text(encoding="utf-8")


def test_error_and_warning_severities_are_distinct(tmp_path):
    directory = _copy_pilot(tmp_path)
    claim = _synthetic_claim(0)
    claim["evidence"][0]["source_title"] = None  # warning
    claim["evidence"][0]["source_url"] = "http://not-https.example"  # error
    _write_records(directory, [claim])
    report = audit_pilot(directory)
    severity_by_code = {item["code"]: item["severity"] for item in report["findings"]}
    assert severity_by_code["invalid_source_url"] == "error"
    assert severity_by_code["missing_metadata"] == "warning"
    assert report["distribution_readiness"] == "blocked_errors"

