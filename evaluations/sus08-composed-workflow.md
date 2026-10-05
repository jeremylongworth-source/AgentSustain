# SUS-08 initial composed workflow

Recorded 2026-10-04 against base 62c79a9 and this increment's scope 3 helpers. The JSON artifact includes initial state, four operation requests/results and final state. It consumes the previous scope 1/2 workflow with its unresolved leased operation and open professional review.

An explicit fictional 100 kg purchased-material activity and synthetic 2 kg CO2e/kg aggregate lifecycle intensity yield a category 1 subtotal of 200 kg CO2e. The selected inventory combines 25 kg direct emissions, one 500 kg location-based scope 2 account and the 200 kg category 1 account, yielding 725 kg CO2e. The market account remains in history but is not added. Category 8 is screened as unknown because leased control is unresolved. Every step remains partial; the leased operation is never converted to zero or automatically moved into scope 3.

The workflow regression test reruns all four operations, rechecks the inventory's underlying component totals and compares the full final state. Category calculation and inventory composition are also reproduced through common-request CLI entrypoints. Category/discriminator tests cover all 15 category labels, outbound purchased freight, tier-2 transport and lease exclusion prerequisites. Error cases cover missing factors, lifecycle basis, source/context overlap, ordinary-mode fixture rejection and tampered subtotals.

All data, factors, category screening and applicability judgments are author supplied and fictional. This is deterministic helper evaluation, not independent extraction/classification, proof of minimum-category coverage, assurance or an organization-wide finished product. Specialized category derivation and inventory comparison/ranking execution remain work.
