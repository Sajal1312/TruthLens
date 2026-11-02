"""Approval/import safety contracts using synthetic records in temp folders only."""
import copy
import importlib
import json
from pathlib import Path

import pytest

from evaluation.annotation.candidate_review import (
    approval_report,
    candidate_checksum,
    prepare_review_packets,
    submit_review,
)
from evaluation.annotation.import_candidates import import_candidates


ANNOTATION = Path(__file__).parents[1] / "evaluation" / "annotation"


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate(number=1):
    """No real-world assertions, sources or labels enter these fixtures."""
    return {
        "claim_id": "synthetic-review-claim-{0:03d}".format(number),
        "claim_text": "Synthetic approval fixture {0}; not a real candidate.".format(number),
        "claim_family_id": "synthetic-review-family-{0:03d}".format(number),
        "event_group_id": None,
        "claim_category": ["ordinary_control", "numerical"],
        "split": "pilot",
        "annotation_status": "unannotated",
        "evidence": [{
            "evidence_id": "synthetic-review-evidence-{0:03d}".format(number),
            "passage": "Synthetic approval test passage; no live source was used.",
            "source_title": "Synthetic source fixture",
            "source_identifier": "synthetic-review-source-{0:03d}".format(number),
            "source_url": "https://example.test/review/{0}".format(number),
            "publisher_id": "synthetic-fixture-publisher",
            "publication_date": None,
            "event_date": None,
            "checked_on": "2026-11-01",
            "provenance_group_id": "synthetic-review-origin-{0:03d}".format(number),
            "provenance_relation": "unknown",
            "provenance_basis": "Synthetic test only; no source independence asserted.",
        }],
    }


def _review(candidate, *, review_id="synthetic-review-001", decision="approved", supersedes=None):
    return {
        "schema_version": "1.0.0",
        "review_id": review_id,
        "candidate_id": candidate["claim_id"],
        "candidate_sha256": candidate_checksum(candidate),
        "reviewer_alias": "synthetic-reviewer",
        "review_timestamp": "2026-11-01T12:00:00Z",
        "source_verification_status": "verified",
        "claim_scope_assessment": {
            "status": "clear", "rationale": "Synthetic fixture scope reviewed for this test only."},
        "evidence_context_assessment": {
            "status": "adequate", "rationale": "Synthetic fixture context reviewed for this test only."},
        "evidence_reviews": [{
            "evidence_id": item["evidence_id"],
            "source_status": "verified",
            "source_verification_basis": "Synthetic workflow test; no actual source verification claimed.",
            "publication_date_status": "publication_date_unknown",
            "verified_publication_date": None,
            "date_rationale": "Synthetic date is unknown and explicitly accepted for this test only.",
            "provenance_assessment": "unknown",
            "provenance_rationale": "Synthetic provenance is unknown; no independence inferred.",
        } for item in candidate["evidence"]],
        "decision": decision,
        "review_rationale": "Synthetic approval workflow fixture; not a human decision on real candidates.",
        "supersedes": supersedes,
    }


def _pilot(tmp_path):
    """Create an empty temp pilot from the public manifest, never copy annotations."""
    directory = tmp_path / "pilot"
    manifest = _read(ANNOTATION / "pilot_90" / "manifest.json")
    manifest["status"] = "collecting"
    _write(directory / "manifest.json", manifest)
    _write(directory / manifest["claim_records_file"], [])
    _write(directory / manifest["adjudications_file"], [])
    for relative_path in manifest["annotator_submission_files"].values():
        _write(directory / relative_path, [])
    return directory


def _tree_bytes(directory):
    if not directory.exists():
        return {}
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def _row(report, candidate):
    return next(row for row in report["candidates"]
                if row["candidate_id"] == candidate["claim_id"])


def test_candidate_checksum_is_canonical_and_covers_claim_and_evidence():
    candidate = _candidate()
    reordered = dict(reversed(list(candidate.items())))
    assert candidate_checksum(candidate) == candidate_checksum(reordered)
    for field in ("claim_text", "claim_family_id"):
        revised = copy.deepcopy(candidate)
        revised[field] += "-changed"
        assert candidate_checksum(revised) != candidate_checksum(candidate)
    for field in ("passage", "source_url", "provenance_basis"):
        revised = copy.deepcopy(candidate)
        revised["evidence"][0][field] += "-changed"
        assert candidate_checksum(revised) != candidate_checksum(candidate)


