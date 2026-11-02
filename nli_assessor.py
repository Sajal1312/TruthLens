"""Optional local NLI assessment. Heavy ML packages load only when enabled."""
from functools import lru_cache
import re
import time
from typing import Callable, Dict, List, Optional

from verifier import assess_evidence
from evidence_quality import (NEAR_DUPLICATE_JACCARD_THRESHOLD, passage_similarity,
                              publication_date_signal, source_context)

MODEL_ID = "cross-encoder/nli-deberta-v3-xsmall"
MODEL_REVISION = "03d06b2f6f06023bd596151a16477e2fcec601fb"
MIN_CONFIDENCE = 0.70
MIN_MARGIN = 0.15
MIN_DIRECTIONAL_SOURCES = 2

_STOP_WORDS = set("a an and are around as at be by did do does for from has have in is it of on or that the this to was were will with".split())
_RELATION_GROUPS = (
    {"revolve", "revolves", "revolving", "revolved", "orbit", "orbits", "orbiting", "orbited"},
    {"center", "centre", "central"},
    {"located", "location", "situated", "lies"},
)
_HISTORICAL_CUES = re.compile(r"\b(histor(?:y|ical|ically)|ancient|greek|geocentric|medieval|centuries ago|used to believe)\b", re.I)
_ABSENCE_CUES = re.compile(r"\b(no (?:public )?(?:record|evidence|confirmation)|not (?:publicly )?(?:recorded|confirmed)|unconfirmed|could not be verified|unable to confirm)\b", re.I)
_QUALIFICATION_CUES = re.compile(r"\b(coordinates?|coordinate system|barycenter|centre of mass|center of mass|relative to one another|reference frame|which revolves around which)\b", re.I)
_NONASSERTIVE_CUES = re.compile(
    r"\b(what if|hypothetically|hypothetical|suppose that|imagine that|imagine if|for example, if|"
    r"keep the truth aside|older belief|thought experiment|a world where|a universe where)\b|"
    r"\bif\b[^.!?]{0,180}\b(would|could|might)\b", re.I)
_BELIEF_ATTRIBUTION_CUES = re.compile(
    r"\b(believ(?:e|es|ed|ing)|beliefs?|thought|proposed|claimed|according to the (?:old|ancient|geocentric|ptolemaic) "
    r"(?:view|model)|once (?:widely )?(?:accepted|held|thought)|idea that|appears to|hold that|world view)\b", re.I)
_CLAIM_ABOUT_BELIEF = re.compile(r"\b(believ(?:e|es|ed|ing)|beliefs?|thought|histor(?:y|ical|ically))\b", re.I)
_QUANTIFIER_SCOPE_CUES = re.compile(
    r"\b(?:all|every|each|some|most|none|no|only|never)\b|"
    r"\b(?:at\s+least|at\s+most)\b", re.I
)
_FUTURE_CLAIM_CUES = re.compile(r"\b(?:will|shall|going\s+to)\b", re.I)
_REPORTED_INTENT_CUES = re.compile(
    r"\b(?:plan|plans|planned|planning|intend|intends|intended|intending|aim|aims|aimed|expect|expects|expected|hope|hopes|hoped)\s+to\b|"
    r"\b(?:announced|stated|reported)\s+(?:a\s+)?plan\s+to\b", re.I
)
_CURRENT_REFUTATION_CUES = re.compile(
    r"\b(now )?(debunked|disproved|false|incorrect|not true|no longer accepted|refuted)\b", re.I)
_HISTORICAL_TITLE_CUES = re.compile(r"\b(geocentr(?:ic|ism)|ptolemaic|history|historical)\b", re.I)
_MOTION_RELATION = re.compile(
    r"\b(?:revolv\w*\s+(?:in\s+orbit\s+)?(?:around|about)|"
    r"orbit\w*\s+(?:(?:around|about)\s+)?|"
    r"mov(?:e|es|ing)\s+(?:around|about)|motion\s+(?:around|about))\b", re.I)
_GRAVITY_ORBIT_RELATIONS = (
    re.compile(r"\b(?P<center>[a-z][a-z'-]*)['’]s\s+(?:(?:immense|gravitational)\s+)?"
               r"(?:mass|gravity|gravitational pull)\s+(?:pulls|holds)\s+"
               r"(?P<orbiter>[a-z][a-z'-]*)\s+(?:into|in)\s+(?:its|their|an?)\s+orbit\b", re.I),
    re.compile(r"\b(?:the\s+)?(?:immense\s+)?(?:mass|gravity)\s+of\s+"
               r"(?:the\s+)?(?P<center>[a-z][a-z'-]*)\s+(?:pulls|holds)\s+"
               r"(?P<orbiter>[a-z][a-z'-]*)\s+(?:into|in)\s+(?:its|their|an?)\s+orbit\b", re.I),
)
_YEAR_PATTERN = re.compile(r"\b(?:1[0-9]{3}|20\d{2})\b")
_CLAUSE_PREDICATE = re.compile(
    r"\b(?:is|are|was|were|has|have|had|does|do|did|can|could|will|would|may|might|must|should|"
    r"revolv\w*|orbit\w*|mov\w*|located|lies|lie|contains|contain|launch\w*|promis\w*)\b", re.I)
