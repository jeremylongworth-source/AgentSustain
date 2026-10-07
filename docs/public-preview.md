# AgentSustain — draft public preview

**Prepared for owner review. Not published and not v1. Original project material is MIT licensed; third-party rights and publication approval remain separate.**

AgentSustain is an evidence-driven sustainability agent-skill project. The full repository follows SUS-00 through SUS-25. This limited preview packages selected original, vendor-neutral arithmetic helpers and shared schemas so reviewers can inspect a small runnable surface while source, professional and public-v1 gates remain open.

## What this preview includes

Data unit/period/baseline/KPI primitives; selected energy, water, material/waste and financial helpers; their Python dependencies; shared input/state/result/evidence schemas; one original fictional conversion request; and local wiki drafts. Dependencies use the repository's declared `jsonschema>=4.23,<5` range. No dependencies, binary runtimes or installed environments are bundled.

This is a **helper preview**, not the full agent-skill library. It contains no installed skills, specialist router, framework mappings, Canadian regulatory pack, emission-factor or GWP database, reference tables, historical evaluation archives, raw-source documents or customer records. Supplied quantities remain unverified. Unknowns, assumptions and review requirements must stay visible. Nothing here certifies compliance, engineering performance, financial suitability or an environmental claim.

## Run the fictional conversion

Use Python 3.11 or newer. The recorded repository tests cover Windows Python 3.11.17, 3.12.14 and 3.14.3 at their recorded revisions; this package has its own narrower smoke checks. Native Linux and general agent-host discovery remain unverified.

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m scripts.data_tools examples/preview-conversion.json
```

These commands use the virtual environment on Windows. Other systems use their environment's Python path; native Linux has not been validated here.

The example converts a fictional 2 MWh quantity into 2,000 kWh. It tests unit arithmetic, not energy savings, fuel properties or emissions. Install into your chosen environment; dependencies require normal package access and are not vendored. Prefer using the virtual environment's Python when multiple interpreters are installed.

The state-based entry points are `scripts.run_energy`, `scripts.run_water`, `scripts.run_resources` and `scripts.run_finance`. They accept a common JSON request and emit a qualified result/candidate state; they do not write or approve organization state. Invalid requests return an error. Review their included source and schemas before supplying your own data. This draft has no complete organization walkthrough or automatic skill discovery.

## Review and distribution

Read [distribution status](preview-distribution-status.md) before sharing or reusing the package. Jeremy selected the collection's MIT license and GitHub private vulnerability reporting. The archive includes the license and policy notices. MIT does not relicense third-party material; selected-content rights, the private-reporting setting and publication approval remain separate.

Start the [wiki](../wiki/Home.md) for scope, setup, evidence and remaining decisions. Full roadmap capability and public-v1 acceptance remain separate from this preview. The intended repository is [AgentSustain](https://github.com/jeremylongworth-source/AgentSustain); its visibility/content is not changed by this preparation.
