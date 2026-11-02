# Candidate collection review

Collection: truthlens-phase2-15-v1

All candidates await independent human review. No gold labels or model predictions were created.

Collected: 2026-11-01. Claims: 15. Evidence passages: 16.

## Topic distribution

- cybersecurity_technology: 5
- general_factual: 5
- sustainability_environment: 5

## Candidate claims and source provenance

### candidate-p2-env-001

Not all plastics labelled biodegradable will fully biodegrade under marine conditions.

- Topic: sustainability_environment
- Challenge tags: quantifier_scope, partial_negation

- Source: [Biodegradable Plastics Are Not the Answer to Reducing Marine Litter, Says UN](https://www.unep.org/en/news-and-stories/press-release/biodegradable-plastics-are-not-answer-reducing-marine-litter-says-un) (unep; institutional_report_summary).
- Passage locator: Second paragraph, report findings
- Publication date: 2015-11-17; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Faithful collector paraphrase of the report summary; not a verbatim organically occurring claim. Conditions, polymer type and time horizon require review.

### candidate-p2-env-002

A single year above 1.5°C does not by itself establish failure of the Paris Agreement long-term temperature goal.

- Topic: sustainability_environment
- Challenge tags: partial_negation, quantifier_scope, numerical, event_vs_publication_date

- Source: [WMO confirms 2024 as warmest year on record at about 1.55°C above pre-industrial level](https://wmo.int/news/media-centre/wmo-confirms-2024-warmest-year-record-about-155degc-above-pre-industrial-level) (wmo; institutional_assessment).
- Passage locator: Secretary-General quote beginning It is important to emphasize
- Publication date: 2025-01-10; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Claim preserves the single-year versus long-term qualifier. Event period is 2024, not the January 2025 publication day. Stored fragment needs surrounding quote checked; do not infer that the long-term goal is secure.

### candidate-p2-env-003

The Atlantic Meridional Overturning Circulation will collapse before 2100.

- Topic: sustainability_environment
- Challenge tags: conflicting_evidence, future_intent_vs_event, insufficient_evidence

- Source: [Warning of a forthcoming collapse of the Atlantic meridional overturning circulation](https://www.nature.com/articles/s41467-023-39810-w) (springer-nature; primary_research).
- Passage locator: Abstract, concluding sentence
- Publication date: 2023-07-25; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector-formulated proposition for reviewing differing published projections; not presented as a study quotation or established event. 2023 estimate is scenario-dependent; its interval extends beyond 2100. Compare assumptions and definitions, not just opposite-sounding snippets.

- Source: [Climate change: AMOC likely to withstand future warming](https://www.metoffice.gov.uk/about-us/news-and-media/media-centre/weather-and-climate-news/2025/climate-change-amoc-likely-to-withstand-future-warming) (uk-met-office; study_team_announcement).
- Passage locator: Jonathan Baker quotation, paragraph beginning Although our study shows
- Publication date: 2025-02-26; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Excerpt stops before the consequence clause while retaining likelihood and AMOC context. The next 75 years is relative to the February 2025 publication. Study-team communication concerns its own modelling; 2023 paper uses statistical extrapolation. Newer full Nature page failed retrieval. Compare definitions and scenarios; neither projection is a future observation.

### candidate-p2-env-004

Microplastics in drinking water are harmless at current exposure levels.

- Topic: sustainability_environment
- Challenge tags: insufficient_evidence, quantifier_scope

- Source: [WHO calls for more research into microplastics and a crackdown on plastic pollution](https://www.who.int/news/item/22-08-2019-who-calls-for-more-research-into-microplastics-and-a-crackdown-on-plastic-pollution) (who; institutional_research_summary).
- Passage locator: Maria Neira quotation
- Publication date: 2019-08-22; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector-formulated stronger proposition, not attributed as WHO wording. Source explicitly qualifies the evidence; a 2019 limited assessment cannot settle all current exposure, particle-size and health outcomes. Requires updated research and human review.

### candidate-p2-env-005

Not every plastic item labelled compostable is suitable for a home compost pile.

- Topic: sustainability_environment
- Challenge tags: quantifier_scope, partial_negation

- Source: [Frequently Asked Questions about Plastic Recycling and Composting](https://www.epa.gov/trash-free-waters/frequently-asked-questions-about-plastic-recycling-and-composting) (us-epa; official_guidance).
- Passage locator: If a plastic product is labeled compostable, can I add it to my home compost pile?
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector paraphrase of conditional guidance. Industrial and home composting differ. Visible strategy date is an event on the page, not this page original publication date.

### candidate-p2-tech-001

Every website using HTTPS is legitimate.

- Topic: cybersecurity_technology
- Challenge tags: quantifier_scope

- Source: [Online Shopping](https://consumer.ftc.gov/articles/online-shopping) (us-ftc; official_consumer_guidance).
- Passage locator: Pay by Credit Card When Possible
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Verification proposition based on an actual misconception addressed by the FTC; not attributed as FTC advice. Encryption and seller trustworthiness are different properties.

### candidate-p2-tech-002

Not all multifactor authentication methods are phishing-resistant.

- Topic: cybersecurity_technology
- Challenge tags: quantifier_scope, partial_negation

- Source: [NIST SP 800-63B-4: Authentication and Authenticator Management](https://pages.nist.gov/800-63-4/sp800-63b.html) (nist; primary_standard).
- Passage locator: Section 3.1.5 Multi-Factor OTPs
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector scope paraphrase; this sentence appears in both single-factor and multi-factor OTP sections, and the locator identifies multi-factor context. Same source as Phase 1 password claim: keep linked provenance together in future splits. Catalog publication precision is July 2025.

### candidate-p2-tech-003

It is not the case that no practical SHA-1 collision has ever been demonstrated.

- Topic: cybersecurity_technology
- Challenge tags: double_negation, event_vs_publication_date

- Source: [CWI and Google announce first collision for Industry Security Standard SHA-1](https://www.cwi.nl/en/news/cwi-and-google-announce-first-collision-for-industry-security-standard-sha-1/) (cwi; primary_research_announcement).
- Passage locator: Signature forgeries; opening announcement and Publication date fields
- Publication date: 2017-02-27; event date: 2017-02-23; access date: 2026-11-01.
- Review: Collector-authored double-negation paraphrase of a real documented result, not a naturally occurring quotation. The body announces 23 February while the page labels Publication date 27 February 2017. Do not confuse either with access date.

### candidate-p2-tech-004

On 11 March 2025, NIST selected HQC for standardization and expected a finalized standard in 2027.

- Topic: cybersecurity_technology
- Challenge tags: compound_claim, future_intent_vs_event, event_vs_publication_date

- Source: [NIST Selects HQC as Fifth Algorithm for Post-Quantum Encryption](https://www.nist.gov/news-events/news/2025/03/nist-selects-hqc-fifth-algorithm-post-quantum-encryption) (nist; original_announcement).
- Passage locator: Key messages, third bullet; heading and dated selection context
- Publication date: 2025-03-11; event date: 2025-03-11; access date: 2026-11-01.
- Review: Historical as-of claim: selection is the 2025 event; the 2027 final standard is a forecast, not a confirmed release. The event_date field records selection only. Do not replace forecast with actual delivery without new evidence.

### candidate-p2-tech-005

A CVSS v4.0 base score measures vulnerability severity and does not alone measure organizational risk.

- Topic: cybersecurity_technology
- Challenge tags: partial_negation, compound_claim

- Source: [Common Vulnerability Scoring System version 4.0: User Guide](https://www.first.org/cvss/v4.0/user-guide) (first-org; primary_specification_guidance).
- Passage locator: Heading before guidance on Environmental and Threat metrics
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Scope is the Base score, not all possible CVSS metric combinations. Guide version 1.2 is visible; original publication day is not established.

### candidate-p2-general-001

Not all deserts are hot; Antarctica has a polar desert.

- Topic: general_factual
- Challenge tags: quantifier_scope, partial_negation, compound_claim

- Source: [Areas of Australian and territory deserts](https://www.ga.gov.au/scientific-topics/national-location-information/landforms/deserts) (geoscience-australia; official_geoscience_reference).
- Passage locator: Opening climate-classification paragraphs
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector paraphrase, with a counterexample to a universal statement. Page last updated 25 November 2022; original publication date unknown. Source classification refers to Australian Antarctic Territories; review geographic scope.

### candidate-p2-general-002

It is not true that no woman has ever won a Nobel Prize.

- Topic: general_factual
- Challenge tags: double_negation, quantifier_scope

- Source: [Marie Curie](https://oumnh.ox.ac.uk/learn-marie-curie) (university-of-oxford; institutional_historical_summary).
- Passage locator: Opening Marie Curie biography
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector-authored double-negation paraphrase, not a source quotation. She refers to Marie Curie in the preceding sentence. Official Nobel pages returned 403; this university museum summary is secondary, and primary award records remain follow-up.

### candidate-p2-general-003

There is life beneath Europa’s surface.

- Topic: general_factual
- Challenge tags: insufficient_evidence

- Source: [Europa](https://science.nasa.gov/jupiter/jupiter-moons/europa/) (nasa; mission_agency_summary).
- Passage locator: Europa Clipper Website section
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector-formulated proposition about a real open research question; NASA does not assert this proposition here. Habitability and detected life are different. Mission goals and missing evidence do not establish absence or presence of life.

### candidate-p2-general-004

Venus’s sidereal rotation period is longer than its orbital period.

- Topic: general_factual
- Challenge tags: numerical, compound_claim

- Source: [All About Venus](https://spaceplace.nasa.gov/all-about-venus/en/) (nasa; mission_agency_education).
- Passage locator: Time on Venus, two adjacent bullets
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Collector makes sidereal reference frame explicit; solar-day length is about 117 Earth days in surrounding text. Requires numerical comparison and reference-frame interpretation, not an unqualified claim about every meaning of day.

### candidate-p2-general-005

The Great Wall of China can be seen from the Moon with the naked eye.

- Topic: general_factual
- Challenge tags: ordinary_control

- Source: [Cosmicopia: Ask Us — Earth and Moon](https://science.gsfc.nasa.gov/attic/cosmicopia.gsfc.nasa.gov/qa_earth.html) (nasa-goddard; archived_agency_explanation).
- Passage locator: Question 99, See Great Wall from the Moon?, answer by Beth Barbier
- Publication date: unknown; event date: not recorded / partial precision; access date: 2026-11-01.
- Review: Candidate expresses the public misconception addressed by the archived NASA question. Pronoun it refers to the Great Wall. Archived page contains dates for other answers; do not assign them to this answer.

## Candidate QC

Errors: 0; warnings: 10; informational: 3.

Duplicate flags: 0; provenance overlap flags: 0.

Missing metadata: {"publication_date": 9}

Publisher document counts: {"unep": 1, "wmo": 1, "springer-nature": 1, "uk-met-office": 1, "who": 1, "us-epa": 1, "us-ftc": 1, "nist": 2, "cwi": 1, "first-org": 1, "geoscience-australia": 1, "university-of-oxford": 1, "nasa": 2, "nasa-goddard": 1}

Repeated publishers show concentration; they do not establish shared reporting chains or source independence.

Unique source URLs: 16; shared source references across claims: 0; shared provenance groups: 0.

Challenge distribution: {"compound_claim": 4, "conflicting_evidence": 1, "direct_negation": 0, "double_negation": 2, "event_vs_publication_date": 3, "future_intent_vs_event": 2, "insufficient_evidence": 3, "numerical": 2, "ordinary_control": 1, "partial_negation": 6, "quantifier_scope": 8}

- warning: claim candidate-p2-env-005 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-tech-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-tech-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-tech-005 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-general-001 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-general-002 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-general-003 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-general-004 evidence[0] is missing optional metadata: publication_date.
- warning: claim candidate-p2-general-005 evidence[0] is missing optional metadata: publication_date.
- informational: Metadata completeness summary for publication_date.
- informational: Publication dates and event dates are checked as separate fields; an event date is never inferred from a publication date.
- warning: No current claim is tagged with planned challenge category direct_negation.
- informational: For future development/diagnostic/final-test splits, keep claim-family, event, and documented provenance groups together; do not create a split in this audit.

## Research limitations and collection follow-up

- Purposive collector-authored candidates and scope/double-negation paraphrases from real sources; not a blind or representative sample of naturally occurring claims.
- Challenge tags describe review tasks, not gold evidence relevance, stance or final verdict labels.
- Some propositions are deliberately stronger than the source or address an open scientific question; they are not attributed as publisher assertions.
- Most claims still have one short excerpt; provenance and sufficient context require human review.
- Publication dates remain null when only updated, month-only or unrelated dates are available.
- Schema, hashes and QC were checked offline; this command does not refetch pages or establish truth or human approval.
- Retrieval attempt: https://www.nature.com/articles/s41586-024-08544-0 — Full-page open failed with publisher cookie redirect; accessible study-team communication used instead.
- Retrieval attempt: https://www.nobelprize.org/prizes/physics/1903/marie-curie/facts/ — 403; Oxford museum secondary source used, primary award record still needed.
- Retrieval attempt: https://blog.chromium.org/2023/05/an-update-on-lock-icon.html — Google challenge redirect; FTC guidance used instead.
- Retrieval attempt: https://security.googleblog.com/2017/02/announcing-first-sha1-collision.html — Google challenge redirect; primary CWI announcement used instead.
- Retrieval attempt: https://www.bas.ac.uk/about/antarctica/geography/ — Robot verification page; Geoscience Australia source used instead.
- Retrieval attempt: https://www.cosmos.esa.int/web/gaia/release — 451; no additional Gaia excerpt admitted.
