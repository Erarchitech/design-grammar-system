# T1_ITcon_DG_Draft R15.2 — Revision Plan

**Status: CLOSED — fully applied 2026-09-06.** R15.2 is at `sha256:6b64cc92e672` after four apply passes (E1–E24). The applied record is `T1_ITcon_DG_Draft_R15.2_revision-summary.md`, which is authoritative for this round; what follows is the proposal record, kept for audit.

**Superseded status line:** `T1_ITcon_DG_Draft_R15.2.docx` **now exists** and carries **E1–E6 and E9**, applied outside this session on 2026-09-06 at 10:15. It is the working file from here on; R15.1 is closed as an original. **E7, E8, E10a, E10b, E11 and E12 remain unapplied** and all re-verify against R15.2 at exactly one match. Two defects in the applied text need correcting — **E13, E14**. Full account at **§6.14**.

**Gate re-fired 2026-09-06.** The author reviewed the approved package and required four things: remove statements repeating claims already made elsewhere in the manuscript; replace the ambiguous word *discipline*; justify the BOT alignment or drop it; and add a control-scope open question with a Lawson citation. E1, E5, E7 and E10b are rewritten, E11 and E12 are new, and the label returns to **awaiting gate**. Retired reasoning is kept at §6.9.

**Round is open for other sessions.** The author is adding further labels from a concurrent session, and everything will be applied together in one pass. Read §2 before claiming anything.

---

## 1. Round settings — the entry interview, recorded

A resuming session, or a **second session joining this round**, reads this block and adopts it rather than re-asking. Confirm once with the author — *"joining under these settings, still right?"* — and proceed.

| # | Question | Answer | How derived |
|---|---|---|---|
| 1 | In place, or a copy at a new revision? | **copy as `R15.2`**, base `T1_ITcon_DG_Draft_R15.1.docx` | Author's instruction, 2026-09-05: *"Create plan for R15.2 next to R15.1 file"* |
| 2 | Comprehensive sweep, or pointwise? | **pointwise**, multi-label — `AU-R151-ONTO` here, further labels expected from a concurrent session | Author: *"in other concurrent session I will add other fixes to this plan later on and then apply them together"* |
| 3 | Comment source | `T1_ITcon_DG_Draft_R15.1.docx` — **.docx with embedded comments**; comment `w:id=20`, quoted by the author in-session | `extract_comments.py` returned 11 anchored comments, 4 tracked changes, 0 highlighted runs |
| 4 | Context in scope | `DG_OBSIDIAN/` · prior revisions R14.2–R15.1 with their summaries and logs · `Publications/survey/` · project repository root | All probed paths resolved |
| 4b | Bound to project-stage data, or theoretical? | **theoretical** | Author's choice, carried from R15.1 and re-confirmed this round. No deployment status may be stated; no claim may rest on repository state |
| 5 | New plan + summary, or update existing? | **new** — this file. Summary `T1_ITcon_DG_Draft_R15.2_revision-summary.md` is created at apply | R15.1's plan and summary are closed (PROMOTED 2026-09-02) |
| 6 | Response letter? | **no** | Matches every prior round |

**Recorded:** 2026-09-05 · **By:** Evgenii (r.prishchep@genpro.life) · **Session:** `s-29130ee1`

**Stages disabled by these answers, not skipped:** three-analyst comprehensive fan-out and full 14-field register build (Q2 = pointwise); all implementation verification and every repository claim as a *paper* claim, and project artifacts as a write target (Q4b = theoretical — see §9, where the code change request is recorded as a roadmap item and explicitly not a write); response letter and the eleven-check `final-revision-validator` (Q6 = no). The fixed verification checklist in §6.10 runs regardless.

### 1.1 Constraint documents

| Document | What it constrains | Labels affected |
|---|---|---|
| `DG_OBSIDIAN/dissemination/consistency-map.md` (series coherence map) | Which concepts T1 may **define** vs merely reference. Row `OntoGraph/Metagraph schema` = T1 **defines** | `AU-R151-ONTO` — clear. The Ontograph's layer scope is T1's to define |
| `ontology/DesignGrammar-BOT-extension-V7.owl` (deposited, R14.4) | The SKOS match vocabulary and its additive-not-substitutive semantics. The paper may not contradict what is deposited | `AU-R151-ONTO` — honoured; E2 keeps the mechanism and changes only its scoping words |
| Author directive, R14.2 D4 | *"Don't state deployment status in the paper. This is purely theoretical claim."* | All labels. Governs the requirement-voice wording in E7 |

---

## 2. Claims table — parallel sessions

The round's state and its coordination surface. Every session working this revision reads and writes this table.

| Label | Session | Status | Anchors | Heartbeat |
|---|---|---|---|---|
| `AU-R151-ONTO` (E7, E8, E10a, E10b, E11, E12) | `s-29130ee1` | **applied** 2026-09-06 | 208, 300, 333 | 2026-09-06 |
| `AU-R151-ONTO` (E1–E6, E9) | *not this session* | **applied** to R15.2 at 10:15 | 82, 113, 127, 173 | — |
| `AU-R151-FIX` (E14, E1b, E5b, E15) | `s-29130ee1` | **applied** 2026-09-06 | 82, 113, 173 | 2026-09-06 |
| `E13` — ¶127 doubled verb | — | **fixed manually by the author** before this apply | 127 | 2026-09-06 |
| `AUTHOR (manual)` | — | detected by diff | 82, 113, 127, 173 — the applied edits above; no other divergence from R15.1 | 2026-09-06 |
| `AU-R151-TOPO` (T1–T20) | `s-aadf61bc` | **drafting — at the gate, nothing applied** | §2.2 (×7 incl. Fig 2 caption), §3.2, §5.4, §6.1 (×4), Table 1, Availability (×2), Annex C, Conclusion (×2) | 2026-09-07 |

**`AU-R151-TOPO` overlap declaration** (per §2.0 rule 6). It touches **¶113 and ¶173**, both held by `AU-R151-ONTO`, and **¶300**, held by it too — but **every one of its twenty before-strings was verified against applied R15.2 at exactly one match**, so no in-flight string is contested. Four of its edits **amend text `AU-R151-ONTO` applied on 2026-09-06**: T5 re-targets E2's SKOS object, T8 replaces E7's coverage passage, T10 replaces E10b's closing clause, and T18 rewrites E10b's emergent-terminology sentence. That is amendment of applied text rather than collision with a pending string.

> **Authorised by the author, 2026-09-07**, who owns both sessions' work. T5 and T18 touch binding records — `AU-R143-C01`'s additive-match semantics and E10b's Lawson argument respectively — and both preserve the substance; their rationale is kept visible under §6A.7.

⚠ **The working file changed.** Every remaining before-string now anchors against **`T1_ITcon_DG_Draft_R15.2.docx`**, not R15.1. A joining session must re-verify its own anchors against R15.2 before drafting: seven of the twelve strings in this plan no longer exist in the working file, because their edits are already in it.

### 2.0 Joining this round — read first

1. Adopt §1 as written. Do **not** re-run the interview, and in particular do not re-decide Q1: this round produces **`R15.2`**, by copy from R15.1. Two sessions disagreeing about which file they are producing is not a merge conflict, it is two different papers.
2. Take a label nobody has claimed. Naming: `AU-R151-<TOPIC>` or `AU-R151-C<nn>` — base revision is the one **under review** (R15.1 → `R151`), per the round's existing `AU-R151-XREF` precedent.
3. Add your row here with your session id and status `drafting`. Never edit or release another session's row.
4. Snapshot your baseline to `Publications/work/baselines/<label>.json` **once your anchors are known**, not at session start — a resolution routinely pulls a pre-existing claim into scope mid-round.
5. Add a `## 6.x` block for your label. Do not renumber existing blocks.
6. **Check §6.4 before drafting.** `AU-R151-ONTO` holds seven paragraphs. If your edit touches 82, 113, 127, 173, 208, 300 or 333, say so rather than drafting over it.

### 2.1 No session holds a copy

> The file on disk is always the base. A session holds a **plan**, and a plan is a *text transformation* — exact old string to exact new string.

Paragraph numbers below are **reporting labels only**, never what a replacement matches on. Index drift is harmless; text drift is exactly the collision signal, and `docx_replace.py` will find zero matches and refuse to write. That refusal is a safety feature — never pass a flag or a loosened pattern that writes through a mismatch.

### 2.2 Three-way overlap check

```
my anchors  INTERSECT  ( other sessions' claimed anchors  UNION  author-changed paragraphs )
```

Baseline for `AU-R151-ONTO`: `Publications/work/baselines/AU-R151-ONTO.json` — per-paragraph SHA-256 for 82, 113, 127, 173, 208, 300, plus the whole-file hash and package part count. **Re-snapshot to add ¶333** when the reference insertion (E12) is approved.

| Run | When | Result | Action |
|---|---|---|---|
| 1 | 2026-09-05, at approval | **empty** — no peer claims existed; all 11 before-strings verified at exactly 1 match | proceeded |
| 2 | 2026-09-06, on discovering R15.2 | **NON-EMPTY** — ¶82, ¶113, ¶127, ¶173 changed by a writer other than this session | **Stopped and re-anchored.** E1–E6 and E9 recognised as applied; the remaining six re-verified against R15.2 at 1/1; E13 and E14 raised against defects in the applied text; gate re-fired |
| 3 | 2026-09-06, immediately before the apply | **empty** — only ¶127 had moved since run 2, by the author, and it anchors none of the remaining edits | proceeded |

Run 2 is the one that matters: the wait for the concurrent session's labels is precisely the window in which the author saves in Word. Non-empty means **stop, name the conflicting session or the author's edit, re-anchor, and re-fire the gate** — never apply only the non-overlapping part.

### 2.3 Live-file guard

| Label | Run | `~$` lock | mtime / size | Verdict |
|---|---|---|---|---|
| `AU-R151-ONTO` | at drafting, 2026-09-05 | **PRESENT** — `~$_ITcon_DG_Draft_R15.1.docx`, 08:21 | base `sha256:530d04f30600baad`, 42 package parts | **BLOCKED** — Word appears open. Author to close before any apply |
| `AU-R151-ONTO` | 2026-09-06, on discovering R15.2 | **PRESENT** — `~$_ITcon_DG_Draft_R15.2.docx` | R15.2 `sha256:ce5ece98c15e`, 42 parts, 359 paragraphs, 117 301 chars | **BLOCKED** — R15.2 is open in Word. Nothing may be written to it |
| `AU-R151-ONTO` | 2026-09-06, before the apply | **absent** — Word closed | R15.2 `sha256:b8e98229b065` at read, unchanged at write | **PASS** |

`Publications/` also holds five stale locks from July–August (R6, R9, R10.1, R13, R14.1), so a `~$` file is not by itself proof of an open session — but this one is timestamped sixteen minutes before comment 20 was written, so treat it as live until the author says otherwise.

### 2.4 Advisory lock

`scratchpad/T1_ITcon_DG_Draft.lock` — session id, acquired-at, operation. Held for **seconds**, only around the apply:

```
acquire -> live-file guard -> three-way check -> re-anchor if moved
        -> re-fire gate if changed -> apply -> update plan + summary -> release
```

| Acquired | Session | Operation | Released |
|---|---|---|---|

Stale locks and stale claims are **reported to the author, never auto-stolen**. Two Claude Code sessions are separate processes whose only shared state is the filesystem.

---

## 3. Capability probe results

