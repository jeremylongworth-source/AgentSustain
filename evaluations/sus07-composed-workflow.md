# SUS-07 composed helper workflow

Date: 2026-10-04. Base implementation: ea9b253 plus source-classification work in this increment. The JSON capture preserves initial state, supplied source facts, each invocation's parameters, actual helper results, proposal reasons, domain result references and final state.

Both classification workflows identify the controlled boiler as scope 1 and consumed purchased electricity as scope 2. The lease lacks operational-control facts and remains unknown with an open scoped professional review. The assessment does not infer control from ownership or lease labels, modify the organizational boundary, or classify the operation into a scope 3 category.

The explicit synthetic gas factors yield 20 kg CO2e for CO2 and 5 kg CO2e for CH4; scope 1 composition sums their disjoint gas coverage to 25 kg CO2e. The electricity component yields 500 kg CO2e. Separate location and market accounts each retain 500 kg CO2e; the market account discloses absent residual mix and the grid-factor fallback. These alternatives are not summed. All calculations remain partial because leased-operation emissions are unresolved; no missing quantity becomes zero.

tests/test_sus07_workflow.py reruns all eight helper calls from the initial state, compares emitted results and proposed state with the capture, and checks known answers and retained obligations. This is stronger than replaying saved envelopes alone, but the source facts and eligibility judgments were supplied by the author. It does not test agent extraction/reasoning independently, authenticate source/control facts, supply real factors, or establish inventory completeness or assurance. Purchased thermal-factor derivation and broader behavioral evaluations remain additional work.
