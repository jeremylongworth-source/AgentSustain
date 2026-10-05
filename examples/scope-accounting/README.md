# Synthetic separate scope accounts

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_scope_accounting examples/scope-accounting/location-request.json
.\.venv\Scripts\python.exe -m scripts.run_scope_accounting examples/scope-accounting/market-request.json
```

The location request consumes an existing fictional 1000 kWh CO2e component with a synthetic 0.5 kg CO2e/kWh factor. The result is 500 kg CO2e. The market request retains that location result and adds two synthetic components: 60% consumption with a zero factor and 40% with a 0.3 kg CO2e/kWh residual factor. The separate market account is 120 kg CO2e. Do not add 500 and 120 together.

Outputs were generated with the actual composition helper and are saved for reproduction. Every numerical factor, source-coverage judgment and market criterion assessment is fictional. These records cannot establish a real contract claim, source completeness, factor eligibility or assurance. No private state is written by either command. Instruction-based source classification and thermal-factor derivation are not demonstrated by these electricity fixtures.