def test_valid_synthetic_approval_is_bound_to_snapshot(tmp_path):
    candidate = _candidate()
    reviews = tmp_path / "reviews"
    review = _review(candidate)
    assert submit_review(review, {candidate["claim_id"]: candidate}, reviews) == review["review_id"]
    row = _row(approval_report({candidate["claim_id"]: candidate}, reviews), candidate)
    assert row["review_status"] == "approved"
    assert row["import_eligible"] is True
    assert row["blocked_reasons"] == []
    snapshot = reviews / "submitted" / review["review_id"] / "candidate.json"
    assert _read(snapshot) == candidate


def test_missing_approval_is_pending_and_import_is_blocked(tmp_path):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    pilot = _pilot(tmp_path)
    before = _tree_bytes(pilot)
    row = _row(approval_report(candidates, reviews), candidate)
    assert row["review_status"] == "pending"
    assert row["import_eligible"] is False
    plan = import_candidates(candidates, reviews, pilot)
    assert candidate["claim_id"] in plan["blocked"]
    assert plan["applied"] is False
    assert _tree_bytes(pilot) == before


def test_stale_checksum_is_rejected_at_submission_and_invalidates_prior_approval(tmp_path):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    original_review = _review(candidate)
    submit_review(original_review, candidates, reviews)
    revised = copy.deepcopy(candidate)
    revised["evidence"][0]["passage"] += " Updated synthetic context."
    revised_candidates = {revised["claim_id"]: revised}
    row = _row(approval_report(revised_candidates, reviews), revised)
    assert row["review_status"] == "stale"
    assert row["import_eligible"] is False
    plan = import_candidates(revised_candidates, reviews, _pilot(tmp_path))
    assert revised["claim_id"] in plan["blocked"]
    with pytest.raises(ValueError):
        submit_review(original_review, revised_candidates, reviews)


@pytest.mark.parametrize("decision", ["rejected", "revision_required"])
def test_rejected_or_revision_required_candidate_cannot_be_imported(tmp_path, decision):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    submit_review(_review(candidate, decision=decision), candidates, reviews)
    assert _row(approval_report(candidates, reviews), candidate)["review_status"] == decision
    pilot = _pilot(tmp_path)
    before = _tree_bytes(pilot)
    plan = import_candidates(candidates, reviews, pilot, apply=True)
    assert candidate["claim_id"] in plan["blocked"]
    assert plan["applied"] is False
    assert _tree_bytes(pilot) == before


def test_latest_explicit_revision_supersedes_old_approval_without_overwrite(tmp_path):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    original = _review(candidate)
    submit_review(original, candidates, reviews)
    original_files = _tree_bytes(reviews / "submitted" / original["review_id"])
    rejection = _review(candidate, review_id="synthetic-review-002", decision="rejected",
                        supersedes=original["review_id"])
    submit_review(rejection, candidates, reviews)
    row = _row(approval_report(candidates, reviews), candidate)
    assert row["review_status"] == "rejected"
    assert row["import_eligible"] is False
    assert _tree_bytes(reviews / "submitted" / original["review_id"]) == original_files
    with pytest.raises(ValueError):
        submit_review(_review(candidate, review_id="synthetic-review-003",
                              supersedes=original["review_id"]), candidates, reviews)


def test_review_decisions_and_blank_packets_cannot_be_overwritten(tmp_path):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    record = _review(candidate)
    submit_review(record, candidates, reviews)
    before_reviews = _tree_bytes(reviews)
    with pytest.raises((ValueError, FileExistsError)):
        submit_review(record, candidates, reviews)
    assert _tree_bytes(reviews) == before_reviews
    packets = tmp_path / "packets"
    prepare_review_packets(candidates, packets)
    draft = _read(packets / candidate["claim_id"] / "review.json")
    assert draft["reviewer_alias"] is None
    assert draft["review_timestamp"] is None
    assert draft["decision"] is None
    assert len(draft["evidence_reviews"]) == len(candidate["evidence"])
    before_packets = _tree_bytes(packets)
    with pytest.raises((ValueError, FileExistsError)):
        prepare_review_packets(candidates, packets)
    assert _tree_bytes(packets) == before_packets


