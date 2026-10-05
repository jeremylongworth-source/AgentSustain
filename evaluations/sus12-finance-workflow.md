# SUS-12 initial financial calculations

Recorded 2026-10-04 against 06eee96 and this increment. Three actual helper calls with full result history and proposed states are saved and rerun by regression.

Fictional investment: CAD 1000 at 2025 year end. Explicit constant annual net savings: CAD 600/year. The two-year undiscounted net gain after investment is CAD 200. Simple payback is 1.6666667 years and horizon ROI is 20%. Signed end-of-year cash flows (-1000, 600, 600) at a supplied 10% real discount rate yield NPV CAD 41.32231405. The rate is fixture input, not a recommended default.

Tests retain negative ROI/NPV, accept zero discount, block nonpositive annual savings, reject mismatched currency/rate bases and periods, require projected source assumptions and preserve review/gap obligations despite instruction-like text. Payback beyond the horizon is qualified. These prove supplied arithmetic and definition checks, not model completeness, valid engineering benefits, accounting assurance or investment approval. Independent agent reasoning and wider economic methods remain further work.
