# Fictional baseline, KPI and target workflow

The [complete capture](sus15-target-workflow.json) contains three common-envelope requests, actual helper outputs and checked state proposals. All input data are fictional. `tests/test_strategy.py` reruns every saved request and compares the entire output, in addition to direct arithmetic/adversarial tests and a CLI replay.

1. Select the sourced fictional plant's 1,000 kWh annual electricity metric as a conditional baseline. Other plants and fuels remain excluded, selected coverage is incomplete, and the recalculation policy is recorded without historical replacement.
2. Define electricity intensity against 100 equivalent fictional completed units. The definition retains kWh/count, the absolute baseline, matched service evidence, owner and annual monitoring basis; no monitoring starts.
3. Propose a supplied 20% intensity reduction for calendar year 2030: baseline 10 kWh/count → endpoint 8 kWh/count. The proposed difference is 2 kWh/count. No future production quantity, absolute future electricity, annual trajectory or delivery feasibility is inferred.

A separate known-answer check uses an absolute definition: the same supplied 20% objective gives 800 kWh; a supplied 750 kWh endpoint remains 750 kWh. Conversion, zero endpoint, leap-year calendar windows and source changes are checked. Unknown/zero/negative or unsuitable service denominators, missing factors, unsupported offsets, mismatched source/accounting scope, overlapping quantities, wrong units and incomparable commitment periods cannot produce a target metric.

All old gaps, assumptions and open reviews survive. Target adoption, implementation, science-based/net-zero validation and claims remain false; a new professional review stays open. These author-led executions demonstrate the bounded method, not source authenticity, target credibility, organization-wide strategy completion or general reliability. The source-reading evaluation is recorded separately.
