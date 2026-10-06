# Consuming AgentSustain skills

This guide describes repository-local use and a focused installation recommendation. No skill has been installed into an agent host by this step. File presence, source review, helper execution, host discovery and live agent behavior are different evidence. License, rights, source/professional and public-v1 requirements remain open.

## Start with one workflow

For an organization-wide source-to-disclosure task, start with [sustainability-manager](../skillsets/sustainability-manager/SKILL.md) and its [dependency manifest](../skillsets/sustainability-manager/manifest.json). For a narrower job, choose the matching composition below. Load the selected skill and its linked contracts first; read only dependencies needed by the request. Keep the complete repository layout so relative references, source registries and approved Git history remain available.

| Work requested | Repository entry point | Existing local runner |
|---|---|---|
| Organization baseline through proposed targets/roadmap and qualified disclosure | [sustainability-manager](../skillsets/sustainability-manager/SKILL.md) | `scripts/run_manager.py` |
| Selected physical-domain opportunities and proposed actions | [sustainable-operations](../skillsets/sustainable-operations/SKILL.md) | `scripts/run_operations.py` |
| Selected GHG calculations and partial inventory | [carbon-accounting](../skillsets/carbon-accounting/SKILL.md) | `scripts/run_carbon_workflow.py` |
| Supplier/procurement analysis | [sustainable-procurement](../skillsets/sustainable-procurement/SKILL.md) | `scripts/run_procurement_workflow.py` |
| Source-attributed climate risk/adaptation candidates | [climate-risk](../skillsets/climate-risk/SKILL.md) | `scripts/run_climate_workflow.py` |
| Conditional financial/business-case analysis | [sustainability-business-case](../skillsets/sustainability-business-case/SKILL.md) | `scripts/run_investment_workflow.py` |
| Qualified inventory/framework disclosure candidates | [sustainability-reporting](../skillsets/sustainability-reporting/SKILL.md) | `scripts/run_reporting_workflow.py` |

Read [current review status](current-review-status.md) and the authoritative owner ledger before interpreting historical pending wording in frozen skill assets. Owner approval is tied to a reviewed revision and named scope; it does not authenticate sources, extend to later material interfaces, clear state reviews, or authorize funding/publication. Specialist router pins stay unchanged.

## Source preparation and local execution

The manager starts from an already normalized common state. [CSV ingestion](business-ingestion-contract.md) or [literal workbook ingestion](workbook-ingestion-contract.md) can propose that state from explicit source bytes, declarations and review context. Observations, hypothetical model inputs, unknown quantities and their uncertainty remain distinct. Missing factors produce `EMISSION_FACTOR_REQUIRED`; source tier declarations and hashes do not supply missing factors or authenticity.

Use the current [common input envelope](../schemas/input.schema.json), exact selected runner/skill name, and the parameters in that workflow's contract. Inspect the proposed state and outstanding reviews before accepting any state update. Existing runners print candidate results and do not write shared-state files or implement proposed actions. The host environment must support the declared local validation dependencies; [platform evidence](platform-validation.md) states what has actually run.

A ready controlled exercise is:

```text
python -m scripts.run_organization_acceptance examples/organization-acceptance.json examples/organization-acceptance-oracle.json
```

[The acceptance map](organization-acceptance.md) explains the case/oracle wrapper, versioned comparison limits and conditional expected outputs. This command tests source-to-manager composition; it does not prove the host automatically found or followed a skill. For a blind behavior test, withhold the answer key and saved results until the evaluator seals its report, using [the prepared protocol](../evaluations/agent-workflow-forward-test-plan.md).

## Installation/discovery recommendation

If host installation is later requested, prefer one project-scoped composition, initially sustainability-manager for recurring organization analysis. Keep broader personal/global bundles out of this repository-specific setup. Select atomic dependencies only when the narrower recurring task needs them. No new MCP preset is needed for the current local file/helper exercise; external-source services, browser/account access and production actions require their own scoped need and authorization.

Before specifying exact host paths, installer commands, adapters or config, verify that host's current official documentation. This guide provides no speculative host config and does not claim these repository directories are automatically discovered. Preview any installer operation, preserve existing instruction files, record changes and rollback steps, and verify copied/present files separately from fresh-host discovery. Installation and project instruction edits need the actual requested scope; no installer, global configuration, project instruction file or pinned skill is changed here.

After an authorized setup, run a fresh-host trigger such as:

> Use AgentSustain to analyze the supplied fictional organization records, preserving evidence, units, periods, assumptions, uncertainty and unresolved review. Return conditional physical, emissions, modeled finance, target and roadmap results with clear gaps. Do not guess factors, conflate unknown with zero, clear review, implement actions or publish a claim.

Record the selected skill, actual model/effort where exposed, host, revision, source hashes, tools and sealed output. Verify that the agent read repository instructions, found the intended entry point and respected review/source gates. A prompt walkthrough or source inspection must be labeled separately from a live run. Explicit authorization for a separate evaluator remains pending; no independent-agent result is claimed.

## Current actions and remaining decisions

Completed: source/manifest/runner inventory, focused repository-consumption recommendation, linked review/input contracts and existing controlled exercise. Unperformed: host installation, instruction/config edits, new MCP access, global setup and independent delegation. This documentation has no installer rollback; ordinary Git restoration can revert it without changing runtime assets. Owner license/security/contribution decisions, requested delegation authorization, host-specific discovery and source/domain/expert/organization acceptance remain open. No release/publication is authorized.
