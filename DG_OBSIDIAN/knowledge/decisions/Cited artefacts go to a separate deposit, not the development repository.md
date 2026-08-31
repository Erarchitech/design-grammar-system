---
type: decision
status: accepted
date: 2026-08-31
tags: [dissemination, open-science, licensing, deposit, itcon, t1]
decision_id: D-C55
supersedes: none
---

# Cited artefacts go to a separate deposit, not the development repository

**Decision.** When a paper cites this project's code or ontology, it cites a **purpose-built deposit
repository**, never `Erarchitech/design-grammar-system`. The development repository is not a
publishable artefact and is not named in any paper.

First applied for T1 (C55, 2026-08-31): `https://github.com/Erarchitech/design-grammar-ontology`,
tag `v1.0.1`.

## Why

The development repository publicly tracks material that must not be openly licensed or pointed at
from a paper under review:

- **539 tracked files** under `DG_OBSIDIAN/` — the PhD knowledge vault, session notes, decisions
- **121 tracked files** under `Publications/` — draft manuscripts including papers currently under
  review, and `01_Comments/` holding review files named after their authors

Two independent failures follow from citing it:

1. **Licensing.** A repository-root licence declares everything in the tree openly licensed. That
   would cover the vault and other people's review comments.
2. **Review exposure.** A reviewer following the citation lands on the manuscript they are reviewing
   and on a colleague's named feedback.

Removing the material from `HEAD` is one commit; removing it from ~1,000 commits of history needs
`git filter-repo` and a force-push that breaks every clone. A separate deposit avoids the choice
entirely, and is what the AVAILABILITY section of these papers already promises — *"deposited at an
open, citable archive"*.

## What the deposit contains

Whatever the paper's own AVAILABILITY section enumerates, and nothing else. For T1 that was the core
ontology module and catalogue, three alignment extensions, the SHACL shape set and disjointness
overlay, four normative specifications, the rule-shape catalogue, the schema migrations, and the
three runtime services — **sources only**, with build output, IDE caches and dependency trees
excluded.

Originals stay in the development repository. The deposit is a copy, not a move.

## Licensing pattern

Two licences, because a deposit holds two kinds of work — following comparable AEC ontologies
(Brick ships schema and code under BSD-3-Clause; ifcOWL declares `cc:license` CC BY 3.0 in its RDF
header):

| Part | Licence |
|---|---|
| `ontology/`, `spec/` | **CC BY 4.0**, declared as a `cc:license` triple *inside each ontology header* so it travels with the file, not only with the repository |
| services, code, `llm/`, `migrations/` | **Apache-2.0** — canonical text, patent grant matters for institutionally funded output |

Copyright names **both the author and the University of Minho** — the work is FCT-funded doctoral
research.

`CITATION.cff` at the root, so GitHub renders a citation block and Zenodo reads authorship when the
DOI is minted.

## Obligations this decision creates

1. **Verify the paper's numeric claims against the deposit before writing the citation**, not against
   the source tree. For T1 this caught a real defect: `ontology/DesignGrammar.owl` — the file a
   reader would take for the core module — yields 143/38/66 and does **not** reproduce Table 3.
   Only `DesignGrammar-V7.owl` does (62/43/68). The deposit ships V7 and its README carries the
   recount commands.
2. **Tag the deposit** and cite the tag. An untagged link is not a reproducible reference.
3. **Archive to Zenodo at acceptance** and swap the reference's URL for the minted DOI — ITcon's
   author guide requires a DOI wherever one exists.
4. **Secret-scan before publishing.**

## Consequences for the manuscript

Any sentence saying the runtime services live *"in the same repository"* becomes false and must say
*deposit*. Bare URLs in AVAILABILITY become author–date citations once a reference entry exists.

## Related

- [[../../dissemination/revisions/T1 R14.3 — R14.4 package port and C45 resolution|T1 R14.3 revision record — PART 4]]
- [[../../sessions/2026-08-31 T1 R14.3 — C55 repository reference and the ontology deposit|Session — C55 and the deposit]]
- [[Word silently reverts scripted docx edits while the file is open]]
