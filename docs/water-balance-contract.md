# Selected water-volume balance reconciliation

`water-balance-0.1.0` is a separate neutral method alongside unchanged same-basis water totals. Run `python -m scripts.run_water_balance REQUEST.json` with the existing `build-water-baseline` common envelope. It reconciles a declared facility's inflow, outflow and point-stock change, retaining internal reuse separately and leaving the residual unexplained.

The method reference is [USGS Water Budgets: Foundations for Effective Water-Resources and Environmental Management](https://pubs.usgs.gov/publication/cir1308), read on 2026-10-06. It motivates explicitly bounded inflow/outflow/storage accounting. This facility-volume implementation is conditional selected-source bookkeeping, not a hydrological model, statistical metrology method or normative reporting adapter. The [GRI 303 reference](https://www.globalreporting.org/publications/documents/english/gri-303-water-and-effluents-2018) retains its own consumption/storage definitions; the core residual here is not relabeled consumption or conformance. No reference source bytes, default density, tolerance or normative data are imported.

## Exact source inputs

Parameters are `quantities`, `balance_review`, `fixture_mode`, `result_id`. Use an explicit fixture boolean and fresh result identity. Each quantity is exactly `metric_id`, `kind`, `facility_id`, `source_fragment`, `evidence_ids`, `evidence_fit`, `rationale`, `bounds`. Kinds are `inflow`, `outflow`, `storage_opening`, `storage_closing`, `internal_reuse`.

`balance_review` is exactly `boundary_id`, `facility_id`, `period`, `as_of_date`, `measurement_boundary`, `coverage_complete`, `nonoverlap_assessment`, `evidence_ids`, `evidence_fit`, `rationale`, `reviewer_role`. The selected facility belongs to the organizational boundary, every quantity has that facility, and the period/boundary match current state. Coverage is a literal boolean and reviewed-supporting source context is required. The assessment date is on or after the observed period end; full-period review evidence has a known version and nonfuture access. Actual facility identity, completeness and source fitness remain unverified.

Selected metrics are current supported nonnegative source-leaf observations, with declared evidence, unit and boundary. Flows/reuse cover the exact reporting period. Opening/closing stocks instead have point periods at the reporting-period start/end respectively; those dated observations are retained. Source evidence covers the selected metric's full interval/point, has matching units, known versions and nonfuture access. Projected/tier-5/assumption quantities and hidden derived metric chains are unsupported. Unknown source quantities stay unknown; no absent stock is assigned zero. Synthetic source locators or known synthetic CSV/workbook ingestion ancestry cannot enter ordinary mode.

Metrics are unique across roles. Repeated evidence plus the same declared source fragment cannot supply a different term; shared documents require distinct explicit fragments and qualified nonoverlap review. Hidden aliases and physical coverage still require source examination. Raw unit L/m3 conversion is dimension-preserving. Mass, density, evaporation/phase, temperature/reference-volume adjustments, basin stress and water-quality equivalence are not inferred. The review must assess common measurement/reference meaning; same numeric unit alone is not physical closure proof.

## Arithmetic, missing data and bounds

Supported selected inflow/outflow/reuse subtotals may remain when other records are unknown. A subtotal is not complete source coverage. Exactly one supported opening and closing snapshot supplies `storage change = closing - opening`, retaining signed increases/drawdown. Repeated or absent stock roles withhold that delta.

The residual requires supported selected inflow and outflow records, both stocks and explicit declared complete coverage:

`unresolved residual = selected inflow - selected outflow - (closing stock - opening stock)`

Internal reuse never enters this equation and is shown as separate throughput. Unsupported sources, missing flow/stock roles or incomplete coverage withhold the residual rather than deriving an understated amount. Positive/negative/zero residuals remain signed numerical candidates; none identifies actual leakage, consumption, an omitted process or verified meter closure. Even exact zero requires qualified source/engineering interpretation.

Each optional `bounds` record is exactly `low`, `high`, `unit`, `basis`, `evidence_ids`, `evidence_fit`. Supported nonnegative ordered volume bounds enclose the current source quantity and have source-backed temporal fitness. Values convert explicitly to m3. Bounds are supplied external envelopes, not automatically derived from a metric's uncertainty number, normal distribution, tolerance or confidence level.

If every required balance term has supported bounds, the interval is the sum of positive-term lower bounds minus negative-term upper bounds through the corresponding upper/lower combination. Positive terms are inflow/opening stock; negative terms are outflow/closing stock. `zero_within_supplied_bounds` records only that interval comparison. Missing/inconsistent/unfit bounds leave the comparison unknown and create a gap; no zero-tolerance assumption fills it. Source covariance/confidence and actual interval/closure validity remain unverified. All output uncertainty is unquantified, with original observations/bounds retained.

## Evidence, proposals and review

`WATER_BALANCE` retains full quantity bindings, current source metric/evidence snapshots, exact source-result hashes, stock periods, support flags, converted values, supplied bounds, review and the signed residual. `WATER_BALANCE_INPUTS` preserves complete parameters. Metrics include only supported selected quantities/delta/residual, each with source lineage, period/boundary and 34-digit Decimal arithmetic before finite JSON representation. The result stays partial or blocked and adds an open engineering review; malformed/duplicate/mixed-facility data yields no new metric.

Original state evidence, factors, results, assumptions, gaps and reviews survive the checked proposal. No state file, factor/GWP, consumption/leakage fact or external action is created. Source authenticity, actual coverage, measurement closure and engineering approval flags remain false. This multi-role reconciliation cannot substitute for the old helper's single-basis `WATER_BASELINE` report or automatically supply water-consumption intensity/hotspots.

[Known-answer/adversarial CLI evidence](../evaluations/sus11-water-balance.md) includes an exact pinned CSV-to-balance handoff with full-period flows and point-stock records. The old water baseline/intensity/hotspot algorithms, schemas, units, skill instructions, catalogs and captures remain unchanged. This later method requires scoped owner/source/engineering review alongside earlier later interfaces. Broader water-quality/phase/source/hydrological/consumption/sector methods, independent organization/behavioral/platform acceptance and all public-v1/release requirements remain open. No wave or full-goal closure follows.
