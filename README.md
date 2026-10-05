# AgentSustain

AgentSustain is an evidence-driven sustainability agent-skill library for business analysis and practical action. Its domain library is called Sustainability Skills in the [roadmap](ROADMAP.md).

Intended users include manufacturers, logistics businesses, commercial facilities, SMEs, and sustainability consultants. The operational MVP connects data, carbon accounting, energy, waste, water, materials, and business-case analysis.

## Current status

Foundation architecture approved by the user on 2026-10-04 at revision f2d0ac9; no individual skills or production workflows are implemented. The mandatory [architecture review](docs/architecture-review.md) gate has passed, authorizing SUS-05 and subsequent development in roadmap order. Architecture tests are not evidence of domain calculation correctness.

Start with [development status](docs/development-status.md), [domain contract](docs/domain-contract.md), and [architecture](docs/architecture.md). `ROADMAP.md` remains authoritative for scope and sequencing. Material changes to the approved architecture contracts require renewed review.

## Validate the architecture pack

Requires Python 3.11 or later. JSON Schema is a development dependency; consumers of future skills need not use Python.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Schemas use JSON Schema Draft 2020-12. Examples are fictional fixtures, not emission factors or advice for a real organization. No license has been chosen yet; public release is gated on the owner's licensing decision.