| Capability | Verdict | Evidence | Consequence if unavailable |
|---|---|---|---|
| `paper-revision` skill | **Available** | `C:\Users\Admin\.claude\skills\paper-revision\` | Hard stop — no manuscript write |
| `extract_comments.py` | **Available, exercised** | Returned 11 comments / 4 tracked changes / 0 highlights on R15.1 | Comment source falls back to raw XML |
| `docx_replace.py` | **Available, not yet exercised this round** | Present in `scripts/` | Hard stop — no controlled replacement |
| `validate_docx.py` | **Available, not yet exercised this round** | Present in `scripts/` | Verification row 6 Unverifiable |
| `figure_print_size.py` | Available, not needed | Present in `scripts/` | Not applicable — no figure work this round |
| DOCX comment preservation | **Not yet verified this round** | Must run a no-op round trip before the first write | **Hard stop before writing** |
| Threaded comment replies | Precedent exists | R14.4 wrote `paraIdParent` replies; comment 20 needs one | Standalone traceability comments only |
| Tracked-changes preservation | **Not yet verified this round** | 4 `w:ins`/`w:del` by Bruno present, two of them inside anchor ¶208 | Stop and offer alternatives |
| Citation / bibliography fields | **Not yet verified this round** | | Hard stop — flattening breaks the bibliography |
| Draw.io MCP | Not applicable | No figure work this round | — |
| Perplexity | Not required | No literature claim this round | — |
| DOI resolution | Not required | No new citation proposed (§10) | — |
| Project repository (Q4b = theoretical) | Read for §9 only | Read-only; no paper claim rests on it | — |
| `Publications/survey/` | **Available** | `corpus_log.md`, `backlog.md`, `synthesis/`, `inventory/` all present | Measure-first unsatisfiable |
| Obsidian vault | **Available** | `DG_OBSIDIAN/` | Vault-only decisions become evidence gaps |

**The three "not yet verified" rows are a gate on the first write, not on this plan.** Run the no-op round trip before applying anything, and record the before/after counts in the summary.

---

## 4. Source manifest and the gate artifact

| Type | Relative path | Format | SHA-256 (first 16) | Notes |
|---|---|---|---|---|
| Base manuscript | `Publications/T1_ITcon_DG_Draft_R15.1.docx` | DOCX, 42 parts | `530d04f30600baad` | **Original — must be unchanged at round close** |
| Comment source | same file, `word/comments.xml` | — | — | Comment `w:id=20`, unresolved |
| Prior summary | `Publications/T1_ITcon_DG_Draft_R15.1_revision-summary.md` | MD | — | Closed; read for prior commitments |
| Deposited ontology | `ontology/DesignGrammar-BOT-extension-V7.owl` | OWL | — | Constrains E2 |
| Baseline | `Publications/work/baselines/AU-R151-ONTO.json` | JSON | — | Written 2026-09-05 by `s-29130ee1` |

### 4.1 The copy is the gate artifact

Q1 = copy, so the gate signal **is** the copy at the next revision name:

```
Publications/T1_ITcon_DG_Draft_R15.1.docx  ->  Publications/T1_ITcon_DG_Draft_R15.2.docx
```

**Done 2026-09-06 at 10:15, outside this session.** R15.2 exists at `sha256:ce5ece98c15e`; R15.1 has been re-hashed at `530d04f30600baad` and is confirmed unchanged. The copy can no longer serve as the gate artifact for what remains, so the backup does:

```
scratchpad/T1_ITcon_DG_Draft_R15.2_BACKUP_before_AU-R151-ONTO.docx
```

Taken at approval, before the first write to R15.2, never earlier.

---

## 5. Comment index

| Label | Word id | Location | Category | Plan status |
|---|---|---|---|---|
| `AU-R151-ONTO` | 20 | §6.1 ¶300, anchored on two sentences | methods / ontology layer scope | **Applied** 2026-09-06 — comment 20 **still unresolved in the file**, see §6A.4 |
| `AU-R151-TOPO` | 21 | §6.1, the sentence *"The second follows from the first…"* | methods / module architecture and exchange alignment | **Drafted, at the gate** — §6A |

Carried over, **not in scope this round**: comment 16 (`AU-R151-XREF`, unresolved but already actioned in R15.1); `BF-R15-Ct` (comments 1, 2 — validation time *t*), deferred since R15.1; the `SEQ`-field request, open since R14.2 in its 6th round.

---

## 6. `AU-R151-ONTO` — Ontograph layer scope

**Author's comment (verbatim, Word id 20, Evgenii Ermolenko, 2026-09-05T08:37:00Z, unresolved):**

> "Don't agree with this statement. This question is not just related to the concept misleading between different projects, but also within a single project, as all projects share classes within the graph maintained by organisation. Accordingly, Ontograph is cross-project layer. LLM Agent is used to analyse and detect existing classes with similar semantic meanings when ingesting new rule, so automatic alignment is applied."

**Anchor:** §6.1 `[P300]`, on the two sentences beginning *"Ontograph classes are minted per project…"*
**Pulled into scope by the sweep:** `[P82]` §2.1, `[P113]` §2.2, `[P127]` §3.2, `[P173]` §3.6, `[P208]` §4
**Claimed:** 2026-09-05 by `s-29130ee1`

### 6.1 The model, as the author corrected it

The comment as written asserts more than the paper can carry, and the author refined it during the round. The model to be stated is:

- The **Ontograph is a cross-project layer** — a vocabulary the organisation maintains, shared by all its projects. Ontograph entities do **not** carry project identity.
- **Project identity is carried by the referring nodes** — the Metagraph atoms that ground themselves in a class through `REFERS_TO`, and their counterparts in the other project-scoped layers.
- **No duplication is assumed.** Semantic matching at ingest is performed by an agent and **approved by a human**, so a concept is declared once.
- **Cross-project reach runs through the shared class, not through the rules.** Rules stay project-scoped and are not queried from another project — the label filter sees to that. A query entered at a shared term reaches the instances referencing it in every project, which is what lets two projects' facade rules be compared and a rule then imported from one into the other.
- **The organisation is the boundary.** The graph attaches to a company's CDE and its vocabulary is aligned within it; distribution beyond that CDE is an open question, and §6.1 should raise it.

### 6.2 Evidence

Q4b = theoretical, so **none of this enters the manuscript**. It is recorded because it decides what the paper may *not* say, and because it drives §9.

| Item | Source | Status | Bearing |
|---|---|---|---|
| OntoGraph nodes carry `project` and every read path filters on it | `data-service/dg_context.py:318`; `DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs:11`; `ui-v2/src/lib/graphApi.js:43`; n8n `Annotate Graph Props` | **Verified** | The comment's cross-project claim is not the current code. Under Q4b nothing is claimed either way; §9 records the gap |
| `MERGE` on `iri` alone, then `SET n.project` | `cypher_template.txt:175`; `training/dataset_schema.json:42` | **Verified** (semantics **inferred**) | Last-write-wins reassignment, not sharing. Inference from Cypher semantics, not asserted by any doc |
| Existing entities injected at ingest with *"you MUST reuse these, do NOT create duplicates"* | n8n `rules-to-metagraph.json`, `Build LLM Prompt` | **Verified** | Reuse is prompt-level and project-scoped; exact-IRI MERGE makes it idempotent |
| No similarity detection anywhere in the ingest path; embeddings forbidden | `dg_context.py:32`, `:286`, `:467` (CTXA-05) | **Verified** | *"detect existing classes with similar semantic meanings"* is not implemented. The paper states the discipline, never its deployment |
| `AU-R143-C01` — additive graded SKOS match, never substitution | R14.4 summary §2; `ontology/DesignGrammar-BOT-extension-V7.owl` | **Verified** | Binding. E2 preserves it |
| R14.4's §6.1 replacement never reached the R15 lineage | R15.1 §2.2 carries R14.4 wording; §6.1 carries the pre-R14.4 text | **Verified** | Why §2.2 and §6.1 disagree. Superseded by this round |
| Vault records cross-project sharing as *"could eventually be shared"* | `DG_OBSIDIAN/knowledge/decisions/Project isolation uses property filtering not separate databases.md` | **Verified** | Unrealised potential, not a decision. Becomes stale if §9 lands |

### 6.3 Cross-section consistency sweep

| `[Pnn]` | § | Verbatim | Relation |
|---|---|---|---|
| 82 | 2.1 | *"the Ontograph contains a project's domain vocabulary"* | **CONTRADICTS** |
| 113 | 2.2 | *"a domain class minted per project… keeps its project identity"* | **CONTRADICTS** (scoping words only; the SKOS mechanism is correct) |
| 127 | 3.2 | *"isolated per project via a project label"* | **CONTRADICTS** |
| 127 | 3.2 | *"REFERS_TO grounds every Metagraph atom in Ontograph vocabulary"* | **PRESUPPOSES** — the bridge that carries the corrected model |
| 173 | 3.6 | *"All nodes carry a project label"* | **CONTRADICTS** |
| 173 | 3.6 | *"Extensions are engaged automatically… assigns them to the appropriate external classes"* | **BROADER** — an automatic-alignment claim of the same family |
| 173 | 3.6 | *"accumulated rules remain queryable across projects"* | **CONTRADICTS** the corrected model — rules are label-filtered; the vocabulary is what crosses |
| 208 | 4 | *"resolved against the Ontograph entities the project already declares"* | **CONTRADICTS** — and it is where resolve-then-mint is actually described |
| 208 | 4 | *"tag → recognise → preview → confirm → publish… nothing is written without confirmation"* | **PRESUPPOSES** — supplies the human approval E7 cites |
| 300 | 6.1 | the anchored two sentences | **CONTRADICTS** |
| 103, 105, 292 | 2.1, 5.4 | CQ4: *"rules authored independently in different projects and offices remain interoperable"* | **PRESUPPOSES** — CQ4 already assumes a shared vocabulary |
| 212, 265 | 5.1 | *"the Ontograph, not the rule, owns — so each vocabulary term is defined once"* | **ASSERTS** — already consistent; no edit |

**Vocabulary count** (body text, R15.1):

| Term | Occurrences |
|---|---|
| `CDE` | **0** |
| `common data environment` | **0** |
| `shared data environment` | 1 — in ¶173, the sentence E9 edits |
| `recycling` | **0** (the paper's established term is *reuse*) |
| `cross-project` | 1 |
| `minted per project` | 2 (¶113, ¶300) |
| `SKOS` | 1 (¶113) |
| `office` / `offices` | 7 |
| `interoperab*` | 7 |

Zero for `CDE` is the finding that decides E9: the term has to be introduced at first use, and ¶173 precedes both later uses in document order.

### 6.4 Anchors held by this label

Paragraphs **82, 113, 127, 173, 208, 300** and — if E12 is approved — **333** (reference list). A joining session touching any of these must say so in §2 before drafting.

### 6.5 Author's approved decisions (2026-09-05)

| Question | Approved |
|---|---|
| Position for §6.1 | **Reconcile scope and identity** — the vocabulary layer is organisation-level; project identity sits on the referring nodes; duplication is not assumed; matching is agent-proposed and human-approved |
| Deployment status | **Stay theoretical.** No implementation claim. The layer scope is stated as a schema property; the ingest procedure stays in requirement voice |
| Scope of the round | Fix the §3 auto-alignment claim · reconcile §2.2 ↔ §6.1 · log a code change request |
| §6.1 first open question | **The coverage ceiling** — the discipline is settled; how far the aligned vocabularies reach is not |
| §2.2 wording | **"minted once into the shared vocabulary… the author's own term is retained rather than replaced"** |
| Cross-project querying | Runs **through the shared origin class**, not by querying one project's rules from another |
| Fourth open question | **Add it** — CDE as the boundary, and interoperability between separately maintained DG databases as open |

**Added 2026-09-06, after review of the approved package:**

| Question | Approved |
|---|---|
| Repetition across the manuscript | **Remove it.** No edit may restate a claim the paper already makes elsewhere. Sweep run at §6.11; six found, six removed |
| The word *discipline* | **Substitute.** It reads as a design field (MEP, architectural, structural) — the sense the paper uses four times. Replaced with *rule* (E7, E11) |
| The BOT alignment | **Argue it or drop it**, given BOT covers few of the terms being aligned. Reviewed at §6.12 — kept, with the case restated and the cost stated plainly |
| Control scope of the shared vocabulary | **Add as the fourth open question**, with the emergent-not-canonical argument and Lawson. Merged into E10b rather than added separately |

### 6.6 Proposed changes — exact before/after

Every before-string was verified against R15.1 on 2026-09-05 at **exactly one match**. Copied from the file, not retyped.

**E1 — §2.1 `[P82]`**

*Before:*
> the Ontograph contains a project's domain vocabulary, the Metagraph includes its design rules,

*After:*
> the Ontograph contains the shared domain vocabulary, the Metagraph includes a project's design rules,

Trimmed 2026-09-06. §3.1 ¶72 already reads *"the Ontograph holds the generative domain vocabulary"*, and E3 states the organisation-level scope in full — so spelling it out a third time here would be exactly the repetition objected to. ¶82 only has to stop saying *a project's*. Note that `its` in the second clause loses its antecedent once *a project's* goes, hence *a project's design rules*.

**E2 — §2.2 `[P113]`**

*Before:*
> a domain class minted per project carries a graded SKOS match to the BOT class it corresponds to, where one exists, so the term keeps its project identity while remaining resolvable to the shared vocabulary.

*After:*
> a domain class is minted once into the shared vocabulary and carries a graded SKOS match to the BOT class it corresponds to, where one exists, so the author's own term is retained rather than replaced, while remaining resolvable to the external vocabulary.

**E3 — §3.2 `[P127]`** *(author's own wording, copy-edited per §6.7)*

*Before:*
> logically partitioned by a graph property and isolated per project via a project label.

*After:*
> logically partitioned by a graph property. Four of them — the Metagraph, ComputGraph, ValidGraph and SpecGraph — are scoped to a named design project by a project label, while the Ontograph declares shared classes maintained across an organisation's projects, which the instances in those project-scoped layers reference. This is what allows design data to be interoperable and reused between projects.

**E4 — §3.2 `[P127]`**

*Before:*
> REFERS_TO grounds every Metagraph atom in Ontograph vocabulary;

*After:*
> REFERS_TO grounds every Metagraph atom in Ontograph vocabulary, so that project identity is carried by the atom and not by the term it grounds in;

**E5 — §3.6 `[P173]`** *(author's own wording, copy-edited per §6.7)*

*Before:*
> Extensions are engaged automatically: when new entities are ingested into a given graph layer, the extension aligned with that layer assigns them to the appropriate external classes, so a consumer loads the lean core for schema editing and rule authoring and gains cross-vocabulary reasoning only where needed.

*After:*
> Extensions are engaged during ingest. When a new entity enters a given graph layer, the extension associated with that layer proposes the external classes to which the entity may correspond. After human review and approval, the match is recorded. This human-in-the-loop process allows users to load a lean core for schema editing and rule authoring, while enabling cross-vocabulary reasoning only when it is required.

⚠ **The before-string was extended 2026-09-06, and this is not cosmetic.** The existing sentence does not stop at *"external classes,"* — it continues *"so a consumer loads the lean core for schema editing and rule authoring and gains cross-vocabulary reasoning only where needed."* Your new closing sentence says the same thing. With the short before-string, applying E5 would have left the old clause dangling after a full stop: a broken sentence carrying the lean-core claim twice. The extended before-string swallows it. Verified at exactly one match.

⚠ **Recommendation, not applied:** *human* appears twice in three words — *"After human review and approval… This human-in-the-loop process"* — and the abstract already labels the workflow human-in-the-loop. Consider *"After review and approval, the match is recorded. This allows users to load a lean core…"*. Your call; the meaning is identical either way.

**E6 — §3.6 `[P173]`** — see the superseded block at §6.9

*Before:*
> All nodes carry a project label that scopes them to a named design project, allowing a graph database to host multiple concurrent projects with logical isolation while still permitting cross-project queries, so accumulated rules remain queryable across projects.

*After:*
> Nodes in the four project-scoped layers carry a project label that scopes them to a named design project, allowing a graph database to host multiple projects with logical isolation: a rule is read within the project that authored it, since every query on those layers filters by that label. What crosses the boundary is the vocabulary rather than the rule. The Ontograph carries no project label, and the rules of every project ground themselves in the same shared classes through REFERS_TO, so a query entered at a shared term reaches the instances that reference it in each project — the facade rules of two comparable schemes can be retrieved and set side by side, and a rule read in one can then be imported into the other. Accumulation across an organisation's projects proceeds by that route.

The import step is stated as something a reader does with a query result, not as a schema feature — nothing in the deposit performs it, and Q4b forbids claiming otherwise.

⚠ **Recommendation, not applied:** drop the closing sentence *"Accumulation across an organisation's projects proceeds by that route."* The sentence immediately preceding this one in ¶173 already reads *"The schema also supports accumulation and sharing of design grammars across offices and projects."* Everything before the closing sentence explains the route in detail, so the summary adds nothing the paragraph has not just said.

**E7 — §6.1 `[P300]`** — the comment's anchor

*Before:*
> Ontograph classes are minted per project from the terms a rule author uses, which keeps the schema free of a fixed spatial hierarchy but also allows two projects to name one concept twice. A default-class discipline would resolve a generated term against the aligned vocabularies first and mint a new class only where no candidate matches it semantically, so that reuse accumulates across projects rather than being re-declared in each.

*After:*
> The vocabulary is declared once for the organisation rather than per project (section 3.2), and what this asks of ingest is a resolve-then-mint rule: a generated term is matched against the vocabulary already declared and against the aligned external vocabularies, and a new class is minted only where no candidate matches it semantically. What the rule cannot settle is how far those external vocabularies reach. BOT anchors the spatial containment terms — Site, Building, Storey, Space and Zone — which is where agreement between projects matters most and is cheapest to obtain; element terms such as Facade or GlassPanel reach only the generic bot:Element, for the reason given in section 2.2, and urban terms such as Street or Plot have no counterpart in it at all and fall to the mint branch by construction.

Rewritten 2026-09-06. Four statements went out as repetitions of text already in the manuscript, and the BOT sentence turned from a complaint into a justification — see §6.11 and §6.12. What remains is what §6.1 alone has to say: the **scope** is a pointer to §3.2 rather than a restatement of it; the **procedure** is named once and stays in requirement voice (*"what this asks of ingest"*), since the present indicative would assert deployment status that Q4b forbids; and the **open question** is the reach of the external anchors, which is what motivates the IfcOWL sentence that follows it.

**E8 — §4 `[P208]`** *(author's own wording, copy-edited per §6.7)*

*Before:*
> A natural-language constraint is first resolved against the Ontograph entities the project already declares; where a term the constraint needs has no counterpart there, that entity is declared and the Ontograph grows to hold it before any rule is written. The Ontograph is in this sense a generative part of the schema rather than a fixed vocabulary — it is enriched in step with the constraints a project accumulates —

*After:*
> A natural-language constraint is first resolved against the Ontograph entities already declared, which the organisation maintains across its projects within its CDE; where a term the constraint needs has no counterpart there, that entity is declared and the Ontograph grows to hold it before any rule is written. The Ontograph is in this sense a generative part of the schema rather than a fixed vocabulary — it is enriched in step with the shared classes and properties its projects accumulate, while the relationships between their instances are defined by the Metagraph's rules within the scope of a project —

⚠ **Ordering dependency:** this uses `CDE` bare, so **E9 must be applied** — it introduces the expansion at ¶173, which precedes ¶208. If E9 is dropped, E8 must read *"within its common data environment"*.

⚠ **¶208 carries two of the four tracked changes** (`w:ins` id 10 by Bruno). They sit earlier in the paragraph than this before-string, but verify preservation after applying.

**E9 — §3.6 `[P173]`** — introduces CDE at first use

*Before:*
> This isolation strategy is adequate for a single organisation operating a handful of concurrent projects in a shared data environment.

*After:*
> This isolation strategy is adequate for a single organisation operating a handful of concurrent projects within one common data environment (CDE); section 6.1 takes up what lies beyond that boundary.

**E10a — §6.1 `[P300]`** — opening sentence admits a fourth question

*Before:*
> Three of the boundaries recorded in section 2.2 are open questions rather than settled limits.

*After:*
> Three of the boundaries recorded in section 2.2 are open questions rather than settled limits, and the shared-vocabulary position this section takes raises a fourth.

§2.2's cross-reference *"Three of these boundaries — generated vocabulary, IFC alignment, and movement between Design States — are developed in section 6.1"* stays true and needs no edit: the fourth question comes from this section's own position, not from §2.2.

**E10b — §6.1 `[P300]`** — the fourth question, appended at the paragraph end

*Before (anchor, text appended after it):*
> while the designer's interpretation of either belongs to protocol study.

*After:*
> while the designer's interpretation of either belongs to protocol study. The fourth question is one this section's own position raises: at what scope should the shared vocabulary be controlled? Defining the full taxonomy of terms an architectural project might need is deliberately not attempted, because design terminology is emergent rather than canonical — it is produced in the course of designing rather than settled in advance of it (Lawson, 2005). The scope proposed here is the CDE an organisation already operates: within it the vocabulary is a maintainable master core, bounded by a defined set of activities and toolsets, and a rule authored in one project stays readable in the next because both resolve against the same maintained vocabulary. This is also what CQ4 assumes when it asks about interoperability between offices — offices sharing one such environment share one vocabulary. What the proposal does not settle is exchange beyond that boundary. Two organisations each maintaining a vocabulary of their own meet the resolve-then-mint problem one level up, between vocabularies rather than between projects, and the graded matches of section 2.2 describe the mechanism a bridge would use without settling who curates it or how a match is agreed between parties who each authored one side. It is at that boundary that the external anchors earn their place: the spatial terms BOT covers would carry across it, an IfcOWL alignment under question two would extend that reach to element terms, and terms with no counterpart in either would remain local to the organisation that minted them.

Merged 2026-09-06 from your supplied text and the earlier fourth-question draft, which said much of the same thing. **The CQ4 conflict is now resolved rather than hedged.** The earlier draft narrowed §5.4's guarantee, which put it at odds with ¶82 (*"a rule library is only interoperable between offices if the vocabulary its rules are grounded in is itself consistent and structurally complete"*). Distinguishing *offices sharing one CDE* from *separate organisations each maintaining their own vocabulary* makes both statements true at once, and no §5.4 edit is needed.

⚠ **Depends on E12** — the Lawson reference. If E12 is not applied, the citation must come out of this text.

**E11 — §6.1 `[P300]`, the IfcOWL sentence** *(new — the "discipline" substitution)*

*Before:*
> under the same resolve-then-mint discipline that the topology alignment already expresses

*After:*
> under the same resolve-then-mint rule that the topology alignment already expresses

Required, not optional: E7 and this sentence sit in the same paragraph, so leaving one *discipline* standing would defeat the substitution. §6.13 lists the two further occurrences elsewhere in the paper, which are **not** in scope.

**E12 — reference list `[P333]`** *(new — a paragraph insertion, not a replacement)*

A new reference, inserted alphabetically between `Janowicz, K., … (2019)` `[P332]` and `Lin, C.-J. (2016)` `[P333]`:

> Lawson, B. (2005). How designers think: The design process demystified (4th ed.). Architectural Press.

⚠ **The bibliographic details supplied do not check out.** The text given was *"B. Lawson, 'How Designers Think – The Design Process Demystified', University Press, Cambridge, Jan. 2006."* The book is **Architectural Press**, an imprint of Elsevier, Oxford — 4th edition, **2005**, ISBN 978-0-7506-6077-8. It is not a Cambridge University Press title. Verified via Perplexity against the Elsevier listing, Open Library and the Internet Archive record. **Crossref and OpenAlex were both unreachable from this machine**, so there is no DOI-resolved record and the entry rests on ISBN identification instead; it is a monograph, so a DOI may not exist at all. **Confirm against your own reference manager before applying.**

⚠ **This is an insertion, so `docx_replace.py` cannot do it.** The reference list is one `w:p` per entry with a hanging indent (`w:ind w:left="567" w:hanging="567"`). The safe method is to clone the `[P333]` paragraph node, swap its text, and insert the clone before it, preserving the paragraph properties. Do not hand-build a `w:p`.

The in-text citation `(Lawson, 2005)` is introduced by E10b. House style is APA 7 with DOIs where they exist — cf. `Mubarak, K. (2004). Case-based reasoning for design composition in architecture [Doctoral dissertation, Carnegie Mellon University].`, which carries no DOI either.


### 6.7 Copy-edits folded into the author's own wording

The author revised E3, E5, E7 and E8 by hand. The substance is theirs and is unchanged. These are copy-level corrections, applied above and listed here so the diff is auditable:

| Edit | As the author wrote it | Correction | Why |
|---|---|---|---|
| E3 | `…project label; while the Ontograph declares…` | `…project label, while…` | A semicolon needs an independent clause; `while` makes it subordinate |
| E3 | `other project-scoped layers of the graph reference their instances to the shared vocabulary` | `…which the instances in those project-scoped layers reference.` | `other` is loose right after the four are named; `reference X to Y` is unidiomatic |
| E3 | `ensures data interoperability and recyling between projects` | `This is what allows design data to be interoperable and reused between projects.` | `recyling` is a typo; `recycling` appears **0** times in the paper while *reuse* is its established term (§2.2 is titled *"…reuse and alignment"*); `ensures` overstates against the surrounding register |
| E5 | `implying human-in-the-loop approach` | `implying a human-in-the-loop approach` | Missing article |
| E7 | `declared once for shared vocabulary of the organisation` | `declared once as the organisation's shared vocabulary` | Missing article; reads as a purpose clause where an appositive is meant |
| E8 | `across its projects within CDE` | `across its projects within its CDE` | Missing article; and see the E9 ordering dependency |
| E8 | `defined in the rules of Metagraph within the project scope` | `…accumulate, while the relationships between their instances are defined by the Metagraph's rules within the scope of a project` | Comma before the contrastive `while`; possessive reads more naturally |

