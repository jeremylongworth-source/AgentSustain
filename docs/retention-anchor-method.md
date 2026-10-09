# Explicit required versus actual submission retention anchors

The draft task contract `jurisdiction-tasks-0.2.0` adds explicit retention anchor selection to the existing neutral helper. It leaves the exact v1 catalog/interface/captures unchanged; no old task or result is migrated. Shared schemas remain unchanged. This material extension awaits scoped review after approved foundation 898d790.

## Primary-source motivation

The [2023 primary notice](https://gazette.gc.ca/rp-pr/p1/2023/2023-12-09/html/sup1-eng.html), opening retention paragraph, uses required submission as the three-year anchor. Its [2025 amendment](https://gazette.gc.ca/rp-pr/p1/2025/2025-12-06/html/notice-avis-eng.html), Schedule item 2, supplies reporting-year dates. [The separate research calendar (original archived)](../evaluations/sus25-source-remediation-tree-manifest.json) records those source dates and calculated anniversary candidates:

| Reporting year | Selected required date | Three-year candidate anniversary |
|---|---|---|
| 2024 | 2025-06-02 | 2028-06-02 |
| 2025 | 2026-06-01 | 2029-06-01 |
| 2026 | 2027-06-01 | 2030-06-01 |

The calendar is explicitly non-executable research. It determines no operator applicability, individual extension/exception, legal endpoint or record-disposal authorization. Publication/reporting years are distinct from legal commencement. Storage, underlying records and parent-address conditions remain separate open review items. Parsed sources were read; complete original source bytes are not archived. Source access is not qualified legal/current-source approval or a filing action.

## V2 catalog requirements

The existing `prepare-jurisdiction-task-register` operation and request fields stay the same. Exact catalog byte pins select either v1 or v2; no inferred upgrade occurs. V2 adds `retention_anchor_basis` and `retention_anchor_task_id` to every task. Non-retention tasks set both null. A retention task explicitly chooses `actual_submission` with no report reference, or `required_submission` with a report-task reference.

Actual-submission retention uses trigger `current_submission` and the supported actual date, matching v1 behavior. Required-submission retention uses trigger `reporting_condition` and an actual report task's year-specific deadline from the same pinned catalog. It does not depend on whether actual submission occurred. Referenced tasks must exist, be report tasks and cover every selected retention reporting year. Self/non-report/missing references, wrong triggers or v2 fields inserted into a v1 catalog block loading.

Both the retention source and referenced report-date source need independently matched locator/version/current-date fitness and suitable selected subject/planning context. The source snapshot/review and full referenced task are retained in `retention_anchor_selection`. Unknown dates remain null; unfit or stale date sources leave the anchor and anniversary unknown. The helper never falls back to the actual date when a required-date anchor is missing or unverified. Explicit leap-day/overflow anniversaries remain unknown rather than selecting a replacement day.

The required anchor is a declared sourced calendar date, not publication, commencement, an observed date, an inferred filing date or a statutory applicability decision. Computed dates are conditional anniversary candidates rather than permission to destroy records. Required-date source versions and original actual-history dates remain visible together without overwriting each other. All original quantities, source history, EMISSION_FACTOR_REQUIRED gaps and engineering/legal reviews survive; each task result adds open legal review.

## Evidence and limits

[The fictional v2 capture](../evaluations/sus19-retention-anchors.md) uses a fictional required date 2026-06-10, an early actual date 2026-04-01 and three years, yielding candidate 2029-06-10. Removing the actual date leaves the required candidate unchanged; withholding the referenced report-date source leaves no anchor/date. This is not an executable Canadian calendar or actual company example. The researched Canadian dates above are kept in a different non-executable record.

Known-answer/adversarial checks cover early/late/absent/false submission, independent current date-source fitness, unknown dates, explicit actual-anchor behavior, report-condition versus submission triggers, catalog/reference/type isolation, leap-day withholding and full v1 output preservation. V1 still uses its original fictional actual-submission/two-year model; historical captures are preserved rather than reinterpreted.

Actual Canadian rule/profile coverage, notice-specific subject/operator applicability, regulated emission quantities, exceptions/extensions, storage/address tasks, qualified legal interpretation, independent organization evaluation and all scoped/release gates remain open. No individual skill, law adoption, filing, record removal, phase closure or public-v1 readiness is supplied.
