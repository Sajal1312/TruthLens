# Automated preliminary candidate source review

AI-generated assistance, not independent human review, approval, or gold labels.
Recommendations concern inclusion quality, not claim truth. A disputed or false claim can be a valid annotation candidate.

## Actual inspection totals

```json
{
  "record_type": "automated_preliminary_summary",
  "candidate_count": 30,
  "evidence_count": 38,
  "distinct_source_urls": 37,
  "distinct_sources_opened": 36,
  "inaccessible_source_urls": [
    "https://www.bipm.org/en/measurement-units/si-defining-constants"
  ],
  "passages_located": 37,
  "excerpt_status_counts": {
    "format_normalized": 4,
    "exact_fragment": 29,
    "structured_extract": 4,
    "incomplete": 1
  },
  "candidates_with_inaccessible_sources": [
    "candidate-p1-general-004"
  ],
  "missing_candidate_publication_dates": 27,
  "publication_status_counts": {
    "publication_day_not_established": 26,
    "matched_existing_date": 11,
    "incomplete": 1
  },
  "recommendation_counts": {
    "suitable for human approval": 21,
    "needs revision": 7,
    "insufficient evidence": 2
  },
  "human_approval_status": "Not established by this report; all recommendations require a real reviewer."
}
```

Opened means readable content returned through the web tool. It does not mean measured HTTP 200, an uncached origin response, full DOM inspection, or authenticated archival capture.
Located means the saved excerpt was found as a fragment, with documented formatting normalization or table/bullet assembly. It does not establish truth, sufficient context, or source independence.
No new evidence, dates, or candidate text were imported. See [inspection notes](../README.md) for methods and remaining human steps.

## All candidates

