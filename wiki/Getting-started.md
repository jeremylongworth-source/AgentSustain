# Getting started

Use Python 3.11 or newer and a complete Git checkout. Router integrity checks require reviewed historical objects, so shallow clones and source-only archives cannot run the full repository suite. No AI-provider account or API key is needed for the deterministic examples.

```powershell
git clone https://github.com/jeremylongworth-source/AgentSustain.git
cd AgentSustain
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m scripts.data_tools examples/preview-conversion.json
```

The fictional conversion reports 2,000 kWh from 2 MWh. It demonstrates unit arithmetic, not savings or emissions.

Run the two-facility, 150-employee fictional food-manufacturer workflow:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_workflow_example examples/food-manufacturer-forward-test-input.json
.\.venv\Scripts\python.exe -m scripts.run_workflow_example examples/food-manufacturer-forward-test-input.json --omit-factor synthetic-factor
```

The runner reconstructs CSV ingestion, supplied fuel conversions and all eight manager stages without an answer key. Results remain qualified and partial. Missing defensible factors withhold inventory/disclosure outputs while supported physical branches continue. Exit 0 means execution completed, not that the organization result is accepted or certified.

On POSIX shells, use `python3 -m venv .venv` and `.venv/bin/python`. Native Linux execution remains unverified; see [platform evidence](https://github.com/jeremylongworth-source/AgentSustain/blob/main/docs/platform-validation.md).

For agent-host use, read the [skill-consumption guide](https://github.com/jeremylongworth-source/AgentSustain/blob/main/docs/skill-consumption.md) and choose the relevant specialist. Repository presence does not prove automatic host installation or discovery. Keep real private evidence outside version control and use fictional examples in contributions.

The separately prepared helper-preview archive uses `requirements.txt`; the full repository uses `requirements-dev.txt`. See [Preview scope](Preview-scope.md).