def test_tampered_submitted_snapshot_fails_integrity_verification(tmp_path):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    record = _review(candidate)
    submit_review(record, candidates, reviews)
    snapshot = reviews / "submitted" / record["review_id"] / "candidate.json"
    snapshot.chmod(0o644)
    snapshot.write_bytes(snapshot.read_bytes() + b" ")
    with pytest.raises(ValueError):
        approval_report(candidates, reviews)


@pytest.mark.parametrize("status", ["publication_date_unknown", "verified_undated_source", "verified_publication_date"])
def test_unknown_undated_and_verified_date_assessments_are_distinct_valid_review_choices(tmp_path, status):
    candidate = _candidate()
    if status == "verified_publication_date":
        candidate["evidence"][0]["publication_date"] = "2026-01-15"
    review = _review(candidate)
    review["evidence_reviews"][0]["publication_date_status"] = status
    review["evidence_reviews"][0]["verified_publication_date"] = candidate["evidence"][0]["publication_date"]
    candidates = {candidate["claim_id"]: candidate}
    submit_review(review, candidates, tmp_path / "reviews")
    assert _row(approval_report(candidates, tmp_path / "reviews"), candidate)["import_eligible"] is True


def test_conflicting_date_metadata_cannot_receive_an_effective_approval(tmp_path):
    candidate = _candidate()
    review = _review(candidate)
    review["evidence_reviews"][0]["publication_date_status"] = "conflicting_date_metadata"
    with pytest.raises(ValueError):
        submit_review(review, {candidate["claim_id"]: candidate}, tmp_path / "reviews")


@pytest.mark.parametrize("field", ["overall_source", "source", "scope", "context", "provenance"])
def test_inconsistent_assessments_cannot_be_recorded_as_approved(tmp_path, field):
    candidate = _candidate()
    review = _review(candidate)
    if field == "overall_source":
        review["source_verification_status"] = "partially_verified"
    elif field == "source":
        review["evidence_reviews"][0]["source_status"] = "inaccessible"
    elif field == "scope":
        review["claim_scope_assessment"]["status"] = "revision_required"
    elif field == "context":
        review["evidence_context_assessment"]["status"] = "revision_required"
    else:
        review["evidence_reviews"][0]["provenance_assessment"] = "conflicting"
    with pytest.raises(ValueError):
        submit_review(review, {candidate["claim_id"]: candidate}, tmp_path / "reviews")


def test_verified_date_must_match_the_exact_candidate_evidence(tmp_path):
    candidate = _candidate()
    candidate["evidence"][0]["publication_date"] = "2026-01-15"
    review = _review(candidate)
    review["evidence_reviews"][0]["publication_date_status"] = "verified_publication_date"
    review["evidence_reviews"][0]["verified_publication_date"] = "2026-01-16"
    with pytest.raises(ValueError):
        submit_review(review, {candidate["claim_id"]: candidate}, tmp_path / "reviews")


def test_every_evidence_item_needs_a_separate_review(tmp_path):
    candidate = _candidate()
    extra = copy.deepcopy(candidate["evidence"][0])
    extra["evidence_id"] += "-extra"
    candidate["evidence"].append(extra)
    review = _review(candidate)
    review["evidence_reviews"].pop()
    with pytest.raises(ValueError):
        submit_review(review, {candidate["claim_id"]: candidate}, tmp_path / "reviews")


def test_missing_evidence_cannot_be_approved(tmp_path):
    candidate = _candidate()
    candidate["evidence"] = []
    with pytest.raises(ValueError):
        submit_review(_review(candidate), {candidate["claim_id"]: candidate}, tmp_path / "reviews")


