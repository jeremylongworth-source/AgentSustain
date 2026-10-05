# SUS-05 initial author-led execution

Date: 2026-10-04 (America/Toronto). Skill source snapshot: a602818; line-level reconciliation was improved after the first execution. These are author-led applications of the checked-in skills, not independent blind model runs.

## Observed outcomes

| Scenario | Recorded outcome |
|---|---|
| Duplicate invoice and missing unit | One supported 1000 kWh record retained; duplicate identity and unknown-unit gaps remain; no complete total |
| Shared invoice line items | Both 200 kg and 300 kg line items retained under one document; initial conservative helper blocked aggregation |
| Source tier versus fitness | Primary meter record flagged for annual coverage; supplier industry-average estimate labeled as tier 5 proxy with assumption and unquantified uncertainty |
| Energy intensity | Helpers calculated 2 MWh -> 2000 kWh and 2000 / 400 -> 5 kWh/count; both evidence references preserved |
| Zero denominator | Helper rejected undefined intensity; no KPI metric or substitute production emitted |
| Fiscal period and new facility | Missing fiscal dates, control evidence and comparability blocked comparison; original 2024 context preserved |
| Embedded source instructions | Only 100 kWh extracted; legal and assurance reviews preserved; no publication or certified claim |
| Independent-meter baseline | Explicitly disjoint source quantities summed to 1500 kWh with conversion and coverage assumption |
| Comparable periods | 2022/2023 quantities produced -20 kWh and -20 percent, with both periods and sources retained |

Result envelopes, common input requests and checked proposed revisions are saved in sus05-author-run-01/. Fixture setup supplies the fictional organization and operating context explicitly; it is not inferred about a real company. Raw prompts and scenario inputs remain attached to each execution. The original execution used only hypothetical evidence, with no real emission factors or customer data.

## Improvement and rerun

The first shared-document case exposed an unnecessary aggregation limit: repeated evidence did not distinguish duplicate quantities from legitimate disjoint lines. The helper now accepts explicit coverage_details for every selected metric, keyed to actual evidence IDs and source fragments, after nonoverlap confirmation. It rejects missing mappings, invented evidence references and repeated source fragments. The skill still must inspect actual activity overlap; differing line labels alone do not prove independence.

The rerun in sus05-author-run-02/SUS05-line-items.json calculated 500 kg from the two stated nonoverlapping lines while retaining one original document. The first blocked execution remains available as evaluation history. No independent source IDs were fabricated.

## Verification and limits

The project test command passes 51 methods: 20 foundation checks, 16 data-helper checks, 6 state-proposal checks and 9 saved-artifact checks. Helpers ran for conversions, intensity, denominator rejection, period rejection, baseline and comparison. Candidate states passed shape, reference, history, review-preservation and lineage checks. The changed baseline skill also passed skill-creator packaging validation.

Saved-artifact checks validate these specific recorded outputs; they do not rerun agent inference or establish performance on arbitrary records. Author-led execution is weaker evidence than independent evaluation. No external benchmark, real supplier data, production persistence, accounting methodology validation, regulatory interpretation, emissions inventory, router or public-v1 workflow has been demonstrated. General readiness remains unproven, and the overall development goal is unfinished.