| Candidate | Claim | Passage checks | Priority | Preliminary recommendation | Reason |
|---|---|---|---|---|---|
| candidate-p1-env-001 | The ocean absorbs about 30 percent of carbon dioxide released into the atmosphere, according to NOAA. | [candidate-p1-env-001-e01](https://oceanservice.noaa.gov/facts/acidification.html): format_normalized | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-env-002 | Making new aluminum cans from recycled cans uses 95 percent less energy than making them from bauxite ore. | [candidate-p1-env-002-e01](https://www.eia.gov/energyexplained/energy-and-the-environment/recycling-and-energy.php): exact_fragment; [candidate-p1-env-002-e02](https://nems.nih.gov/environmental-programs/Pages/Benefits-of-Recycling.aspx): exact_fragment | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-env-003 | UNEP estimates that 19–23 million tonnes of plastic waste enter aquatic ecosystems each year. | [candidate-p1-env-003-e01](https://www.unep.org/en/what-we-do/ocean-seas-and-coasts/ecosystem-degradation-pollution/plastic-pollution-marine-litter): exact_fragment; [candidate-p1-env-003-e02](https://pubmed.ncbi.nlm.nih.gov/32943526/): exact_fragment | high | needs revision | Explain the reference-year relationship in the fixed evidence context before inclusion; do not silently rewrite the claim. |
| candidate-p1-env-004 | The Montreal Protocol was signed in 1987 and entered into force in 1989. | [candidate-p1-env-004-e01](https://ozone.unep.org/treaties/montreal-protocol): exact_fragment; [candidate-p1-env-004-e02](https://treaties.un.org/Pages/showDetails.aspx?objid=080000028003f7f7): structured_extract | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-env-005 | Current global warming cannot be explained by changes in energy from the Sun. | [candidate-p1-env-005-e01](https://science.nasa.gov/climate-change/causes/): exact_fragment | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-tech-001 | RFC 8446 specifies version 1.3 of the Transport Layer Security protocol. | [candidate-p1-tech-001-e01](https://www.rfc-editor.org/rfc/rfc8446): format_normalized | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-tech-002 | RFC 9110 defines HTTP as a stateless application-level protocol. | [candidate-p1-tech-002-e01](https://www.rfc-editor.org/rfc/rfc9110.html): exact_fragment | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-tech-003 | NIST announced its first three finalized post-quantum encryption standards on 13 August 2024. | [candidate-p1-tech-003-e01](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards): structured_extract; [candidate-p1-tech-003-e02](https://csrc.nist.gov/pubs/fips/203/final): structured_extract | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-tech-004 | NIST SP 800-63B-4 says verifiers and CSPs must not require periodic password changes. | [candidate-p1-tech-004-e01](https://pages.nist.gov/800-63-4/sp800-63b.html): exact_fragment | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-tech-005 | Python 3.13 provides a build configuration that can disable the global interpreter lock. | [candidate-p1-tech-005-e01](https://docs.python.org/3.13/glossary.html#term-global-interpreter-lock): format_normalized; [candidate-p1-tech-005-e02](https://peps.python.org/pep-0703/): format_normalized | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-general-001 | Mars has two moons named Phobos and Deimos. | [candidate-p1-general-001-e01](https://science.nasa.gov/mars/moons/): exact_fragment; [candidate-p1-general-001-e02](https://www.esa.int/Science_Exploration/Space_Science/Mars_Express/Mars_Express_tracks_the_phases_of_Phobos): exact_fragment | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-general-002 | Venus is the hottest planet in our solar system. | [candidate-p1-general-002-e01](https://science.nasa.gov/venus/venus-facts/): exact_fragment | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-general-003 | CERN placed the World Wide Web software in the public domain on 30 April 1993. | [candidate-p1-general-003-e01](https://home.cern/science/computing/the-birth-of-the-web/where-web-was-born/): exact_fragment | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p1-general-004 | The International System of Units is defined using seven defining constants. | [candidate-p1-general-004-e01](https://www.bipm.org/en/measurement-units/si-defining-constants): incomplete; [candidate-p1-general-004-e02](https://www.bipm.org/en/committees/cg/cgpm/26-2018/resolution-1): exact_fragment | high | needs revision | Retry the definition page and review the operative resolution, not only the considering clause. |
| candidate-p1-general-005 | ESA lists Gaia Data Release 4 as expected in December 2026. | [candidate-p1-general-005-e01](https://www.esa.int/Science_Exploration/Space_Science/Gaia): exact_fragment | high | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-env-001 | Not all plastics labelled biodegradable will fully biodegrade under marine conditions. | [candidate-p2-env-001-e01](https://www.unep.org/en/news-and-stories/press-release/biodegradable-plastics-are-not-answer-reducing-marine-litter-says-un): exact_fragment | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-env-002 | A single year above 1.5°C does not by itself establish failure of the Paris Agreement long-term temperature goal. | [candidate-p2-env-002-e01](https://wmo.int/news/media-centre/wmo-confirms-2024-warmest-year-record-about-155degc-above-pre-industrial-level): exact_fragment | medium | needs revision | For a standalone annotation bundle, preserve the preceding single-year qualification or an approved context note. |
| candidate-p2-env-003 | The Atlantic Meridional Overturning Circulation will collapse before 2100. | [candidate-p2-env-003-e01](https://www.nature.com/articles/s41467-023-39810-w): exact_fragment; [candidate-p2-env-003-e02](https://www.metoffice.gov.uk/about-us/news-and-media/media-centre/weather-and-climate-news/2025/climate-change-amoc-likely-to-withstand-future-warming): exact_fragment | high | needs revision | Define the intended prediction/as-of scope and compare assumptions before presenting this as a genuine evidence-conflict case. |
| candidate-p2-env-004 | Microplastics in drinking water are harmless at current exposure levels. | [candidate-p2-env-004-e01](https://www.who.int/news/item/22-08-2019-who-calls-for-more-research-into-microplastics-and-a-crackdown-on-plastic-pollution): exact_fragment | high | insufficient evidence | A short historical risk statement cannot establish present-day harmlessness. Missing initial qualification needs reviewer attention. |
| candidate-p2-env-005 | Not every plastic item labelled compostable is suitable for a home compost pile. | [candidate-p2-env-005-e01](https://www.epa.gov/trash-free-waters/frequently-asked-questions-about-plastic-recycling-and-composting): exact_fragment | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-tech-001 | Every website using HTTPS is legitimate. | [candidate-p2-tech-001-e01](https://consumer.ftc.gov/articles/online-shopping): exact_fragment | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-tech-002 | Not all multifactor authentication methods are phishing-resistant. | [candidate-p2-tech-002-e01](https://pages.nist.gov/800-63-4/sp800-63b.html): exact_fragment | medium | needs revision | Preserve section 3.1.5 and its second-factor definition in approved context so an annotator need not guess which occurrence was collected. |
| candidate-p2-tech-003 | It is not the case that no practical SHA-1 collision has ever been demonstrated. | [candidate-p2-tech-003-e01](https://www.cwi.nl/en/news/cwi-and-google-announce-first-collision-for-industry-security-standard-sha-1/): exact_fragment | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-tech-004 | On 11 March 2025, NIST selected HQC for standardization and expected a finalized standard in 2027. | [candidate-p2-tech-004-e01](https://www.nist.gov/news-events/news/2025/03/nist-selects-hqc-fifth-algorithm-post-quantum-encryption): exact_fragment | high | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-tech-005 | A CVSS v4.0 base score measures vulnerability severity and does not alone measure organizational risk. | [candidate-p2-tech-005-e01](https://www.first.org/cvss/v4.0/user-guide): exact_fragment | routine | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-general-001 | Not all deserts are hot; Antarctica has a polar desert. | [candidate-p2-general-001-e01](https://www.ga.gov.au/scientific-topics/national-location-information/landforms/deserts): exact_fragment | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-general-002 | It is not true that no woman has ever won a Nobel Prize. | [candidate-p2-general-002-e01](https://oumnh.ox.ac.uk/learn-marie-curie): exact_fragment | medium | needs revision | Preserve the antecedent context or request a versioned excerpt revision; identify collector-authored linguistic transformation. |
| candidate-p2-general-003 | There is life beneath Europa’s surface. | [candidate-p2-general-003-e01](https://science.nasa.gov/jupiter/jupiter-moons/europa/): exact_fragment | high | insufficient evidence | Do not turn an unestablished event into a false claim. A deliberately insufficient bundle may still be included after explicit human review. |
| candidate-p2-general-004 | Venus’s sidereal rotation period is longer than its orbital period. | [candidate-p2-general-004-e01](https://spaceplace.nasa.gov/all-about-venus/en/): structured_extract | medium | suitable for human approval | Excerpt fidelity and claim scope are traceable; a real reviewer must accept the stated date, context and provenance limitations before inclusion. |
| candidate-p2-general-005 | The Great Wall of China can be seen from the Moon with the naked eye. | [candidate-p2-general-005-e01](https://science.gsfc.nasa.gov/attic/cosmicopia.gsfc.nasa.gov/qa_earth.html): exact_fragment | medium | needs revision | Preserve question 99 context or request an excerpt revision. Archived status and missing answer date require acknowledgment, not an invented date. |

## Per-candidate context, dates and provenance

### candidate-p1-env-001

- Claim/evidence interpretation: The NOAA summary states the same approximate fraction and atmosphere-to-ocean scope.
- Clarity: Clear attributed approximate fraction; not a constant annual carbon-budget measurement.
- Dates: candidate-p1-env-001-e01: Last updated 2026-09-23; original publication day not established.
- Provenance: Single NOAA summary; no independent corroboration is claimed.
- Research concerns: Retain approximation and attribution; underlying carbon-budget measurements were not independently audited.

- [candidate-p1-env-001-e01](https://oceanservice.noaa.gov/facts/acidification.html): **opened / format_normalized**
  - Observed title/publisher: What is Ocean Acidification? / NOAA National Ocean Service
  - Source role: institutional explanatory summary
  - Locator/method: Opening ocean-carbon paragraph
  - Date status: publication_day_not_established; original day: unknown; Last updated 2026-09-23; original publication day not established.
  - Context: The NOAA summary states the same approximate fraction and atmosphere-to-ocean scope.

### candidate-p1-env-002

- Claim/evidence interpretation: EIA matches the can-specific claim. NIH gives a broader aluminum comparison, not a separate measurement.
- Clarity: Comparison specifies cans, recycled feedstock and bauxite route.
- Dates: candidate-p1-env-002-e01: No original publication day visible in the retrieved text. candidate-p1-env-002-e02: No original publication day established; older statistics and a funding-lapse currency warning are visible.
- Provenance: EIA and NIH are different agencies; a shared underlying calculation is unresolved. Do not count them as two independent measurements.
- Research concerns: Underlying 95% calculation and lifecycle boundaries were not checked; NIH carries a currency warning.

- [candidate-p1-env-002-e01](https://www.eia.gov/energyexplained/energy-and-the-environment/recycling-and-energy.php): **opened / exact_fragment**
  - Observed title/publisher: Recycling and energy / U.S. Energy Information Administration
  - Source role: institutional explanatory summary
  - Locator/method: Recycling saves energy and other resources, aluminum-can comparison
  - Date status: publication_day_not_established; original day: unknown; No original publication day visible in the retrieved text.
  - Context: EIA matches the can-specific claim. NIH gives a broader aluminum comparison, not a separate measurement.
- [candidate-p1-env-002-e02](https://nems.nih.gov/environmental-programs/Pages/Benefits-of-Recycling.aspx): **opened / exact_fragment**
  - Observed title/publisher: Benefits of Recycling / NIH National Environmental Management System
  - Source role: institutional recycling guidance
  - Locator/method: Energy savings bullet under Benefits of Recycling
  - Date status: publication_day_not_established; original day: unknown; No original publication day established; older statistics and a funding-lapse currency warning are visible.
  - Context: Broader aluminum comparison, not can-specific raw-material process data; visible currency warning and old statistics. Calculation lineage not established.

### candidate-p1-env-003

- Claim/evidence interpretation: UNEP states an annual estimate; the research abstract estimates plastic generated in 2016. Numeric agreement does not erase this scope difference.
- Clarity: Attribution is clear but annual framing can conceal the reference year.
- Dates: candidate-p1-env-003-e01: No original publication day established. candidate-p1-env-003-e02: Epub 2020-09-17; journal issue 2020-09-18. Estimate concerns 2016, not the access year.
- Provenance: UNEP and the study may share an estimate; a direct citation chain was not established.
- Research concerns: Explain the reference-year relationship in the fixed evidence context before inclusion; do not silently rewrite the claim.

- [candidate-p1-env-003-e01](https://www.unep.org/en/what-we-do/ocean-seas-and-coasts/ecosystem-degradation-pollution/plastic-pollution-marine-litter): **opened / exact_fragment**
  - Observed title/publisher: Plastic pollution & marine litter / UN Environment Programme
  - Source role: institutional environmental summary
  - Locator/method: Facts, first annual-leakage bullet
  - Date status: publication_day_not_established; original day: unknown; No original publication day established.
  - Context: UNEP states an annual estimate; the research abstract estimates plastic generated in 2016. Numeric agreement does not erase this scope difference.
- [candidate-p1-env-003-e02](https://pubmed.ncbi.nlm.nih.gov/32943526/): **opened / exact_fragment**
  - Observed title/publisher: Predicted growth in plastic waste exceeds efforts to mitigate plastic pollution / Science / AAAS; abstract indexed by U.S. National Library of Medicine PubMed
  - Source role: primary research abstract, not full study review
  - Locator/method: PMID 32943526, abstract and bibliographic header
  - Date status: matched_existing_date; original day: 2020-09-17; Epub 2020-09-17; journal issue 2020-09-18. Estimate concerns 2016, not the access year.
  - Context: UNEP states an annual estimate; the research abstract estimates plastic generated in 2016. Numeric agreement does not erase this scope difference.

### candidate-p1-env-004

- Claim/evidence interpretation: The overview states both years; the registry supplies conclusion and entry-into-force dates.
- Clarity: Two independently checkable treaty-event components are explicit.
- Dates: candidate-p1-env-004-e01: 1987 and 1989 are event years; no page publication day established. candidate-p1-env-004-e02: Conclusion 1987-09-16; entry into force 1989-01-01. These are not publication dates.
- Provenance: Both records concern the same original treaty; not independent event observations.
- Research concerns: Table-cell excerpt is an assembled extract, not a continuous sentence. Review both event components.

- [candidate-p1-env-004-e01](https://ozone.unep.org/treaties/montreal-protocol): **opened / exact_fragment**
  - Observed title/publisher: The Montreal Protocol on Substances that Deplete the Ozone Layer / UNEP Ozone Secretariat
  - Source role: official treaty overview
  - Locator/method: Opening treaty overview
  - Date status: publication_day_not_established; original day: unknown; 1987 and 1989 are event years; no page publication day established.
  - Context: The overview states both years; the registry supplies conclusion and entry-into-force dates.
- [candidate-p1-env-004-e02](https://treaties.un.org/Pages/showDetails.aspx?objid=080000028003f7f7): **opened / structured_extract**
  - Observed title/publisher: Montreal Protocol on Substances that Deplete the Ozone Layer / United Nations Treaty Collection
  - Source role: primary treaty registry
  - Locator/method: Registration 26369; conclusion and EIF table cells
  - Date status: publication_day_not_established; original day: unknown; Conclusion 1987-09-16; entry into force 1989-01-01. These are not publication dates.
  - Context: The overview states both years; the registry supplies conclusion and entry-into-force dates.

### candidate-p1-env-005

- Claim/evidence interpretation: NASA states the same conclusion and supplies surrounding reasons; solar effects on past climates are acknowledged.
- Clarity: Current warming is narrower than all historical climate changes.
- Dates: candidate-p1-env-005-e01: Original publication day not established; last-updated date is separate metadata.
- Provenance: NASA summary links research, but no independence among those studies was audited.
- Research concerns: Single synthesis and a list-introduction excerpt; underlying cited studies were not separately reviewed.

- [candidate-p1-env-005-e01](https://science.nasa.gov/climate-change/causes/): **opened / exact_fragment**
  - Observed title/publisher: Causes / NASA Science
  - Source role: institutional climate synthesis with study references
  - Locator/method: Evidence Shows That Current Global Warming Cannot Be Explained by Solar Irradiance
  - Date status: publication_day_not_established; original day: unknown; Original publication day not established; last-updated date is separate metadata.
  - Context: NASA states the same conclusion and supplies surrounding reasons; solar effects on past climates are acknowledged.

### candidate-p1-tech-001

- Claim/evidence interpretation: Abstract specifies TLS 1.3. The landing page now marks RFC 8446 obsoleted by RFC 9846.
- Clarity: Claim explicitly names RFC 8446, not the latest TLS standard.
- Dates: candidate-p1-tech-001-e01: Published August 2018 only. Current landing page lists RFC 9846 as obsoleting RFC 8446.
- Provenance: Single normative document, not multiple corroborating sources.
- Research concerns: Retain the document-version scope; do not describe RFC 8446 as the current standard.

- [candidate-p1-tech-001-e01](https://www.rfc-editor.org/rfc/rfc8446): **opened / format_normalized**
  - Observed title/publisher: RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3 / IETF / RFC Editor
  - Source role: normative protocol document
  - Locator/method: Abstract, first sentence; About this RFC, Obsoleted by
  - Date status: publication_day_not_established; original day: unknown; Published August 2018 only. Current landing page lists RFC 9846 as obsoleting RFC 8446.
  - Context: Abstract specifies TLS 1.3. The landing page now marks RFC 8446 obsoleted by RFC 9846.

### candidate-p1-tech-002

- Claim/evidence interpretation: The abstract contains the stateless application-level definition; application sessions are not denied.
- Clarity: Document-specific protocol definition is clear.
- Dates: candidate-p1-tech-002-e01: Header gives June 2022 only; no publication day imputed.
- Provenance: Single normative document.
- Research concerns: Avoid interpreting stateless protocol semantics as absence of all application state.

- [candidate-p1-tech-002-e01](https://www.rfc-editor.org/rfc/rfc9110.html): **opened / exact_fragment**
  - Observed title/publisher: RFC 9110: HTTP Semantics / IETF / RFC Editor
  - Source role: normative protocol document
  - Locator/method: Abstract, first sentence
  - Date status: publication_day_not_established; original day: unknown; Header gives June 2022 only; no publication day imputed.
  - Context: The abstract contains the stateless application-level definition; application sessions are not denied.

### candidate-p1-tech-003

- Claim/evidence interpretation: The announcement heading/date match. FIPS 203 supplies only one standard/date, not all three.
- Clarity: Announcement date and three-standard count are explicit.
- Dates: candidate-p1-tech-003-e01: Released 2024-08-13; updated 2025-08-29. Announcement event is 2024-08-13. candidate-p1-tech-003-e02: Date Published 2024-08-13; later planning notes are not the publication date.
- Provenance: Both passages are from NIST and the same release program, not independent corroboration.
- Research concerns: Heading/date assembly and partial second-passage coverage need acknowledgment; the three standards have different cryptographic roles.

- [candidate-p1-tech-003-e01](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards): **opened / structured_extract**
  - Observed title/publisher: NIST Releases First 3 Finalized Post-Quantum Encryption Standards / NIST
  - Source role: original institutional announcement
  - Locator/method: Article heading and date; Released/Updated footer
  - Date status: matched_existing_date; original day: 2024-08-13; Released 2024-08-13; updated 2025-08-29. Announcement event is 2024-08-13.
  - Context: The announcement heading/date match. FIPS 203 supplies only one standard/date, not all three.
- [candidate-p1-tech-003-e02](https://csrc.nist.gov/pubs/fips/203/final): **opened / structured_extract**
  - Observed title/publisher: FIPS 203, Module-Lattice-Based Key-Encapsulation Mechanism Standard / NIST CSRC
  - Source role: primary standard catalog
  - Locator/method: FIPS 203 heading and Date Published
  - Date status: matched_existing_date; original day: 2024-08-13; Date Published 2024-08-13; later planning notes are not the publication date.
  - Context: The announcement heading/date match. FIPS 203 supplies only one standard/date, not all three.

### candidate-p1-tech-004

- Claim/evidence interpretation: The requirement matches; the immediately following sentence mandates changes on compromise evidence.
- Clarity: Periodic changes are distinct from compromise-triggered changes.
- Dates: candidate-p1-tech-004-e01: HTML build timestamp 2025-08-26 is not established as the original publication day.
- Provenance: Same document is reused by p2-tech-002; group these for leakage review.
- Research concerns: Retain the adjacent exception in reviewer context; a ban on all password changes would misrepresent the source.

- [candidate-p1-tech-004-e01](https://pages.nist.gov/800-63-4/sp800-63b.html): **opened / exact_fragment**
  - Observed title/publisher: NIST Special Publication 800-63B / NIST
  - Source role: normative authentication guidance
  - Locator/method: Password requirements item 6; Multi-Factor OTP section 3.1.5
  - Date status: publication_day_not_established; original day: unknown; HTML build timestamp 2025-08-26 is not established as the original publication day.
  - Context: The requirement matches; the immediately following sentence mandates changes on compromise evidence.

### candidate-p1-tech-005

- Claim/evidence interpretation: The versioned glossary describes the option. PEP 703 is the accepted design, not independent evidence of deployment.
- Clarity: Version 3.13 and optional build configuration are explicit.
- Dates: candidate-p1-tech-005-e01: Version 3.13 documentation; no original publication day for this entry established. candidate-p1-tech-005-e02: Created 2023-01-09; Python-Version 3.13; Status Final. Creation is not assumed to be publication.
- Provenance: The glossary directly cites PEP 703: linked implementation/design lineage, not independent reports.
- Research concerns: Keep build/runtime conditions; do not imply every default Python build has the GIL disabled.

- [candidate-p1-tech-005-e01](https://docs.python.org/3.13/glossary.html#term-global-interpreter-lock): **opened / format_normalized**
  - Observed title/publisher: Glossary — Python 3.13.18 documentation / Python Software Foundation / Python documentation project
  - Source role: versioned official implementation documentation
  - Locator/method: global interpreter lock glossary entry
  - Date status: publication_day_not_established; original day: unknown; Version 3.13 documentation; no original publication day for this entry established.
  - Context: The versioned glossary describes the option. PEP 703 is the accepted design, not independent evidence of deployment.
- [candidate-p1-tech-005-e02](https://peps.python.org/pep-0703/): **opened / format_normalized**
  - Observed title/publisher: PEP 703 – Making the Global Interpreter Lock Optional in CPython / Python PEP project; author Sam Gross
  - Source role: accepted design proposal
  - Locator/method: Abstract; Created, Status and Python-Version fields
  - Date status: publication_day_not_established; original day: unknown; Created 2023-01-09; Python-Version 3.13; Status Final. Creation is not assumed to be publication.
  - Context: The versioned glossary describes the option. PEP 703 is the accepted design, not independent evidence of deployment.

### candidate-p1-general-001

- Claim/evidence interpretation: NASA and ESA both name Phobos and Deimos in the retrieved context.
- Clarity: Both named moons are specified.
- Dates: candidate-p1-general-001-e01: No original publication day established; footer last-updated field is not publication. candidate-p1-general-001-e02: Article 2019-12-12; described image sequence 2019-11-17. Neither is a date when Mars acquired its moons.
- Provenance: NASA and ESA mission summaries; no shared-copy text beyond the basic fact observed, but independence not established.
- Research concerns: Different institutional publishers do not prove independent underlying observations.

- [candidate-p1-general-001-e01](https://science.nasa.gov/mars/moons/): **opened / exact_fragment**
  - Observed title/publisher: Mars Moons / NASA Science
  - Source role: institutional planetary summary
  - Locator/method: Opening moon overview
  - Date status: publication_day_not_established; original day: unknown; No original publication day established; footer last-updated field is not publication.
  - Context: NASA and ESA both name Phobos and Deimos in the retrieved context.
- [candidate-p1-general-001-e02](https://www.esa.int/Science_Exploration/Space_Science/Mars_Express/Mars_Express_tracks_the_phases_of_Phobos): **opened / exact_fragment**
  - Observed title/publisher: Mars Express tracks the phases of Phobos / European Space Agency
  - Source role: original mission communication
  - Locator/method: Opening explanation of two moons; displayed article date
  - Date status: matched_existing_date; original day: 2019-12-12; Article 2019-12-12; described image sequence 2019-11-17. Neither is a date when Mars acquired its moons.
  - Context: NASA and ESA both name Phobos and Deimos in the retrieved context.

### candidate-p1-general-002

- Claim/evidence interpretation: NASA explicitly makes the comparison and discusses surface conditions.
- Clarity: Planetary comparison is clear with surface-temperature context.
- Dates: candidate-p1-general-002-e01: No original publication day established; footer last-updated field is separate.
- Provenance: Single NASA summary.
- Research concerns: Do not confuse hottest surface with closest planet to the Sun.

- [candidate-p1-general-002-e01](https://science.nasa.gov/venus/venus-facts/): **opened / exact_fragment**
  - Observed title/publisher: Venus: Facts / NASA Science
  - Source role: institutional planetary summary
  - Locator/method: Surface section and opening overview
  - Date status: publication_day_not_established; original day: unknown; No original publication day established; footer last-updated field is separate.
  - Context: NASA explicitly makes the comparison and discusses surface conditions.

### candidate-p1-general-003

- Claim/evidence interpretation: CERN supplies the event date; later open licensing is described separately.
- Clarity: Software public-domain event is separate from inventing the Web.
- Dates: candidate-p1-general-003-e01: Event 1993-04-30; original page publication day not established.
- Provenance: Institutional participant historical account; no independent archival record checked.
- Research concerns: Keep the named software-release event and avoid mixing it with the 1989 invention date.

- [candidate-p1-general-003-e01](https://home.cern/science/computing/the-birth-of-the-web/where-web-was-born/): **opened / exact_fragment**
  - Observed title/publisher: Where the web was born / CERN
  - Source role: institutional historical account
  - Locator/method: Public-domain release paragraph
  - Date status: publication_day_not_established; original day: unknown; Event 1993-04-30; original page publication day not established.
  - Context: CERN supplies the event date; later open licensing is described separately.

### candidate-p1-general-004

- Claim/evidence interpretation: The main definition URL timed out twice. The accessible resolution fragment describes a 2011 proposal; its later decision takes effect in 2019.
- Clarity: Current SI formulation is clear but the evidence bundle has incomplete verification and historical context.
- Dates: candidate-p1-general-004-e01: Original publication day and current page contents could not be rechecked. candidate-p1-general-004-e02: Resolution year 2018 and effective date 2019-05-20 are distinct; exact page publication day not established.
- Provenance: Both sources originate in BIPM/CGPM standards; same institutional lineage.
- Research concerns: Retry the definition page and review the operative resolution, not only the considering clause.

- [candidate-p1-general-004-e01](https://www.bipm.org/en/measurement-units/si-defining-constants): **inaccessible / incomplete**
  - Observed title/publisher: not established / not established
  - Source role: institutional SI definition page, not accessible in this check
  - Locator/method: Requested original URL twice through web open; both attempts returned Timeout fetching
  - Date status: incomplete; original day: unknown; Original publication day and current page contents could not be rechecked.
  - Context: Original source timed out in both attempts; previous collection claims are not counted as verification in this run.
- [candidate-p1-general-004-e02](https://www.bipm.org/en/committees/cg/cgpm/26-2018/resolution-1): **opened / exact_fragment**
  - Observed title/publisher: Resolution 1 of the 26th CGPM (2018) / BIPM / General Conference on Weights and Measures
  - Source role: primary standards resolution
  - Locator/method: Considering clause referring to 2011 proposal; decision effective 20 May 2019
  - Date status: publication_day_not_established; original day: unknown; Resolution year 2018 and effective date 2019-05-20 are distinct; exact page publication day not established.
  - Context: Saved fragment is in a considering clause about the 2011 proposal. Later operative decision takes effect 2019-05-20; not an independent present-tense assertion by this fragment alone.

### candidate-p1-general-005

- Claim/evidence interpretation: The opened ESA schedule still lists the expected month.
- Clarity: Explicitly an ESA forecast, not a completed release.
- Dates: candidate-p1-general-005-e01: Expected month December 2026; no day invented and no completed release inferred. Page publication day unknown.
- Provenance: Single official mission schedule; linked release-planning material was not independently checked.
- Research concerns: Time-sensitive: freeze an as-of observation and recheck at approval; this does not establish that a release will occur.

- [candidate-p1-general-005-e01](https://www.esa.int/Science_Exploration/Space_Science/Gaia): **opened / exact_fragment**
  - Observed title/publisher: Gaia / European Space Agency
  - Source role: official mission schedule
  - Locator/method: Fact sheet, Data Release 4 schedule bullet
  - Date status: publication_day_not_established; original day: unknown; Expected month December 2026; no day invented and no completed release inferred. Page publication day unknown.
  - Context: The opened ESA schedule still lists the expected month.

### candidate-p2-env-001

- Claim/evidence interpretation: The report summary describes conditions rarely met in marine environments and industrial-composting requirements.
- Clarity: Limited quantifier and marine conditions are specified.
- Dates: candidate-p2-env-001-e01: Dateline 2015-11-17; historical report, not a current polymer-by-polymer survey.
- Provenance: UNEP press release summarizes its report; report methods were not independently audited.
- Research concerns: 2015 summary is not an exhaustive current survey of every polymer; preserve conditions and limited quantifier.

- [candidate-p2-env-001-e01](https://www.unep.org/en/news-and-stories/press-release/biodegradable-plastics-are-not-answer-reducing-marine-litter-says-un): **opened / exact_fragment**
  - Observed title/publisher: Biodegradable Plastics Are Not the Answer to Reducing Marine Litter, Says UN / UN Environment Programme
  - Source role: press release summarizing a UN report
  - Locator/method: Opening report-findings paragraph
  - Date status: matched_existing_date; original day: 2015-11-17; Dateline 2015-11-17; historical report, not a current polymer-by-polymer survey.
  - Context: The report summary describes conditions rarely met in marine environments and industrial-composting requirements.

### candidate-p2-env-002

- Claim/evidence interpretation: The surrounding quotation explicitly makes the distinction, but the saved fragment contains only its trailing long-term-goal clause.
- Clarity: Annual observation versus long-term Paris goal is a clear distinction.
- Dates: candidate-p2-env-002-e01: Published 2025-01-10; temperature event covers calendar year 2024, not a single day.
- Provenance: WMO aggregates international datasets; that does not make this single saved passage multiple independent sources.
- Research concerns: For a standalone annotation bundle, preserve the preceding single-year qualification or an approved context note.

- [candidate-p2-env-002-e01](https://wmo.int/news/media-centre/wmo-confirms-2024-warmest-year-record-about-155degc-above-pre-industrial-level): **opened / exact_fragment**
  - Observed title/publisher: WMO confirms 2024 as warmest year on record at about 1.55°C above pre-industrial level / World Meteorological Organization
  - Source role: official institutional climate announcement
  - Locator/method: Celeste Saulo quotation on annual versus long-term temperature goals
  - Date status: matched_existing_date; original day: 2025-01-10; Published 2025-01-10; temperature event covers calendar year 2024, not a single day.
  - Context: The surrounding quotation explicitly makes the distinction, but the saved fragment contains only its trailing long-term-goal clause.

### candidate-p2-env-003

- Claim/evidence interpretation: One study projects conditional collapse; another modelling announcement describes collapse as unlikely. These are not observations of a future event.
- Clarity: Unqualified future certainty and deadline contrast with conditional research estimates.
- Dates: candidate-p2-env-003-e01: Published 2023-07-25; conditional future estimate, not observed collapse. Article text readable despite cookie-error query on redirect. candidate-p2-env-003-e02: Displayed 16:00 UTC, 2025-02-26; next 75 years is a projection interval, not an event date.
- Provenance: Different research teams and methods are identified; full data/citation dependence was not audited. Met Office announcement is dependent on its own paper.
- Research concerns: Define the intended prediction/as-of scope and compare assumptions before presenting this as a genuine evidence-conflict case.

- [candidate-p2-env-003-e01](https://www.nature.com/articles/s41467-023-39810-w): **opened / exact_fragment**
  - Observed title/publisher: Warning of a forthcoming collapse of the Atlantic meridional overturning circulation / Nature Communications / Springer Nature; authors Peter Ditlevsen and Susanne Ditlevsen
  - Source role: primary research article
  - Locator/method: Abstract, conditional mid-century estimate; Published field
  - Date status: matched_existing_date; original day: 2023-07-25; Published 2023-07-25; conditional future estimate, not observed collapse. Article text readable despite cookie-error query on redirect.
  - Context: One study projects conditional collapse; another modelling announcement describes collapse as unlikely. These are not observations of a future event.
- [candidate-p2-env-003-e02](https://www.metoffice.gov.uk/about-us/news-and-media/media-centre/weather-and-climate-news/2025/climate-change-amoc-likely-to-withstand-future-warming): **opened / exact_fragment**
  - Observed title/publisher: Climate change: AMOC likely to withstand future warming / UK Met Office; author Grahame Madge
  - Source role: research-team announcement about a modelling paper
  - Locator/method: Lead-author quotation; article timestamp
  - Date status: matched_existing_date; original day: 2025-02-26; Displayed 16:00 UTC, 2025-02-26; next 75 years is a projection interval, not an event date.
  - Context: One study projects conditional collapse; another modelling announcement describes collapse as unlikely. These are not observations of a future event.

### candidate-p2-env-004

- Claim/evidence interpretation: The 2019 source expresses limited-information uncertainty, not demonstrated absence of harm at all current exposures.
- Clarity: Harmless is categorical; current exposure has no fixed as-of date.
- Dates: candidate-p2-env-004-e01: Published 2019-08-22; current levels refers to the information available then.
- Provenance: One WHO review summary, not independent contemporary measurements.
- Research concerns: A short historical risk statement cannot establish present-day harmlessness. Missing initial qualification needs reviewer attention.

- [candidate-p2-env-004-e01](https://www.who.int/news/item/22-08-2019-who-calls-for-more-research-into-microplastics-and-a-crackdown-on-plastic-pollution): **opened / exact_fragment**
  - Observed title/publisher: WHO calls for more research into microplastics and a crackdown on plastic pollution / World Health Organization
  - Source role: institutional press release summarizing a review
  - Locator/method: Maria Neira quotation; displayed date
  - Date status: matched_existing_date; original day: 2019-08-22; Published 2019-08-22; current levels refers to the information available then.
  - Context: The 2019 source expresses limited-information uncertainty, not demonstrated absence of harm at all current exposures.

### candidate-p2-env-005

- Claim/evidence interpretation: EPA gives the label-dependent warning and explains the different conditions.
- Clarity: Home composting is distinguished from industrial composting.
- Dates: candidate-p2-env-005-e01: No original publication day established. The 2024-11-21 strategy date refers to a linked strategy, not this FAQ publication.
- Provenance: Single EPA guidance page.
- Research concerns: U.S. guidance and product-specific labels; do not treat all compostability certifications as identical.

- [candidate-p2-env-005-e01](https://www.epa.gov/trash-free-waters/frequently-asked-questions-about-plastic-recycling-and-composting): **opened / exact_fragment**
  - Observed title/publisher: Frequently Asked Questions about Plastic Recycling and Composting / U.S. Environmental Protection Agency
  - Source role: official consumer guidance
  - Locator/method: If a plastic product is labeled compostable, can I add it to my home compost pile?
  - Date status: publication_day_not_established; original day: unknown; No original publication day established. The 2024-11-21 strategy date refers to a linked strategy, not this FAQ publication.
  - Context: EPA gives the label-dependent warning and explains the different conditions.

### candidate-p2-tech-001

- Claim/evidence interpretation: FTC explicitly distinguishes encryption from legitimacy. The claim is not a faithful paraphrase of the source, intentionally providing an opposing-evidence candidate.
- Clarity: Universal HTTPS legitimacy proposition is easy to interpret as a claim under test.
- Dates: candidate-p2-tech-001-e01: No original publication day established in the opened text.
- Provenance: Single FTC guidance page.
- Research concerns: A source challenging the claim does not invalidate the candidate. Humans must assign stance and verdict independently.

- [candidate-p2-tech-001-e01](https://consumer.ftc.gov/articles/online-shopping): **opened / exact_fragment**
  - Observed title/publisher: Online Shopping / U.S. Federal Trade Commission Consumer Advice
  - Source role: official consumer guidance
  - Locator/method: Pay by credit card section, HTTPS/encryption warning
  - Date status: publication_day_not_established; original day: unknown; No original publication day established in the opened text.
  - Context: FTC explicitly distinguishes encryption from legitimacy. The claim is not a faithful paraphrase of the source, intentionally providing an opposing-evidence candidate.

### candidate-p2-tech-002

- Claim/evidence interpretation: The same OTP sentence occurs in single-factor and multi-factor sections. The multi-factor section is the relevant context.
- Clarity: Limited MFA quantifier is clear, but generic OTP wording needs a section locator.
- Dates: candidate-p2-tech-002-e01: HTML build timestamp 2025-08-26 is not established as the original publication day.
- Provenance: Same NIST document as p1-tech-004: shared-source leakage group, not independent evidence.
- Research concerns: Preserve section 3.1.5 and its second-factor definition in approved context so an annotator need not guess which occurrence was collected.

- [candidate-p2-tech-002-e01](https://pages.nist.gov/800-63-4/sp800-63b.html): **opened / exact_fragment**
  - Observed title/publisher: NIST Special Publication 800-63B / NIST
  - Source role: normative authentication guidance
  - Locator/method: Password requirements item 6; Multi-Factor OTP section 3.1.5
  - Date status: publication_day_not_established; original day: unknown; HTML build timestamp 2025-08-26 is not established as the original publication day.
  - Context: The same OTP sentence occurs in single-factor and multi-factor sections. The multi-factor section is the relevant context.

### candidate-p2-tech-003

- Claim/evidence interpretation: The participant announcement describes a practical collision; the collector-authored double-negation claim is not quoted from the source.
- Clarity: Double-negation wording is intentional and cognitively demanding.
- Dates: candidate-p2-tech-003-e01: Displayed publication 2017-02-27; body announcement 2017-02-23. The distinct dates match the candidate fields.
- Provenance: CWI and Google jointly performed the work; one announcement, not two independent confirmations.
- Research concerns: Retain the documented collector-paraphrase origin and avoid conflating collision attacks with all cryptographic breaks.

- [candidate-p2-tech-003-e01](https://www.cwi.nl/en/news/cwi-and-google-announce-first-collision-for-industry-security-standard-sha-1/): **opened / exact_fragment**
  - Observed title/publisher: CWI and Google announce first collision for Industry Security Standard SHA-1 / Centrum Wiskunde & Informatica, with Google collaborators
  - Source role: original research-team announcement
  - Locator/method: Second explanatory paragraph; article date and opening dateline
  - Date status: matched_existing_date; original day: 2017-02-27; Displayed publication 2017-02-27; body announcement 2017-02-23. The distinct dates match the candidate fields.
  - Context: The participant announcement describes a practical collision; the collector-authored double-negation claim is not quoted from the source.

### candidate-p2-tech-004

- Claim/evidence interpretation: NIST identifies selection and the expected 2027 standard in its March 2025 announcement.
- Clarity: Historical selection and an expectation as of that announcement are explicit components.
- Dates: candidate-p2-tech-004-e01: Released 2025-03-11; updated 2025-03-20. Final standard expected in 2027 in this announcement.
- Provenance: Original NIST announcement; no independent implementation or later completion evidence reviewed.
- Research concerns: Future intent must remain attributed and time-bound; no completed standard is inferred.

- [candidate-p2-tech-004-e01](https://www.nist.gov/news-events/news/2025/03/nist-selects-hqc-fifth-algorithm-post-quantum-encryption): **opened / exact_fragment**
  - Observed title/publisher: NIST Selects HQC as Fifth Algorithm for Post-Quantum Encryption / NIST
  - Source role: original institutional selection announcement
  - Locator/method: Key Takeaways, selection paragraph and Released/Updated footer
  - Date status: matched_existing_date; original day: 2025-03-11; Released 2025-03-11; updated 2025-03-20. Final standard expected in 2027 in this announcement.
  - Context: NIST identifies selection and the expected 2027 standard in its March 2025 announcement.

### candidate-p2-tech-005

- Claim/evidence interpretation: The official guide has the matching severity-versus-risk heading and surrounding risk-factor discussion.
- Clarity: Base score is distinguished from organization-specific risk.
- Dates: candidate-p2-tech-005-e01: Document Version 1.2; original publication day not established.
- Provenance: Single FIRST/CVSS normative explanatory guide.
- Research concerns: Do not extend this claim to say all CVSS metric groups ignore environmental or threat context.

- [candidate-p2-tech-005-e01](https://www.first.org/cvss/v4.0/user-guide): **opened / exact_fragment**
  - Observed title/publisher: CVSS v4.0 User Guide / FIRST.org / CVSS Special Interest Group
  - Source role: official scoring-system documentation
  - Locator/method: CVSS Base Score (CVSS-B) Measures Severity, not Risk
  - Date status: publication_day_not_established; original day: unknown; Document Version 1.2; original publication day not established.
  - Context: The official guide has the matching severity-versus-risk heading and surrounding risk-factor discussion.

### candidate-p2-general-001

- Claim/evidence interpretation: Geoscience Australia describes the Antarctic polar desert and temperature context.
- Clarity: Not all deserts are hot; Antarctic polar context is explicit.
- Dates: candidate-p2-general-001-e01: Page last updated 2022-11-25; original publication day unknown.
- Provenance: Single government geographic summary.
- Research concerns: Australian-territory page scope; retain polar definition and do not treat all deserts as having the same climate.

- [candidate-p2-general-001-e01](https://www.ga.gov.au/scientific-topics/national-location-information/landforms/deserts): **opened / exact_fragment**
  - Observed title/publisher: Areas of Australian and territory deserts / Geoscience Australia
  - Source role: institutional geographic summary
  - Locator/method: Opening Antarctica polar-desert paragraph
  - Date status: publication_day_not_established; original day: unknown; Page last updated 2022-11-25; original publication day unknown.
  - Context: Geoscience Australia describes the Antarctic polar desert and temperature context.

### candidate-p2-general-002

- Claim/evidence interpretation: The opened page identifies Marie Curie before the excerpt, but the saved sentence fragment alone does not name her.
- Clarity: Double negation is deliberate; saved evidence uses an unresolved pronoun when read alone.
- Dates: candidate-p2-general-002-e01: No original publication day established. Passage itself gives no award event day.
- Provenance: Secondary museum biography; original award registry not checked in this inspection.
- Research concerns: Preserve the antecedent context or request a versioned excerpt revision; identify collector-authored linguistic transformation.

- [candidate-p2-general-002-e01](https://oumnh.ox.ac.uk/learn-marie-curie): **opened / exact_fragment**
  - Observed title/publisher: Marie Curie / Oxford University Museum of Natural History
  - Source role: secondary biographical education page
  - Locator/method: Opening Marie Curie biographical summary
  - Date status: publication_day_not_established; original day: unknown; No original publication day established. Passage itself gives no award event day.
  - Context: The opened page identifies Marie Curie before the excerpt, but the saved sentence fragment alone does not name her.

### candidate-p2-general-003

- Claim/evidence interpretation: The saved source describes a mission goal to assess environments that could support life; it reports no detection in this passage.
- Clarity: Existence of life is a much stronger proposition than potential habitability.
- Dates: candidate-p2-general-003-e01: No original publication day established; mission goal is not a discovery event date.
- Provenance: Single NASA mission summary; no detection report is supplied or invented.
- Research concerns: Do not turn an unestablished event into a false claim. A deliberately insufficient bundle may still be included after explicit human review.

- [candidate-p2-general-003-e01](https://science.nasa.gov/jupiter/jupiter-moons/europa/): **opened / exact_fragment**
  - Observed title/publisher: Europa / NASA Science
  - Source role: official mission / planetary summary
  - Locator/method: Europa Clipper mission science-goal paragraph
  - Date status: publication_day_not_established; original day: unknown; No original publication day established; mission goal is not a discovery event date.
  - Context: The saved source describes a mission goal to assess environments that could support life; it reports no detection in this passage.

### candidate-p2-general-004

- Claim/evidence interpretation: The source gives approximately 243 Earth days per rotation and 225 per orbit.
- Clarity: Sidereal rotation wording resolves the ambiguous meaning of day.
- Dates: candidate-p2-general-004-e01: Article last updated 2024-03-15; separate site-footer update 2026-07-31. Neither treated as original publication.
- Provenance: Single NASA educational source; two bullets are not two independent sources.
- Research concerns: Keep sidereal versus solar reference frames explicit and recognize rounded educational values.

- [candidate-p2-general-004-e01](https://spaceplace.nasa.gov/all-about-venus/en/): **opened / structured_extract**
  - Observed title/publisher: All About Venus / NASA Space Place
  - Source role: official educational planetary summary
  - Locator/method: Time on Venus bullets; explanatory rotation paragraph
  - Date status: publication_day_not_established; original day: unknown; Article last updated 2024-03-15; separate site-footer update 2026-07-31. Neither treated as original publication.
  - Context: The source gives approximately 243 Earth days per rotation and 225 per orbit.

### candidate-p2-general-005

- Claim/evidence interpretation: The archived answer opposes the claim; the saved fragment uses it without the Great Wall antecedent.
- Clarity: Moon and naked-eye scope are explicit, not low Earth orbit.
- Dates: candidate-p2-general-005-e01: No original date for this specific answer established; dates on other Q&As must not be borrowed.
- Provenance: Single archived NASA Q&A; no modern observational source was reviewed.
- Research concerns: Preserve question 99 context or request an excerpt revision. Archived status and missing answer date require acknowledgment, not an invented date.

- [candidate-p2-general-005-e01](https://science.gsfc.nasa.gov/attic/cosmicopia.gsfc.nasa.gov/qa_earth.html): **opened / exact_fragment**
  - Observed title/publisher: NASA's Cosmicopia -- Ask Us -- Earth and Moon / NASA Goddard Cosmicopia
  - Source role: archived institutional Q&A
  - Locator/method: Question 99, Great Wall from the Moon; answer credited to Beth Barbier
  - Date status: publication_day_not_established; original day: unknown; No original date for this specific answer established; dates on other Q&As must not be borrowed.
  - Context: The archived answer opposes the claim; the saved fragment uses it without the Great Wall antecedent.
