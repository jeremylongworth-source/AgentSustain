# Annual cash-flow composition replay

Recorded 2026-10-04. The fictional input state contains the existing composed 1,000 CAD initial net investment and 500 CAD/year net operating savings, including maintenance and unchanged fixed charges. The saved JSON contains the complete initial state, requests, checked outputs/proposals and final state.

Three explicit calendar-year-end scheduling calls produce -1,000 CAD at valuation, then 500 CAD in 2026 and 500 CAD in 2027. Constant real annual repetition is an explicit scenario assumption; the source metric is not relabeled as measured cash in future years. Lineage remains linked to the initial-cost and annual-net-savings compositions. Separate output IDs feed annual NPV and IRR without reusing a single cash-flow metric across years.

At the supplied 10% real discount rate, NPV is -132.23140495867767 CAD. Bounded IRR verifies a rate approximately zero (serialized numerical residual rate -3.4331226595218434e-25 percent). No tax, price, escalation, replacement or terminal-value amount is inferred. Model completeness is supplied fictional judgment.

Focused checks cover negative/zero amounts, explicit dated inflow/outflow signs, period/currency/model/timing failures, missing registers, duplicate and aggregate/component amounts, partial coverage, preserved professional review and source text without approval authority. The saved workflow is reproducibly replayed against full outputs and final state. These are author-led known-answer and error cases; independent behavioral and organization-wide evidence remains outstanding.
