---
name: assess-sustainability-maturity
description: Assess current sustainability management practices against an explicit versioned rubric, retaining evidence gaps and owned improvement follow-ups. Use for maturity profiles, not environmental impact calculation or certification.
---

Inspect the supplied current-state records and rubric before assessing practice. Read [the strategy contract](../../../docs/strategy-contract.md) for the helper fields and cumulative level semantics.

Require a sourced rubric with explicit scope, dimensions, ordered levels and substantive practice criteria. Do not invent a universal maturity scale, weights, benchmark or minimum score. Inspect actual rubric source content and record `rubric_evidence_fit` plus `rubric_fit_rationale`; an unrelated known source ID is insufficient. Withhold supporting fitness when the cited document has no rubric. Confirm that the rubric fits the selected organization and reporting period; a narrow plant rubric cannot establish whole-organization maturity.

For each criterion distinguish demonstrated practice, documented non-demonstration, a plan, an unknown and conflicting evidence. A policy or training schedule does not prove implementation, monitoring, corrective action or improved impacts. Inspect source fragments, dates, coverage and contradictions; source IDs and management assertions alone do not establish fitness. Unknown observation dates stay unknown rather than becoming access dates. Preserve qualitative sources with `UNKNOWN_UNIT`; do not create physical quantities from maturity levels.

Use `scripts.run_strategy` with `assess-sustainability-maturity` to produce the checked append-only proposal. Its highest supported level requires every criterion through that level to be demonstrated with current, caller-reviewed supporting evidence. Missing criteria do not become zero, and a high-level document cannot bypass lower-level gaps. Profiles do not average into an organization score or imply sustainability performance.

Retain source uncertainty and all earlier reviews, gaps and assumptions. Identify owned, dated evidence or improvement follow-ups; they remain proposed and unsent, with overdue proposals unverified. Escalate rubric fitness, contradictions and scope coverage before downstream strategy use. Do not certify ISO/framework conformity, resolve professional review, approve implementation or make public maturity claims.
