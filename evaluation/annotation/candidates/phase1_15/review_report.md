# Candidate collection review

Collection: truthlens-phase1-15-v1

All candidates await independent human review. No gold labels or model predictions were created.

Collected: 2026-11-01. Claims: 15. Evidence passages: 22.

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
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: CO2 subscript normalized to plain text. Approximate fraction: reviewers must retain the denominator and scope; no claim of a constant fraction for every year. Page last-updated date is not an original publication date.

- Date check: NOAA shows Last updated 09/23/26, not an original publication date. Exact original publication day remains unknown.

### candidate-p1-env-002

Making new aluminum cans from recycled cans uses 95 percent less energy than making them from bauxite ore.

- Topic: sustainability_environment
- Challenge tags: numerical

- Source: [Energy and the environment explained: Recycling and energy](https://www.eia.gov/energyexplained/energy-and-the-environment/recycling-and-energy.php) (us-eia; institutional_summary).
- Passage locator: Recycling saves energy and other resources, final paragraph
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Keep the comparison limited to aluminum cans and the specified raw-material route. Underlying energy calculation was not independently checked.

- Date check: Opened source page and checked visible title, publisher, excerpt and date information. No authoritative original publication day located; date remains unknown.

- Source: [Benefits of Recycling](https://nems.nih.gov/environmental-programs/Pages/Benefits-of-Recycling.aspx) (us-nih; institutional_summary).
- Passage locator: Benefits of Recycling, energy bullet
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: NIH summary uses aluminum broadly. Its underlying calculation and independence from other government summaries are unknown; not a second independent measurement.

### candidate-p1-env-003

UNEP estimates that 19–23 million tonnes of plastic waste enter aquatic ecosystems each year.

- Topic: sustainability_environment
- Challenge tags: numerical

- Source: [Plastic pollution & marine litter](https://www.unep.org/en/what-we-do/ocean-seas-and-coasts/ecosystem-degradation-pollution/plastic-pollution-marine-litter) (unep; institutional_summary).
- Passage locator: Facts, first bullet
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: This is an estimate and includes lakes and rivers as well as seas. Original estimation study and its reference year still require review.

- Date check: Opened source page and checked visible title, publisher, excerpt and date information. No authoritative original publication day located; date remains unknown.

- Source: [Predicted growth in plastic waste exceeds efforts to mitigate plastic pollution](https://pubmed.ncbi.nlm.nih.gov/32943526/) (aaas-science; primary_research_abstract).
- Passage locator: Abstract; PubMed PMID 32943526; DOI 10.1126/science.aba3656
- Publication date: 2020-09-17; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: PubMed records Epub 17 September and journal issue 18 September 2020; publication_date uses first-online date. Estimate is for 2016, while UNEP uses an annual framing. Review temporal scope before approval; numeric similarity does not prove a direct citation chain.

### candidate-p1-env-004

The Montreal Protocol was signed in 1987 and entered into force in 1989.

- Topic: sustainability_environment
- Challenge tags: compound_claim, event_vs_publication_date

- Source: [The Montreal Protocol on Substances that Deplete the Ozone Layer](https://ozone.unep.org/treaties/montreal-protocol) (unep-ozone-secretariat; official_treaty_summary).
- Passage locator: Introductory treaty overview, first paragraph
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: The excerpt gives two event years, not publication dates. No exact day is inferred; event_date remains null. Review both components against the treaty record.

- Date check: Opened source page and checked visible title, publisher, excerpt and date information. No authoritative original publication day located; date remains unknown.

- Source: [Montreal Protocol on Substances that Deplete the Ozone Layer — UN Treaty Collection](https://treaties.un.org/Pages/showDetails.aspx?objid=080000028003f7f7) (un-treaty-collection; primary_treaty_registry).
- Passage locator: Registration 26369, conclusion and EIF fields
- Publication date: unknown; event date: 1989-01-01; access date: 2026-11-01.
- Review: Table cells extracted with layout normalized; exact conclusion date is 16 September 1987 and entry into force is 1 January 1989. event_date stores entry into force only. Registry publication date is unknown; this is the same treaty, not independent reporting.

### candidate-p1-env-005

Current global warming cannot be explained by changes in energy from the Sun.

- Topic: sustainability_environment
- Challenge tags: direct_negation

- Source: [Causes](https://science.nasa.gov/climate-change/causes/) (nasa; institutional_summary).
- Passage locator: Evidence Shows That Current Global Warming Cannot Be Explained by Solar Irradiance
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: The excerpt introduces a list of reasons. Review the surrounding list and cited research; it does not deny solar influence on past climates. Original studies were not fetched.

- Date check: NASA footer gives Page Last Updated: Oct 23, 2026. This is not treated as original publication date.

### candidate-p1-tech-001

RFC 8446 specifies version 1.3 of the Transport Layer Security protocol.

- Topic: cybersecurity_technology
- Challenge tags: numerical, ordinary_control

- Source: [RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3](https://www.rfc-editor.org/rfc/rfc8446) (ietf-rfc-editor; normative_document).
- Passage locator: Abstract, opening sentence
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: The header gives August 2018 only; no day is inferred. The current RFC landing page marks this RFC obsolete and links RFC 9846. This candidate is explicitly about RFC 8446, not the current standard.

- Date check: RFC header gives August 2018 only. Original publication day remains unknown; no day imputed. Version-scoped historical document.

### candidate-p1-tech-002

RFC 9110 defines HTTP as a stateless application-level protocol.

- Topic: cybersecurity_technology
- Challenge tags: ordinary_control

- Source: [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) (ietf-rfc-editor; normative_document).
- Passage locator: Abstract, opening sentence
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Header publication date is June 2022 only; no day is inferred. Stateless protocol semantics do not mean web applications cannot maintain session state.

- Date check: RFC header gives June 2022 only. Original publication day remains unknown; no day imputed.

### candidate-p1-tech-003

NIST announced its first three finalized post-quantum encryption standards on 13 August 2024.

- Topic: cybersecurity_technology
- Challenge tags: numerical, event_vs_publication_date

- Source: [NIST Releases First 3 Finalized Post-Quantum Encryption Standards](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards) (nist; original_announcement).
- Passage locator: Article heading and publication date
- Publication date: 2024-08-13; event date: 2024-08-13; access date: 2026-11-01.
- Review: Title and date are adjacent source elements. Page footer separately says updated 29 August 2025. Review standard identifiers and avoid claiming all three have the same cryptographic purpose.

- Date check: Publication date and separately stated updated date reconfirmed in NIST article.

- Source: [FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard](https://csrc.nist.gov/pubs/fips/203/final) (nist; primary_standard_catalog).
- Passage locator: FIPS 203 heading and Date Published
- Publication date: 2024-08-13; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Partial coverage only: confirms one standard and its date, not the full three-standard announcement. Same NIST publisher and release program; not independent corroboration.

### candidate-p1-tech-004

NIST SP 800-63B-4 says verifiers and CSPs must not require periodic password changes.

- Topic: cybersecurity_technology
- Challenge tags: direct_negation

- Source: [NIST Special Publication 800-63B-4: Authentication and Authenticator Management](https://pages.nist.gov/800-63-4/sp800-63b.html) (nist; normative_document).
- Passage locator: Section 3.1.1, password requirements, item 6
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: The immediately following sentence requires a change when compromise is evidenced. This is not a ban on all password changes. The HTML build timestamp is not recorded as the original publication date.

- Date check: Official NIST catalog https://csrc.nist.gov/pubs/sp/800/63/b/4/final gives Date Published: July 2025, only month precision. HTML build timestamp is not original publication date.

### candidate-p1-tech-005

Python 3.13 provides a build configuration that can disable the global interpreter lock.

- Topic: cybersecurity_technology
- Challenge tags: numerical

- Source: [Python 3.13 Glossary: global interpreter lock](https://docs.python.org/3.13/glossary.html#term-global-interpreter-lock) (python-software-foundation; official_documentation).
- Passage locator: Glossary, global interpreter lock, third paragraph
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Conditional on build and runtime configuration; does not assert that every Python installation has no GIL. Documentation is version-specific and can be updated.

- Date check: Opened source page and checked visible title, publisher, excerpt and date information. No authoritative original publication day located; date remains unknown.

- Source: [PEP 703 – Making the Global Interpreter Lock Optional in CPython](https://peps.python.org/pep-0703/) (python-software-foundation; primary_design_document).
- Passage locator: Abstract; Created and Python-Version header fields
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Created 09-Jan-2023 is a proposal creation date, not a final documentation publication date. Header identifies Python 3.13; proposal language alone does not prove deployment. Same ecosystem as the glossary.

### candidate-p1-general-001

Mars has two moons named Phobos and Deimos.

- Topic: general_factual
- Challenge tags: numerical, compound_claim

- Source: [Moons of Mars](https://science.nasa.gov/mars/moons/) (nasa; institutional_summary).
- Passage locator: Moons of Mars, opening sentence
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Named-entity list is a single proposition, not two independent clauses. Reviewer should check count and both names.

- Date check: NASA footer gives Page Last Updated: Nov 05, 2024. Original publication date remains unknown.

- Source: [Mars Express tracks the phases of Phobos](https://www.esa.int/Science_Exploration/Space_Science/Mars_Express/Mars_Express_tracks_the_phases_of_Phobos) (esa; mission_agency_summary).
- Passage locator: Opening explanation after dated heading
- Publication date: 2019-12-12; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: ESA publication date shown 12/12/2019. Separately hosted NASA and ESA summaries, but scientific-source independence is not established.

### candidate-p1-general-002

Venus is the hottest planet in our solar system.

- Topic: general_factual
- Challenge tags: ordinary_control

- Source: [Venus Facts](https://science.nasa.gov/venus/venus-facts/) (nasa; institutional_summary).
- Passage locator: Surface section, opening sentence
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Scope is planets and surface temperature; not the Sun, and not every atmospheric altitude. Original requested URL redirected to this canonical URL.

- Date check: NASA footer gives Page Last Updated: Oct 15, 2026. Original publication date remains unknown.

### candidate-p1-general-003

CERN placed the World Wide Web software in the public domain on 30 April 1993.

- Topic: general_factual
- Challenge tags: event_vs_publication_date

- Source: [Where the web was born](https://home.cern/science/computing/the-birth-of-the-web/where-web-was-born/) (cern; institutional_historical_summary).
- Passage locator: Where the web was born, public-domain paragraph
- Publication date: unknown; event date: 1993-04-30; access date: 2026-11-01.
- Review: Do not confuse the software release event with the 1989 invention or later open-licence releases. An earlier CERN URL returned 404; the canonical page was opened successfully.

- Date check: Opened source page and checked visible title, publisher, excerpt and date information. No authoritative original publication day located; date remains unknown.

### candidate-p1-general-004

The International System of Units is defined using seven defining constants.

- Topic: general_factual
- Challenge tags: numerical

- Source: [The International System of Units (SI): Defining constants](https://www.bipm.org/en/measurement-units/si-defining-constants) (bipm; official_metrology_summary).
- Passage locator: SI - Defining constants, opening sentence
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: The official metrology page is a current explanatory entry point. No publication date was visible; linked historical resolutions were not treated as this page publication date.

- Date check: Opened source page and checked visible title, publisher, excerpt and date information. No authoritative original publication day located; date remains unknown.

- Source: [Resolution 1 of the 26th CGPM (2018)](https://www.bipm.org/en/committees/cg/cgpm/26-2018/resolution-1) (bipm; primary_resolution).
- Passage locator: Considering, reference to Resolution 1 of the 24th meeting (2011)
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Historical clause within the 2018 resolution; the decision later specifies effect from 20 May 2019. This excerpt is context, not independent present-tense confirmation. Publication day not stated; do not substitute effective date.

### candidate-p1-general-005

ESA lists Gaia Data Release 4 as expected in December 2026.

- Topic: general_factual
- Challenge tags: future_intent_vs_event, event_vs_publication_date

- Source: [Gaia](https://www.esa.int/Science_Exploration/Space_Science/Gaia) (esa; official_documentation).
- Passage locator: The mission, Upcoming data releases
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: A scheduled release is not a completed release. December 2026 is month precision; event_date remains null rather than inventing a day. Recheck the schedule before annotation.

- Date check: Opened source page and checked visible title, publisher, excerpt and date information. No authoritative original publication day located; date remains unknown.

## Candidate QC

Errors: 0; warnings: 23; informational: 3.

Duplicate flags: 0; provenance overlap flags: 0.

Missing metadata: {"publication_date": 18}

Publisher document counts: {"noaa": 1, "us-eia": 1, "us-nih": 1, "unep": 1, "aaas-science": 1, "unep-ozone-secretariat": 1, "un-treaty-collection": 1, "nasa": 3, "ietf-rfc-editor": 2, "nist": 3, "python-software-foundation": 2, "esa": 2, "cern": 1, "bipm": 2}

Repeated publishers show concentration; they do not establish shared reporting chains or source independence.

Unique source URLs: 22; shared source references across claims: 0; shared provenance groups: 7.

Challenge distribution: {"compound_claim": 2, "conflicting_evidence": 0, "direct_negation": 2, "double_negation": 0, "event_vs_publication_date": 4, "future_intent_vs_event": 1, "insufficient_evidence": 0, "numerical": 8, "ordinary_control": 3, "partial_negation": 0, "quantifier_scope": 0}

- Provenance group source-p1-env-002: candidate-p1-env-002-e01, candidate-p1-env-002-e02. Relationships: related_suspected, unknown. Keep linked material together in future splits; independence is not inferred.
- Provenance group source-p1-env-003: candidate-p1-env-003-e01, candidate-p1-env-003-e02. Relationships: related_suspected, unknown. Keep linked material together in future splits; independence is not inferred.
- Provenance group source-p1-env-004: candidate-p1-env-004-e01, candidate-p1-env-004-e02. Relationships: same_origin, unknown. Keep linked material together in future splits; independence is not inferred.
- Provenance group source-p1-tech-003: candidate-p1-tech-003-e01, candidate-p1-tech-003-e02. Relationships: related_suspected, unknown. Keep linked material together in future splits; independence is not inferred.
- Provenance group source-p1-tech-005: candidate-p1-tech-005-e01, candidate-p1-tech-005-e02. Relationships: related_suspected, unknown. Keep linked material together in future splits; independence is not inferred.
- Provenance group source-p1-general-001: candidate-p1-general-001-e01, candidate-p1-general-001-e02. Relationships: related_suspected, unknown. Keep linked material together in future splits; independence is not inferred.
- Provenance group source-p1-general-004: candidate-p1-general-004-e01, candidate-p1-general-004-e02. Relationships: related_suspected, unknown. Keep linked material together in future splits; independence is not inferred.
- warning: claim candidate-p1-env-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-002 evidence[1] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-003 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-004 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-004 evidence[1] is missing optional metadata: publication_date.
- warning: claim candidate-p1-env-005 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-004 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-005 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-tech-005 evidence[1] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-003 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-004 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p1-general-004 evidence[1] is missing optional metadata: publication_date.
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
- Evidence coverage varies by claim; additional documents include partial or historically scoped evidence, and source independence remains unverified.
- No NLI predictions, annotator submissions or adjudications were generated.
- Institutional summaries are not necessarily the original research underlying the statement.
- No target verdict distribution; no claim of balanced stance classes.
- Schema, hashes and QC were checked offline; this command does not refetch pages or establish truth or human approval.
- Retrieval attempt: https://www.cisa.gov/secure-our-world/turn-mfa — 403 Forbidden; not used as evidence
- Retrieval attempt: https://home.cern/science/computing/birth-web — 404; canonical CERN page subsequently opened
- Retrieval attempt: https://www.rfc-editor.org/rfc/rfc9110 — Timeout; .html form subsequently opened
- Retrieval attempt: https://www.un.org/sites/un2.un.org/files/fasct_fact_-_ocean_oct_2022.pdf — 403 Forbidden; not used as evidence
