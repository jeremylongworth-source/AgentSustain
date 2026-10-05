# Skill naming and identification

Status: proposed. Use lowercase kebab-case action-object names from ROADMAP.md. Names are globally unique even when families differ. Path: `skills/{family}/{name}/SKILL.md`. Family membership and implementation wave are separate metadata; taxonomy IDs SUS-01 through SUS-16 must not be confused with development-wave IDs SUS-00 through SUS-25.

Avoid umbrella consultant prompts. Each atomic skill declares a bounded operation, prerequisites, evidence contract, method, output envelope, gap behavior, review states and validation scenarios. Composed workflows belong in `skillsets/` and call named dependencies.

`establish-baseline` composes `build-sustainability-baseline`; `define-kpis` selects definitions whereas `calculate-sustainability-kpi` computes them. Boundary mapping describes organizational context; GHG boundary definition adds inventory-specific choices. Hotspot skills operate on their named domain; they cannot silently recompute an inventory.

Evidence, results, facilities and entities use stable string IDs rather than display names. IDs cannot be reused to replace historical evidence. Framework/jurisdiction modules include explicit version and effective interval independently of core contract version.
