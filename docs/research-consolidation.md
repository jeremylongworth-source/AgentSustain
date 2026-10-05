# SUS-00: Research consolidation

Status: initial architecture research, not completed domain-methodology research. Checked 2026-10-04 (America/Toronto).

## Evidence

ROADMAP.md is the supplied scope authority. Initial workspace contained only that file. Authenticated GitHub inspection established that `jeremylongworth-source/AgentSustain` is private and empty; unauthenticated web access returned 404. The local Git repository now points to that remote. No customer research, datasets, inherited code or emission factors were supplied.

Primary-source orientation:

- [GHG Protocol standards and guidance](https://ghgprotocol.org/standards-guidance) distinguishes corporate, value-chain and scope 2 resources. This supports separate method/version selection; it does not validate any factor or calculation in this pack.
- [IFRS sustainability supporting materials](https://www.ifrs.org/supporting-implementation/supporting-materials-for-ifrs-sustainability-disclosure-standards/) provides distinct IFRS S1 and S2 implementation resources. Adapter mappings must pin the actual applicable issued version before use.
- [GRI standards](https://www.globalreporting.org/standards) is the official entry point for GRI source research. No GRI compliance determination or licensed-text reproduction is included.

## Design inferences and assumptions

JSON Schema is proposed for portable machine-readable contracts. A Python development test harness is proposed for local validation; it is not a core runtime requirement. User needs and MVP scope come from the roadmap rather than interviews. Research orientation is sufficient to draft architecture, not to approve regulatory, accounting or claims logic.

## Follow-up research by wave

SUS-06-08: pin inventory, scope 2/3 and GWP methods and authoritative factor sources with geographical and temporal applicability. SUS-09-12: establish unit bases, operational calculations and finance conventions. SUS-16: distinguish screening from specialist climate modeling and identify hazard-source licenses. SUS-17: retrieve actual framework versions/clauses and reproduction conditions. SUS-19: research official Canadian rules with effective dates and applicability facts. SUS-20: pin claims evidence and review requirements. Retain citations and uncertainty with every adopted rule.