def test_import_dry_run_leaves_pilot_bytes_unchanged(tmp_path):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    submit_review(_review(candidate), candidates, reviews)
    pilot = _pilot(tmp_path)
    before = _tree_bytes(pilot)
    plan = import_candidates(candidates, reviews, pilot)
    assert plan["dry_run"] is True
    assert plan["eligible_candidate_ids"] == [candidate["claim_id"]]
    assert plan["applied"] is False
    assert _tree_bytes(pilot) == before


def test_explicit_import_appends_without_overwriting_existing_records_or_labels(tmp_path):
    existing = _candidate(99)
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    submit_review(_review(candidate), candidates, reviews)
    pilot = _pilot(tmp_path)
    _write(pilot / "claim_records.json", [existing])
    before_submissions = {name: (pilot / name).read_bytes() for name in (
        "submissions/annotator_1.json", "submissions/annotator_2.json", "adjudications.json")}
    plan = import_candidates(candidates, reviews, pilot, apply=True)
    assert plan["applied"] is True
    assert _read(pilot / "claim_records.json") == [existing, candidate]
    assert all(record["annotation_status"] == "unannotated" for record in _read(pilot / "claim_records.json"))
    assert _read(pilot / "claim_records.json")[1]["evidence"] == candidate["evidence"]
    assert _read(pilot / "claim_records.json")[1]["claim_category"] == candidate["claim_category"]
    assert {name: (pilot / name).read_bytes() for name in before_submissions} == before_submissions
    before_second_import = _tree_bytes(pilot)
    blocked = import_candidates(candidates, reviews, pilot, apply=True)
    assert blocked["applied"] is False
    assert candidate["claim_id"] in blocked["blocked"]
    assert _tree_bytes(pilot) == before_second_import


def test_duplicate_requested_ids_are_rejected(tmp_path):
    candidate = _candidate()
    with pytest.raises(ValueError):
        import_candidates({candidate["claim_id"]: candidate}, tmp_path / "reviews", _pilot(tmp_path),
                          candidate_ids=[candidate["claim_id"], candidate["claim_id"]])


def test_duplicate_evidence_id_against_pilot_is_blocked(tmp_path):
    candidate = _candidate()
    existing = _candidate(99)
    existing["evidence"][0]["evidence_id"] = candidate["evidence"][0]["evidence_id"]
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    submit_review(_review(candidate), candidates, reviews)
    pilot = _pilot(tmp_path)
    _write(pilot / "claim_records.json", [existing])
    before = _tree_bytes(pilot)
    plan = import_candidates(candidates, reviews, pilot, apply=True)
    assert candidate["claim_id"] in plan["blocked"]
    assert plan["applied"] is False
    assert _tree_bytes(pilot) == before


def test_batch_import_is_all_or_nothing_when_one_candidate_has_no_approval(tmp_path):
    first, second = _candidate(1), _candidate(2)
    candidates = {row["claim_id"]: row for row in (first, second)}
    reviews = tmp_path / "reviews"
    submit_review(_review(first), candidates, reviews)
    pilot = _pilot(tmp_path)
    before = _tree_bytes(pilot)
    plan = import_candidates(candidates, reviews, pilot, apply=True)
    assert second["claim_id"] in plan["blocked"]
    assert plan["applied"] is False
    assert _tree_bytes(pilot) == before


def test_empty_candidate_import_is_noop(tmp_path):
    pilot = _pilot(tmp_path)
    before = _tree_bytes(pilot)
    plan = import_candidates({}, tmp_path / "reviews", pilot)
    assert plan["eligible_candidate_ids"] == []
    assert plan["applied"] is False
    assert _tree_bytes(pilot) == before


@pytest.mark.parametrize("hazard", ["ready", "annotation_started", "snapshot_exists"])
def test_import_refuses_frozen_or_annotation_started_pilot(tmp_path, hazard):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    submit_review(_review(candidate), candidates, reviews)
    pilot = _pilot(tmp_path)
    if hazard == "ready":
        manifest = _read(pilot / "manifest.json")
        manifest["status"] = "ready"
        _write(pilot / "manifest.json", manifest)
    elif hazard == "annotation_started":
        _write(pilot / "submissions" / "annotator_1.json", [{}])
    else:
        _write(pilot / "submissions" / "snapshots" / "annotator_1" / "synthetic-snapshot.json", [])
    before = _tree_bytes(pilot)
    try:
        plan = import_candidates(candidates, reviews, pilot, apply=True)
    except (ValueError, RuntimeError):
        pass  # Fail-closed validation may reject before planning.
    else:
        assert plan["applied"] is False
        assert plan["blocked"]
    assert _tree_bytes(pilot) == before


