# Jurisdiction-module contract

Status: proposed for SUS-18-19. Canada is the reference pack; no regulatory rules are currently implemented.

Canonical location is `standards/jurisdictions/`. Country modules may contain federal and subnational rules. Canadian subject groups are applicability, carbon, climate-disclosure, environmental-claims, energy, waste, procurement and reporting.

Every rule needs jurisdiction ID, official authority/source and clause locator, version, effective-from/to interval, retrieval date, legal status, subject, required company attributes, screening logic, exceptions, uncertainty, and reviewer requirement. Null effective-to means open ended, not permanently current. Proposed rules cannot be treated as law. Recheck official sources at use time when currency matters; preserve the version used in historical results.

Inputs include operating locations, legal entity attributes, size/sector thresholds where relevant and reporting period. Outputs are preliminary applicable/potentially_applicable/not_applicable/undetermined screens, evidence references, missing attributes, basis, uncertainty and review requirements. Insufficient company facts, missing version or conflicting federal/subnational interpretation yields undetermined plus gaps; definitive legal conclusions require legal review.

Acceptance scenarios cover threshold boundaries, missing facts, overlapping jurisdictions, effective dates, amendments and repealed rules. Jurisdiction packs cannot alter neutral calculation schemas or invent factors. Specific Canadian requirements must be researched from official sources during SUS-19 rather than inferred from this design.