_CLAUSE_NEGATION = re.compile(r"\b(?:not|never|no|doesn't|does not|isn't|is not|cannot|can't|without)\b", re.I)
_PASSIVE_ORBIT = re.compile(
    r"\b(?P<center>[a-z][a-z'-]*)\s+(?:is|are|was|were|be|been)\s+orbited\s+by\s+"
    r"(?:the\s+)?(?P<orbiter>[a-z][a-z'-]*)\b", re.I)


def _claim_parts(claim: str) -> List[str]:
    """Split simple coordinated propositions so each must earn its own verdict."""
    parts = re.split(r",\s+and\s+|\s+and\s+(?=[A-Z])", claim.strip())
    return [part.strip(" ,.") for part in parts if part.strip(" ,.")] or [claim]


def _looks_like_independent_clause(text: str) -> bool:
    """Conservative surface check: require a subject before a predicate verb."""
    match = _CLAUSE_PREDICATE.search(text)
    if not match:
        return False
    subject = re.sub(r"[^a-zA-Z'-]+", " ", text[:match.start()]).strip().casefold()
    return bool(subject and subject not in {"a", "an", "the", "and", "or"})


def _claim_parts_experimental(claim: str) -> List[str]:
    """Split only explicit independent clauses joined by `and`; preserve lists and `or`.

    This heuristic intentionally leaves coordinated noun phrases, negated
    clauses and disjunctions intact. The original full claim is retained in
    the returned assessment and remains the NLI hypothesis when no safe split
    is detected.
    """
    text = claim.strip()
    pieces = re.split(r"\s+and\s+", text, flags=re.I)
    if len(pieces) < 2:
        return [claim]
    clauses = []
    current = pieces[0].strip(" ,.")
    for next_piece in pieces[1:]:
        next_piece = next_piece.strip(" ,.")
        if (_looks_like_independent_clause(current)
                and _looks_like_independent_clause(next_piece)):
            clauses.append(current)
            current = next_piece
        else:
            current = current + " and " + next_piece
    clauses.append(current)
    return clauses if len(clauses) > 1 else [claim]


def _content_terms(text: str) -> set:
    terms = set(re.findall(r"[a-z]+", text.lower())) - _STOP_WORDS
    # Normalize common inflections for a modest relevance gate, not for verdicts.
    normalized = set()
    for term in terms:
        normalized.add(term)
        if term.endswith("s"):
            normalized.add(term[:-1])
        if term.endswith("ing"):
            normalized.add(term[:-3])
    return normalized


def _relevant_window(part: str, window: str) -> bool:
    """Reject topical-only text before NLI; lexical overlap never decides a label."""
    terms = _content_terms(part)
    if not terms:
        return False
    window_terms = _content_terms(window)
    matched = terms & window_terms
    has_relation = False
    for group in _RELATION_GROUPS:
        if terms & group and window_terms & group:
            has_relation = True
            matched.update(terms & group)
    # Shared subjects alone do not make a passage evidence for the relation in a claim.
    if any(terms & group for group in _RELATION_GROUPS) and not has_relation:
        return False
    claim_motion = _motion_sides(part)
    passage_motion = _motion_sides(window)
    if claim_motion and passage_motion:
        # A relation about a different endpoint (for example a central fire) is
        # merely topical. The reverse direction remains relevant contradiction evidence.
        matches_claim_endpoints = any(
            (claim_subject & passage_subject and claim_object & passage_object)
            or (claim_subject & passage_object and claim_object & passage_subject)
            for claim_subject, claim_object in claim_motion
            for passage_subject, passage_object in passage_motion
        )
        if not matches_claim_endpoints:
            return False
    return len(matched) >= min(2, len(terms)) and len(matched) / len(terms) >= 0.5


def _relevance_level(part: str, window: str) -> str:
    """Explain the existing conservative gate without equating overlap with support."""
    if _relevant_window(part, window):
        return "Directly relevant candidate"
    terms = _content_terms(part)
    if terms & _content_terms(window):
        return "Weakly related"
    return "Unrelated"


def _near_duplicate(left: str, right: str) -> bool:
    return passage_similarity(left, right) >= NEAR_DUPLICATE_JACCARD_THRESHOLD