def test_pilot_submission_symlink_is_rejected_before_validator_can_read_it(tmp_path, monkeypatch):
    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    submit_review(_review(candidate), candidates, reviews)
    pilot = _pilot(tmp_path)
    outside = tmp_path / "outside-synthetic.json"
    _write(outside, [])
    submission = pilot / "submissions" / "annotator_1.json"
    submission.unlink()
    submission.symlink_to(outside)
    importer = importlib.import_module("evaluation.annotation.import_candidates")
    called = []

    def must_not_read_redirected_input(*args, **kwargs):
        called.append(True)
        raise AssertionError("Validator must not read redirected pilot inputs")

    monkeypatch.setattr(importer, "validate_pilot", must_not_read_redirected_input)
    with pytest.raises(ValueError):
        import_candidates(candidates, reviews, pilot, apply=True)
    assert called == []
    assert outside.read_text(encoding="utf-8") == "[]"


def test_manual_change_after_completed_import_blocks_the_next_import(tmp_path):
    first, second = _candidate(1), _candidate(2)
    candidates = {row["claim_id"]: row for row in (first, second)}
    reviews = tmp_path / "reviews"
    submit_review(_review(first), candidates, reviews)
    submit_review(_review(second, review_id="synthetic-review-002"), candidates, reviews)
    pilot = _pilot(tmp_path)
    assert import_candidates(candidates, reviews, pilot, [first["claim_id"]], apply=True)["applied"]
    changed = _read(pilot / "claim_records.json")
    changed[0]["evidence"][0]["passage"] += " Accidental synthetic post-import change."
    _write(pilot / "claim_records.json", changed)
    before = _tree_bytes(pilot)
    try:
        plan = import_candidates(candidates, reviews, pilot, [second["claim_id"]], apply=True)
    except (ValueError, RuntimeError):
        pass
    else:
        assert plan["applied"] is False
        assert second["claim_id"] in plan["blocked"]
    assert _tree_bytes(pilot) == before


def test_captured_latest_rejection_cannot_be_used_as_if_it_were_an_approval(tmp_path, monkeypatch):
    """A decision change between preflight and the locked snapshot fails closed."""
    from evaluation.annotation.candidate_review import verify_reviews

    candidate = _candidate()
    candidates = {candidate["claim_id"]: candidate}
    reviews = tmp_path / "reviews"
    original = _review(candidate)
    submit_review(original, candidates, reviews)
    # Build a genuine verified rejection chain in another temp store so the
    # mocked capture contains a valid snapshot, not an invented integrity hash.
    replacement = tmp_path / "replacement-reviews"
    submit_review(original, candidates, replacement)
    submit_review(_review(candidate, review_id="synthetic-review-002", decision="rejected",
                          supersedes=original["review_id"]), candidates, replacement)
    latest_rejection = verify_reviews(replacement)
    importer = importlib.import_module("evaluation.annotation.import_candidates")
    captured = []

    def capture_new_decision(*args, **kwargs):
        captured.append(True)
        return latest_rejection

    monkeypatch.setattr(importer, "verify_reviews", capture_new_decision)
    pilot = _pilot(tmp_path)
    claims_before = (pilot / "claim_records.json").read_bytes()
    manifest_before = (pilot / "manifest.json").read_bytes()
    try:
        plan = import_candidates(candidates, reviews, pilot, apply=True)
    except (ValueError, RuntimeError):
        pass
    else:
        assert plan["applied"] is False
    assert captured  # Ensure the snapshot transition was actually exercised.
    assert (pilot / "claim_records.json").read_bytes() == claims_before
    assert (pilot / "manifest.json").read_bytes() == manifest_before
