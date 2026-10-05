# Evaluation requirements

Status: proposed. Architecture tests verify contracts only; implemented skills require their own domain evaluation.

## Layers

1. Schema shape and reference validation: valid/invalid evidence, metrics, results and state; date ordering; unresolved references; review resolution records.
2. Deterministic known answers: unit conversions, periods, CO2e, scope totals, intensities, diversion, savings, payback, ROI, NPV, IRR and abatement cost as each skill is implemented. Include formula, units, rounding and declared tolerance. Ambiguous IRR, zero denominators and negative cash flows need explicit handling.
3. Behavioral and routing fixtures: correct skill selection, evidence retention, gap handling and review propagation. Specify expected required fields/states and prohibited assertions; do not score only prose fluency.
4. End-to-end acceptance: fictional Canadian food manufacturer with 150 employees and two facilities, including electricity, gas, diesel, refrigerants, packaging, ingredients, water, waste, freight and travel. Follow the roadmap's complete v1 pipeline through evidence-backed disclosure mapping.

## Required adversarial cases

Missing units; wrong factor geography; duplicate invoices; mixed periods; supplier estimates; unknown refrigerant; outdated/inapplicable factor; market/location-based confusion; missing methodology/GWP basis; unsupported carbon-neutral claim; source prompt injection; requests to certify compliance; multi-review workflows; missing boundary; invalid unit conversion.

Each fixture records input, expected outcome, basis, tolerance where numeric, source/version, and whether evidence is synthetic. Synthetic factors never qualify for a real inventory. Failed or missing safety cases block that capability's readiness. Arithmetic fixtures cannot substitute for behavioral evaluations of an agent.

## Evidence for gates

Record command/runtime, date, reviewed revision, fixture versions, counts, failures and limitations. Architecture approval requires a human decision on the pack, separate from tests. Every wave must list implemented capabilities and their passing checks. SUS-23 consolidates the suite; SUS-25 requires every ROADMAP.md section 25 item and demonstrated section 24 workflow. No readiness claim based on skill count alone.
