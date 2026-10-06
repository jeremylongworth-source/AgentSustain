# Selected water balance evaluation

All source quantities, point stocks, facility classifications, coverage/engineering declarations and bounds are fictional. [Complete actual CLI requests/outputs](sus11-water-balance.json) preserve nine balance cases and two exact raw CSV-to-balance handoffs. Input/source bytes are unchanged and full CLI/helper outputs agree.

| Case | Expected result / limitation |
| --- | --- |
| 1,000 m3 inflow, 900 m3 outflow, stock 100 to 150 m3 | Signed unresolved residual 50 m3; declared supplied envelope 20â€“80 m3 |
| 1,000 m3 internal reuse | Separate throughput; no addition to external inflow or residual |
| Outflow 1,100 m3 | Residual -150 m3, envelope -180 to -120 m3; no clamping or negative-loss interpretation |
| Outflow 950 m3 | Zero residual, envelope -30 to 30 m3; actual closure/engineering approval remain false |
| Closing stock 50 m3 | Signed storage change -50 m3; no missing-stock or zero default |
| Missing opening stock / unknown outflow / incomplete coverage | Residual withheld; supported selected subtotals retained |
| Missing input bound | Residual point retained, bound/zero-comparison unknown; no inferred tolerance |
| Ordinary-mode fictional sources | Sources unsupported; no actual measurement identity inferred |

Nine focused tests also cover wrong stock dates, unsupported source/unit/version/time/model context, incomplete roles, invalid bounds, duplicate metric/source-fragment coverage and mixed facilities, original-state/evidence/factor/review custody, exact source hashes and unquantified output uncertainty. Whole quantities stay partial and source/engineering review remains open.

The two raw-source CLI steps ingest five pinned CSV stream/point-stock records through the unchanged importer, then pass the exact candidate to the balance helper. Stock ISO dates and flow periods remain distinct; hostile source instructions remain data. Explicit fake reviewed envelopes attach to their original records and reproduce the same residual/bounds. This is controlled source/arithmetic evaluation, not real measurement completeness or independent organization acceptance.

[The method contract](../docs/water-balance-contract.md) links primary USGS budget methodology and preserves the separate GRI consumption/storage terminology. It imports no normative adapter, source archive, density/tolerance/confidence or actual consumption/leakage finding. Later scoped owner/source/engineering/scientific/legal/rights and all broader independent/public-v1 requirements remain open. The full roadmap goal stays active.

[Final validation](sus11-water-balance-validation.json) records 807 repository tests in 739.127 seconds, nine focused tests in 1.395 seconds, twenty architecture checks in 0.181 seconds, nine new balance actual CLI/helper cases and two raw-source actual handoffs. [The durable witness](sus11-water-balance-suite-run.json) confirms unchanged recorded code/catalog/schema/test/data hashes during the run; the new CSV was created after the witness started and its byte custody is verified separately in the actual source composition. Three legacy water CLI/helper results plus their complete final state and all 384 prior source files remain exact. These checks establish selected arithmetic/source preservation, not actual measurement/reference/phase/coverage/consumption/leakage/closure or independent organization/public-v1 acceptance.
