# SUS-08 inventory analysis cases

Recorded 2026-10-04 against 7d43987 plus this increment's inventory analysis implementation. The JSON artifact stores two complete common requests, actual results and proposal reasons. Their source data and review judgments are fictional.

The comparison uses preserved 2024 and 2025 snapshots with the same selected location-based electricity coverage and synthetic intensity. The inventories contain 500 and 400 kg CO2e respectively. The helper revalidates each inventory, checks preserved prior lineage and an explicit comparability record, then reports -100 kg CO2e and -20%. Full calendar years remain comparable across the leap-year difference without annualization. Both accounts are partial because direct-emissions coverage is missing. The result is not evidence of attributable or verified emissions reductions.

The source ranking consumes the existing 725 kg partial scope 1/2/3 fixture. Electricity contributes 500 kg, purchased materials 200 kg and the boiler's disjoint gas components 25 kg. Shares use the selected 725 kg inventory subtotal as denominator. The unknown leased operation and open professional review remain unresolved; these are shares of supported selected emissions, not a complete organization's footprint or reduction potential.

tests/test_inventory_analysis.py reruns saved results and checks known answers, zero denominators, full calendar cadence, review requirements, preserved history, changed boundary/gas/category coverage, scope 2 method changes, source allocation and CLI operation. Source facts, applicability and review authenticity are not independently evaluated. The helper cannot reconcile or restate a changed inventory automatically.
