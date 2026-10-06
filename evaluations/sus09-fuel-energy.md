# Fuel calorific-energy evaluation

All fuel quantities, calorific values, organizations and review facts are fictional. They are not real fuel coefficients. [Complete requests and actual outputs](sus09-fuel-energy.json) include eight new fuel CLI/helper cases and one sequential existing baseline CLI/helper composition. Every CLI preserves request bytes and agrees with the full helper output.

| Case | Known result / boundary |
| --- | --- |
| 1 t fictional fuel, supplied 18 MJ/kg LHV | 5,000 kWh input calorific energy |
| Same quantity, supplied 18 GJ/t | 5,000 kWh; equivalent unit representation |
| 100 m3 fictional fuel, supplied 36 MJ/m3 with matching conditions | 1,000 kWh |
| Same supplied value, explicitly reviewed HHV | 1,000 kWh HHV; no automatic LHV conversion |
| Zero fuel with supplied positive calorific value | Zero kWh; coefficient provenance remains required |
| Missing selected calorific record | Blocked with CALORIFIC_VALUE_REQUIRED; no quantity inferred |
| Unfit conversion review | Blocked; no converted metric |
| Reference-temperature mismatch | Blocked; no reference-volume correction inferred |
| Exact 5,000 kWh fuel candidate plus 1,000 kWh separate electricity | Existing helper produces 6,000 kWh selected delivered-energy baseline; engineering review retained |

Eleven focused tests additionally cover MJ/L volume scaling, wrong physical/calorific units, unknown/negative/zero inputs, dry/received/fuel mismatch, unknown reference conditions, invalid absolute conditions, nonfuture full-period source/unit/version/date fitness, source/metric projections, hidden derived inputs, explicit fictional isolation, fresh identities, source-result hashes, untouched original state and persistent uncertainty/reviews. The initial malformed adversarial fixtures were corrected to exercise valid but unsupported source context; shared-schema rejection was not counted as a helper pass.

[The method contract](../docs/fuel-energy-contract.md) records the primary parsed IPCC method reading without importing defaults, source bytes or normative text. Arithmetic and declared source fitness do not authenticate fuel identity, laboratory values, sampling/annual representativeness, reference-volume basis, engineering applicability or useful heat. No emissions, verified saving, independent organization reliability, roadmap closure, scoped approval or public-v1 readiness follows. The full roadmap remains active.

A tenth actual CLI/helper execution feeds the converted fuel energy into the unchanged CO2e helper with no emission factor. It returns blocked with EMISSION_FACTOR_REQUIRED, no emissions metric and the original engineering review retained; a supplied heating value cannot substitute for an emission factor. Five original energy CLI/helper cases also reproduce their saved result/reason records (including complete project state), with exact current CLI/helper equality.

Four further actual CLI/helper executions ingest the pinned fictional CSV, convert its source-leaf fuel/calorific rows, build the existing 6,000 kWh baseline and reject ordinary-use relabeling of synthetic ingestion ancestry. Logical row literals, physical source units, exact raw-byte hash, review history and the source instruction text remain preserved as data. This raw-source composition is author-led and does not authenticate measurements or establish independent organization acceptance. The preliminary full-suite run preceded the CSV ancestry guard and is not counted as final-version validation.

[Final validation](sus09-fuel-energy-validation.json) records 766 repository tests in 626.301 seconds, eleven focused tests in 1.205 seconds, twenty architecture checks in 0.177 seconds, fourteen new actual CLI/helper executions and five original energy actual CLI/helper replays. The [durable final witness](sus09-fuel-energy-suite-run.json) confirms successful completion and unchanged runtime/test/Canada/raw-CSV hashes during that run. All 368 prior runtime/test/schema/standard/router/skill/data files remain unchanged. The [preliminary witness](sus09-fuel-energy-preliminary-suite-run.json) records 765 tests with changed source hashes and explicitly does not validate the final version. This author-led evidence establishes the bounded method and source flow, not actual source/scientific fitness, independent organization acceptance or full-roadmap readiness.
