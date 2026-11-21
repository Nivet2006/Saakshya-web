# Sub-agent 1C — Healthcare Visit Field Extraction and Validation

## Mission
Implement typed extraction and validation of the visit fields required by the ASHA Voice Field Register. The extractor must handle Indic speech transcripts with English healthcare code-mixing and must never invent missing facts.

## Start condition
You may design the schema, parser tests and synthetic fixtures in parallel. Begin substantial integration after Agent 1's Milestone 1 voice loop is demonstrated, unless Agent 1 explicitly reprioritises.

## Required fields
- `beneficiary_id`
- `visit_type`: `ANC`, `PNC`, `Newborn`, `Immunisation`
- `weight_kg`
- `vaccinations_due`
- `next_visit_date`
- `danger_signs`
- `danger_sign_flagged`
- `follow_up_actions`

Coordinate exact types and optionality with Agent 1D. Do not unilaterally publish a competing contract.

## Requirements
- Support natural language and common English/Indic code-mixing for selected supported languages.
- Resolve beneficiary IDs/names only against synthetic demo data supplied through a defined interface. Ask when identity is ambiguous; never fabricate an ID.
- Normalise weight to kilograms while retaining source text/parse confidence where useful.
- Parse dates using the configured visit-local timezone and an explicit reference date. Ask for clarification when a date is ambiguous or incomplete; do not silently guess the year.
- Distinguish administered/completed vaccinations from due/pending vaccinations.
- Do not invent vaccination status or follow-up actions unsupported by the utterance/rules.
- Use `null` or explicit unknown states for missing information.
- Keep extraction separate from diagnosis. Danger-sign classification is owned by 1A.
- Return field-level provenance/confidence or clarification requirements where useful.
- Ensure a voice correction changes only the specified field.

## Synthetic test examples
Create tests with fictional beneficiaries and phrases such as ANC checkup, TT injection, IFA goli, newborn weight in kilo and next-visit date. Include ambiguous numbers, alternate units, code-mixing, missing fields, noisy/partial transcript artefacts and corrections. Do not use real beneficiary records or real health data.

## Out of scope
- No Android UI.
- No web dashboard.
- No Supabase schema/migrations/RLS.
- No treatment recommendations or clinical diagnosis.

## Deliverables
- typed visit model or extraction DTO proposal;
- extraction/normalisation module;
- field validators and clarification outputs;
- synthetic fixtures and unit tests;
- integration notes for state machine and contract owner.

## Handoff report
List changed files, supported patterns/languages, known ambiguities, tests/results and any fields requiring follow-up clarification.
