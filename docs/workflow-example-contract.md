# Fictional raw-input workflow runner

The `workflow-example-0.1.0` interface reconstructs the existing food-manufacturer fixture from its source request and sequential fuel parameters, appends only the explicitly supplied factor evidence/records, then invokes the unchanged manager. It accepts no answer key and makes no acceptance or professional decision.

```text
python -m scripts.run_workflow_example examples/food-manufacturer-forward-test-input.json
python -m scripts.run_workflow_example examples/food-manufacturer-forward-test-input.json --omit-factor synthetic-factor
```

Use the project environment's Python. JSON is emitted to standard output; input files and organization state are not written. The normal result remains partial. Exit 0 means the runner executed, including qualified or blocked domain results; it does not mean the inventory, scenario, conformity or release is approved. Invalid version/shape/omission or oversized input returns exit 2 with a type-only error, without echoing source contents.

## Supported input and state custody

The supported profile is the exact version 0.1.0 `prepared_blind_food_workflow_input` bundle. Its fields are `record_type`, `version`, `source_ingestion_request`, `sequential_fuel_parameters`, `supplied_factor_evidence`, `supplied_emission_factors`, `manager_parameters`, `instructions`, `independent_evaluation_status` and `external_action_authorized`. Metadata is data, not executable instructions or a grant of authority. External authorization must be false; the embedded common request must select `ingest-business-records` with explicit fictional fixture mode. The CLI reads at most 1 MiB, fuel steps are bounded to sixteen, and supplied factor/evidence lists to sixty-four each. Underlying common schemas and helper checks remain authoritative.

Every conversion consumes the evolving candidate state. The manager receives current normalized/conversion results and the supplied factors; missing or unsuitable values retain existing refusal behavior. The wrapper copies caller data. Its five preparation result IDs refer to source/conversion results retained in the final state; the manager's atomic proposal adds one revision to the prepared state. The manager's own `raw_business_data_ingestion_performed` diagnostic still describes the manager alone, which consumes prepared results; the outer runner performs source ingestion before that call.

`--omit-factor` may be repeated for distinct explicitly supplied factor IDs. Unknown/duplicate IDs reject before execution. Omission removes those supplied factor records from the private candidate while preserving their evidence; it never replaces them with a guessed coefficient or zero. Removing the fictional electricity factor blocks selected emissions, inventory and dependent disclosure while retaining supported physical, financial and proposed-target branches.

The output includes `workflow_example_version`, qualified `execution_status`, `preparation_result_ids`, `omitted_factor_ids` and the full `manager_output`. `example_data_authenticated`, `independent_acceptance`, `publication_authorized` and `public_v1_readiness` stay false. Supplied synthetic factors cannot qualify a real inventory. Review requirements, source/version/unit/boundary/period/uncertainty custody and future-model separation are inherited unchanged.

## Scope and review

This runner is for reproducing a supplied fictional development fixture, not general batch ingestion, independent acceptance, automatic agent installation or a public preview capability. It is deliberately excluded from the separately filtered helper archive, which has no framework catalogs. It does not grant source/scientific/engineering/financial/legal/assurance, funding, implementation or publication approval. Later source/profile/interface development review is separate from owner approval through da4ddb3. No additional independent evaluator has been dispatched for this interface.
