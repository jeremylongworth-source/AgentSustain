# SUS-01: Domain contract

Status: proposed, pending architecture review. Source: ROADMAP.md sections 1, 2, 5, 23-26.

## Purpose and audience

Convert organizational sustainability evidence into traceable analysis, decision support, executable action plans, and verification steps for business users. Core capabilities are vendor neutral, composable, and adaptable to reporting frameworks and jurisdictions.

## Permitted work

Collect information; classify evidence; normalize and validate data; calculate metrics; identify gaps; analyze scenarios; compare performance; explain frameworks; prepare draft reports; develop action plans; screen regulatory applicability; assess opportunities and risks; analyze project economics; check claims against evidence.

## Professional boundaries

The system must not act as an auditor, certifier, lawyer, professional engineer, financial adviser, or authoritative regulator. Legal conclusions and definitive compliance determinations require LEGAL_REVIEW_REQUIRED. Certification, assurance opinions, and official GHG verification require ASSURANCE_REQUIRED and PROFESSIONAL_REVIEW_REQUIRED. Engineering certification requires ENGINEERING_REVIEW_REQUIRED. Investment recommendations, authoritative lifecycle assertions, and ISO conformity assertions require PROFESSIONAL_REVIEW_REQUIRED. Analytical financial comparisons remain permitted; personalized investment advice is outside scope.

Outputs must describe methodology and limitations, distinguish preliminary screening from a determination, identify the qualified reviewer needed, and state which use is withheld pending review. A polished draft cannot imply assurance or approval. Unknown jurisdiction, missing effective version, or missing company attributes prevents a definitive applicability result.

## Review states

`review_states` is a nonempty set. ADVISORY identifies explanatory work; ANALYTICAL identifies analysis; EVIDENCE_INCOMPLETE identifies material gaps. PROFESSIONAL_REVIEW_REQUIRED, LEGAL_REVIEW_REQUIRED, ASSURANCE_REQUIRED, and ENGINEERING_REVIEW_REQUIRED identify separate obligations. Multiple obligations may coexist; these states are not a severity ladder and must never be collapsed into one winner.

Execution status (`completed`, `partial`, `blocked`, `invalid_input`) is separate. A completed calculation can still require professional review. A blocked result must provide gaps and next actions rather than invented values.

Outstanding review requirements propagate by set union across composed work. Clearing one requires a recorded reviewer, role, decision, scope, evidence references, and date; a skill cannot approve itself. Historical decisions remain preserved. Removing a gap requires replacement evidence and a new evaluation, not a state rename.

## Observable requirements

- Every significant numeric result carries provenance, a method, unit, reporting period, boundary, assumptions, uncertainty, and evidence references.
- Missing or incompatible factor metadata prevents emissions calculation and emits EMISSION_FACTOR_REQUIRED with EVIDENCE_INCOMPLETE.
- Requested certification, legal determinations, and engineering sign-off retain the corresponding review states in composed results.
- Estimates are labeled; unknown and zero remain distinct. Incomplete evidence cannot be described as a verified inventory.
- Reports and claims reference their supporting results and qualifications; unsupported claims cannot be strengthened for marketing.

Validation: schema fixtures plus the scenarios in docs/evaluation-requirements.md. Domain enforcement in actual skills remains future work.
