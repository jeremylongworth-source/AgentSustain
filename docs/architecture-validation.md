# Architecture validation evidence

Checked 2026-10-04 (America/Toronto). Architecture draft only; human review remains pending.

## Executed validation

Command: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

Result: 20 test methods passed, no failures, on Python 3.14.3 with jsonschema 4.26.0. Subtests cover multiple missing fields and invalid references. Six Draft 2020-12 schema definitions were checked and both fictional example envelopes validated. Taxonomy coverage matched all 101 atomic names listed in ROADMAP.md sections 7-13 and all 16 families.

Coverage: evidence provenance; explicit assumptions for proxies; input envelope; factor metadata; missing-factor diagnostic constraints; blocked result metric restrictions; date formats and ordering; duplicate IDs and dangling references; null versus zero; uncertainty representation; multiple review obligations; review resolution evidence/scope; retained gaps and assumptions; taxonomy completeness.

Content hashes are recorded in ../evaluations/architecture-content-manifest.json for schemas, examples, tests, contracts, README, instructions and the roadmap. The manifest excludes this report and itself to avoid recursive hashes. It identifies the reviewed draft contents, not approval or a released revision.

## Limits

These are architecture contract tests. They do not demonstrate implemented skills, valid real-world emission factors, correct carbon calculations, dimensional compatibility, factor geography/vintage fitness, official-source authenticity, full evidence-lineage cycle detection, agent routing behavior, framework mappings, regulatory currency or end-to-end workflow performance. Numerical factors in test code are explicitly synthetic and never approved for real inventories. Human review resolution records are structurally validated, not identity-authenticated by this local harness. Runtime enforcement requires an appropriate access-control layer if a consumer is later built.

The complete v1 definition and public readiness gate remain unproven. Domain known-answer and behavioral evaluations must accompany implementation after architecture approval.