### 6.8 Predicted verification counts

| Check | Predicted |
|---|---|
| `docx_replace.py` match count | **1/1 on each of E7, E8, E10a, E10b, E11, E13, E14** — 7 remaining replacements, each verified **against R15.2** at exactly one match on 2026-09-06. E1–E6 and E9 are already applied |
| Paragraphs changed | exactly `[P113]`, `[P127]`, `[P208]`, `[P300]` — four; plus one **new** paragraph before `[P333]` if E12 is approved |
| Package parts | unchanged at **42** |
| `w:ins` / `w:del` | unchanged at **4** — none is inside a replaced span |
| Comments / comment references | R15.2 currently carries R15.1's 11 threads and **no traceability comments for the seven edits already applied** — see §6.14. On apply: a reply on comment 20, plus one comment per edit |
| Comment 20 | `w15:done` `0` → `1` |
| `validate_docx.py` | no findings beyond those already present in R15.1 |
| R15.1 hash at round close | unchanged at `530d04f30600baad` — **verified 2026-09-06** |
| R15.2 hash before the next write | `ce5ece98c15e`; if it differs, re-run the overlap check before doing anything |

### 6.9 Superseded

**Superseded at:** 2026-09-05 · **Cause:** premise correction by the author
**What the retired E6 proposed:** *"…while still permitting cross-project queries, so accumulated rules remain queryable across projects. The Ontograph carries no such label: the vocabulary those rules ground themselves in is maintained once for the organisation…"*
**Why it no longer holds:** the author's correction — *"Rules are project-scoped and are not implied to be queried from another project as they have project label filtering. Instead class instances of the project referenced to the shared origin class in Ontograph can be a part of cross-project query."*
**What survives:** the Ontograph-carries-no-label clause. What changed is the mechanism of crossing: through the shared class, not by querying another project's rules.

**Superseded at:** 2026-09-06 · **Cause:** author review of the approved package
**What the retired plan proposed:** an E7 opening on *"Ontograph classes are generated from the terms rule authors use rather than imposed as a fixed spatial hierarchy"*, a middle clause naming *"the encoding agent"* and *"the approver the authoring workflow already places in the loop"*, a closing sentence restating *"BOT constrains an instance of bot:Element no further"*, the noun *discipline* throughout, and a separate fourth open question in E10b built on the CDE boundary alone.
**Why it no longer holds:** each of the first three restated something the manuscript already says — in the abstract, §3.1 ¶72, §4 ¶208 and §2.2 ¶113 respectively; *discipline* collides with the design-field sense the paper uses four times; and the separate fourth question duplicated the author's own supplied text on control scope.
**What survives:** the requirement voice, the layer-scope position, the coverage-ceiling structure of the open question, and the resolve-then-mint name. E10b keeps the cross-organisation argument but reaches it through the control-scope question rather than asserting a boundary.

A second premise correction earlier in the round retired the **first** model put to the author — that Ontograph classes keep a project identity — on the author's statement that *"Ontograph entities don't need project identity as they are cross-project entities. Instead class instances from other layers (e.g. Metagraph) which refer to Ontograph classes, have specific project identity."* That correction is what produced E3, E4 and E8. Recorded so the dead end is not re-derived.

### 6.10 Fixed verification checklist — run at apply

1. `~$` lock gone; R15.1 re-hashed and compared to `530d04f30600baad`.
2. Three-way overlap check run 2 — empty, or stop and re-fire the gate.
3. No-op round-trip test passes (comments, tracked changes, citation fields).
4. `R15.2.docx` created by copy; R15.1 never opened for write.
5. All 11 replacements report 1/1; **partial application is forbidden**.
6. `validate_docx.py` clean against the predictions in §6.8.
7. Comment 20 replied to and resolved; 11 traceability comments present.
8. §2.1, §2.2, §3.2, §3.6, §4, §6.1 read back in sequence — one position on Ontograph scope, `CDE` expanded at ¶173 before its bare uses.
9. §6.1 presents four questions and its opening sentence agrees with the count.
10. Predicted-vs-actual table written to the summary; any divergence is a finding, not a footnote.

### 6.11 Redundancy sweep — every claim the package introduces, against the whole manuscript

Run 2026-09-06 at the author's instruction. Each claim the edits introduce was searched across the full body text, reference list included. **Six repetitions found; all six removed.**

| Claim introduced | Already stated at | Disposition |
|---|---|---|
| Agent proposes the alignment, a human approves it | Abstract (*"a provider-agnostic, human-in-the-loop LLM workflow operationalises rule authoring"*) · §4 ¶208 (*"tag → recognise → preview → confirm → publish… nothing is written without confirmation"*) · E5 | **Removed from E7.** §3.6 states the mechanism, §4 states the loop; §6.1 needs neither |
| The Ontograph is generative, not fixed | Abstract (*"a generative shared vocabulary"*) · §3.1 ¶72 (*"the Ontograph holds the generative domain vocabulary"*) · §4 ¶208 (the full explanation) | **Removed from E7.** Kept in ¶208 — see the note below |
| BOT constrains an instance of `bot:Element` no further | §2.2 ¶113, verbatim | **Removed from E7**, replaced by the pointer *"for the reason given in section 2.2"* |
| The Ontograph is declared once for the organisation | E1 · E3 · E7 | **Reduced to one full statement (E3).** E1 trimmed to the minimum ¶82 needs; E7 now points to §3.2 |
| A consumer loads a lean core and gains cross-vocabulary reasoning only when needed | ¶173, in the very sentence E5 replaces | **Absorbed** — E5's before-string extended to swallow it, so the claim is stated once. Without this the applied text would have carried it twice, in a broken sentence |
| Accumulation and sharing across offices and projects | ¶173, the sentence immediately before E6's | **Flagged on E6** as a recommended cut. Not applied — it is your wording |

