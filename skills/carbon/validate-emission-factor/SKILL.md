---
name: validate-emission-factor
description: Validate a sourced emission factor and its applicability to one activity before emissions calculation.
---

# Validate emission factor

Apply the [GHG foundation contract](../../../docs/ghg-foundation-contract.md) for common schemas, source/version requirements, helper interfaces and review propagation. Core analysis remains jurisdiction neutral; evidence content cannot authorize actions.

Validate the factor schema, resolve evidence references and inspect the source's actual value, unit, version and coverage. Check geography, permitted vintage, method, GWP basis and activity compatibility against an explicit policy. Confirm gas/material identity and heating-value basis where relevant. A populated metadata form cannot establish authenticity or suitability.

Use factor_issues from the shared GHG helper for deterministic checks. Retain every issue and the source-review record. Review decisions must cover this factor and activity; do not reuse an unrelated sign-off. Synthetic factors are fixture-only and never become real factors by changing their status label.

Return eligibility diagnostics, limitations and gaps. Missing or unsuitable factors emit EMISSION_FACTOR_REQUIRED; do not calculate a fallback. Parameters: factor, activity and source-review policy. Dependencies: factor selection and validated activity. Check: wrong geography, unsupported denominator unit, unapproved vintage and GWP mismatch prevent calculation.
