# Sub-agent 1A — Official Danger-Sign Research and Deterministic Engine

## Mission
Build a source-grounded, deterministic, multilingual danger-sign detection module for ASHA maternal/newborn visit notes. This is safety-critical because a missed danger sign carries a double judging penalty.

## Start condition
You may begin official guideline research and test-case design immediately. Begin substantial implementation after Agent 1's Milestone 1 voice loop is demonstrated, unless Agent 1 explicitly reprioritises the work.

## Research requirements
1. Locate current official Indian public-health documents, prioritising NHM ASHA Handbook, NHM/MoHFW HBNC guidance and relevant official maternal-health guidance.
2. Use the official publication, not a blog or secondary summary, as the source of truth.
3. For every proposed danger sign, capture exact document title, issuing authority, version/year, page/section and a short faithful description.
4. Do not invent clinical thresholds or assume that an illustrative example is in the official list.
5. Produce `docs/DANGER_SIGN_GUIDELINES.md` with a citation table and explain any scope limits or discrepancies between sources.

## Implementation requirements
- Deterministic canonical phrase matcher.
- Indic-language variants and English code-mix aliases for the supported languages selected by the team.
- Normalisation for Unicode, punctuation, common transliteration and ASR spelling variations.
- Context handling for negation, historical symptoms and another person's symptoms.
- Preserve the matched phrase/category and evidence metadata.
- Positive deterministic match must not be suppressed by an LLM.
- Ambiguous cases should be surfaced for clarification/review; do not silently label them safe.
- Expose a small typed interface, for example `detect_danger_signs(text, language, context) -> DetectionResult`. Coordinate the exact interface with Agent 1 before finalising it.
- Do not diagnose or provide treatment advice. The only action is the configured urgent PHC referral message.

## Test requirements
Create synthetic test cases for every included danger sign, language/code-mix variant, transliteration/ASR spelling variation, negation, historical context, wrong subject, incomplete phrase and ambiguous phrase. Test positive and negative examples independently.

## Out of scope
- No Android UI.
- No web dashboard.
- No Supabase schema or migrations.
- No real beneficiary data or real recordings.

## Deliverables
- `docs/DANGER_SIGN_GUIDELINES.md`
- deterministic detector module and typed result model;
- multilingual test fixtures using synthetic examples;
- unit tests and actual test report;
- recommended high-priority escalation event payload for Agent 1D.

## Handoff report
List source references/pages, changed files, matching limitations, tests and results, false-positive/false-negative risks, and unresolved questions. Never claim clinical completeness beyond the verified source scope.
