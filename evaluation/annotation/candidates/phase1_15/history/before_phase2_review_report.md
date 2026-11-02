# Phase 1 candidate collection review

All candidates await independent human review. No gold labels or model predictions were created.

Collected: 2026-11-01. Claims: 15. Evidence passages: 15.

## Topic distribution

- cybersecurity_technology: 5
- general_factual: 5
- sustainability_environment: 5

## Candidate claims and source provenance

### candidate-p1-env-001

The ocean absorbs about 30 percent of carbon dioxide released into the atmosphere, according to NOAA.

- Topic: sustainability_environment
- Challenge tags: numerical
- Source: [What is Ocean Acidification?](https://oceanservice.noaa.gov/facts/acidification.html) (noaa; institutional_summary).
- Passage locator: Opening explanatory paragraph
- Review: CO2 subscript normalized to plain text. Approximate fraction: reviewers must retain the denominator and scope; no claim of a constant fraction for every year. Page last-updated date is not an original publication date.

### candidate-p1-env-002

Making new aluminum cans from recycled cans uses 95 percent less energy than making them from bauxite ore.

- Topic: sustainability_environment
- Challenge tags: numerical
- Source: [Energy and the environment explained: Recycling and energy](https://www.eia.gov/energyexplained/energy-and-the-environment/recycling-and-energy.php) (us-eia; institutional_summary).
- Passage locator: Recycling saves energy and other resources, final paragraph
- Review: Keep the comparison limited to aluminum cans and the specified raw-material route. Underlying energy calculation was not independently checked.

### candidate-p1-env-003

UNEP estimates that 19–23 million tonnes of plastic waste enter aquatic ecosystems each year.

- Topic: sustainability_environment
- Challenge tags: numerical
- Source: [Plastic pollution & marine litter](https://www.unep.org/en/what-we-do/ocean-seas-and-coasts/ecosystem-degradation-pollution/plastic-pollution-marine-litter) (unep; institutional_summary).
- Passage locator: Facts, first bullet
- Review: This is an estimate and includes lakes and rivers as well as seas. Original estimation study and its reference year still require review.

### candidate-p1-env-004

The Montreal Protocol was signed in 1987 and entered into force in 1989.

- Topic: sustainability_environment
- Challenge tags: compound_claim, event_vs_publication_date
- Source: [The Montreal Protocol on Substances that Deplete the Ozone Layer](https://ozone.unep.org/treaties/montreal-protocol) (unep-ozone-secretariat; official_documentation).
- Passage locator: Introductory treaty overview, first paragraph
- Review: The excerpt gives two event years, not publication dates. No exact day is inferred; event_date remains null. Review both components against the treaty record.

### candidate-p1-env-005

Current global warming cannot be explained by changes in energy from the Sun.

- Topic: sustainability_environment
- Challenge tags: direct_negation
- Source: [Causes](https://science.nasa.gov/climate-change/causes/) (nasa; institutional_summary).
- Passage locator: Evidence Shows That Current Global Warming Cannot Be Explained by Solar Irradiance
- Review: The excerpt introduces a list of reasons. Review the surrounding list and cited research; it does not deny solar influence on past climates. Original studies were not fetched.

### candidate-p1-tech-001

RFC 8446 specifies version 1.3 of the Transport Layer Security protocol.

- Topic: cybersecurity_technology
- Challenge tags: numerical, ordinary_control
- Source: [RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3](https://www.rfc-editor.org/rfc/rfc8446) (ietf-rfc-editor; normative_document).
- Passage locator: Abstract, opening sentence
- Review: The header gives August 2018 only; no day is inferred. The current RFC landing page marks this RFC obsolete and links RFC 9846. This candidate is explicitly about RFC 8446, not the current standard.

### candidate-p1-tech-002

RFC 9110 defines HTTP as a stateless application-level protocol.

- Topic: cybersecurity_technology
- Challenge tags: ordinary_control
- Source: [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) (ietf-rfc-editor; normative_document).
- Passage locator: Abstract, opening sentence
- Review: Header publication date is June 2022 only; no day is inferred. Stateless protocol semantics do not mean web applications cannot maintain session state.

### candidate-p1-tech-003

NIST announced its first three finalized post-quantum encryption standards on 13 August 2024.

- Topic: cybersecurity_technology
- Challenge tags: numerical, event_vs_publication_date
- Source: [NIST Releases First 3 Finalized Post-Quantum Encryption Standards](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards) (nist; original_announcement).
- Passage locator: Article heading and publication date
- Review: Title and date are adjacent source elements. Page footer separately says updated 29 August 2025. Review standard identifiers and avoid claiming all three have the same cryptographic purpose.

### candidate-p1-tech-004

NIST SP 800-63B-4 says verifiers and CSPs must not require periodic password changes.

- Topic: cybersecurity_technology
- Challenge tags: direct_negation
- Source: [NIST Special Publication 800-63B-4: Authentication and Authenticator Management](https://pages.nist.gov/800-63-4/sp800-63b.html) (nist; normative_document).
- Passage locator: Section 3.1.1, password requirements, item 6
- Review: The immediately following sentence requires a change when compromise is evidenced. This is not a ban on all password changes. The HTML build timestamp is not recorded as the original publication date.

### candidate-p1-tech-005

Python 3.13 provides a build configuration that can disable the global interpreter lock.

- Topic: cybersecurity_technology
- Challenge tags: numerical
- Source: [Python 3.13 Glossary: global interpreter lock](https://docs.python.org/3.13/glossary.html#term-global-interpreter-lock) (python-software-foundation; official_documentation).
- Passage locator: Glossary, global interpreter lock, third paragraph
- Review: Conditional on build and runtime configuration; does not assert that every Python installation has no GIL. Documentation is version-specific and can be updated.

### candidate-p1-general-001

Mars has two moons named Phobos and Deimos.

- Topic: general_factual
- Challenge tags: numerical, compound_claim
- Source: [Moons of Mars](https://science.nasa.gov/mars/moons/) (nasa; institutional_summary).
- Passage locator: Moons of Mars, opening sentence
- Review: Named-entity list is a single proposition, not two independent clauses. Reviewer should check count and both names.

### candidate-p1-general-002

Venus is the hottest planet in our solar system.

- Topic: general_factual
- Challenge tags: ordinary_control
- Source: [Venus Facts](https://science.nasa.gov/venus/venus-facts/) (nasa; institutional_summary).
- Passage locator: Surface section, opening sentence
- Review: Scope is planets and surface temperature; not the Sun, and not every atmospheric altitude. Original requested URL redirected to this canonical URL.

### candidate-p1-general-003

CERN placed the World Wide Web software in the public domain on 30 April 1993.

- Topic: general_factual
- Challenge tags: event_vs_publication_date
- Source: [Where the web was born](https://home.cern/science/computing/the-birth-of-the-web/where-web-was-born/) (cern; official_documentation).
- Passage locator: Where the web was born, public-domain paragraph
- Review: Do not confuse the software release event with the 1989 invention or later open-licence releases. An earlier CERN URL returned 404; the canonical page was opened successfully.

### candidate-p1-general-004

The International System of Units is defined using seven defining constants.

- Topic: general_factual
- Challenge tags: numerical
- Source: [The International System of Units (SI): Defining constants](https://www.bipm.org/en/measurement-units/si-defining-constants) (bipm; normative_document).
- Passage locator: SI - Defining constants, opening sentence
- Review: The official metrology page is a current explanatory entry point. No publication date was visible; linked historical resolutions were not treated as this page publication date.

### candidate-p1-general-005

ESA lists Gaia Data Release 4 as expected in December 2026.

- Topic: general_factual
- Challenge tags: future_intent_vs_event, event_vs_publication_date
- Source: [Gaia](https://www.esa.int/Science_Exploration/Space_Science/Gaia) (esa; official_documentation).
- Passage locator: The mission, Upcoming data releases
- Review: A scheduled release is not a completed release. December 2026 is month precision; event_date remains null rather than inventing a day. Recheck the schedule before annotation.

## Candidate QC

Errors: 0; warnings: 19; informational: 3.

Duplicate flags: 0; provenance overlap flags: 0.

Missing metadata: {"publication_date": 14}

Publisher document counts: {"noaa": 1, "us-eia": 1, "unep": 1, "unep-ozone-secretariat": 1, "nasa": 3, "ietf-rfc-editor": 2, "nist": 2, "python-software-foundation": 1, "cern": 1, "bipm": 1, "esa": 1}

Repeated publishers show concentration; they do not establish shared reporting chains or source independence.

Challenge distribution: {"compound_claim": 2, "conflicting_evidence": 0, "direct_negation": 2, "double_negation": 0, "event_vs_publication_date": 4, "future_intent_vs_event": 1, "insufficient_evidence": 0, "numerical": 8, "ordinary_control": 3, "partial_negation": 0, "quantifier_scope": 0}

- warning: claim candidate-p1-env-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-003 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-004 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-005 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-004 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-005 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-003 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-004 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-005 evidence[0] is missing optional metadata: publication_date.
- informational: Metadata completeness summary for publication_date.
- informational: Publication dates and event dates are checked as separate fields; an event date is never inferred from a publication date.
- warning: No current claim is tagged with planned challenge category conflicting_evidence.
- warning: No current claim is tagged with planned challenge category double_negation.
- warning: No current claim is tagged with planned challenge category insufficient_evidence.
- warning: No current claim is tagged with planned challenge category partial_negation.
- warning: No current claim is tagged with planned challenge category quantifier_scope.
- informational: For future development/diagnostic/final-test splits, keep claim-family, event, and documented provenance groups together; do not create a split in this audit.

## Research limitations and collection follow-up

- Convenience sample authored from accessible official pages, not a sample of organically occurring online claims.
- One short source excerpt per claim; no source independence established; no claim-level verdicts assigned.
- No NLI predictions, annotator submissions or adjudications were generated.
- Institutional summaries are not necessarily the original research underlying the statement.
- No target verdict distribution; no claim of balanced stance classes.
- Schema, hashes and QC were checked offline; this command does not refetch pages or establish truth or human approval.
- Retrieval attempt: https://www.cisa.gov/secure-our-world/turn-mfa — 403 Forbidden; not used as evidence
- Retrieval attempt: https://home.cern/science/computing/birth-web — 404; canonical CERN page subsequently opened
- Retrieval attempt: https://www.rfc-editor.org/rfc/rfc9110 — Timeout; .html form subsequently opened
- Retrieval attempt: https://www.un.org/sites/un2.un.org/files/fasct_fact_-_ocean_oct_2022.pdf — 403 Forbidden; not used as evidence
