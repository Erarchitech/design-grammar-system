---
tags: [business, audience, personas]
date: 2026-04-05
---

# Target Audience is Architects and Urban Planners

## Primary Users

- **Architects** — need to verify building designs against regulatory constraints
- **Urban planners** — define design grammars (rules) for districts/zones
- **Computational designers** — use Grasshopper/Rhino for parametric modeling

## User Workflow

1. **Planner** defines rules in the web UI (NL text → graph)
2. **Architect** loads rules in Grasshopper, connects to their Rhino model
3. **Grasshopper plugin** binds model geometry to rule variables
4. **Validator** evaluates rules, shows pass/fail per building element
5. **Model Viewer** provides 3D visualization of validation results

## Assumptions

- Users have Rhino 8 + Grasshopper installed (for validation workflow)
- Users have basic understanding of design constraints (height limits, setbacks, etc.)
- Web UI should be accessible without technical knowledge
- Self-hosted deployment (Speckle, Neo4j, etc.) managed by IT or the consulting firm

## Related

- [[Design Grammars automates architectural compliance checking]]
- [[Product bridges natural language rules to graph-based validation]]
