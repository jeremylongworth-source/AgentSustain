# Canonical catalog byte replay

The initial reporting captures used SHA-256 pins of CRLF worktree catalog files, while Git stored LF bytes. Fresh checkouts could therefore reject otherwise identical catalog JSON. A scoped `.gitattributes` rule now enforces LF for framework JSON; no global Git setting changes.

The companion JSON records all three old/new pins and confirms unchanged parsed catalogs and exact reviewed Git blob bytes. Original author and independent captures retain their byte hashes. Three actual CLI executions match complete helper outputs: author mapping, authored version diff using the corrected mapping proposal, and parent replay of the independent mapping. Only catalog pin representation changes in parameters and serialized diagnostics. Every original quantity, boundary, period, fitness judgment, gap and review survives. The independent reader was not rerun.

Three regression checks cover actual temporary Git commits/clones with autocrlf true and false, complete saved canonical helper replay with source-state and exact diff handoff preservation, and rejection of old CRLF pins. Tests run on Windows; native Linux runtime validation remains open. Scope/rights/applicability, broader domain coverage and all professional/owner/release requirements remain open.

Validation: 13 focused tests passed in 7.031 seconds; the final repository suite passed 505 tests in 286.975 seconds, including architecture checks. See `sus17-canonical-catalog-validation.json` for exact current hashes and scope. No skill instruction or normative catalog content changed; no new independent reading or publication authority is claimed.