**On the *generative* claim in E8, which you gave as the example.** I recommend the opposite direction, and the reason matters: §4 ¶208 is the **only** place the claim is explained (*"…rather than a fixed vocabulary — it is enriched in step with…"*). The abstract and §3.1 ¶72 merely use *generative* as a label. Abstract labels it, overview lists it, body explains it, is the normal progression and not redundancy; four statements of it was. So the fourth (E7's) is gone and ¶208 keeps the explanation. If you would still rather trim ¶208, the phrase to cut is *"is in this sense a generative part of the schema rather than a fixed vocabulary — it"*, leaving *"The Ontograph is enriched in step with…"* — say the word and I will restate E8 that way.

**Not repetitions, checked and cleared:** E2's *"retained rather than replaced"* against §5.1 ¶265 (*"the Ontograph, not the rule, owns — so each vocabulary term is defined once"*) — different claims, ownership versus substitution. E4's *"project identity is carried by the atom"* against E3's layer scoping — E3 says *which* layers are scoped, E4 says *what carries* the scope, and only E4 names the bridge. CQ4 at ¶82/¶103/¶105/¶292 against E10b — reconciled rather than duplicated, see the note under E10b.

### 6.12 BOT — is the alignment necessary? A critical review

You asked for this to be argued or dropped. It survives, but the paper was making the case badly, and the corrected case is narrower than the one it implied.

**What BOT actually supplies.** Per §2.2 ¶113, the building-topology module imports BOT and subsumes `bot:Site`, `bot:Building`, `bot:Storey`, `bot:Space`, `bot:Zone` and `bot:Element` under the core's Topology concept. That is a **spatial containment backbone** and nothing else. BOT says so itself by delegating element classification to other vocabularies.

**Measured against the paper's own running example** — project `UrbanBlock`, rule `R_BUILDING_MAX_HEIGHT_75_V`, per-zone planning constraints, plus a hexagonal curtain-wall facade grammar:

| Term the demonstrated rules quantify over | BOT anchor | Quality |
|---|---|---|
| Building — the maximum-height rule | `bot:Building` | exact |
| Zone — per-zone planning constraints | `bot:Zone` | exact |
| Storey, Space — minimum floor-plate area | `bot:Storey`, `bot:Space` | exact |
| Facade, GlassPanel — the curtain-wall grammar | `bot:Element` | generic, close to information-free |
| Street, Plot — street-wall height, street width | none | absent |

So the premise *"BOT does not cover many terms under alignment"* is half right, and the half it gets wrong is the important one: **BOT covers precisely the terms the headline rules quantify over.** It fails on element and urban terms.

**Three arguments for keeping it.**

1. **Without an external anchor the shared vocabulary is entirely self-declared.** CQ4 asks whether rules authored independently stay interoperable; if every term is minted locally and resolves to nothing outside, the answer rests on nothing a second party can check. BOT is the W3C Linked Building Data community's minimal spatial core and the cheapest anchor available.
2. **Its smallness is the point, not a shortfall.** The position E10b now states is that architectural terminology is emergent rather than canonical, so importing a large fixed taxonomy would contradict the paper's own argument. BOT imports six classes and imposes no element hierarchy: it is the **largest anchor compatible with refusing to canonicalise**. This is the argument the paper was missing, and it is what makes the modest coverage a consequence of the design rather than a defect in it.
3. **It is what survives outside the CDE.** Under the new fourth question, two organisations maintaining separate vocabularies have nothing in common except their external anchors. The spatial terms are the ones that would carry across that boundary — which makes BOT load-bearing exactly where the schema is otherwise weakest. E10b now says this.

**The cost, which the paper should not hide and now does not.** A graded SKOS match from `Facade` to `bot:Element` asserts little more than *this is a building thing*; urban terms get no match at all. E7 states both plainly rather than presenting the alignment as more complete than it is.

**What would overturn the argument.** If the schema's rules quantified mainly over element and urban terms, BOT would buy almost nothing and IfcOWL should be the **first** alignment rather than the second open question. The running example splits roughly evenly, so the case holds without being overwhelming. Worth having ready if a reviewer presses on why IFC is deferred.

### 6.13 *Discipline* — the substitution, and what is left

Your reading is correct and the risk is concrete: the paper uses *discipline* in the design-field sense four times — *"across files, tools, and disciplines"* (Summary), *"reused across disciplines and projects"* (§1), *"across disciplines and platforms"* (§2.1), *"across offices and disciplines"* (§3.6). That sense owns the word.

| Occurrence | § | Sense | In scope |
|---|---|---|---|
| *"A default-class discipline would resolve…"* | 6.1 ¶300 | procedure | **Yes** — deleted by E7 |
| *"the same resolve-then-mint discipline"* | 6.1 ¶300 | procedure | **Yes** — E11, → *rule*. Same paragraph as E7, so it cannot be left |
| *"the graph-grounded discipline that distinguishes reliable text-to-Cypher systems"* | 3.5 ¶199 | methodological rigour | No — see §13 |
| *"whose absence-of-violation verdict depends on explicit population discipline"* | 7 ¶302 | methodological rigour | No — see §13 |

*Rule* was chosen over *procedure* or *policy* because the sentence following E7 already calls it *"the same resolve-then-mint …"*, and *rule* reads naturally in both. It does collide with the paper's other sense of *rule* (a design rule), but only inside the compound *resolve-then-mint rule*, where the hyphenated name carries the meaning.

### 6.14 Applied state of R15.2 — what landed, what it introduced

Discovered 2026-09-06 by the overlap check, not announced to this session. R15.2 (`sha256:ce5ece98c15e`, 42 parts, 359 paragraphs) differs from R15.1 in exactly four paragraphs — 82, 113, 127, 173 — and nowhere else.

| Edit | State in R15.2 | Variance from the plan |
|---|---|---|
| E1 ¶82 | **applied** | The untrimmed wording (*"the shared domain vocabulary the organisation maintains across its projects"*). The trim proposed at §6.11 was drafted after the apply, so it is now optional, not pending |
| E2 ¶113 | **applied, with two variances** | Applied as *"by annotation: A domain class is created and added to the shared vocabulary once and carries…"*. **Capital `A` mid-sentence after a colon** → E14. And *minted* was replaced by *created and added*, which matters: §6.1 still says *resolve-then-mint* and *the mint branch*, so the term of art is now introduced nowhere and used twice |
| E3 ¶127 | **applied, with a broken clause** | *"…which are referenced by the instances in those project-scoped layers reference."* — a doubled verb. → **E13** |
| E4 ¶127 | **applied as planned** | none |
| E5 ¶173 | **applied** | Your wording. **The duplication warned about did not occur** — whoever applied it replaced the whole sentence including the trailing lean-core clause, which is what the extended before-string was for. The doubled *human* remains, as expected |
| E6 ¶173 | **applied in full** | Including the closing sentence I recommended cutting. R15.2 now reads *"The schema also supports accumulation and sharing of design grammars across offices and projects"* and, two sentences later, *"Accumulation across an organisation's projects proceeds by that route."* The redundancy is live → optional **E15** below |
| E9 ¶173 | **applied, shortened** | *"…in a Common Data Environment (CDE)."* The forward link *"section 6.1 takes up what lies beyond that boundary"* was dropped. No consequence for E8 or E10b — the term is defined at ¶173, which still precedes both — so this is a stylistic loss only |
| E7, E8, E10a, E10b, E11, E12 | **not applied** | All re-verified against R15.2 at exactly one match |

⚠ **Traceability hole.** R15.2 carries exactly the comment state of R15.1 — 12 comments, 9 resolved, no new threads. **No `[AU-R151-ONTO]` traceability comment exists for any of the seven applied edits, and comment 20 is still unresolved.** Per the traceability spine a change present in the document but absent from the log is a finding, not a success. Either add the seven comments retrospectively at the next apply, or record in the summary that this round's traceability lives in the plan and summary alone. **That is your call, and it should be a deliberate one.**

**E13 — §3.2 `[P127]`, fix the doubled verb** *(required — anchors against R15.2)*

*Before:*
> which are referenced by the instances in those project-scoped layers reference.

*After:*
> which the instances in those project-scoped layers reference.

**E14 — §2.2 `[P113]`, fix the capital after the colon** *(required — anchors against R15.2)*

*Before:*
> by annotation: A domain class is created and added to the shared vocabulary once and

*After:*
> by annotation: a domain class is minted once into the shared vocabulary and

Two things in one replacement, and the second is optional. The capital `A` is a plain defect. Restoring **minted** is a judgement call: the paper's §6.1 uses *resolve-then-mint* (E11) and *the mint branch* (E7), and with E2 as applied the term is used twice but introduced nowhere. If you prefer *created and added*, take `> by annotation: a domain class is created and added to the shared vocabulary once and` instead, and I will re-word E7 and E11 to drop *mint* — but then the compound *resolve-then-mint* has to go too, and it is the name the IfcOWL sentence already reuses.

**E15 — §3.6 `[P173]`, the doubled accumulation claim** *(optional — your wording, your call)*

*Before:*
> Accumulation across an organisation's projects proceeds by that route.

*After:*
> *(deleted)*

¶173 now states accumulation and sharing twice: *"The schema also supports accumulation and sharing of design grammars across offices and projects"*, then the whole mechanism, then this summary. Cutting the summary loses nothing the paragraph has not already said at length.

---

## 6A. `AU-R151-TOPO` — topology and classification alignment architecture

**Author's comment (verbatim, Word id 21, Evgenii Ermolenko, 2026-09-05, unresolved):**

> "Not clear why this statement follows from the first. IFC alighnment is strategically necessary step as it is well-defined industry internatianelly accepted open schema in AEC. Include this as extension module (section 2.2), but this module does not need to be included into ontologic pack as it is open-source schema available online, so LLM can access it and align classes with Ontograph by assigning reference property to the DG class. Topologic and BOT ontologies are small and constant so they attached as extensions within the DG ontology. Or they also should be referenced directly if they are avaialable in Web?"

**Anchor:** §6.1, the sentence *"The second follows from the first…"* — **still present verbatim in applied R15.2.** `AU-R151-ONTO` rewrote the *first* question and changed only *discipline*→*rule* in the second; the entailment comment 21 objects to was never addressed.
**Claimed:** 2026-09-06 by `s-aadf61bc`

### 6A.1 The finding that drives this label

**Topologic has a published OWL ontology.** This was not known to `AU-R151-ONTO` when it wrote §6.12, and it triggers that section's own stated overturn condition.

| | Verified 2026-09-06 by direct retrieval |
|---|---|
| Namespace | `http://w3id.org/topologicpy#` (prefix `top:`) |
| Document | `https://wassimj.github.io/topologicpy/ontology/topologicpy.ttl` — resolves |
| Core classes | **All eight** — Cluster, CellComplex, Cell, Shell, Face, Wire, Edge, Vertex, as `owl:Class` |
| Relations | parthood (`aggregates`/`isAggregatedBy`, `isPartOf`, `hasSubTopology`/`isSubTopologyOf`) · adjacency (`adjacentTo`) · containment (`containsElement`, `locatedIn`) · typology (`hasClassification` → `top:ClassificationReference`) · boundary (`hasExternalBoundary`, `hasInternalBoundary`, `interfaceOf`) · the `hasVertex`…`hasCellComplex` constituent chain with inverses |
| Building parts | Site, Building, Storey, Space, Zone, Element **+ ~20 element classes** — Wall, Slab, Column, Beam, Door, Window, Roof, Railing, Furniture, CurtainWall, Aperture, Opening, Member — and zone subtypes (Thermal, Functional, Circulation) |
| **BOT alignment, already present upstream** | **25 `rdfs:subClassOf` + 4 `rdfs:subPropertyOf`** — incl. `top:Site ⊑ bot:Site`, `top:Storey ⊑ bot:Storey`, `top:Space ⊑ bot:Space`, `top:Element ⊑ bot:Element`, `top:connectsTo ⊑ bot:connectsTo`, `top:adjacentTo ⊑ bot:adjacentZone`, `top:interfaceOf ⊑ bot:interfaceOf`, `top:containsElement ⊑ bot:containsElement` |

**Every relation family §2.2 claims for the locally-declared module is present upstream.** The project's own declaration duplicates a published ontology exactly, and the manuscript's *"thereby adapting Topologic to formal OWL"* claims a contribution its own cited author has since made — a priority risk with any reviewer who knows `topologicpy`.

### 6A.2 How the three vocabularies relate — and what that settles

They are not three competing choices. They are already chained, upstream of this paper:

```
top:  (topologicpy)   ⊑   BOT   ↔   ifcOWL / IFC
   25 rdfs:subClassOf        LBD's published
 + 4 rdfs:subPropertyOf      IFCOWL4_ADD2Alignment.ttl
```

- **`top:` is not an LBD deliverable** — it is Jabi's ontology for the Topologic library. But it declares `bot:`, `brick:` and `ifc:` prefixes and **subsumes its own building-part classes under BOT**, positioning itself downstream of LBD.
- **LBD publishes the BOT↔ifcOWL alignment itself** (`IFCOWL4_ADD2Alignment.ttl`, mapping `bot:Site`/`Building`/`Storey`/`Space`/`Element` onto the `ifc:` counterparts).

**So the schema aligns at two points and inherits the rest.** No DG-maintained bridge is needed between them.

**IFC versus LBD is not a choice between alternatives.** IFC is the industry **exchange schema and classification authority** (ISO 16739-1:2024, internationally mandated, ~800 entities, resolvable identifiers through bSDD). The LBD stack is the **semantic-web-native relational layer**, which exists precisely because ifcOWL's reified `IfcRel*` model is unusable for lightweight linked data — and whose own answer is to align *to* IFC rather than replace it. The division the schema adopts is therefore:

> **IFC says what things *are*. The topology layer says how things *relate*.**

**Why BOT is subsumed rather than bridged or removed.** §6.12 argued BOT survives, and recorded its own overturn condition: *"If the schema's rules quantified mainly over element and urban terms, BOT would buy almost nothing."* Its table records BOT failing exactly there — `Facade`, `GlassPanel` → `bot:Element` (*"close to information-free"*); `Street`, `Plot` → absent. **The argument is not overturned; its premise is.** `top:` closes the element half (`CurtainWall`, `Window`, `Aperture`, `Wall`, `Slab`) and already subsumes BOT's spatial classes, so a DG→BOT bridge would be a **second path to a vocabulary the topology module already reaches**. BOT therefore stays in the paper as *the layer `top:` extends* and *the origin of the topology/classification division the schema adopts* — cited, not aligned. §6.12 is **narrowed, not reversed**.

**The division is BOT's own, and it is citable.** BOT's scope statement restricts it — *"the group aimed to limit to referential topological concepts of a building"* — and `bot:Element` is deliberately unconstrained: *"It can be any tangible object (product, device, construction element, etc.) that exists in the context of a zone."* Classification is delegated by design to a **named sibling module, PRODUCT/BPO**. The two-bridge architecture below is therefore the LBD stack's own decomposition (BOT : PRODUCT :: topology : classification), not an invention of this paper.

### 6A.3 Critical revision of the extension set — two findings nobody flagged

Checking the core band (Object, Function, Behaviour, Structure, Geometry, Topology, DesignState, Session) against what each module does:

| DG core concept | Alignment today | LBD counterpart | Verdict |
|---|---|---|---|
| Topology | BOT **+** Topologic | BOT / `top:` | **redundant** → one module |
| classification of minted terms | `bot:Element` only | PRODUCT/BPO | **weak** → IFC via bSDD |
| **Geometry** | **none** | **OMG + FOG** | ⚠ **gap** |
| **DesignState** | none | **OPM** | ⚠ **overlap risk** |

**⚠ The Geometry gap.** §3.2 states *"Geometry and Topology complete the structural side of the core."* Topology is anchored; **Geometry is anchored to nothing.** OMG (Ontology for Managing Geometry) and FOG (File Ontology for Geometry formats) are LBD's reference pattern for attaching geometry descriptions. The schema has a good answer — geometry travels as a platform `Representation` rather than as an RDF geometry description — but the paper never states it, leaving an unexplained asymmetry between Structure's two legs.

**⚠ The OPM overlap.** OPM (Ontology for Property Management) inserts an `opm:PropertyState` between a property and its value, carrying timestamps, `opm:CurrentPropertyState`, provenance, versioning, derivation metadata and **reliability labels** (`assumption`, `confirmed`, `deleted`). That is close enough to `DesignState`/ValidGraph that a reviewer who knows LBD will ask *why not OPM*.

**The paper already contains the answer and does not use it.** OPM models **per-property fine-grained history**; a Design State is a **whole-configuration checkpoint**. §6.1 says exactly this — *"it describes movement between the moments an architect chose to validate, at the granularity of those checkpoints."* The literature treats the two as complementary (snapshots for milestones, per-property states within them). Naming OPM converts a latent objection into positioning.

**Author's decision (2026-09-06): both are addressed in §2.2 as declared non-alignments** — see T3.

### 6A.4 The resulting architecture

**Three alignment modules. One question each. One attachment point each. No overlap.**

| Module | Vocabulary | Answers | Attaches at |
|---|---|---|---|
| **Topology** | `top:` (⊑ BOT) | *how does this relate spatially?* | the core's **Topology** concept |
| **Classification** | **IFC**, referenced through **bSDD** | *what kind of building thing does this term denote?* | the minted **Ontograph Class** |
| **Standards** | W3C/OGC — SWRL, PROV-O, SOSA, SHACL, SKOS, DCTERMS, GeoSPARQL | *how is this expressed and provenanced?* | core and rule layer |

**Two attachment points is what delivers non-overlap.** Even if both vocabularies contained a "Wall", they could not collide: one types the *topological entity* at the core band, the other classifies the *vocabulary term* at the Ontograph. Different layers, different questions.

**Plus two declared non-alignments** (T3): geometry (OMG/FOG) and property states (OPM), each with its reason.

### 6A.5 Author's approved decisions

| Question | Approved |
|---|---|
| Q4b | **Theoretical.** The article leads; `ontology/` is rebuilt to match it later |
| Module taxonomy | **Janowicz et al. (2019)** distinction — alignment modules (mapping axioms only) vs extension modules. The schema ends with **three alignment modules and no extension module** |
| Topology target | **`top:`**, used for its topological entity types and relations **only** — never as a classification source, which is what would reintroduce overlap |
| BOT | **Subsumed, not bridged and not removed.** Reached through `top:`; cited as the layer it extends and the origin of the division |
| Classification target | **IFC via bSDD**, not PRODUCT/BPO — BPO is small and thinly adopted, and only IFC supports the strategic-necessity argument comment 21 makes |
| IFC mechanism | **bSDD reference + graded SKOS match, never `owl:imports` of ifcOWL** |
| IFC status | **Hybrid** — module *declared* in §2.2; §6.1 keeps a **narrowed** question about its *reach* |
| Geometry gap · OPM overlap | **Addressed in §2.2 as declared non-alignments** |
| Search tractability | **State the mechanism, not the agent** — bSDD's search interface makes the candidate set tractable; no deployment claim (R14.2 D4) |
| Terminology | **LBD** and **bSDD** glossed at first use in §2.2; **OPM** and **BPO** glossed inside the non-alignment sentences |
| Figure 2 | **Revised in place — no new figure, no renumbering.** Spec at §6A.8; built only after approval |
| Conclusion future work (3) | **Narrow to IDS** |
| `top:` version risk | Recorded in **§6.1 only**, as a handled risk |
| Traceability | Add the missing `[AU-R151-ONTO]` comments retrospectively at this apply; resolve comments 20 and 21 |

### 6A.6 Consistency with what `AU-R151-ONTO` applied — reconciliation

| Applied text | Consistent? | Disposition |
|---|---|---|
| E2 ¶113 — SKOS match *"to the **BOT** class"* | **No** — target changes | **T5.** `AU-R143-C01` preserved: the match stays *additive, never substitutive* — *"the author's own term is retained rather than replaced"* is kept verbatim; only the object changes, which that decision does not constrain |
| E7 ¶300 — *"Facade or GlassPanel reach only the generic bot:Element"* | **No** — false once `top:` anchors | **T8** |
| E10b ¶300 — *"an IfcOWL alignment **under question two**"* | **Partly** — the module now exists, and it is not ifcOWL | **T10** |
| E10a ¶300 — *"Three of the boundaries… raises a fourth"* | **Yes** | **No edit.** Under Hybrid, IFC alignment remains a boundary *developed* in §6.1, so §2.2's *"Three of these boundaries…"* cross-reference also stays true |
| E10b — *"design terminology is emergent rather than canonical (Lawson, 2005)"* | **Yes, once import/reference is explicit** | IFC is a canonical taxonomy, so this reads as self-contradiction unless the paper distinguishes *referencing a resolution target* from *importing a canon*. **T1, T4 and T12 carry that distinction.** The verified absence of an `IfcFacade` class is the evidence that the mint branch stays live |
| §6.12 — BOT *"the largest anchor compatible with refusing to canonicalise"* | **Yes** — it constrains what is **imported** | Nothing is imported under this package. Argument holds; its subject narrows |
| E11 — *resolve-then-mint **rule*** | **Yes** | T8 and T9 use *rule*, never *discipline* |
| E9 — `CDE` defined at ¶173 | **Yes** | No edit touches it |

### 6A.7 Proposed changes — exact before/after

**All sixteen before-strings verified against applied `T1_ITcon_DG_Draft_R15.2.docx` (`sha256:6b64cc92e672df99`, 369 paragraphs) at exactly one match, 2026-09-06.**

**T1 — §2.2, the two module kinds** *(introduces LBD)*

*Before:* The Building Topology Ontology (BOT) and Topologic, by contrast, are bridged through dedicated extension modules rather than embedded in the schema, so that reuse does not couple the core to a particular external vocabulary, following the core-plus-extension modularisation established for W3C vocabularies such as SOSA/SSN (Janowicz et al., 2019), and the same mechanism accommodates further alignments as the ecosystem around the ontology grows.

*After:* The Building Topology Ontology (BOT) and Topologic, by contrast, remain external and are reached through dedicated alignment modules, so that reuse does not couple the core to a particular external vocabulary, following the core-plus-extension modularisation established for W3C vocabularies such as SOSA/SSN (Janowicz et al., 2019). That modularisation distinguishes an extension module, which adds vocabulary to the core, from an alignment module, which carries only mapping axioms to an external vocabulary. The schema uses alignment modules throughout, so that every external vocabulary is referenced at its published identifier and retains its own namespace. This use of alignment modules follows the polylithic approach of the W3C Linked Building Data (LBD) Community Group, which distributes building semantics across small interoperable modules, and the same mechanism accommodates further alignments as the ecosystem around the ontology grows.

> **Trimmed by the redundancy sweep (§6A.7a):** *"and none is redeclared or redistributed here, which is also how a large external schema can be reached without importing it"* — redistribution is a deposit concept owned by T12, and the size argument is made properly and specifically by T4.

**T2 — §2.2, one topology alignment replacing two modules**

*Before:* The building-topology module imports BOT and subsumes bot:Site, bot:Building, bot:Storey, bot:Space, bot:Zone and bot:Element under that concept; the topology relations the schema evaluates come from the non-manifold module. That module declares Topologic's Cluster, CellComplex, Cell, Shell, Face, Wire, Edge, and Vertex, together with containment, parthood, adjacency, and typology relations, in this project's own namespace, thereby adapting Topologic to formal OWL.

*After:* BOT and Topologic are both reached through a single topology alignment module, which targets the published Topologic ontology (Jabi & Chatzivasileiadi, 2021). That ontology declares Cluster, CellComplex, Cell, Shell, Face, Wire, Edge and Vertex, together with the containment, parthood, adjacency and boundary relations the schema evaluates, and it subsumes its own building-part classes under the corresponding BOT classes (Rasmussen et al., 2020). The schema therefore reaches BOT's spatial vocabulary through that subsumption, and the topology alignment module attaches at the core's Topology concept.

> **Named in place (§6A.7c):** *"reaches **both**"* left the antecedent to the previous sentence, and the trailing *"the alignment"* named no module. Both subjects are now stated where they are used.

> **Neutral voice (§6A.7b):** *"rather than through a second bridge of its own"* argued against an alternative the module list already rules out by simply not containing it.

> **This edit removes the novelty claim.** *"thereby adapting Topologic to formal OWL"* does not survive: a formal OWL Topologic exists, published by the same author the sentence cites.
>
> **It also repairs two uncited references.** `Jabi & Chatzivasileiadi (2021)` and `Rasmussen et al. (2020)` are both in the reference list and cited **nowhere in the body** — verified, one occurrence each, and that occurrence is the reference entry itself. T2 is the first body citation of either. Two uncited references are a copy-editing defect a journal will catch.
>
> **Trimmed by the redundancy sweep (§6A.7a):** *", where it answers how an entity relates spatially rather than what kind of thing it is"* — T3 states the topology/classification division in the paragraph that exists to record such decisions.

**T3 — §2.2, declared non-alignments** *(introduces BPO and OPM; carries the Geometry gap)*

*Before:* The alignments that were deliberately not made are recorded here as well. BOT leaves element classification to other vocabularies — it constrains an instance of bot:Element no further — so there is no element taxonomy to import.

*After:* The scope of each alignment is recorded here as well. BOT defines bot:Element as any tangible constituent of a construction entity and assigns its classification to other vocabularies, which is why element classification is carried by the separate classification alignment module described below. LBD assigns that role to its Building Product Ontology (BPO), while this schema aligns to IFC. Geometry follows a different route: LBD attaches geometry descriptions through the Ontology for Managing Geometry (OMG) and the File Ontology for Geometry formats (FOG), while in this schema geometry travels with the object as a platform representation, the mechanism the schema already uses for it. The Ontology for Property Management (OPM) addresses a neighbouring concern: OPM models the evolution of a single property as a chain of time-stamped states, whereas the Design State of section 3.3 records a whole configuration at a moment an architect chose to validate, so OPM and the Design State describe change at different granularities and are complementary.

> **Positive scope (§6A.7d).** Four negations removed, and with them the hedge that propped them up:
>
> | Was | Now |
> |---|---|
> | *"The alignments that were **deliberately not made** are recorded here as well"* | *"The **scope of each alignment** is recorded here as well"* |
> | *"BOT leaves element classification to other vocabularies — it **constrains an instance of bot:Element no further**"* | *"BOT **defines bot:Element as any tangible constituent of a construction entity** and **assigns** its classification to other vocabularies"* |
> | *"Geometry is **left unaligned**"* | *"Geometry **follows a different route**"* |
> | *"OPM is **left unaligned** for a comparable reason"* | *"OPM **addresses a neighbouring concern**"* |
>
> The second is also **more informative**: it states BOT's actual definition of `bot:Element` — *"a constituent of a construction entity with a characteristic technical function, form or position… any tangible object"* — where the original only said what BOT declines to do. **A positive statement of scope needs no defending, so *deliberately* is unnecessary rather than merely removed.**

> **Neutral voice (§6A.7b):** four oppositions removed — *"rather than by the topology one"*, *"Geometry is **not** aligned **either**"*, *"rather than as an RDF description… would duplicate"*, *"**Nor** is OPM aligned"*, *"complementary **rather than interchangeable**"*. *Left unaligned* states the decision; *while* and *whereas* carry the comparison without arguing.

**T4 — §2.2, declare the classification alignment module** *(comment 21's R3; introduces bSDD)*

*Before:* An IfcOWL alignment is kept out of the core on the same principle, where importing it would bind the schema to one exchange format.

*After:* A classification alignment module carries the correspondence to IFC. IFC is the internationally adopted open schema for cross-platform exchange in this domain, and openBIM deliverables are increasingly mandated (buildingSMART, 2025, 2026), so an alignment to it belongs to the schema's standards commitment.

> ⚠ **Ordinal collision caught by §6A.7c.** The first draft opened *"A third module carries classification"* — but this same paragraph already contains *"**A third module** carries the alignment axioms to the W3C and OGC standards stack"*. Two *third module*s in one paragraph. Naming the module removes the ordinal and the collision together. **The existing ordinal also goes stale** once T2 merges two topology modules into one, which is what **T17** repairs. It remains external to the core on the same principle that governs the other alignments, and the schema reaches it by reference: a minted term is related to the IFC class that classifies it, referenced at its identifier in the buildingSMART Data Dictionary (bSDD), the service that publishes each IFC class with a resolvable identifier and a definition. Alignment therefore proceeds by retrieving a candidate class through that service's search interface and storing the resulting reference, so the classification alignment module remains the size of its mapping axioms and the size of the IFC schema bears on it only through that search.

> **Neutral voice (§6A.7b):** *"a commitment of the schema **rather than an optional extension**"* was evaluative, and *"The schema's size is **no obstacle**, because… **rather than** by loading the schema"* argued against an objection. Both now state the mechanism, and the size conclusion follows from it. *"without importing ifcOWL"* is kept — it specifies what the module does, and is not an argument against a rival reading.

> **Trimmed by the redundancy sweep (§6A.7a):** *"whose full serialisation the schema deliberately avoids"* — Table 1 [P71] and the Introduction [P29] each already state it.

**T5 — §2.2, re-target the match and name its attachment point** *(amends applied E2 — needs `s-29130ee1`'s agreement)*

*Before:* Rather than importing a hierarchy, the schema relates its own generated terms to the imported spatial classes by annotation: a domain class is minted once into the shared vocabulary and carries a graded SKOS match to the BOT class it corresponds to, where one exists, so the author's own term is retained rather than replaced, while remaining resolvable to the external vocabulary.

*After:* Rather than importing a hierarchy, the schema relates its own generated terms to the external classes by annotation, and it does so on the Ontograph class itself: a domain class is minted once into the shared vocabulary and carries a graded SKOS match to its counterpart in the topology ontology and to the IFC class that classifies it, where each exists, so the author's own term is retained rather than replaced, while remaining resolvable to both external vocabularies.

> ⚠ **One surviving *rather than*, held back for your decision.** *"so the author's own term is retained **rather than** replaced"* is applied text from `AU-R151-ONTO`'s E2, and the phrase is the **record of binding decision `AU-R143-C01`** — the graded SKOS match is *additive, never substitution*. Rewording it unilaterally would edit another session's text at the one point where it encodes a constraint.
>
> A more formal alternative, which states the property `AU-R143-C01` specifies instead of implying it by contrast:
>
> *"…where each exists, so the match is additive and the author's own term is preserved, while remaining resolvable to both external vocabularies."*
>
> This is arguably **more** faithful to the decision than the original, since it names *additive* directly. **Not applied.** It needs `s-29130ee1`'s agreement, as T5 already does.

**T6 — §2.2, module inventory**

*Before:* The core module, the three extension modules, and the catalogue that binds them are itemised under Availability.

*After:* The core module, the three alignment modules, and the catalogue that binds them are itemised under Availability.

**T7 — §3.2, module inventory**

*Before:* Extension modules carry the alignment axioms to external vocabularies — currently the W3C/OGC standards stack, building topology, and a non-manifold spatial hierarchy — and further extensions can be added in the same manner.

*After:* Alignment modules carry the mapping axioms to external vocabularies — currently the W3C/OGC standards stack, topological structure, and IFC classification — and further alignments can be added in the same manner.

**T8 — §6.1, the anchor-coverage passage** *(replaces applied E7 text — needs agreement)*

*Before:* BOT anchors the spatial containment terms — Site, Building, Storey, Space and Zone — which is where agreement between projects matters most and is cheapest to obtain; element terms such as Facade or GlassPanel reach only the generic bot:Element, since BOT leaves element classification to other vocabularies (section 2.2), and urban terms such as Street or Plot have no counterpart in it at all and fall to the mint branch by construction.

*After:* The topology alignment anchors the spatial containment terms — Site, Building, Storey, Space and Zone — which is where agreement between projects matters most and is cheapest to obtain, and the classification alignment reaches the element terms, so that a term such as GlassPanel resolves to a panel class (section 2.2). Beyond those two anchors, a composite term such as Facade corresponds to an assembly of classes, and terms at urban scale, such as Street or Plot, fall to the mint branch by construction. The topology ontology is published without a version identifier, so the alignment records the date on which its terms were retrieved. Its containment and adjacency relations carry no transitivity or symmetry declarations, so the schema treats the alignment as a resolvable reference and evaluates containment and adjacency itself as graph paths (section 3.6).

> **Version risk folded in (§6A.11 item 2).** Approved as a §6.1-only note. It is carried by T8 instead of a separate edit because T8's before-string already ends this passage, so the two sentences need no anchor of their own. Both caveats are stated positively: what the alignment *records* (a retrieval date) and what the schema *does* (evaluates paths), in place of what the target lacks.

> **Neutral voice (§6A.7b).** *"resolves to a panel class **rather than to a generic building thing**"* argued against BOT's weakness; *"The reach is **not** complete"* framed a limit negatively. The replacement states where the anchors reach and what lies beyond them, which carries the same information positionally.

**T9 — §6.1, comment 21's sentence** — the entailment, broken

*Before:* The second follows from the first. IFC is the agreed open format for cross-platform exchange, and an IfcOWL alignment would let generated classes resolve against IFC entities under the same resolve-then-mint rule that the topology alignment already expresses, giving the schema a route to exchange without binding its core to one format.

*After:* The second question concerns exchange, for which section 2.2 carries a classification alignment module targeting IFC. That alignment establishes agreement on identity: a minted term and an IFC class are recorded as denoting entities of the same kind. Exchange requires a further determination — which information must accompany an object as it crosses between platforms — and that determination belongs to requirement specification, the direction in which the alignment is extended next.

> **Rewritten by the redundancy sweep (§6A.7a).** The first draft restated the coverage inventory — element terms resolving well, no facade class, urban terms outside both anchors — all of which **T8 already states**, and re-cited the openBIM mandate that the Introduction [P30] and T4 both carry. Removing the repetition exposed that under the Hybrid decision the second question had **no content of its own left**: *whether* to align is settled by §2.2, and *how far it reaches* belongs to the first question. The open question now stated is the one nothing else in the paper makes — that agreement on identity and agreement on exchange are different things. It sets up T14's IDS item without naming it, the paper's established discussion → future-work progression.
>
> **Neutral voice (§6A.7b).** The second draft answered comment 21 by *denying* the entailment (*"stands on its own rather than following from the first… not a consequence of how generated terms are resolved"*). **Deleting the entailment is the fix; denying it is redundant and reads defensively** — and a negation invites the reader to reconstruct the claim being denied. The replacement simply does not assert a linkage, and grounds the question in §2.2. The reviewer learns what changed from the `[AU-R151-TOPO]` traceability comment, which is where that explanation belongs.

**T10 — §6.1, E10b's closing clause** *(amends applied E10b — needs agreement)*

*Before:* the spatial terms BOT covers would carry across it, an IfcOWL alignment under question two would extend that reach to element terms, and terms with no counterpart in either would remain local to the organisation that minted them.

*After:* the terms the topology and classification alignments reach carry across it, and those lacking a counterpart in either alignment would remain local to the organisation that minted them.

> **Tightened by the redundancy sweep (§6A.7a).** This sits at the fourth question, a closing recap position, so it may point at the anchors but must not re-list what each covers — **T8 owns that inventory**. The contrast that makes the sentence work (anchored terms travel, unanchored ones do not) is preserved.

**T11 — Availability, module list**

*Before:* The core ontology module, its three extension modules (standards, BOT, Topologic)

*After:* The core ontology module, its three alignment modules (standards, topology, classification)

**T12 — Availability, the deposit rule**

*Before:* The deposit comprises the core ontology module and its catalogue; the three extension modules for the standards stack, building topology, and non-manifold topology;

*After:* The deposit comprises the core ontology module and its catalogue; the three alignment modules for the standards stack, topology, and IFC classification, each carrying only the mapping axioms the project authors, while the external vocabularies themselves — the W3C and OGC stack, Topologic and BOT, and IFC — are referenced at their published identifiers and remain external to the deposit;

**T13 — Annex C, one word**

*Before:* The standards extension module is the largest single body of reuse in the schema

*After:* The standards alignment module is the largest single body of reuse in the schema

**T14 — Conclusion, future work (3) narrowed to IDS**

*Before:* (3) deepen the standards bridges toward full topological reasoning and requirement-driven exchange workflows (IfcOWL/IDS).

*After:* (3) deepen the standards bridges toward full topological reasoning, and extend the classification alignment from class-level correspondence to requirement-driven exchange workflows (IDS).

**T15 — Conclusion, release sentence**

*Before:* The ontology, its extension modules, and the supporting artifacts will be released as open source

*After:* The ontology, its alignment modules, and the supporting artifacts will be released as open source

**T17 — §2.2, the standards module's stale ordinal** *(new — forced by T2's merge)*

*Before:* A third module carries the alignment axioms to the W3C and Open Geospatial Consortium (OGC) standards stack, itemised axiom by axiom in Annex C.

*After:* A standards alignment module carries the mapping axioms to the W3C and Open Geospatial Consortium (OGC) standards stack, itemised axiom by axiom in Annex C.

> **Required, not optional.** The paragraph currently counts the building-topology module first, the non-manifold module second, and the standards module *"third"*. T2 merges the first two into a single topology alignment module, which makes the standards module the **second** and the ordinal wrong. Naming each module instead of numbering it removes the dependency altogether, so no future merge or addition can strand a count. Verified against applied R15.2 at exactly one match.

**T18 — §6.1, the emergent-terminology sentence** *(new — amends applied E10b, needs `s-29130ee1`'s agreement)*

*Before:* Defining the full taxonomy of terms an architectural project might need is deliberately not attempted, because design terminology is emergent rather than canonical — it is produced in the course of designing rather than settled in advance of it (Lawson, 2005).

*After:* The vocabulary accumulates as designing proceeds, because architectural terminology is emergent — produced in the course of designing (Lawson, 2005).

> **Positive scope (§6A.7d).** The applied sentence carries **one defensive hedge and two oppositions** in a single clause: *"deliberately not attempted"*, *"emergent rather than canonical"*, *"produced in the course of designing rather than settled in advance of it"*. The positive half of each pair already carries the meaning, so the negated halves are removable without loss: a vocabulary that *accumulates as designing proceeds* is by that fact not fixed in advance. The Lawson citation and the argument are untouched. **Amends another session's applied text — held for agreement.**

**T19 — §5.4, class disjointness stated positively** *(new — author-approved 2026-09-07, outside the original anchor set)*

*Before:* Class disjointness is deliberately not embedded in the core TBox but supplied through a separate, curated overlay so the core remains minimal for reasoning;

*After:* Class disjointness is supplied through a separate, curated overlay, so the core remains minimal for reasoning;

> **The positive half was already in the sentence.** *"deliberately not embedded in the core TBox **but supplied** through a separate, curated overlay"* states the fact twice — once by denial, once by assertion. Leading with the assertion carries the whole meaning, and *deliberately* becomes unnecessary rather than merely deleted.

**T20 — Table 1 [P72], the *Standards alignment* cell** *(new — author-approved 2026-09-07)*

*Before:* OWL 2 DL / SWRL / SHACL / GQL path

*After:* OWL 2 DL / SWRL / SHACL / GQL path; IFC classification by reference

> Once §2.2 declares a classification alignment, this cell understates the schema on the very dimension Table 1 uses to position it. *by reference* keeps the row consistent with [P71]'s *"Low — no full IfcOWL serialisation required"* in the adjacent column: the schema reaches IFC, and it does so without serialising it.

**T16 — Figure 2 caption** *(paired with the figure revision, §6A.8)*

*Before:* Figure 2: Reuse and alignment of the four knowledge sources onto the Design Grammar ontology.

*After:* Figure 2: Reuse and alignment of the four knowledge sources onto the Design Grammar ontology, and the relationship between the external vocabularies the alignment modules reach.

### Not edited, deliberately

| | Why |
|---|---|
| §2.2 *"**Four sources** were analysed"* | Unchanged. FBS, DCM, BOT and Topologic remain the four analysed **sources**; what changes is how two of them are reached. **BOT is not removed from the paper**, so the count stands and Figure 2 needs no renumbering |
| Table 1 [P71] *"Low — no full IfcOWL serialisation required"*, [P47], [P29] | **Must remain true.** Nothing here imports ifcOWL; T4 states the avoidance explicitly, so the Conclusion and Table 1 now agree |
| §2.2 *"Three of these boundaries…"* cross-reference · E10a | Stay true under Hybrid |
| Table 1 [P72] *Standards alignment* cell | `T-leave` — logged in §13 |

### 6A.7a Redundancy sweep — every claim this package introduces

Run 2026-09-06 at the author's instruction, on the pattern of §6.11. Each claim the T-edits introduce was checked **against the manuscript** and **against the other T-edits**. **Six repetitions found; all six removed.**

| Claim introduced | Already stated at | Disposition |
|---|---|---|
| **Anchor coverage and its limits** — element terms resolve to IFC · no facade class, only an assembly · urban terms outside both anchors | **T8** · T9 · T10 — *three times* | **T8 keeps it.** Removed from T9 entirely; T10 reduced to a pointer. This was the author's example, and it was the largest repetition in the package |
| openBIM deliverables are increasingly mandated (buildingSMART, 2025, 2026) | Introduction ¶30 (**existing**) · T4 · T9 — *three times* | **T4 keeps it**, where the module is declared and a reader asks *why IFC*. Removed from T9, which points to §2.2 instead |
| A large external schema can be reached without importing it | T1 (general clause) · T4 (the specific mechanism) | **T4 keeps it.** T1's trailing clause removed — it forward-referenced what T4 states properly |
| External vocabularies are referenced, not redistributed | T1 (§2.2) · **T12** (Availability) | **Split by role.** T1 keeps the architecture principle (*referenced rather than redeclared*); *redistribution* is a deposit concept and stays in T12 alone |
| The topology/classification division | T2 (*"rather than what kind of thing it is"*) · **T3** | **T3 keeps it** — it is the paragraph that exists to record deliberate non-alignments. T2 keeps only its unique content, the attachment point |
| The schema avoids full ifcOWL serialisation | Table 1 [P71] (**existing**) · Introduction ¶29 (**existing**) · T4 | **Trimmed from T4** to *"without importing ifcOWL"*. Two existing statements are enough; the third was restatement, not progression |

**What the sweep exposed beyond repetition.** Removing the coverage restatement from T9 left the second question with **no content of its own** — *whether* to align is settled by §2.2 under the Hybrid decision, and *how far it reaches* belongs to the first question. That is a structural finding, not a wording one: it means the earlier T9 draft was padding a question that had been emptied. The rewrite gives it a genuine open question — **class-level correspondence is not exchange** — which no other part of the paper states.

**Not repetitions, checked and cleared.**

- **T2's attachment point** (core Topology concept) against **T5's** (the Ontograph class). These are the deliberate *contrast* that makes the two modules non-overlapping; stating one without the other would lose the point.
- **T9's** *"requirement specification"* against **T14's** *"requirement-driven exchange workflows (IDS)"*. Discussion raises the question, Conclusion lists it as future work — the paper's established progression, used already for the disjunctive-and-temporal-constraints item (§6.1 ¶308 → future work item 2). T9 deliberately does **not** name IDS.
- **T3's** OMG/FOG and OPM glosses against anything existing: `LBD`, `Linked Building Data`, `bSDD`, `OPM`, `BPO`, `OMG`, `FOG` all occur **0 times** in the manuscript. Every term this package introduces is genuinely new and is glossed at first use.
- **T11 / T12** (Availability) against **T6** (§2.2 inventory). §2.2 names the module count in the architecture; Availability itemises what is deposited. Different jobs, both needed for a reader who jumps to Availability.

**Net effect on the package:** still 16 edits, but roughly 120 words shorter in the manuscript, and the second question in §6.1 now carries an argument instead of an echo.

### 6A.7b Neutral voice — oppositions removed

Author's directive, 2026-09-06, prompted by T9's *"…a commitment section 2.2 makes on its own grounds, **not a consequence of how generated terms are resolved**."*

**The rule applied.** State what is the case. Do not define a position by denying an alternative — least of all an alternative a reviewer has raised, because a negation invites the reader to reconstruct the claim being denied and puts the paper in the posture of arguing rather than reporting.

**The distinction that governs which contrasts survive:**

| Removed — argues against a position | Kept — specifies a mechanism |
|---|---|
| *"not a consequence of how generated terms are resolved"* (T9) | *"referenced at its published identifier rather than redeclared here"* (T1) |
| *"stands on its own rather than following from the first"* (T9) | *"carried without importing ifcOWL"* (T4) |
| *"a commitment … rather than an optional extension"* (T4) | *"reached through alignment modules rather than embedded in the schema"* (T1 — the paper's existing wording) |
| *"The reach is not complete"* (T8) | *"the author's own term is retained rather than replaced"* (T5 — applied text, binding under `AU-R143-C01`) |
| *"resolves to a panel class rather than to a generic building thing"* (T8) | *"carries mapping axioms … and nothing else"* (T1 — definitional) |
| *"rather than through a second bridge of its own"* (T2) | |
| *"The schema's size is no obstacle, because … rather than by loading the schema"* (T4) | |
| *"Geometry is not aligned either"* · *"Nor is OPM aligned"* · *"rather than as an RDF description"* · *"complementary rather than interchangeable"* (T3) | |

A contrast that tells the reader **how the schema works** stays. A contrast whose only job is to **rebut a reading** goes.

**Second pass, same directive (2026-09-06): register.** The author extended the rule to pseudo-cleft constructions, the remaining contrastive *rather than*, and informal nouns.

| Pattern | Removed from | Replaced by |
|---|---|---|
| **Pseudo-cleft** — *"**What** that alignment establishes **is** agreement on identity"* | T9 | *"That alignment establishes agreement on identity"* |
| *"Exchange **asks a further question**"* — anthropomorphic | T9 | *"Exchange requires a further determination"* |
| *"the same kind of **thing**"* · *"that **thing** as it crosses between platforms"* | T9 | *"the same kind of **entity**"* · *"an **object** as it crosses between platforms"* — the latter matching the core band's own term |
| *"reached … **rather than** embedded in the schema"* | T1 | *"**remain external** and are reached through dedicated alignment modules"* |
| *"referenced … **rather than** redeclared here"* | T1 | *"referenced at its published identifier and **retains its own namespace**"* |
| *"divides … **rather than** one comprehensive schema"* | T1 | *"**distributes** building semantics across small interoperable modules"* |
| *"carries mapping axioms … **and nothing else**"* | T1 | *"carries **only** mapping axioms"* |
| *"**which is** the mechanism the schema already uses"* | T3 | *"the mechanism the schema already uses for it"* — appositive |
| *"those **minted without** a counterpart"* (and *minted* twice in one clause) | T10 | *"those **lacking** a counterpart"* |
| *"**are not redistributed** here"* | T12 | *"**remain external to the deposit**"* |

**Edits touched across both passes:** T1, T2, T3, T4, T8, T9, T10, T12. **Twenty-one constructions revised.** Before-strings are unaffected throughout, so §6A.10's predicted counts stand.

**One deliberate survivor.** T5's *"retained rather than replaced"* is applied text encoding binding decision `AU-R143-C01`; a formal replacement is proposed under T5 and held for `s-29130ee1`'s agreement.

### 6A.7c Named in place — elided subjects and stale ordinals

Author's directive, 2026-09-06, prompted by *"The second concerns exchange"* — **second what?**

**The rule applied.** Every sentence names its subject where the subject is used. A cross-reference to another section is **additional** to that naming, never a substitute for it: a reader who has not just read §2.2 must still be able to parse a sentence in §6.1. Ordinals that count things elsewhere in the paragraph are replaced by names, because a count goes stale whenever the set it counts changes.

| Elision | Edit | Named as |
|---|---|---|
| *"The **second** concerns exchange"* — second what | T9 | *"The **second question** concerns exchange"* — restoring the paragraph's own *"The first question concerns…"* / *"The third question concerns movement"* pattern |
| *"reaches **both**"* · trailing *"the alignment"* | T2 | *"**BOT and Topologic** are both reached…"* · *"the **topology alignment module** attaches…"* |
| *"the internationally adopted taxonomy"* — unnamed, and forward of where IFC is introduced | T3 | *"this schema aligns to **IFC**"* |
| *"a separate module **below**"* | T3 | *"the separate **classification alignment module** described below"* |
| *"its file-format companion (FOG)"* — acronym unexpanded | T3 | *"the **File Ontology for Geometry formats** (FOG)"* |
| *"**here** geometry travels…"* | T3 | *"**in this schema** geometry travels…"* |
| *"so **the two** describe change…"* | T3 | *"so **OPM and the Design State** describe change…"* |
| *"the **topology class** it corresponds to"* — of which ontology | T5 | *"its counterpart **in the topology ontology**"* |
| *"Beyond **them**"* | T8 | *"Beyond **those two anchors**"* |
| *"the terms **both anchors** reach"* · *"in **either**"* | T10 | *"the terms **the topology and classification alignments** reach"* · *"in either **alignment**"* |
| *"**This** follows the polylithic approach"* | T1 | *"**This use of alignment modules** follows…"* |

**Two stale ordinals, both structural.**

1. **Collision.** T4's first draft opened *"A third module carries classification"* while the same paragraph already reads *"**A third module** carries the alignment axioms to the W3C and OGC standards stack"*. Fixed by naming: *"A classification alignment module…"*.
2. **Stranded count — a defect this package would otherwise have introduced.** That existing *"A third module"* counts building-topology first and non-manifold second. **T2 merges those two**, making the standards module the second and the ordinal false. **T17** repairs it by naming rather than renumbering, which removes the dependency permanently.

**Edits touched:** T1, T2, T3, T4, T5, T8, T9, T10, plus new **T17**. The package is now **17 edits**; §6A.10's counts are updated accordingly.

**Where the rebuttal belongs instead.** Comment 21 objects to an entailment. The manuscript answers it by **no longer asserting one** — silence is the correction. The explanation of what changed and why goes in the `[AU-R151-TOPO]` Word comment, per the traceability spine. That separation is why the prose can afford to be neutral.

### 6A.7d Positive scope — negation-defined statements

Author's directive, 2026-09-07: *"avoid negation expressions… paraphrase them to positive statements. Then we don't need to defend all the time with the word 'deliberately'."*

**The rule applied.** State what a vocabulary, module or schema **does** cover. A scope defined by what it declines to do needs a hedge (*deliberately*, *intentionally*) to signal that the omission was chosen, and the hedge is the symptom: a positive statement of scope carries the same information and needs no defending.

**Manuscript sweep.** `deliberately` occurs **5 times**; `intentionally`, `by design`, `on purpose` occur **0**.

| # | Site | Status |
|---|---|---|
| 1 | §2.2 — *"The alignments that were **deliberately not made** are recorded here as well"* · *"constrains an instance of bot:Element **no further**"* | **Fixed in T3** — both fall inside its before-string |
| 2 | §6.1 — *"Defining the full taxonomy… is **deliberately not attempted**… emergent **rather than** canonical… **rather than** settled in advance"* | **T18** — applied E10b text, held for agreement |
| 3 | §3.2 ¶131 — *"The vocabularies inside them are **deliberately** standardised"* | **No defect.** The statement is already positive; *deliberately* here marks a design choice, not an omission. **Not edited** |
| 4 | §5.4 ¶302 — *"Class disjointness is **deliberately not embedded** in the core TBox **but supplied** through a separate, curated overlay so the core remains minimal for reasoning"* | **Out of scope** — outside every `AU-R151-TOPO` anchor. The positive half is already in the sentence, so the fix is to lead with it: *"Class disjointness is supplied through a separate, curated overlay, so the core remains minimal for reasoning"*. **Reported, not fixed** |
| 5 | §6.1 ¶308 — *"It **does not yet support** disjunctive rules, complex class expressions, or temporal constraints"* | **Out of scope**, and **arguably correct as written** — this is the *Expressiveness and limitations* section, where stating a limitation negatively is the section's job. A positive alternative exists (*"Support for disjunctive rules… remains future work"*), but the negation here reports a limit rather than defending a scope. **Reported, not fixed** |

**Edits touched:** T3, T4, plus new **T18**. Sites 4 and 5 are logged in §13 as out-of-scope observations, per constraint 9 — a manuscript-wide negation cleanup is not what comment 21 asked for, and both sit outside this label's anchors.

### 6A.8 Figure 2 — BUILT 2026-09-07, at the gate

**Status: produced, measured, and awaiting approval.** Files sit in `figures/R15.2_proposed/` and are promoted to `figures/R15.2/` only on approval. **No manuscript file was touched.**

| | |
|---|---|
| Source of record | `figures/R14.3/fig02_reuse_mapping.drawio` — **confirmed by the author**, and corroborated by mtime **2026-08-31 19:02**, matching FIGURES.md's record of the author revision of that date |
| Output | `fig02_reuse_mapping.drawio` (13 144 B) · `.png` (scale 4, **6578 × 6251**) · `.svg` — **triplet complete** |
| Print size | **8.02 pt as placed** (content 1502 units); 8.03 pt on the §4 `pageWidth` convention. Smallest font 25, `pageWidth` 1500, both unchanged. **4 units of headroom before the 8.00 floor** — see FIGURES.md §1a |
| Author revision | **2026-09-07, by hand.** Layout reworked — *Addressed by other means* moved to a left column beside BOT, source column compacted (content height 1585 → 1144), and the BOT ↔ IFC label extended to name `IFCOWL4_ADD2Alignment.ttl`. **`.png` and `.svg` re-exported**; both had gone stale against the revised `.drawio` |
| Renumbering | **None.** Figure 2 keeps its number and slot, so no in-text reference and no other caption moves |
| Bookkeeping | `figures/FIGURES.md` §1a added in the same round. The **missing `.svg`** that `R14.3/`'s Fig 2 has carried since 2026-08-31 is now closed |

**Layout defects found on first render and fixed:** two vertical edge labels overhung the left content margin, `t5`'s third line over-wrapped, and the `e6` label block sat 27 units left of its column centre. Re-exported and re-checked after each fix.

**Legibility defect found at author review, 2026-09-07 — the §6A.7c rule applies to figures too.** The author asked which subject *"LBD alignment, maintained externally"* referred to, IFC or BOT. It referred to **neither alone**: `e8` runs BOT ⇢ IFC bidirectionally and annotates the *relation* — LBD's published `IFCOWL4_ADD2Alignment.ttl`, which maps `bot:Site`/`Building`/`Storey`/`Space`/`Element` onto their `ifc:` counterparts, maintained by the W3C LBD Community Group rather than by this project. **A bare label on a vertical connector reads as belonging to whichever box it sits nearest**, so the label failed to name its own subject. `e6` carried the same fault more mildly, naming the target of the subsumption without naming what was subsumed.

| Edge | Was | Now |
|---|---|---|
| `e8` (BOT ⇢ IFC) | *"LBD alignment, maintained externally"* | *"**BOT ↔ IFC alignment** / published and maintained by LBD"* |
| `e6` (Topologic → BOT) | *"subsumed under BOT / 25 subClassOf, 4 subPropertyOf"* | *"**Topologic** subsumed under BOT / 25 subClassOf, 4 subPropertyOf"* |

**Name-in-place governs edge labels as well as prose.** A relation label must name both ends, because a reader cannot recover the endpoints from position alone.

**Content verified against the SVG**, every new label present exactly once — *Topologic ontology*, *w3id.org/topologicpy*, *reached through the Topologic ontology*, *IFC — buildingSMART*, *buildingSMART Data Dictionary*, *Ontograph*, *topology / classification / standards alignment module*, *subsumed under BOT*, *LBD alignment*, *Addressed by other means* — and every superseded label absent: *extension module: imported*, *extension module: declared*, *Not aligned*, *IfcOWL*, *minted in this project*.

### 6A.8a Original specification (satisfied by the build above)

**Revised in place. No new figure, and therefore no renumbering.** The precedent is explicit in `figures/FIGURES.md`: inserting the reuse-mapping diagram in §2.2 once before *"places it before the old Figure 2, so Figures 2–9 became 3–10. All 19 in-text references and 8 captions were updated in one operation."* With numbering carried as static literals and `SEQ`-field automation open since R14.2, a second cascade is a cost this round should not incur.

**What the figure must show**

| Element | Content |
|---|---|
| Absorption routes (unchanged) | FBS and DCM integrated **into** the core module |
| Three alignment modules | topology → `top:` · classification → IFC via bSDD · standards → W3C/OGC |
| **Inheritance chain** | `top:` ⊑ BOT ↔ ifcOWL — with **BOT shown as reached-through, not bridged** |
| **Two attachment points** | core **Topology** concept vs minted **Ontograph Class** |
| **Declared non-alignments** | OMG/FOG (geometry), OPM (property states), BPO (classification alternative) — dashed or greyed, visually distinct from live alignments |

**Production constraints**

| | |
|---|---|
| Source of record | `figures/R14.3/fig02_reuse_mapping.drawio` — the latest `.drawio` |
| Output | `figures/R15.2_proposed/fig02_reuse_mapping.{drawio,png,svg}`, promoted to `figures/R15.2/` only on approval |
| Tooling | draw.io desktop present at `C:\Program Files\draw.io\draw.io.exe`; house scripts in `figures/_tools/`. **No Draw.io MCP is available in this session** — the `.drawio` is edited as mxGraph XML and exported through the desktop CLI |
| Print size | Fig 2 currently clears the floor at **8.03 pt**. Must be **measured before the gate**, not after; a failure is reported, not absorbed |
| Bookkeeping | `figures/FIGURES.md` updated in the same round |

⚠ **Two pre-existing figure-state findings, reported not fixed.**
1. `figures/R14.3/fig02_reuse_mapping` ships `.drawio` + `.png` but **no `.svg`** — the triplet is already incomplete. Rebuilding Figure 2 this round is the opportunity to close it.
2. `FIGURES.md`'s R15.1 table records Fig 2 as revised (*"author revision, 2026-08-31"*), but `figures/R15.1/` contains **only `fig01`** files. The recorded revision is not in its round folder. **Confirm which source is current before editing.**

### 6A.9 The `top:` version risk — §6.1 only, as approved

**Verified absent** from `topologicpy.ttl`: `owl:versionInfo`, `owl:versionIRI`, `dcterms:created`/`modified`, any date string. Alignment-module best practice — the same SOSA/SSN literature §2.2 cites — is to declare which version of the target the alignment targets. **Here there is none to declare.** `top:` is served from GitHub Pages under a personal account behind a `w3id.org` redirect, at package version 0.9.x.

A second, narrower caveat: `top:` declares **no `owl:TransitiveProperty` or `owl:SymmetricProperty`** characteristics, where `bot:containsZone` is transitive and `bot:adjacentZone` symmetric in OWL 2 RL. The schema evaluates containment and adjacency as **GQL/Cypher path queries**, not OWL entailments, so little is lost — but the paper must claim *resolvability*, not *inference*.

**Both are recorded in §6.1 as handled risks, not in §2.2.** Wording **not yet drafted** — it belongs inside the applied §6.1 paragraph and would be a seventeenth edit. Flagged rather than smuggled in.

> ⚠ **`skos:closeMatch` is not subsumption.** No reasoner infers `dg:X ⊑ bot:Space` from `dg:X skos:closeMatch top:Space` plus `top:Space ⊑ bot:Space`. T2 says the schema *reaches* BOT's vocabulary, never that it entails it. **Do not strengthen that verb.**

### 6A.10 Predicted verification — filled in as actuals after apply

| Check | Predicted | Actual |
|---|---|---|
| `docx_replace.py` match count | **20 edits, each `1/1`** across 9 paragraphs | — |
| Paragraph diff | exactly §2.2 ¶2, Figure 2 caption ¶, §3.2 last ¶, **Table 1 [P72] cell ¶**, **§5.4 ¶302**, §6.1 ¶309, Availability ¶315, Annex C ¶367, Conclusion ¶313 — **no others** | — |
| Package parts | 42, unchanged | — |
| Paragraph count | 369, unchanged (no insertions) | — |
| `w:ins` / `w:del` | 4 / 0, unchanged | — |
| Comments | 12 → **12 + 1** (`[AU-R151-TOPO]`) **+ 7 retrospective `[AU-R151-ONTO]`**; comments 20 and 21 resolved | — |
| `validate_docx.py` | byte-identical to the backup | — |
| Figure 2 print size | **≥ 8 pt**, measured before the gate | — |

### 6A.11 Open items — status

**Resolved by the author, 2026-09-07.**

| # | Item | Resolution |
|---|---|---|
| 1 | Agreement on T5, T8, T10, T18 — edits amending applied text | **Authorised by the author**, who owns both sessions' work. Recorded in §2's claims table. T5 and T18 touch binding records (`AU-R143-C01`; E10b's Lawson argument), so their rationale stays visible in §6A.7 |
| 2 | §6.1 version-risk sentence | **Included as drafted, both sentences** — folded into **T8**, whose before-string already ends the passage it follows. One anchor, one edit |
| 3 | Figure 2 source ambiguity | **Resolved: `figures/R14.3/fig02_reuse_mapping.drawio`.** Confirmed by the author, and corroborated by its mtime — **2026-08-31 19:02**, matching FIGURES.md's record of the author revision of that date. It was never copied into `figures/R15.1/`, which is the whole of the bookkeeping gap |
| 4 | §7 *"Figure impact: None"* | **Corrected** — Figure 2 is revised this round, so the round-level statement is updated |
| 5 | Table 1 [P72] *Standards alignment* cell | **Joins the package as T20** |
| 6 | §5.4 *"deliberately not embedded"* | **Joins the package as T19** |

**Still open — carried, not blocking this label.**

7. **`ontology/` follows the paper.** Under Q4b the deposit is later rebuilt to this architecture: one topology alignment to `top:`, one classification alignment to IFC/bSDD, the standards module retained, the BOT bridge and the local Topologic declaration dissolved. **Not a write this round** — a roadmap item alongside §9.
8. **§6.1 ¶308** — *"It does not yet support disjunctive rules…"*. **Left as written by decision.** It reports a limitation inside the *Expressiveness and limitations* section, where a negation states a limit instead of defending a scope. Logged in §13.

**Blockers cleared since this plan was written.**

- **§11 item 0 is stale.** `~$_ITcon_DG_Draft_R15.2.docx` is **absent** as of 2026-09-07; Word is closed. `T1_ITcon_DG_Draft_R15.2.docx` is byte-identical to the apply state (`sha256:6b64cc92e672df99`, mtime 2026-09-06 20:57), so **every before-string in §6A.7 remains valid**.
- The other session's §11 items **2, 3, 4, 5 and 7** (Lawson reference, the E12 insertion mechanism, the E5/E6 cuts, the E8 trim, and round-trip verification) are **unchanged and still gate the joint apply**. They belong to `AU-R151-ONTO`, not to this label.

---

## 6B. Joint apply — the single pass

**Author's instruction, 2026-09-07: the whole round applies in one pass.** Nothing is written until every gate below is green. `AU-R151-TOPO` is otherwise **complete and idle** — 20 edits drafted and verified, Figure 2 built and measured.

### 6B.1 Readiness

| Label | State | Blocking |
|---|---|---|
| `AU-R151-ONTO` (E1–E15) | **already applied** to R15.2 on 2026-09-06 | — |
| `AU-R151-TOPO` (T1–T20 + Figure 2) | **ready** — all 20 before-strings verified at one match; figure built, 8.03 pt | nothing of its own |
| Traceability backlog | 7 retrospective `[AU-R151-ONTO]` comments; comments 20 and 21 to resolve | rides with the pass |

### 6B.2 Gates that must be green before the pass starts

| # | Gate | Owner | State 2026-09-07 |
|---|---|---|---|
| 1 | Word closed on `R15.2.docx` | Author | ✅ **clear** — no `~$` file; hash `6b64cc92e672df99` unchanged |
| 2 | Author authorisation for T5, T8, T10, T18 | Author | ✅ **given** |
| 3 | Figure 2 approved | Author | ⬜ **pending** — built, at the gate |
| 4 | **Lawson reference confirmed** — publisher and year supplied were wrong; corrected entry carries no DOI | Author | ⬜ **open** |
| 5 | **E12 insertion mechanism** — a reference-list entry cannot be added by `docx_replace.py`; needs a clone of the `[P333]` paragraph node with its hanging indent preserved | Run before the pass | ⬜ **open** |
| 6 | **E5 / E6 cuts** — two recommended trims, both the author's wording | Author | ⬜ **open** |
| 7 | **E8 *generative* trim** — recommended against; author's call | Author | ⬜ **open** |
| 8 | **Round-trip verification** — comment preservation, tracked changes, citation fields, on a throwaway copy | Run before the pass | ⬜ **open** |

Gates 4–8 belong to `AU-R151-ONTO`. They gate the pass, not this label.

### 6B.3 Order of operations

Ordering matters in three places, and nowhere else.

1. **Acquire the advisory lock**; re-run the live-file guard; re-verify all 20 `AU-R151-TOPO` before-strings against the live file. Any drift → re-anchor and **re-fire the gate**.
2. **Capability probe** on a throwaway copy — the no-op identity round trip, which also discharges gate 8.
3. **Back up** to `scratchpad/T1_ITcon_DG_Draft_R15.2_BACKUP_before_joint_apply.docx`.
4. **Apply the replacements.** Order among them is free — every before-string is disjoint, and `docx_replace.py` refuses on any mismatch. **Exception:** T17 and T4 both concern §2.2's module ordinals, so verify the paragraph reads correctly once both have landed.
5. **Apply E12 last**, because it is the only *insertion* and the only operation that changes the paragraph count (369 → 370). Applying it earlier would invalidate every paragraph index reported afterwards.
6. **Promote Figure 2** — `figures/R15.2_proposed/` → `figures/R15.2/`; re-embed in the manuscript; confirm the placed width still yields 8.03 pt.
7. **Add the comments** — one `[AU-R151-TOPO]`, seven retrospective `[AU-R151-ONTO]`; resolve comments 20 and 21.
8. **Verify** against §6A.10 and §6.8 together, then promote both labels into `T1_ITcon_DG_Draft_R15.2_revision-summary.md` and fill §12.

### 6B.4 Combined predicted verification

| Check | Predicted |
|---|---|
| Replacements | **20** (`AU-R151-TOPO`), each `1/1`, plus any `AU-R151-ONTO` residue from gates 6–7 |
| Insertions | **1** (E12, the Lawson entry) |
| Paragraph count | 369 → **370** |
| Paragraphs modified | 9 by `AU-R151-TOPO` — §2.2 ¶2, Fig 2 caption, §3.2 last ¶, Table 1 [P72], §5.4 ¶302, §6.1 ¶309, Availability ¶315, Annex C ¶367, Conclusion ¶313 |
| Package parts | 42, unchanged |
| `w:ins` / `w:del` | 4 / 0, unchanged |
| Comments | 12 → **13**, and 9 → **11** resolved |
| `validate_docx.py` | byte-identical to the backup |
| Figure 2 | 8.03 pt, triplet present in `figures/R15.2/` |

**A mismatch on any row stops the pass and restores from the backup.** Partial application of a joint pass is the one outcome to avoid: it leaves two labels half-landed with no clean restore point.

---

## 7. Figure impact

**Updated 2026-09-07 — `AU-R151-TOPO` revises Figure 2.** The statement below was written when `AU-R151-ONTO` was the round's only label and remains true of that label; it is no longer true of the round.

**`AU-R151-ONTO`: none.** No comment in that label's scope implicates a figure.

**`AU-R151-TOPO`: Figure 2 is revised in place** — same number, same slot, so **no renumbering**. Source confirmed as `figures/R14.3/fig02_reuse_mapping.drawio` (mtime 2026-08-31 19:02, the author revision FIGURES.md records). Output goes to `figures/R15.2_proposed/`, promoted to `figures/R15.2/` on approval, and completes the `.svg` that R14.3's triplet lacks. Specification and production constraints: **§6A.8**. Caption edit: **T16**.

Carried forward unfixed from R15.1 §8, and still not in scope: Figure 1 print size 6.06 pt against an 8 pt floor; Figures 2, 4, 5, 9 embedded at 220 DPI.

---

## 8. Proposed survey updates

| This round did | Must update | Proposed change |
|---|---|---|
| Read a new source | `corpus_log.md` | None — no external source read |
| Found a source, did not read it | `backlog.md` | None |
| Changed or added a claim | `synthesis/claim_evidence_audit.md` | **Yes** — Ontograph layer scope changes from project-scoped to organisation-shared across §2.1, §2.2, §3.2, §3.6, §4, §6.1; and a fourth open question is added at §6.1 |
| Resolved or opened a reviewer comment | `synthesis/publication_readiness.md` | **Yes** — `AU-R151-ONTO` resolved; the CQ4 qualification recorded as a narrowed claim |
| Did state-of-the-art work | `synthesis/novelty_positioning.md` | None |
| Hit a cross-paper boundary | `synthesis/concept_ownership_matrix.md` | **Check** — the coherence map gives T1 the OntoGraph/Metagraph schema, so this is within T1's allocation. Record that it was checked |
| Touched any project number | `inventory/metrics.py` | None — no number enters the manuscript this round |
| Completed a round | `survey_intent.md` §2 | **Yes** — advance the surveyed revision to R15.2 at round close |

### 8.1 Measure-first

| Number proposed for the manuscript | Where | `metrics.py` value | Match |
|---|---|---|---|

Empty by design: **no number enters the manuscript this round.** The counts in §6.3's vocabulary table are measurements *about* the manuscript, used to decide E9; none of them is written into it.

### 8.2 Surveyed-content currency

| Field | Value |
|---|---|
| Survey records the manuscript at | R15.1 |
| Manuscript will be at | R15.2 |
| Advance proposed this round | **yes**, at round close |

---

## 9. Project artifacts — code change request, NOT a write

Q4b = theoretical, so **no project artifact is written this round and no paper claim rests on repository state.** The author asked for the divergence to be recorded as a roadmap item.

The paper will state the corrected model; the implementation does not match it. Scope strictly to `Class` / `DatatypeProperty` / `ObjectProperty` — `Var` must keep its `project` merge key, since dropping it is what caused the shipped v2.0 cross-project collision bug recorded in the DG-ID decision note.

| Change | Where |
|---|---|
| Stop writing `project` on OntoGraph labels | n8n `rules-to-metagraph.json` (`Prepare Graph Payload` → `Annotate Graph Props` back-fill), `cypher_template.txt`, `training/dataset_schema.json`, `llm/cypher_catalog.json` |
| Drop `AND n.project = $project` so the candidate set is organisation-wide | `data-service/dg_context.py:318` |
| Drop OntoGraph project filters | `Neo4jOntoGraphRepository.cs` (3 queries), `ui-v2/src/lib/graphApi.js` `fetchGraph`; stop `tagProjectNodes` claiming OntoGraph nodes |
| Add a uniqueness constraint on `Class.iri` | none exists today, and *"defined once"* depends on it |
| Migration for OntoGraph nodes already stamped by the last-write-wins path | `migrations/` |
| Add the alignment step — agent proposes, human approves before mint | CTXA-05 forbids embeddings for determinism, so the matcher is either an explicit LLM call with a recorded verdict or a graded lexical match. **That choice is not made here** |

**Propagation surfaces** per `CLAUDE.md`: `cypher_template.txt`, `dataset_schema.json`, n8n prompts, `config.template.js`, data-service Cypher, `spec/DATABASE.md`, `ontology/dg-shapes.ttl`, `llm/structure_rules.json`, `.github/copilot-instructions.md`, `README.md`. The vault note *"Project isolation uses property filtering not separate databases"* records cross-project class sharing as unrealised potential and becomes stale once this lands.

---

## 10. Proposed new citations

| Proposed citation | Discovery route | DOI | Resolved record | Where cited |
|---|---|---|---|---|
| Lawson, B. (2005). *How designers think: The design process demystified* (4th ed.). Architectural Press. | Supplied by the author | **none found** — monograph; Crossref and OpenAlex both unreachable from this machine | ISBN 978-0-7506-6077-8, verified via Perplexity against the Elsevier listing, Open Library and the Internet Archive record | §6.1 ¶300 (E10b), reference list (E12) |

⚠ **The two-tier citation rule is not fully satisfied**, and that is recorded rather than waved through: the rule admits a citation only on a DOI-resolved record, and no DOI was obtainable here. Two mitigations apply — the reference was supplied by the author rather than generated, and the paper already carries at least one DOI-less entry (`Mubarak, 2004`). **The publisher and year supplied were wrong** (see E12), so confirm the corrected entry against your reference manager before applying.

---

## 11. Open questions and blockers

| # | Question / blocker | Blocks | Who answers |
|---|---|---|---|
| 0 | **R15.2 is open in Word** (`~$_ITcon_DG_Draft_R15.2.docx`) | **All applies** | Author — close Word |
| 0b | **Traceability comments missing for the seven applied edits**, and comment 20 still unresolved — see §6.14 | Round close | Author — add retrospectively, or record the gap deliberately |
| 0c | **E13 and E14 are defects in text already in R15.2**, not proposals | Nothing — but they should go in with the next apply | Author |
| 1 | Who applied E1–E6 and E9, and is that session still working? A stale claim is reported, never released | The joint apply | Author / the other session |
| 2 | **Lawson reference** — publisher and year supplied were wrong; corrected entry has no DOI. Confirm against your reference manager | E10b, E12 | Author |
| 3 | **E12 is a paragraph insertion**, which `docx_replace.py` cannot perform — needs a clone-and-insert of the `[P333]` node | E12 | Run before applying |
| 4 | Two recommended cuts not applied, both your wording: E5's doubled *human*, E6's closing sentence | E5, E6 | Author |
| 5 | Optional: trim the *generative* explanation in E8 — I recommend keeping it, see §6.11 | E8 | Author |
| 6 | Concurrent session's labels not yet drafted | The joint apply | The other session |
| 7 | Comment-preservation, tracked-changes and citation-field round trips not yet verified | The first write | Run before applying |

**Closed 2026-09-06:** the CQ4 qualification, previously question 2 — resolved constructively in E10b by separating *offices sharing one CDE* from *separate organisations*, so §5.4 needs no edit.

---

## 12. Promotion record

| Label | Approved at | Applied at | Promoted to summary § | Plan block marked |
|---|---|---|---|---|
| `AU-R151-ONTO` | 2026-09-05, re-fired 2026-09-06 | 2026-09-06 | summary §2, §3, §4 | promoted |

A label showing `applied` in §2's claims table with no row here is a traceability hole. The two must agree.

## 13. Out-of-scope observations — recorded, NOT fixed

1. R14.4's §6.1 replacement never reached the R15 lineage, lost when R14.4 was retired — which is why §2.2 and §6.1 disagreed. Superseded by this round, but worth knowing the retirement dropped an approved edit.
2. Table 3 and the Figure 4 caption may restate per-project isolation. **Check at apply time**; raise separately rather than widening this diff.
3. The deleted scalability paragraph — multi-tenant, sharding, national regulatory libraries — is still absent from the R15 lineage. Open since R15.1 §9, and it is exactly the kind of limitation reviewers ask for.
4. The `SEQ`-field numbering request is open in its 6th round.
5. `BF-R15-Ct` (validation time *t*) still deferred.
6. The SKOS match vocabulary decided in R14.4 was never written back to the vault as a decision note.
7. **Two further uses of *discipline* in the methodological-rigour sense**, both outside this label's anchors and therefore not fixed: §3.5 ¶199 *"the graph-grounded discipline that distinguishes reliable text-to-Cypher systems"* and §7 ¶302 *"depends on explicit population discipline"*. With E11 applied the word means the design-field sense everywhere except these two. Cheap to fix — *"the graph-grounded practice"* and *"explicit population of the graph"* — but each is a separate paragraph and would widen this diff. Say the word and they become E13/E14.
8. §3.6 ¶173 *"The schema also supports accumulation and sharing of design grammars across offices and projects"* asserts cross-office sharing flatly, which E10b now frames as bounded by the CDE. Not a contradiction — offices within one CDE do share — but a reviewer reading §3.6 before §6.1 may see a stronger claim than the paper defends.
