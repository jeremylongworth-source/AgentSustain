# AgentSustain

AgentSustain is an evidence-driven sustainability agent-skill library for business analysis and practical action. Its domain library is called Sustainability Skills in the [roadmap](ROADMAP.md).

Intended users include manufacturers, logistics businesses, commercial facilities, SMEs, and sustainability consultants. The operational MVP connects data, carbon accounting, energy, waste, water, materials, and business-case analysis.

## Current status

Foundation architecture draft; no individual skills or production workflows are implemented. [Architecture review](docs/architecture-review.md) is the mandatory gate before SUS-05. An architecture validation pass is not human approval or evidence of domain calculation correctness.

Start with [development status](docs/development-status.md), [domain contract](docs/domain-contract.md), and [architecture](docs/architecture.md). `ROADMAP.md` remains authoritative for scope and sequencing. Proposed conventions in the architecture pack require review.

## Validate the architecture pack

Requires Python 3.11 or later. JSON Schema is a development dependency; consumers of future skills need not use Python.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Schemas use JSON Schema Draft 2020-12. Examples are fictional fixtures, not emission factors or advice for a real organization. No license has been chosen yet; public release is gated on the owner's licensing decision.