def _windows(content: str) -> List[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", content) if s.strip()]
    # Add a preceding sentence to preserve context such as “the ancient model said…”.
    output = []
    for index, sentence in enumerate(sentences):
        output.append((sentences[index - 1] + " " if index else "") + sentence)
    return output or ([content] if content.strip() else [])


def _historical_context(window: str) -> bool:
    return bool(_HISTORICAL_CUES.search(window))


def _context_exclusion_reason(claim: str, window: str, title: str) -> Optional[str]:
    """Keep attributed history and counterfactuals from becoming factual votes."""
    claim_is_about_belief = bool(_CLAIM_ABOUT_BELIEF.search(claim))
    historical_frame = _historical_context(window) or bool(_HISTORICAL_TITLE_CUES.search(title))
    attributed_belief = bool(_BELIEF_ATTRIBUTION_CUES.search(window))
    explicitly_refuted_now = bool(_CURRENT_REFUTATION_CUES.search(window))
    if historical_frame and attributed_belief and not claim_is_about_belief and not explicitly_refuted_now:
        return "Historical or attributed belief, not a present-day endorsement"
    if (window.rstrip().endswith("?") or _NONASSERTIVE_CUES.search(window)
            or _NONASSERTIVE_CUES.search(title)) and not claim_is_about_belief:
        return "Question or hypothetical framing, not a factual assertion"
    return None


def _motion_sides_experimental(text: str) -> List[tuple]:
    """Extract motion pairs while normalizing passive `X is orbited by Y` wording."""
    found = []
    for sentence in re.split(r"[.!?;\n]+", text):
        passives = list(_PASSIVE_ORBIT.finditer(sentence))
        for match in passives:
            found.append((_content_terms(match.group("orbiter")),
                          _content_terms(match.group("center"))))
        active_text = _PASSIVE_ORBIT.sub(" ", sentence)
        found.extend(_motion_sides(active_text))
    return found


def _states_reverse_motion_relation(claim: str, passage: str, *, experimental: bool = False) -> bool:
    """Catch a common NLI role-reversal error without turning overlap into a vote."""
    side_extractor = _motion_sides_experimental if experimental else _motion_sides
    claim_sides = side_extractor(claim)
    passage_sides = side_extractor(passage)
    for claim_subject, claim_object in claim_sides:
        for passage_subject, passage_object in passage_sides:
            if (claim_subject & passage_object) and (claim_object & passage_subject):
                if not ((claim_subject & passage_subject) and (claim_object & passage_object)):
                    return True
    return False


def _has_same_motion_relation_experimental(claim: str, passage: str) -> bool:
    """Detect matching active/passive orbit relations for the experimental path."""
    if _CLAUSE_NEGATION.search(passage):
        return False
    claim_sides = _motion_sides_experimental(claim)
    passage_sides = _motion_sides_experimental(passage)
    return any((claim_subject & passage_subject) and (claim_object & passage_object)
               for claim_subject, claim_object in claim_sides
               for passage_subject, passage_object in passage_sides)


def _experimental_motion_relation_direction(claim: str, passage: str) -> Optional[str]:
    """Classify explicit pair direction; mixed same/reverse assertions are ambiguous."""
    claim_sides = _motion_sides_experimental(claim)
    passage_sides = _motion_sides_experimental(passage)
    same = any((claim_subject & passage_subject) and (claim_object & passage_object)
               for claim_subject, claim_object in claim_sides
               for passage_subject, passage_object in passage_sides)
    reverse = any((claim_subject & passage_object) and (claim_object & passage_subject)
                  and not ((claim_subject & passage_subject) and (claim_object & passage_object))
                  for claim_subject, claim_object in claim_sides
                  for passage_subject, passage_object in passage_sides)
    if same and reverse:
        return "mixed"
    if reverse:
        return "reverse"
    if same:
        return "same"
    return None


def _claim_negation_count(claim: str) -> int:
    """Count surface negation cues; multiple cues are ambiguous in this MVP."""
    return len(_CLAUSE_NEGATION.findall(claim))


def _has_unnnegated_same_motion_relation(claim: str, passage: str) -> bool:
    """Detect explicit same-direction wording that NLI incorrectly calls contradiction."""
    for sentence in re.split(r"[.!?;\n]+", passage):
        for match in _MOTION_RELATION.finditer(sentence):
            subject = _content_terms(sentence[:match.start()])
            object_ = _content_terms(sentence[match.end():])
            if not subject or not object_:
                continue
            same_direction = any(
                (claim_subject & subject) and (claim_object & object_)
                for claim_subject, claim_object in _motion_sides(claim)
            )
            if not same_direction:
                continue
            prefix = sentence[:match.start()]
            suffix = sentence[match.end():]
            negated_before = re.search(
                r"\b(?:not|never|no longer|doesn't|does not|isn't|is not|cannot|can't|rather than|instead of|as opposed to)\b.{0,35}$",
                prefix, re.I)
            negated_after = re.search(r"\b(?:is|was|are|were)\s+(?:false|incorrect|not true)\b", suffix, re.I)
            if not negated_before and not negated_after:
                return True
    return False


def _motion_sides(text: str) -> List[tuple]:
    """Extract lightweight subject/object clues from explicit orbit phrasing."""
    found = []
    for sentence in re.split(r"[.!?;\n]+", text):
        for match in _MOTION_RELATION.finditer(sentence):
            subject = _content_terms(sentence[:match.start()])
            object_ = _content_terms(sentence[match.end():])
            if subject and object_:
                found.append((subject, object_))
        for pattern in _GRAVITY_ORBIT_RELATIONS:
            for match in pattern.finditer(sentence):
                orbiter = _content_terms(match.group("orbiter"))
                center = _content_terms(match.group("center"))
                if orbiter and center:
                    found.append((orbiter, center))
    return found


@lru_cache(maxsize=1)
def load_local_nli_model() -> Callable[[str, str], Dict[str, object]]:
    """Load the pinned safetensors model on demand; tests mock this function."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        use_safetensors=True,
    )
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model.to(device)
    model.eval()

    id_to_label = getattr(model.config, "id2label", {}) or {}
    labels = _label_indices(id_to_label)
    if not labels:
        # The selected model card documents this three-class order.
        labels = {0: "CONTRADICTS", 1: "SUPPORTS", 2: "NOT ENOUGH INFORMATION"}

    def predictions_from_logits(logits) -> List[Dict[str, object]]:
        probability_rows = torch.softmax(logits, dim=-1).detach().cpu().tolist()
        predictions = []
        for probabilities in probability_rows:
            ordered = sorted(enumerate(probabilities), key=lambda pair: pair[1], reverse=True)
            best_id, confidence = ordered[0]
            margin = confidence - ordered[1][1] if len(ordered) > 1 else confidence
            predictions.append({
                "label": labels.get(best_id, "UNKNOWN"),
                "confidence": float(confidence),
                "margin": float(margin),
                "scores": {labels.get(index, "UNKNOWN"): float(score)
                           for index, score in enumerate(probabilities)},
            })
        return predictions

    def predict_batch(pairs):
        if not pairs:
            return []
        encoded = tokenizer(
            [premise for premise, _hypothesis in pairs],
            [_hypothesis for _premise, _hypothesis in pairs],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        encoded = {name: tensor.to(device) for name, tensor in encoded.items()}
        with torch.inference_mode():
            logits = model(**encoded).logits
        return predictions_from_logits(logits)

    def predict(premise: str, hypothesis: str) -> Dict[str, object]:
        encoded = tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        encoded = {name: tensor.to(device) for name, tensor in encoded.items()}
        with torch.inference_mode():
            logits = model(**encoded).logits
        return predictions_from_logits(logits)[0]

    # Used by the offline benchmark to compare batch inference. Production
    # assessment remains sequential until an end-to-end integration is proven.
    predict.predict_batch = predict_batch
    return predict


def _label_indices(id_to_label: Dict[object, object]) -> Dict[int, str]:
    found = {}
    for raw_index, raw_label in id_to_label.items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        label = str(raw_label).lower()
        if "contrad" in label:
            found[index] = "CONTRADICTS"
        elif "entail" in label or "support" in label:
            found[index] = "SUPPORTS"
        elif "neutral" in label or "not enough" in label:
            found[index] = "NOT ENOUGH INFORMATION"
    return found if len(set(found.values())) == 3 else {}


def _source_key(item: Dict[str, str]) -> Optional[str]:
    from verifier import _source_key as verifier_source_key
    return verifier_source_key(item)


def assess_evidence_nli(
    claim: str,
    results: List[Dict[str, str]],
    predict: Callable[[str, str], Dict[str, object]],
    *,
    experimental_semantic: bool = False,
    experimental_quantifier_guard: bool = False,
    experimental_temporal_guard: bool = False,
    cache_predictions: bool = False,
    timings: Optional[Dict[str, float]] = None,
) -> Dict[str, object]:
    """Assess relevant passages; experimental semantic behavior is opt-in only."""
    assessment_started = time.perf_counter()
    parts = _claim_parts_experimental(claim) if experimental_semantic else _claim_parts(claim)
    claim_years = set(_YEAR_PATTERN.findall(claim))
    per_source = []
    votes = {part: {} for part in parts}
    vote_passages = {part: {} for part in parts}
    candidate_phase_started = time.perf_counter()
    inference_seconds = 0.0
    model_calls = 0
    cache_hits = 0
    prediction_cache = {}
    for item in results:
        title = item.get("title") or item.get("url") or "Retrieved source"
        row = {"title": title, "url": item.get("url", ""), "label": "UNCERTAIN", "confidence": None,
               "margin": None, "status": "No relevant passage produced a clear prediction", "part_assessments": [],
               "source_context": source_context(item.get("url", "")), "relevance": "Unrelated",
               "independence": "No directional passage counted", "date_relevance": "No explicit claim year",
               "publication_date_signal": publication_date_signal(claim, item.get("published_date", ""))}
        source_key = _source_key(item)
        if not source_key:
            row["status"] = "Not counted: source URL is missing or invalid"
            per_source.append(row)
            continue
        for part in parts:
            candidates = []
            weak_related_seen = False
            temporal_mismatch_seen = False
            matching_claim_year_seen = False
            for window in _windows(item.get("content", "")):
                relevance = _relevance_level(part, window)
                if relevance == "Weakly related":
                    weak_related_seen = True
                    continue
                if relevance != "Directly relevant candidate":
                    continue
                # Record the filtering result before model aggregation so even a
                # within-source conflict is not later displayed as unrelated.
                row["relevance"] = "Directly relevant candidate"
                window_years = set(_YEAR_PATTERN.findall(window))
                if claim_years and window_years:
                    if not claim_years.intersection(window_years):
                        temporal_mismatch_seen = True
                        continue
                    matching_claim_year_seen = True
                try:
                    cache_key = (window, part)
                    cache_hit = cache_predictions and cache_key in prediction_cache
                    if cache_hit:
                        output = prediction_cache[cache_key]
                        cache_hits += 1
                    else:
                        inference_started = time.perf_counter()
                        try:
                            output = predict(window, part)  # Passage is premise; claim component is hypothesis.
                        finally:
                            inference_seconds += time.perf_counter() - inference_started
                            model_calls += 1
                        if cache_predictions and isinstance(output, dict):
                            prediction_cache[cache_key] = output
                    model_label = _canonical_label(output.get("label"))
                    label = model_label
                    confidence = float(output.get("confidence", 0.0))
                    margin = float(output.get("margin", 0.0))
                    scores = output.get("scores") if isinstance(output.get("scores"), dict) else {}
                    if not (0.0 <= confidence <= 1.0 and 0.0 <= margin <= 1.0):
                        continue
                    context_exclusion = _context_exclusion_reason(part, window, title)
                    semantic_adjustment = ""
                    if _ABSENCE_CUES.search(window):
                        label = "NOT ENOUGH INFORMATION"
                        context_exclusion = "No confirmation or public evidence stated"
                    if not context_exclusion:
                        direction = _experimental_motion_relation_direction(part, window)
                        negation_count = _claim_negation_count(part)
                        if negation_count > 1 and direction is not None:
                            # Double/stacked negation is ambiguous regardless
                            # of path or raw model stance. Avoid a confident
                            # SUPPORTS or CONTRADICTS vote when scope is unclear.
                            label = "NOT ENOUGH INFORMATION"
                            context_exclusion = "Multiple negation cues make the motion-relation claim ambiguous"
                    if (experimental_quantifier_guard and not context_exclusion
                            and _QUANTIFIER_SCOPE_CUES.search(part)):
                        # This is an abstention guard, not a lexical verdict rule:
                        # keep the raw NLI output for inspection, but do not let
                        # an unvalidated scope interpretation create a direction.
                        label = "NOT ENOUGH INFORMATION"
                        context_exclusion = "Experimental abstention: quantifier scope is not reliably resolved"
                    if (experimental_temporal_guard and not context_exclusion
                            and _FUTURE_CLAIM_CUES.search(part)
                            and _REPORTED_INTENT_CUES.search(window)):
                        # A reported intention is evidence of a plan, not proof
                        # that a future event will occur. Keep this opt-in.
                        label = "NOT ENOUGH INFORMATION"
                        context_exclusion = "Experimental abstention: reported future intent does not establish that the event will occur"
                    if not context_exclusion and model_label == "SUPPORTS":
                        if experimental_semantic:
                            direction = _experimental_motion_relation_direction(part, window)
                            negation_count = _claim_negation_count(part)
                            if direction == "mixed":
                                label = "NOT ENOUGH INFORMATION"
                                context_exclusion = "Passage states both motion directions; relation is ambiguous"
                            elif direction == "reverse" and negation_count == 1:
                                # One explicit negation makes SUPPORTS compatible
                                # with the opposite relation. Preserve it.
                                label = "SUPPORTS"
                                semantic_adjustment = "Model support retained for a singly negated reverse-relation claim in experimental mode"
                            elif direction == "reverse":
                                # Relevance, time, and contextual checks have
                                # already passed; only the explicit relation
                                # direction changes the model's role-reversal label.
                                label = "CONTRADICTS"
                                semantic_adjustment = "Explicit subject/object reversal treated as contradiction in experimental mode"
                        elif _states_reverse_motion_relation(part, window):
                            label = "NOT ENOUGH INFORMATION"
                            context_exclusion = "Passage states the reverse motion relationship; model support was not counted"
                    same_motion_relation = (
                        _has_same_motion_relation_experimental(part, window)
                        if experimental_semantic else
                        _has_unnnegated_same_motion_relation(part, window)
                    )
                    if not context_exclusion and model_label == "CONTRADICTS" and same_motion_relation:
                        label = "NOT ENOUGH INFORMATION"
                        context_exclusion = "Passage states the same motion direction; model contradiction was not counted"
                    # Preserve the raw model output separately from the conservative
                    # contextual label used for aggregation.
                    if context_exclusion:
                        label = "NOT ENOUGH INFORMATION"
                    # Scope qualifiers only affect the local passage/window; an
                    # unrelated phrase elsewhere in a long snippet must not veto it.
                    source_scope_qualified = _QUALIFICATION_CUES.search(window)
                    if source_scope_qualified:
                        label = "NOT ENOUGH INFORMATION"
                        context_exclusion = "Passage qualifies the claim by reference frame or scope"
                    accepted = confidence >= MIN_CONFIDENCE and margin >= MIN_MARGIN and label in ("SUPPORTS", "CONTRADICTS")
                    candidates.append((confidence, margin, label, accepted, scores, window,
                                       model_label, context_exclusion, semantic_adjustment, cache_hit))
                except Exception:
                    continue
            if candidates:
                # A clear directional pair outranks a high-confidence neutral result.
                clear = [candidate for candidate in candidates if candidate[3]]
                clear_labels = {candidate[2] for candidate in clear}
                if len(clear_labels) > 1:
                    assessment = {"claim_part": part, "label": "CONFLICTING", "confidence": None,
                                  "margin": None, "scores": {}, "contributed": False,
                                  "status": "Relevant passages on this URL conflict; no directional vote counted",
                                  "passages": [{"text": candidate[5], "label": candidate[2],
                                                "model_label": candidate[6], "confidence": candidate[0],
                                                "margin": candidate[1], "inference_cache_hit": candidate[9]}
                                               for candidate in clear]}
                    row["independence"] = "Conflicting passages from this source; no directional vote counted"
                    row["status"] = "Relevant passages conflict; no directional vote counted"
                else:
                    chosen = max(clear or candidates, key=lambda entry: entry[0])
                    confidence, margin, label, accepted, scores, chosen_window, model_label, context_exclusion, semantic_adjustment, cache_hit = chosen
                    passage_key = re.sub(r"\s+", " ", chosen_window).strip().casefold()
                    repeated_passage = any(
                        _near_duplicate(passage_key, prior)
                        for source_passages in vote_passages[part].values()
                        for prior in source_passages.values()
                    )
                    assessment = {"claim_part": part, "label": label if accepted else "UNCERTAIN",
                                  "predicted_label": label, "model_label": model_label,
                                  "confidence": confidence, "margin": margin,
                                  "passage": chosen_window,
                                  "scores": scores, "contributed": bool(accepted and not repeated_passage),
                                  "inference_cache_hit": cache_hit,
                                  "status": ("Excluded as directional evidence: " + context_exclusion if context_exclusion
                                             else semantic_adjustment if semantic_adjustment
                                             else "Repeated passage; not counted as independent evidence" if accepted and repeated_passage
                                             else "Relevant passage; clear model score" if accepted
                                             else "Relevant passage; below threshold or non-directional")}
                    if accepted:
                        if not repeated_passage:
                            votes[part].setdefault(source_key, {})[label] = title
                            vote_passages[part].setdefault(source_key, {})[label] = passage_key
                    row["relevance"] = "Directly relevant candidate"
                    row["date_relevance"] = (
                        "Claim year appears in snippet" if matching_claim_year_seen
                        else "Snippet year differs from claim" if temporal_mismatch_seen
                        else "No explicit claim year"
                    )
                    if repeated_passage:
                        row["independence"] = "Copied or near-duplicate passage; not independently counted"
                    elif accepted:
                        row["independence"] = "Distinct passage counted once for this source"
            else:
                assessment = {"claim_part": part, "label": "NOT ENOUGH INFORMATION", "confidence": None,
                              "margin": None, "scores": {}, "contributed": False,
                              "status": ("Snippet discusses a different year; not treated as evidence for this claim component"
                                         if temporal_mismatch_seen else
                                         "Only weakly related wording; no direct evidence passage"
                                         if weak_related_seen else
                                         "No relevant passage for this claim component")}
                if temporal_mismatch_seen:
                    row["relevance"] = "Different time period"
                    row["date_relevance"] = "Snippet year differs from claim"
                elif weak_related_seen and row["relevance"] == "Unrelated":
                    row["relevance"] = "Weakly related"
            row["part_assessments"].append(assessment)
        directional = [a for a in row["part_assessments"] if a["contributed"]]
        if directional:
            row["label"] = directional[0]["label"] if len({a["label"] for a in directional}) == 1 else "MIXED BY CLAIM PART"
            row["confidence"] = directional[0]["confidence"]
            row["margin"] = directional[0]["margin"]
            row["status"] = "NLI assessed relevant passage(s); see claim-part labels"
        elif any(a.get("predicted_label") == "NOT ENOUGH INFORMATION" for a in row["part_assessments"]):
            row["label"] = "NOT ENOUGH INFORMATION"
        per_source.append(row)

    candidate_phase_finished = time.perf_counter()
    aggregation_started = candidate_phase_finished
    part_outcomes = []
    for part in parts:
        labels_by_source = votes[part]
        # Repeated/copied passages across different result URLs do not become
        # independent evidence merely because they appear on multiple pages.
        support_passages = {vote_passages[part][source].get("SUPPORTS")
                            for source, labels in labels_by_source.items() if "SUPPORTS" in labels}
        contradiction_passages = {vote_passages[part][source].get("CONTRADICTS")
                                  for source, labels in labels_by_source.items() if "CONTRADICTS" in labels}
        supports = len(support_passages - {None})
        contradicts = len(contradiction_passages - {None})
        if supports and contradicts:
            outcome = "conflicting"
        elif supports >= MIN_DIRECTIONAL_SOURCES and not contradicts:
            outcome = "Supported"
        elif contradicts >= MIN_DIRECTIONAL_SOURCES and not supports:
            outcome = "Contradicted"
        else:
            outcome = "Inconclusive"
        part_outcomes.append((part, outcome))

    evidence_used = []
    for part, _outcome in part_outcomes:
        for source_key, labels in votes[part].items():
            for label, source_title in labels.items():
                evidence_used.append("{0} for ‘{1}’: {2}".format(label, part, source_title))
    outcomes = {outcome for _part, outcome in part_outcomes}
    if "conflicting" in outcomes or ("Supported" in outcomes and "Contradicted" in outcomes):
        verdict = "Inconclusive"
        reasoning = "Relevant passages conflict, or different parts point in opposite directions; TruthLens cannot choose an overall direction."
    elif len(parts) > 1 and outcomes == {"Contradicted"}:
        verdict = "Contradicted"
        reasoning = "Each separated claim component has at least two distinct relevant URLs with high-confidence contradiction labels and no support. This is an evidence-based model assessment, not proof."
    elif len(parts) > 1 and outcomes == {"Supported"}:
        verdict = "Supported"
        reasoning = "Each separated claim component has at least two distinct relevant URLs with high-confidence support labels and no contradiction. This is an evidence-based model assessment, not proof."
    elif len(parts) == 1 and outcomes == {"Contradicted"}:
        verdict = "Contradicted"
        reasoning = "At least two distinct relevant URLs yielded high-confidence contradiction labels with no support. This is the model's reading of the evidence, not proof that the claim is false."
    elif len(parts) == 1 and outcomes == {"Supported"}:
        verdict = "Supported"
        reasoning = "At least two distinct relevant URLs yielded high-confidence support labels with no contradiction. This is the model's reading of the evidence, not proof that the claim is true."
    else:
        verdict = "Inconclusive"
        reasoning = "At least one claim component lacks two distinct relevant, high-confidence URLs agreeing on a direction. Irrelevant, absent, or insufficient evidence does not establish falsity."
    if len(parts) > 1:
        reasoning += " Component results: " + "; ".join("{0} → {1}".format(part, outcome) for part, outcome in part_outcomes)
    elif verdict == "Inconclusive":
        if any("SUPPORTS" in labels and "CONTRADICTS" in labels for by_source in votes.values() for labels in by_source.values()) or (
                any("SUPPORTS" in labels for by_source in votes.values() for labels in by_source.values()) and
                any("CONTRADICTS" in labels for by_source in votes.values() for labels in by_source.values())):
            reasoning = "The local NLI model found both supporting and contradicting snippets. The evidence conflicts, so TruthLens cannot choose a direction."
        elif any(sum(label in labels for labels in by_source.values()) == 1
                 for by_source in votes.values() for label in ("SUPPORTS", "CONTRADICTS")):
            reasoning = "Only one distinct URL produced a clear directional NLI result. TruthLens requires agreement from at least two distinct URLs."

    result = {
        "original_claim": claim,
        "experimental_semantic": experimental_semantic,
        "verdict": verdict,
        "method": "Local NLI model: DeBERTa-v3-xsmall (experimental; confidence thresholded)",
        "reasoning": reasoning,
        "evidence_used": evidence_used,
        "limitations": _nli_limitations(),
        "per_source": per_source,
        "part_outcomes": [{"claim_part": part, "verdict": outcome} for part, outcome in part_outcomes],
        "fallback_used": False,
    }
    if timings is not None:
        aggregation_finished = time.perf_counter()
        timings.update({
            "evidence_filtering_ms": max(0.0, (candidate_phase_finished - candidate_phase_started - inference_seconds) * 1000),
            "nli_inference_ms": inference_seconds * 1000,
            "aggregation_ms": (aggregation_finished - aggregation_started) * 1000,
            "assessment_total_ms": (aggregation_finished - assessment_started) * 1000,
            "nli_model_calls": model_calls,
            "nli_cache_hits": cache_hits,
        })
    return result


def assess_with_optional_nli(
    claim: str,
    results: List[Dict[str, str]],
    model_loader: Optional[Callable[[], Callable[[str, str], Dict[str, object]]]] = None,
    *,
    cache_predictions: bool = False,
    timings: Optional[Dict[str, float]] = None,
) -> Dict[str, object]:
    """Use local NLI when possible; fall back to the existing rule-based method."""
    wrapper_started = time.perf_counter()
    if not results:
        result = {
            "verdict": "Inconclusive",
            "method": "Local NLI not run (no retrieved snippets)",
            "reasoning": "No usable search snippets were returned, so there is no evidence to classify.",
            "evidence_used": [],
            "limitations": _nli_limitations(),
            "per_source": [],
            "fallback_used": False,
        }
        if timings is not None:
            timings.update({"model_load_ms": 0.0, "nli_inference_ms": 0.0,
                            "assessment_total_ms": (time.perf_counter() - wrapper_started) * 1000,
                            "nli_model_calls": 0})
        return result
    loader = model_loader or load_local_nli_model
    model_load_started = time.perf_counter()
    try:
        predictor = loader()
        model_load_seconds = time.perf_counter() - model_load_started
    except Exception:
        model_load_seconds = time.perf_counter() - model_load_started
        fallback = assess_evidence(claim, results)
        fallback["method"] = "Rule-based fallback (local NLI model unavailable)"
        fallback["reasoning"] = ("The local NLI model could not be loaded, so the existing conservative rule-based "
                                 "fallback was used. " + str(fallback["reasoning"]))
        fallback["limitations"] = str(fallback["limitations"]) + " The optional NLI model was unavailable for this check."
        fallback["fallback_used"] = True
        fallback["per_source"] = [
            {"title": item.get("title") or item.get("url") or "Retrieved source", "url": item.get("url", ""),
             "label": "NLI not run", "confidence": None, "margin": None,
             "status": "Existing rule-based fallback was used"}
            for item in results
        ]
        if timings is not None:
            timings.update({"model_load_ms": model_load_seconds * 1000,
                            "nli_inference_ms": 0.0,
                            "rule_assessment_ms": (time.perf_counter() - model_load_started) * 1000 - model_load_seconds * 1000,
                            "assessment_total_ms": (time.perf_counter() - wrapper_started) * 1000,
                            "nli_model_calls": 0})
        return fallback
    result = assess_evidence_nli(claim, results, predictor,
                                 cache_predictions=cache_predictions, timings=timings)
    if timings is not None:
        timings["model_load_ms"] = model_load_seconds * 1000
        timings["assessment_total_ms"] = (time.perf_counter() - wrapper_started) * 1000
    return result


def _canonical_label(label: object) -> str:
    value = str(label).strip().lower().replace("_", " ").replace("-", " ")
    if "contrad" in value:
        return "CONTRADICTS"
    if "entail" in value or "support" in value:
        return "SUPPORTS"
    if "neutral" in value or "not enough" in value or value in ("nei", "unknown"):
        return "NOT ENOUGH INFORMATION" if value != "unknown" else "UNKNOWN"
    return "UNKNOWN"


def _nli_limitations() -> str:
    return ("NLI classifies the relationship expressed by text; it does not verify facts or establish that sources are "
            "accurate, credible, or independent. Model scores are not calibrated probabilities. Snippets can omit context, "
            "and NLI can misread dates, quantities, quotations, and complex reasoning. Open the source links and verify them yourself.")
