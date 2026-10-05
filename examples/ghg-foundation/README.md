# Synthetic GHG foundation example

Run from the repository root with the configured Python environment:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_ghg_calculation examples/ghg-foundation/synthetic-request.json
```

The request explicitly enables fixture mode. Its hypothetical factor is 0.5 kg CO2e/kWh, supplied solely for arithmetic tests, not representative of any actual grid. The helper calculated 1000 * 0.5 = 500 kg CO2e and saved the labeled envelope/proposal in synthetic-output.json. Both activity and factor-source evidence references are preserved.

factor-required-output.json records an actual helper invocation with a missing factor ID: EMISSION_FACTOR_REQUIRED, no emissions metric, and a data gap. Disabling fixture mode on the supplied synthetic request also blocks calculation.

These outputs are calculations on fictional records. They do not demonstrate authentic sources, real factor selection, inventory completeness, assurance or scope 1/2/3 accounting. They must not be used for real environmental claims.
