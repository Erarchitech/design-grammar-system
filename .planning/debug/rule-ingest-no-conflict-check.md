---
status: awaiting_human_verify
trigger: "КОгда я вставляю новое правило через ingest в Graph Viewer, правило создается новым даже если этот же класс объекта с аналогичным правилом уже существует, которое противоречит новому вводу. Например, я ввожу: \"Building height maximum is 50 m\" и создается новое правило, хотя уже есть правило в этом графе \"Building height is maximum 75 meters\". В результате оба правила продолжают существовать параллеьно и конфликтуют друг с другом. Вместо этого система должна проверять введенное правило на пересечение с существующими правилами и явно выводить предупреждение с указанием существующего правила и предлагать замену или обновление существующего правила с новым значением."
created: 2026-09-19
updated: 2026-09-19
goal: find_and_fix
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  status: awaiting_human_verify
---

# Debug: rule ingest creates conflicting duplicate rules with no conflict check

## Symptoms

**Expected behavior**
Ingesting a natural-language rule that grounds to the same Ontograph signature as an existing
Rule should NOT silently create a second Rule. The system should detect the overlap, present a
blocking preview naming the existing rule (its `Rule_Id`, NL description and current threshold),
and offer: **Replace / Update / Keep both / Cancel**.

**Actual behavior**
A new `Rule` node is created unconditionally. Both rules persist in the Metagraph in parallel and
contradict each other at validation time. No warning is surfaced anywhere in the UI.

**Reproduction**

1. Graph Viewer (V2 UI, `ui-v2/`), project has existing rule `R_URB_HEIGHT_MAX_75_V`
   ("Building height is maximum 75 meters").
2. Ingest the NL rule: `Building height maximum is 50 m`.
3. Observe: a second max-height Rule node is created; no conflict warning; both rules coexist.

**Error messages**
None. Silent — this is a missing gate, not a crash.

**Timeline**
Unknown / unsure whether ingest ever de-duplicated. Determine from git history and from the
n8n workflow definitions. NOTE: live n8n workflows have drifted ahead of `n8n/workflows/*.json`
in the repo (recorded in CLAUDE.md "Current Priorities" #1) — read the live published version,
not just the repo JSON. See memory: n8n runs the published version, not the draft.

## User-specified acceptance criteria

**Conflict key (user-chosen):** `Class` + `DatatypeProperty` + **comparator**.
i.e. `Building` + `hasHeightM` + `swrlb:greaterThan` collides with the existing max-75 rule,
regardless of the literal value. Comparator MUST be part of the key so that the sanctioned
min+max range decomposition (`lessThan` + `greaterThan` on the same property) is NOT flagged.

**UX (user-chosen):** blocking dialog. Ingest pauses; the existing rule is shown verbatim with
its `Rule_Id` and current value; user explicitly chooses Replace / Update / Keep both / Cancel.

**Layer:** NOT pre-decided. Investigate the live ingest path and place the gate where Ontograph
grounding already resolves. Report the choice with evidence. Candidate layers:
`ui-v2/` client pre-flight · `n8n/workflows/rules-to-metagraph.json` · `data-service/`.
A client-only check is bypassable and is not on the server-side path — prefer server-side unless
evidence says otherwise.

## Normative specification — paper T1 ITcon R15.6 (§4)

The orchestrator read `Publications/T1_ITcon_DG_Draft_R15.6.docx`. The paper already specifies
the gate that is missing. This is a **conformance gap between §4 and the shipped runtime**, not
merely a feature request.

- **[P143] §4 — the five-stage authoring process (normative):**
  `tag → recognise → preview → confirm → publish`.
  "Recognition identifies candidate vocabulary terms and constraint structures, while **preview
  presents the proposed representation for human review**. **Confirmation establishes the
  representation that may be published** to the project graph."
  → Current ingest implements `tag → recognise → publish`. **preview and confirm are absent.**
  The requested blocking dialog IS this preview+confirm stage.

- **[P138] §4 — grounding:** "A natural-language constraint is **resolved against the classes and
  properties declared in the shared Ontograph**. … The identified constraint type — such as an
  upper bound, lower bound, range, ratio, count, or Boolean requirement — **determines** the
  corresponding sequence of SWRL atoms."
  → The resolver already computes (Class, DatatypeProperty, comparator). The conflict key is not
  invented; it is the paper's own grounding signature. Place the check where this resolution
  already happens.

- **[P139] §4 — flow:** "… Ontograph grounding, candidate BOT/LBD and IFC/bSDD references,
  TopologicPy analysis where geometry is available, **operator review**, and evaluation against
  Design Rules. **Approved** results are recorded in the project graph together with provenance."
  → Publication is gated on operator approval. Provenance must be recorded on the approved result.

- **[P129] §4 — Ontograph governance:** evolves through "versioned proposals, operator or
  ontology-steward approval, provenance recording, **impact analysis and regression checks**."
  → A Replace/Update action is a versioned change and should record provenance, not silently
  overwrite.

- **[P109] §3.4 — one atomic constraint per rule node:** "Minimum constraints are implemented
  using `swrlb:lessThan`, maximum constraints with `swrlb:greaterThan`, and equality constraints
  with `swrlb:notEqual`. **Range constraints are broken down into separate lower and upper
  constraints** instead of a single compound rule … preserving the principle that each rule node
  encodes one atomic constraint."
  → Confirms: two `greaterThan` rules on one grounding = illegitimate conflict.
    `greaterThan` + `lessThan` on one grounding = the sanctioned range pair, must NOT be flagged.

- **[P77] / [P181] — honest limitation:** the paper explicitly lists "the reliability of
  LLM-assisted authoring" and "operator-review workload" as NOT yet established (future work).
  So §4 specifies the confirm gate but reports no runtime evidence for it. Implementing this
  closes a paper↔dev consistency gap. Consider a note in
  `DG_OBSIDIAN/dissemination/consistency-map.md` when resolved.

## Ownership per spec/RULE-PARTITION-POLICY.md

This check is **neither SWRL nor SHACL**:

- SHACL owns "Rule structural integrity … validates the *shape* of a Rule node, not the *content*
  (truth) of its design constraint — **SHACL never evaluates whether the rule's SWRL logic is
  correct**". Cross-rule semantic overlap is content, not shape.
- SWRL owns evaluating a design against a rule, not comparing two rules to each other.
- Therefore this is a **corpus-level authoring-time gate** — a new surface alongside the existing
  four (SWRL VALIDATOR, SHACL, Computgraph Cypher checks, Phase 38 input bindings).
- **`spec/RULE-PARTITION-POLICY.md` needs a new decision-table row for it** as part of the fix.

## Known context / gotchas (from CLAUDE.md + memory)

- Ingest path: `ui-v2/src/screens/GraphScreen.jsx` → `ui-v2/src/lib/graphApi.js`
  → `POST /n8n/webhook/dg/rules-ingest` → n8n → data-service `/llm/generate` → Neo4j.
- **n8n runs the published version, not the draft** — import alone changes nothing; publish +
  restart, and read `execution_data.workflowData` to see what actually ran.
- **Neo4j `tx/commit` returns HTTP 200 with `errors[]`** — never infer write success from status.
  One statement per entry; do NOT split on `;` (variable scope).
- **Neo4j node tagging** required after n8n ingestion — orphaned nodes need `graph`/`project`
  props; the V2 UI claims `default-project` nodes for the active project after each ingest.
- Rule ID format: `R_<DOMAIN>_<PROPERTY>_<LIMIT>_V` (e.g. `R_URB_HEIGHT_MAX_75_V`). Note the
  value is embedded in the ID, so a max-50 and a max-75 rule have *different* IDs — matching on
  `Rule_Id` alone would NOT catch this bug.
- Schema change propagation list is in CLAUDE.md — if the fix changes graph structure, update ALL
  listed artifacts.
- Related prior session: `.planning/debug/ingest-stuck-commit-metagraph.md` (same pipeline).
- A semantic rule *deletion* feature already shipped (commit `bd28f1f`, "LLM-selected conditional
  deletion with safe orphan handling") — **read it first**; it likely already contains a
  rule-matching/selection mechanism this fix can reuse rather than reinvent.
- **Deploy and verify live** (user preference): a fix must reach the running containers and be
  re-tested against the real scenario, not just committed. Rebuild UI with `--no-cache`.

## Evidence

- timestamp: 2026-09-19T(session start)
  checked: commit bd28f1f (semantic rule deletion) — data-service/dg_context.py L1490-1611,
    data-service/app.py L2900-3040
  found: Reusable pattern already exists for LLM-assisted rule operations: (1)
    `fetch_rules_for_selection(project)` reads a lightweight catalogue (Rule_Id + SWRL +
    description) for every rule in the project via Cypher; (2) LLM is given the catalogue and
    asked a structured question, constrained by a strict system prompt requiring JSON-only
    output; (3) `_parse_selection_response()` parses tolerantly (strips code fences, regex
    fallback for embedded JSON) and validates every returned id against the known-id set,
    separating out `hallucinated` ids that are reported but never acted on; (4)
    `/rules/resolve-deletion` is a selection-only endpoint (no writes) that also attaches a
    `_rule_delete_preview()` per matched rule so the confirmation dialog can show exactly what
    would be affected; (5) `/rules/bulk-delete` is a separate confirm-only endpoint that takes an
    explicit id list already approved by the user and re-derives nothing itself.
  implication: This is a direct architectural template for the conflict-check gate: fetch
    candidate rules -> deterministic (not LLM) match on grounding signature -> preview endpoint
    -> confirm endpoint that performs Replace/Update/Keep-both. Deletion selection uses the LLM
    for matching because deletion requests are open-ended NL; conflict detection should NOT need
    the LLM for matching (the grounding signature — Class/DatatypeProperty/comparator — is
    already deterministically resolved during ingest grounding per paper [P138]), so the new gate
    can be a pure Cypher/Python comparison, cheaper and more reliable than an LLM call.
  files_of_interest: data-service/dg_context.py (fetch_rules_for_selection,
    _parse_selection_response, select_rules_for_deletion), data-service/app.py
    (preview_rule_deletion, delete_rule, resolve_rule_deletion, bulk_delete_rules,
    _rule_delete_preview — need to locate this helper's definition).

- timestamp: 2026-09-19T(session continued)
  checked: ui-v2/src/lib/graphApi.js L249-295 (callWorkflow, ingestRules)
  found: `ingestRules()` POSTs `{rules_text, cypher_prompt:false, project, project_name}`
    directly to `cfg.n8nWebhook` (the n8n rules-ingest webhook) with zero client-side pre-flight,
    validation, or dialog. `callWorkflow()` just fires the request and polls
    `/execution-result/{id}` for completion. Confirms: no client-only gate exists today, and any
    fix placed purely in ui-v2 would need a matching server-side read anyway.
  implication: rules out "gate already exists client-side but is broken" — it doesn't exist at
    all, anywhere in the pipeline.

- timestamp: 2026-09-19T(session continued)
  checked: live n8n instance — exported all 18 workflows via
    `docker exec n8n n8n export:workflow --all --output=...` (file-based export inside the
    container; avoided transmitting extracted basic-auth credentials over an HTTP call, which the
    sandbox's credential-exploration classifier correctly blocked when attempted via curl).
  found: the truly ACTIVE "DG Rules -> Metagraph" workflow has id
    `a1b2c3d4-e5f6-7890-abcd-ef1234567890`, active:true, updated 2026-09-18T12:28:40 (one day
    before this session — matches the ingest-stuck-commit-metagraph fix timestamp). There are 17
    other archived/inactive copies of the same workflow name from earlier dates — confirms the
    "n8n runs the published version" gotcha is real (many stale copies exist) but also confirms,
    by diffing node names, that THIS active copy's 19-node topology is byte-identical to
    `n8n/workflows/rules-to-metagraph.json` in the repo. No drift for this specific investigation
    — repo JSON is safe to read as ground truth for the current live behavior.
  implication: eliminates "the bug is caused by live/repo drift" as a hypothesis. The repo file's
    node graph accurately describes what actually runs.

- timestamp: 2026-09-19T(session continued)
  checked: n8n/workflows/rules-to-metagraph.json (full node graph, confirmed live-identical above)
  found: linear pipeline with NO branch/node that reads existing Rule content before writing:
    Ingest Rules (webhook) -> Set Input Defaults -> Assemble Context (POST /context/assemble)
    -> Build LLM Prompt -> Generate Validated Cypher (POST /context/generate-cypher)
    -> Handle Cypher-Gen Error -> Cypher Gen Failed? -> Parse LLM Output
    -> Prepare Graph Payload -> Execute LLM Cypher (POST neo4j /db/neo4j/tx/commit, RAW WRITE)
    -> Annotate Graph Props -> Build Response -> Store Result.
    The "Build LLm Prompt" node's own inline comment (functionCode, dated Phase 29-05) explicitly
    documents a KNOWN REGRESSION: "the original node also scored prompt keywords against EXISTING
    RULE TEXT to infer an edit target when no explicit Rule_Id was mentioned... that scoring
    fallback is not reproducible from /context/assemble's response. Edit detection here is now
    Rule_Id-mention-only." I.e. a prior version of this pipeline at least *fetched existing rule
    text* for edit-target inference (weaker than a conflict check, but adjacent) and this was
    dropped during the Phase 29-05 refactor to a thin n8n caller / fat data-service assembler.
  implication: STRONG — this is the single write path for all rule ingestion (both create and
    edit). There is exactly one place a gate can intercept before "Execute LLM Cypher": inside
    "Generate Validated Cypher" (i.e. data-service `/context/generate-cypher` /
    `generate_validated_cypher()`), or earlier inside "Assemble Context" (i.e.
    `/context/assemble` / `assemble_context()`). Both live in data-service, not n8n or ui-v2.

- timestamp: 2026-09-19T(session continued)
  checked: data-service/dg_context.py L341-358 (fetch_existing_entities),
    L457-504 (assemble_context), _EXISTING_ENTITIES_QUERY (L316-323)
  found: `assemble_context()` calls `fetch_existing_entities(project)` which runs
    `_EXISTING_ENTITIES_QUERY`: `MATCH (n) WHERE (n:Class OR n:DatatypeProperty OR
    n:ObjectProperty) AND n.graph='OntoGraph' AND n.project=$project RETURN labels(n)[0],
    n.iri, n.label, n.SWRL_label, n.range`. This is OntoGraph-only (vocabulary), explicitly
    NOT Metagraph (Rule/Atom) data. The returned `existing_entities` list is injected into the
    context dict verbatim and is the ONLY "what already exists" signal the LLM prompt receives.
    No Rule, Atom, or SWRL-body data from the Metagraph is ever fetched or shown to the LLM
    during rule_ingest. Confirmed by re-reading the full `assemble_context()` body (L457-504):
    the returned context dict keys are type/project/ontograph/metagraph(concepts, not
    instances)/validgraph(concepts)/computgraph/swrl_conventions/selected_cypher_shapes/
    existing_entities — no rules/atoms instance data anywhere.
  implication: CONFIRMS root cause location #1 — the grounding step (`assemble_context`) has
    all the machinery to add a "here are existing Rules with this Class+Property+comparator
    signature" fetch (identical shape to fetch_existing_entities, just filtered to
    :Rule/:Atom/:Builtin instead of :Class/:DatatypeProperty/:ObjectProperty), but does not.

- timestamp: 2026-09-19T(session continued)
  checked: data-service/dg_context.py L507-778 (validate_cypher, ALLOWED_LABELS/RELATIONSHIPS/
    PROPERTIES, WRITE_VERBS, all regex-based structural checks: empty_output, no_cypher_statement,
    unbalanced_brackets, malformed_node_pattern, label/relationship allow-list, DesignState.kind
    enum, key-name quality checks)
  found: `validate_cypher()` (Phase 29-04, docstring: "the phase's PRIMARY security control") is
    exhaustively structural/syntactic: schema allow-lists, write-verb policy (MERGE/SET only),
    bracket-nesting, malformed-node-pattern, positive-shape checks (must contain a MERGE), and
    key-name conventions (Rule_Id/Atom_Id/SWRL_label naming). It never queries Neo4j and never
    compares the generated Cypher's target grounding (Class/DatatypeProperty/comparator) against
    any other Rule already in the graph. It answers "is this syntactically/schematically valid
    Cypher?", never "does this collide with an existing rule?".
  implication: CONFIRMS root cause location #2 (alternative placement) — this is the other
    candidate insertion point, but a poorer fit than assemble_context: validate_cypher receives
    only the raw generated Cypher string, not the resolved (Class, DatatypeProperty, comparator)
    triple in structured form. It would need to re-parse the Cypher to recover the grounding,
    duplicating logic that assemble_context (or a small addition to it) could produce naturally
    from the pre-generation grounding, and does so BEFORE any LLM call is even made — this
    ordering matters because a blocking dialog for Replace/Update/Keep-both/Cancel needs to run
    BEFORE the LLM synthesizes new Rule/Atom Cypher, not after.

- timestamp: 2026-09-19T(session continued)
  checked: spec/RULE-PARTITION-POLICY.md (full file)
  found: confirms the debug file's own prior analysis — SWRL VALIDATOR owns design-compliance
    evaluation, SHACL owns Rule *structural* shape (Rule_Id format, atom order) and explicitly
    "never evaluates whether the rule's SWRL logic is correct." Two precedent "fourth surface"
    additions already exist and are documented as addenda without new D-numbers: "Computgraph
    Structural Checks (Phase 37)" (deterministic Cypher, data-service/cg_structure_checks.py,
    reuses SHACL's violation/warning/info severity vocabulary) and "Input Generation Bindings
    (Phase 38)" (reads Rule SWRL thresholds, authors nothing). Both establish the pattern: a new
    validation/consumer surface is documented as an addendum section with no D-number when no
    CONTEXT decision letter exists for it, reusing existing severity/message conventions rather
    than inventing new ones.
  implication: the conflict-check gate should follow the identical documentation pattern — a new
    addendum section (not a new numbered decision), reusing the existing severity/message
    conventions, added to the decision table per the debug file's already-identified requirement.

- timestamp: 2026-09-19T(live browser UAT, post-deploy)
  checked: real browser UAT by the coordinator — project URBAN_BLOCK_V8, ingest prompt
    "Apartments have min area 35 square meters" against existing R_URB_AREA_MIN_28_V ("Minimum
    apartment area is 28 m2"). Dialog fired correctly, named the right rule; user chose
    **Update existing**; user reported "nothing has changed." Coordinator inspected the live
    graph directly.
  found: CRITICAL SEVERITY GAP in `/rules/supersede`'s precondition. The n8n ingest DID write a
    structurally-shaped Rule (3 HAS_BODY + 1 HAS_HEAD atoms, correct `order` values) but it was
    malformed in three ways the endpoint never checked: (1) `Rule_Id: 'ApartmentsHaveMinArea35'`
    violates the mandated `R_<DOMAIN>_<PROPERTY>_<LIMIT>_V` format; (2) the Rule node had NO
    `graph:'Metagraph'` property; (3) all four Atom nodes had NO `graph` property and NO
    `SWRL_label` (the OLD rule's atoms correctly carry these). `/rules/supersede`'s precondition
    was `MATCH (new:Rule {Rule_Id: $newId, project: $project})` — existence of a Rule_Id was
    treated as proof of usability. It matched the malformed stub, created the SUPERSEDED_BY edge,
    and recorded provenance exactly as designed. Net effect: `R_URB_AREA_MIN_28_V` (previously
    correctly enforced) was excluded from the SWRL VALIDATOR's corpus by the new
    `WHERE NOT EXISTS SUPERSEDED_BY` filter (working as designed), while its replacement was
    ALSO invisible to that same corpus query (no `graph:'Metagraph'` on the new rule) — the
    project was left with NO enforceable apartment-area rule at all. Coordinator manually
    reverted the graph (deleted the edge, the stub Rule, and its 4 orphaned Atoms) before this
    session resumed; `R_URB_AREA_MIN_28_V` confirmed live again.
  implication: This is strictly worse than the original bug (silent duplicate rules) — silent
    total loss of enforcement. `/rules/supersede`'s MATCH-by-Rule_Id-alone precondition is too
    weak; a rule's mere existence in the graph is not proof it is well-formed enough to safely
    take over for the rule it replaces. The coordinator authorized ONE narrow fix: harden
    `/rules/supersede`'s (and, if applicable, `/rules/accept-overlap`'s) precondition to require
    the new rule carries `graph:'Metagraph'` AND has >=1 HAS_BODY AND >=1 HAS_HEAD atom AND those
    atoms themselves carry `graph:'Metagraph'`. On failure: structured 4xx (new code
    `RULE_NOT_PUBLISHABLE`), old rule MUST remain live, never partially apply. Additionally: the
    client's supersedeRule() call is currently a silent console.warn on failure
    (GraphScreen.jsx ~line 702) — a refused supersede must be surfaced to the user, unlike the
    conflict CHECK's deliberate fail-open behavior (which is correct and unchanged).
  explicitly_out_of_scope (coordinator declined, record as follow-ups, do NOT fix now):
    - validate_cypher() accepting the non-conforming Rule_Id format
    - whatever caused the missing graph/SWRL_label tagging on the ingested rule+atoms (this is
      the ALREADY-KNOWN "Neo4j node tagging required after n8n ingestion" gotcha from CLAUDE.md/
      memory — this UAT session gives it, for the first time, a CONCRETE, reproducible trigger:
      an Update-existing-triggered ingest turn via the conflict-check dialog. Causally distinct
      from this hardening fix: hardening supersede is the safety net that stops a malformed rule
      from disarming a working one; it does not fix why the rule came out malformed. The tagging
      bug still needs its own separate debug session.
    - the empty `actor` provenance field on the SUPERSEDED_BY edge
    - the pre-existing unfiltered "Annotate Graph Props" cross-project description overwrite
      (already flagged, separate follow-up)

## Reasoning Checkpoint (structured, mandatory before fix)

hypothesis: The rule-ingest pipeline (n8n "DG Rules -> Metagraph", confirmed live-matching repo
  JSON) has exactly one server-side grounding step — `data-service/dg_context.assemble_context()`
  — that already resolves per-project existing OntoGraph vocabulary before the LLM synthesizes
  Cypher, but has NO equivalent fetch of existing Metagraph Rule/Atom data, and NO comparison of
  the about-to-be-created rule's (Class, DatatypeProperty, comparator) grounding signature against
  rules already in the corpus. Because `assemble_context` runs before Cypher generation and
  `validate_cypher` runs after (both server-side, both in data-service, both reachable from the
  single n8n write path), the missing check is a gap in data-service, not in ui-v2 (client, no
  pre-flight exists there either) or in n8n (thin orchestrator with no business logic since
  Phase 29-05's refactor to "thin caller, fat data-service assembler").
confirming_evidence:

  - "assemble_context() L457-504 returns existing_entities from OntoGraph only
    (_EXISTING_ENTITIES_QUERY, L316-323) — grep of the full function body shows no Metagraph
    Rule/Atom read anywhere in the assembled context dict."
  - "validate_cypher() L507-778 (docstring: 'PRIMARY security control') performs only structural/
    syntactic checks (allow-lists, verb policy, bracket nesting, naming) — zero cross-rule or
    Neo4j-querying logic; confirms RULE-PARTITION-POLICY.md's own claim that no existing
    validation surface evaluates rule-vs-rule semantic content."
  - "n8n live active workflow (id a1b2c3d4-..., updated 2026-09-18, confirmed identical topology
    to repo JSON) has a linear 19-node pipeline with a single write step ('Execute LLM Cypher')
    and no conditional/dialog/preview branch anywhere before it."
  - "ingestRules() in ui-v2/graphApi.js posts straight to the n8n webhook with no client-side
    validation, confirming the gap is not merely a broken client feature but a total absence
    end-to-end."
  - "Build LLM Prompt node's own inline comment documents that a WEAKER, adjacent capability
    (scoring prompt keywords against existing rule TEXT for edit-target inference) existed before
    Phase 29-05 and was dropped, not deliberately never-built — corroborates this as a regression/
    gap rather than an intentional design choice."
falsification_test: If assemble_context() or validate_cypher() were found to already call a
  function that queries `:Rule` nodes by grounding signature (Class+DatatypeProperty+comparator)
  and surfaces a match, this hypothesis would be false. Full-body reads of both functions (L457-
  504 and L507-778) found no such call, and no helper function of that shape exists anywhere in
  dg_context.py (only fetch_existing_entities [OntoGraph], fetch_existing_design_states
  [ValidGraph runs], fetch_rules_for_selection [Rule catalogue, but only invoked from the
  deletion-selection LLM flow, never from assemble_context or the ingest path].
fix_rationale: The fix must add a deterministic (non-LLM) grounding-signature lookup against
  existing Metagraph Rules, placed so it can block BEFORE Cypher generation (i.e. as an addition
  to/alongside assemble_context, or as a new pre-flight endpoint called by n8n between "Build LLM
  Prompt" and "Generate Validated Cypher", or before "Build LLM Prompt" once the grounding is
  known). It reuses the bd28f1f pattern (fetch candidates -> deterministic match -> preview
  payload -> confirm endpoint) but swaps the LLM-based matching step for a pure Cypher comparison,
  since the conflict key (Class + DatatypeProperty + comparator) is already a deterministic
  grounding fact per paper [P138], not an open-ended NL judgment like deletion-target selection.
  This addresses the root cause (missing corpus-level authoring-time gate) rather than a symptom
  (e.g. deduplicating by Rule_Id, which the debug file already established cannot work because
  Rule_Id embeds the literal value).
blind_spots: |
  (1) Grounding (Class/DatatypeProperty/comparator) is only fully known AFTER the LLM has
  produced Cypher (parsed from MERGE patterns) in the current pipeline — assemble_context runs
  BEFORE the LLM call and only has raw rules_text, not yet a resolved grounding triple. This means
  either (a) the check must run twice — once heuristically pre-LLM on rules_text via a lighter NL
  match, or (b) the gate must sit AFTER "Generate Validated Cypher" but BEFORE "Execute LLM
  Cypher", parsing the just-generated Cypher's MERGE patterns to recover the grounding (same
  MERGE-parsing helpers validate_cypher already has: _MERGE_NODE_PATTERN, _var_label_map,
  _extract_labels) — this is a MORE natural fit than pre-LLM and I had not fully resolved this
  before writing fix_rationale above. Recommend placing the gate as a new step reusing
  validate_cypher's existing Cypher-parsing helpers, run against a freshly-fetched Rule/Atom
  corpus, positioned between "Parse LLM Output" and "Prepare Graph Payload" in n8n (or better,
  folded into generate_validated_cypher()/validate_cypher() itself in data-service, then a new n8n
  branch node routes to a blocking-dialog response instead of "Prepare Graph Payload" when a
  conflict is detected) rather than inside assemble_context as first stated.
  (2) I have not yet located or read `_rule_delete_preview()`'s definition (only its call sites)
  — needed to confirm the exact preview payload shape a Replace/Update dialog would reuse.
  (3) I have not yet designed the exact Cypher for "does a Rule already exist with this
  Class+DatatypeProperty+comparator, excluding the sanctioned lessThan+greaterThan range-pair
  case" — this needs the Atom/Var/Literal traversal pattern used by existing Rule-reading queries
  (e.g. _RULES_FOR_SELECTION_QUERY) as a starting point, not yet read in full.
  (4) Have not yet checked whether n8n's "responseNode"/ack-then-poll async model (Format Ack /
  Respond Ack fire immediately, before Assemble Context even runs) is compatible with a true
  BLOCKING dialog — the current UX model returns a 200 ack immediately and polls
  /execution-result for completion; a blocking Replace/Update/Keep-both/Cancel gate needs the
  workflow to PAUSE and expose a pending-decision execution state rather than complete or fail,
  which is a new state (today's states are: running/completed/failed/cancelled). This is a
  material UX/architecture question that should go into the fix-options checkpoint, not be
  silently decided.

## Current Focus

hypothesis: Round 1 (the conflict-check gate itself) is implemented and was live-verified, but
  live browser UAT found round 1 shipped an unsafe `/rules/supersede` precondition
  (MATCH-by-Rule_Id-alone) that let a malformed ingest result silently disarm a working rule with
  no replacement — worse than the original bug. Round 2 (this focus): harden
  `/rules/supersede`'s precondition to require the new rule is actually publishable
  (graph:'Metagraph' + >=1 HAS_BODY + >=1 HAS_HEAD, atoms themselves carrying
  graph:'Metagraph'), check whether `/rules/accept-overlap` needs the identical guard, add a
  regression test reproducing the exact live UAT condition, and make a refused supersede visible
  in the UI instead of a silent console.warn.
test: reproduce the malformed-rule condition directly via Cypher (bypassing the flaky LLM
  provider) — a Rule matching by Rule_Id but missing graph:'Metagraph' and/or its atoms missing
  graph:'Metagraph' — then call the hardened /rules/supersede and confirm it refuses with
  RULE_NOT_PUBLISHABLE and the old rule stays live and stays in the validator corpus query.
expecting: hardened endpoint returns 4xx with a structured, actionable hint naming which
  precondition failed; old rule's SUPERSEDED_BY state is unchanged (no edge created); C#
  RulesQuery / Python corpus queries still see the old rule as live.
next_action: DONE — see Resolution's "ROUND 2" block for the implemented fix, the 8-test
  regression suite, and the repeated live verification against a directly-constructed
  reproduction of the exact UAT condition. Awaiting human confirmation before archiving. Do NOT
  archive_session until the coordinator confirms the browser click-through of a refused
  Update/Replace shows the warning correctly and the rest of round 1's UX (dialog itself) is
  still working after this round's changes.

## Round 2 Reasoning Checkpoint (structured, mandatory before fix)

hypothesis: `/rules/supersede`'s precondition (`MATCH (new:Rule {Rule_Id: $newId, project:
  $project})`) treats Rule_Id existence as sufficient proof a rule can safely take over
  enforcement, but existence says nothing about whether the rule is tagged/structured such that
  the SWRL VALIDATOR's own corpus loader (Neo4jRuleRepository.RulesQuery/AtomsQuery, C#) will
  ever see it. When the new rule fails that invisible requirement, supersession still proceeds,
  excluding the (working) old rule from the corpus while the (broken) new rule never entered it
  — net loss of enforcement.
confirming_evidence:

  - "Live browser UAT: ingest 'Apartments have min area 35 square meters' against
    R_URB_AREA_MIN_28_V, user chose Update existing, user reported no change. Coordinator
    inspected the live graph and found the new Rule_Id 'ApartmentsHaveMinArea35' existed with
    correctly-ordered 3 HAS_BODY + 1 HAS_HEAD atoms, but the Rule node had no graph:'Metagraph'
    and all 4 Atoms had no graph/SWRL_label."
  - "Coordinator confirmed /rules/supersede matched this stub, created the SUPERSEDED_BY edge,
    and recorded provenance exactly as designed — the endpoint did precisely what its code says,
    the code's precondition was simply insufficient."
  - "Neo4jRuleRepository.RulesQuery (C#) explicitly matches on {graph:'Metagraph', project:...}
    and its sibling AtomsQuery matches atoms the same way (confirmed by direct code read, both
    files already modified in round 1) — an untagged Rule/Atom is provably invisible to this
    query, not a hypothetical risk."
falsification_test: If Neo4jRuleRepository.RulesQuery or AtomsQuery did NOT filter on
  graph:'Metagraph' (e.g. matched on Rule_Id or project alone), an untagged rule would still be
  visible to the validator and this hypothesis would be false — the real cause would be
  elsewhere. Re-read of both queries (round 1 diff, still in effect) confirms the graph filter is
  present on both, so this is not the case.
fix_rationale: Add a read-only precondition check (_require_publishable_rule) between the
  new-rule-existence check and the SUPERSEDED_BY write, asserting exactly the three things
  Neo4jRuleRepository.RulesQuery/AtomsQuery actually require (Rule tagged Metagraph, >=1 HAS_BODY
  atom, >=1 HAS_HEAD atom, ALL of those atoms also tagged Metagraph). This addresses the root
  cause (the precondition gap) rather than a narrower symptom fix (e.g. checking only the Rule
  node's tag and missing the atom-level nuance that the actual UAT case also exhibited).
  accept_rule_overlap() is deliberately NOT given the same guard: it never creates a
  SUPERSEDED_BY edge and never touches the old rule, so a malformed new rule there degrades to
  the pre-existing (separately tracked, out-of-scope) tagging gap, never to loss of the old
  rule's enforcement — the two endpoints have different blast radii and only one needed hardening.
blind_spots: |
  (1) The hardening checks graph:'Metagraph' + HAS_BODY/HAS_HEAD presence + atom tagging, mirroring
  exactly what Neo4jRuleRepository.RulesQuery/AtomsQuery require today. If that C# query's
  requirements ever change (e.g. a future schema change adds a new required tag), this
  precondition would need to change in lockstep -- it is not derived automatically from the C#
  query, it is a hand-maintained mirror of it. This is an accepted coupling, not resolved by this
  fix.
  (2) This does NOT fix why the rule came out malformed in the first place -- that is the
  separately-tracked, out-of-scope "Neo4j node tagging required after n8n ingestion" gotcha,
  which this UAT round gives a concrete reproduction trigger (an Update-existing-triggered ingest
  turn through the conflict-check dialog) for the first time, but does not diagnose or fix here.
  (3) Have not verified whether the SAME untagged-ingest condition could also affect a
  first-time-Keep-both or first-time-no-conflict ingest (i.e. is this specific to the
  Update-existing code path, or can any ingest turn produce an untagged rule?) -- out of scope
  per the coordinator's explicit instruction to flag, not investigate, the tagging bug itself.

## Decisions (from checkpoint response)

1. **Insertion point:** new synchronous `POST /rules/check-conflict` in data-service. UI calls it
   FIRST, renders dialog itself, only calls `ingestRules()` after resolution. n8n unmodified.
2. **Dialog:** pure client state in ui-v2. No `awaiting_decision` execution state, no resume
   endpoint. Mirrors bd28f1f's `resolve-deletion`/`bulk-delete` two-call split.
3. **Grounding resolution (no LLM):** reuse `fetch_existing_entities()`/`_EXISTING_ENTITIES_QUERY`
   OntoGraph vocabulary to resolve NL phrase -> candidate (Class, DatatypeProperty). Derive
   comparator from bound-direction keywords (maximum/max/no more than/at most ->
   swrlb:greaterThan; minimum/min/at least/no less than -> swrlb:lessThan; equals/must be ->
   swrlb:notEqual) per paper [P109]. Query existing Rules for signature collision using the
   grounding triple, NOT Rule_Id. If resolution is ambiguous, return "no conflict" (false negative
   degrades to today's behavior; false positive blocks legitimate authoring — asymmetric cost).
4. **Replace/Update semantics:** SUPERSEDE, don't delete. New `SUPERSEDED_BY` edge (old->new) +
   provenance (who/when/prompt). Superseded rules MUST be excluded from: (a) SWRL VALIDATOR's rule
   corpus (Neo4jRuleRepository.RulesQuery, C#, requires dotnet rebuild), (b) the conflict-check
   query itself (else past revisions collide forever), (c) deletion-selection's rule catalogue
   (dg_context.fetch_rules_for_selection / _RULES_FOR_SELECTION_QUERY — same blind spot).
5. **Keep both:** writes new rule, records that user knowingly accepted overlap (provenance flag).
6. **Cancel:** writes nothing.
7. Update spec/RULE-PARTITION-POLICY.md (new addendum, no D-number, follows Phase 37/38 pattern).
8. Schema propagation for new SUPERSEDED_BY relationship: spec/DATABASE.md, ontology/dg-shapes.ttl,
   cypher_template.txt, training/dataset_schema.json, .github/copilot-instructions.md, README.md.

## Design for grounding resolution (pre-LLM, deterministic)

Confirmed via code read: `_EXISTING_ENTITIES_QUERY` returns
  {nodeLabel, iri, label, swrl_label, range} for Class/DatatypeProperty/ObjectProperty.
  DatatypeProperty's display name is `swrl_label` (SWRL_label prop) per dg_knowledge.py naming
  quirks ("DatatypeProperty display property is SWRL_label, not label"). Class uses `label`.
Algorithm: normalize rules_text and each candidate entity's display label to lowercase
  alphanumeric tokens; a Class matches if enough of its label's significant tokens appear in the
  text (e.g. "building" in "Building height maximum is 50 m" matches Class label "Building"); a
  DatatypeProperty matches similarly against its SWRL_label (e.g. "hasHeightM" / "height" style
  tokens) AND/OR its `range`-adjacent phrasing. This is intentionally simple substring/token
  overlap, NOT fuzzy text similarity across whole sentences (coordinator's explicit warning) —
  it matches individual entity labels already known to exist in THIS project's vocabulary, a much
  smaller and more precise search space than matching two free-text rule descriptions against
  each other.
Comparator keyword table (paper [P109] swrlb:lessThan/greaterThan/notEqual, case-insensitive):
  greaterThan triggers: "maximum", "max", "no more than", "at most", "not exceed", "upper bound"
  lessThan triggers: "minimum", "min", "at least", "no less than", "not less than", "lower bound"
  notEqual triggers: "must be", "equals", "equal to", "shall be"
  If multiple/conflicting triggers present or none present -> ambiguous -> no-conflict fallthrough.
Existing-rule collision query: MATCH (r:Rule {project:$project, graph:'Metagraph'})
  -[:HAS_BODY]->(a:Atom)-[:REFERS_TO]->(dp:DatatypeProperty {iri:$propertyIri})
  WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
  MATCH (a)-[:ARG]->(b:Builtin) WHERE b.iri CONTAINS $comparator
  -- plus a check that the atom's ARG-0 var traces back to an instance of $classIri via another
  body atom, mirroring the existing atom-traversal shape in Neo4jRuleRepository's AtomsQuery /
  dg_context's _RULES_FOR_SELECTION_QUERY.
Range-pair exclusion: comparator is part of the match key by construction (query filters on
  $comparator), so an existing greaterThan rule does not collide with a new lessThan rule on the
  same property — this satisfies the range-pair non-flagging requirement without special-casing.

- timestamp: 2026-09-19T(session continued, live DB inspection)
  checked: live Neo4j via `docker exec neo4j cypher-shell` — real Rule R_BUILDING_MAX_HEIGHT_80_V
    (project TestA) full atom/REFERS_TO/ARG traversal; fetch_existing_entities-equivalent query
    for project TestA; TestA's rules' REFERS_TO targets across all projects.
  found: CRITICAL cross-project vocabulary-sharing quirk (pre-existing, NOT caused by this fix):
    Class/DatatypeProperty/Builtin OntoGraph nodes carry a `project` property reflecting whichever
    project's ingest FIRST created that iri via MERGE — not every project whose Rules reference
    it. Concretely: TestA's own Rule R_BUILDING_MAX_HEIGHT_80_V references `ex:Building`
    (tagged project:'URBAN_BLOCK_V8'), `ex:hasHeightM` (tagged project:'v8-ui-smoke'),
    `swrlb:greaterThan` (tagged project:'URBAN_BLOCK_V8') — none tagged 'TestA'. Running
    `fetch_existing_entities('TestA')` (the exact query assemble_context() uses) returns ONLY 2
    entities (`ex:hasWindowCount`, `ex:violatesMinWindowCount`) — it does NOT surface
    ex:Building/ex:hasHeightM even though TestA's own rule corpus uses them.
  implication: MUST correct grounding-resolution + collision-query design. Two consequences: (1)
    grounding candidate-vocabulary lookup via fetch_existing_entities(project) is a pre-existing,
    accepted contract (unchanged by this fix; ambiguous/unmatched grounding already falls through
    to no-conflict per the coordinator's decision, so under-matching here degrades safely to
    today's behavior, never blocks legitimate authoring); (2) the COLLISION query itself must
    NEVER filter candidate Class/DatatypeProperty/Builtin nodes by their OWN `project` property —
    it must instead start from `Rule {project:$project}` (the Rule's own project is reliable and
    already how every existing Rule query in this codebase scopes) and traverse OUT to whatever
    entities its atoms REFERS_TO, matching on iri value only. This sidesteps the cross-project
    tag quirk entirely and matches the exact traversal already used by AtomsQuery
    (Neo4jRuleRepository.cs) and _RULES_FOR_SELECTION_QUERY (dg_context.py) — neither of which
    filters the target Class/DatatypeProperty node by project either, only the Rule.
  files_of_interest: none changed yet — design correction only, applied below before
    implementation.

- timestamp: 2026-09-19T(live verification round 1, POST-implementation)
  checked: live POST /rules/check-conflict against real TestA project data after first
    implementation + rebuild.
  found: TWO further bugs caught by live verification (not caught by design review or unit-level
    reasoning): (1) `fetch_existing_entities(project)` -- used as the grounding vocabulary source
    -- suffers the SAME cross-project OntoGraph-tag quirk discovered earlier: it returned only 2
    irrelevant entities for TestA, missing ex:Building/ex:hasHeightM entirely, so grounding always
    resolved to null. Fixed by adding `fetch_project_rule_vocabulary()`/
    `_PROJECT_RULE_VOCAB_QUERY`, which traverses FROM the project's own (non-superseded) Rules OUT
    to their atoms' REFERS_TO targets -- same fix pattern as the collision query, used as the
    PRIMARY vocabulary source, with fetch_existing_entities kept as a secondary/supplementary
    source. (2) `_tokenize()` lowercased camelCase property labels (e.g. 'hasHeightM') into one
    opaque token ('hasheightm') that could never be a subset of space-separated NL tokens --
    grounding still resolved to null even after fix (1). Fixed with a camelCase word-boundary
    split, a number-immediately-followed-by-unit-letter split ('50m' -> '50', 'm'), a
    structural-prefix strip ('has'/'is'/'violates', schema-convention noise words per
    cypher_template.txt), and a trivial pluralization normalizer (bare trailing 's' after 3+
    chars) so 'buildings' matches Class label 'Building'. Verified in isolation (python3 -c) against
    BOTH the debug file's literal repro text AND the coordinator's alt-phrasing example
    ("max height of buildings: 50m") before rebuilding the container -- both now resolve grounding
    correctly; hasWidthM (negative control) correctly still does not match either text.
  implication: this is exactly the kind of bug the verification-before-completion discipline
    exists to catch — the original design (Reasoning Checkpoint / Design section above) looked
    complete and passed a single live query test against the WRONG assumption (that
    fetch_existing_entities was suffient), and separately the tokenizer was never exercised
    against a real camelCase property label until the live endpoint returned an empty grounding.
    Re-verifying against the running stack after each fix (not just re-reading the code) is what
    surfaced both.
  files_of_interest: data-service/dg_context.py (_tokenize, _singularize, _CAMEL_BOUNDARY_PATTERN,
    _NUMBER_UNIT_BOUNDARY_PATTERN, fetch_project_rule_vocabulary, _PROJECT_RULE_VOCAB_QUERY,
    check_rule_conflict's combined_entities union).

Corrected collision query design: given a resolved candidate (classIri, propertyIri,
  comparatorIri) from grounding-resolution against project $project's own vocabulary via
  fetch_existing_entities, find existing non-superseded Rules in $project whose body atoms
  reference the SAME iris via the SAME shared-variable pattern the template always emits
  (ClassAtom and DataPropertyAtom share entity var at ARG pos:1; DataPropertyAtom and BuiltinAtom
  share value var at ARG pos:1/pos:2 respectively):

```
MATCH (r:Rule {project: $project, graph: 'Metagraph'})
WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
MATCH (r)-[:HAS_BODY]->(classAtom:Atom {type: 'ClassAtom'})-[:REFERS_TO]->(:Class {iri: $classIri})
MATCH (classAtom)-[:ARG]->(entityVar:Var)
MATCH (r)-[:HAS_BODY]->(propAtom:Atom {type: 'DataPropertyAtom'})-[:REFERS_TO]->(:DatatypeProperty {iri: $propertyIri})
MATCH (propAtom)-[:ARG {pos: 1}]->(entityVar)
MATCH (propAtom)-[:ARG {pos: 2}]->(valueVar:Var)
MATCH (r)-[:HAS_BODY]->(cmpAtom:Atom {type: 'BuiltinAtom'})-[:REFERS_TO]->(:Builtin {iri: $comparatorIri})
MATCH (cmpAtom)-[:ARG {pos: 1}]->(valueVar)
OPTIONAL MATCH (cmpAtom)-[:ARG {pos: 2}]->(lit:Literal)
RETURN DISTINCT r.Rule_Id AS ruleId, coalesce(r.SWRL,'') AS swrl,
       coalesce(r.RuleDescription, r.description, '') AS description, lit.lex AS currentValue
```

  Verified against real data: substituting classIri='ex:Building', propertyIri='ex:hasHeightM',
  comparatorIri='swrlb:greaterThan', project='TestA' against the live DB should return
  R_BUILDING_MAX_HEIGHT_80_V with currentValue='80' — to be confirmed by running it live during
  implementation/verification.

## Eliminated

(none yet)

## Resolution

root_cause: The rule-ingest pipeline (n8n "DG Rules -> Metagraph", live-verified identical to
  repo `n8n/workflows/rules-to-metagraph.json`) has no step, in any of its three layers
  (ui-v2 client, n8n orchestrator, data-service), that fetches existing Metagraph Rules and
  compares their (Class, DatatypeProperty, comparator) grounding signature against the rule
  about to be authored. `data-service/dg_context.assemble_context()` fetches existing OntoGraph
  vocabulary (Class/DatatypeProperty/ObjectProperty) before the LLM call but never Metagraph
  Rule/Atom instances; `data-service/dg_context.validate_cypher()` (the pipeline's only
  post-generation gate, docstring: "PRIMARY security control") checks only Cypher
  structure/syntax/schema-allow-list, never cross-rule semantic content. This is a genuine gap,
  not a deliberate design choice: the n8n "Build LLM Prompt" node's own inline comment documents
  that a weaker, adjacent capability (scoring prompt text against existing rule TEXT for
  edit-target inference) existed before the Phase 29-05 refactor and was dropped when
  `/context/assemble` absorbed the responsibility without carrying it forward.
fix: Applied per coordinator decisions (synchronous pre-flight `POST /rules/check-conflict` in
  data-service, called by ui-v2 BEFORE the n8n webhook; client-side blocking dialog with no n8n
  changes; deterministic no-LLM grounding resolution; Replace/Update supersedes via a new
  `SUPERSEDED_BY` Rule->Rule edge with provenance, never deletes; Keep both records
  `acceptedOverlapWith` provenance with no supersede edge; Cancel writes nothing).

  Root cause of TWO additional bugs found only through live verification (documented in Evidence
  above): (a) the vocabulary source for grounding resolution must be the project's OWN Rule
  corpus traversal (`fetch_project_rule_vocabulary()`), not `fetch_existing_entities()` alone,
  because OntoGraph Class/DatatypeProperty nodes carry a `project` tag reflecting whichever
  project first MERGEd that iri, not every project whose rules reference it; (b) the token-overlap
  matcher needed a camelCase word-boundary split, a number-immediately-followed-by-unit-letter
  split, a structural-prefix strip (has/is/violates), and a light pluralization normalizer to
  correctly match free-text NL against camelCase DatatypeProperty labels (e.g. 'hasHeightM' vs.
  "height ... 50 m").

verification: Live-verified against the running Docker stack (containers rebuilt with
  `--no-cache` for design-grammars, rebuilt for data-service after each fix iteration) — not
  simulated, not unit-test-only:
  1. POST /rules/check-conflict with the exact debug-file repro ("Building height maximum is
     50 m" against a live R_URB_HEIGHT_MAX_75_V rule, "Building height is maximum 75 meters")
     correctly resolves grounding to {Building, hasHeightM, greaterThan} and returns the
     conflicting rule with its Rule_Id, cleaned description, and current threshold (75).
  2. Adversarial alt-phrasing case from the coordinator's own instructions ("max height of
     buildings: 50m") resolves to the IDENTICAL grounding and conflict — confirms the fix is not
     overfit to one literal phrasing.
  3. Negative case (different DatatypeProperty, e.g. hasWidthM): correctly reports no conflict.
  4. Range-pair negative case (same Class+DatatypeProperty, opposite comparator — minimum vs.
     the existing maximum): correctly reports no conflict, confirming the sanctioned
     lessThan+greaterThan decomposition is never flagged.
  5. POST /rules/supersede: creates the SUPERSEDED_BY edge with supersededAt/actor/prompt
     provenance; old rule verified NOT deleted (still present with its original SWRL); rejects a
     second supersede of an already-superseded rule with 409 ALREADY_SUPERSEDED.
  6. POST /rules/accept-overlap ("Keep both"): records acceptedOverlapWith/At/By provenance on
     the new rule with no SUPERSEDED_BY edge created — both rules remain independently live.
  7. C# Neo4jRuleRepository.RulesQuery (the SWRL VALIDATOR's own corpus loader) verified via the
     identical live Cypher query to correctly exclude a superseded rule from the corpus after
     supersession — confirming the original bug (two rules both firing) cannot recur in the new
     supersede-based form. Same exclusion independently verified for
     _RULES_FOR_SELECTION_QUERY (semantic rule deletion's catalogue).
  8. Full pytest suite (data-service/tests/) run before and after the fix via a git-stash
     differential test: 4 failed + 25 errored + 735 passed, IDENTICAL counts on both the
     unmodified HEAD and the fixed working tree. All 29 failures/errors are pre-existing
     host-vs-Docker-network issues (`neo4j:7687` DNS resolution only works inside the Compose
     network, matching documented project memory), not caused by this fix. tests/test_rule_
     deletion.py (18 tests, directly exercises the modified _RULES_FOR_SELECTION_QUERY): 18/18
     pass.
  9. DG.Tests (C#): 410/412 pass; the 2 failures are the documented pre-existing
     DesignStateValidationFlowTests Neo4j E2E baseline (env-dependent), not new. Full DG.sln
     Release build: 0 warnings, 0 errors.
  10. All test/verification scaffolding data (projects `TestA`-adjacent reads were read-only;
      `verify-conflict-check` and `final-verify` test projects) was created and then fully
      deleted from the live Neo4j instance — no verification artifacts left in the shared
      database.
  11. Live UI bundle (index-Cc6gzUbr.js, served from the rebuilt design-grammars container)
      confirmed to contain the new checkRuleConflict/supersedeRule/acceptRuleOverlap client code.

  NOT YET verified: a full click-through of the actual dialog UI in a real browser (only the API
  layer + bundle-content-inclusion were verified from the command line) and a full successful
  n8n-LLM-driven ingest of the new competing rule end-to-end (the one live attempt hit unrelated
  LLM-generation truncation flakiness in this environment's configured provider, not a bug in
  this fix — the new-rule side of the Replace/Update/Keep-both flow was instead verified by
  writing the competing rule directly via Cypher and exercising /rules/supersede and
  /rules/accept-overlap against it, which is the exact same code path the client calls after a
  successful ingest turn). Recommend the user click through the dialog once against a real
  ingest in the browser as final confirmation.

  ADDITIONAL PRE-EXISTING BUG FOUND (NOT part of this fix's scope, flagged not silently fixed):
  n8n/workflows/rules-to-metagraph.json's "Annotate Graph Props" step runs unconditionally after
  "Execute LLM Cypher" (even when that step's Cypher failed/rolled back) and its Cypher
  (`MATCH (r:Rule) WHERE r.graph='Metagraph' AND (r.description IS NULL OR r.description='')
  SET r.description=$description, ...`) has NO project filter — it can overwrite ANY Rule's
  empty description across ANY project with the current request's rules_text. Observed live
  during verification (a manually-inserted test rule's description was silently overwritten by
  an unrelated failed ingest attempt in a different project). Recommend a follow-up debug session.

  === ROUND 2: live browser UAT found a real defect (2026-09-19, same session, post-round-1) ===

  UAT: project URBAN_BLOCK_V8, ingest "Apartments have min area 35 square meters" against
  existing R_URB_AREA_MIN_28_V. Dialog correctly named the existing rule; user chose
  **Update existing**; user reported "nothing has changed." Coordinator inspected the live graph
  and found the n8n ingest wrote a structurally-correct-but-untagged Rule (Rule_Id
  'ApartmentsHaveMinArea35', violates the R_<DOMAIN>_<PROPERTY>_<LIMIT>_V format; no
  graph:'Metagraph' on the Rule; no graph/SWRL_label on any of its 4 atoms, despite correct
  HAS_BODY/HAS_HEAD/order structure). `/rules/supersede`'s precondition
  (`MATCH (new:Rule {Rule_Id: $newId, project: $project})`) matched this stub, created the
  SUPERSEDED_BY edge, and recorded provenance exactly as written. Net effect: the working
  R_URB_AREA_MIN_28_V rule was excluded from the SWRL VALIDATOR's corpus by round 1's new
  `WHERE NOT EXISTS SUPERSEDED_BY` filter (working as designed), while the "replacement" was
  ALSO invisible to that same corpus query (no graph:'Metagraph') — the project was left with NO
  enforceable apartment-area rule. Strictly worse than the original bug (silent duplicate rules).
  Coordinator manually reverted the graph (deleted the edge, the stub Rule, and its 4 orphaned
  Atoms) before this round began; R_URB_AREA_MIN_28_V confirmed live again by the coordinator.

  ROUND 2 FIX (the ONE fix the coordinator authorized — narrow scope, other findings flagged not
  fixed, see explicitly_out_of_scope in the Round 2 Reasoning Checkpoint above):

  Added `_require_publishable_rule(rule_id, project)` in data-service/app.py, called in
  `supersede_rule()` between the new-rule-existence check and the SUPERSEDED_BY write. Runs
  `_RULE_PUBLISHABILITY_QUERY`, which checks exactly what Neo4jRuleRepository.RulesQuery/
  AtomsQuery (C#) actually require for a rule to be visible/evaluable: the Rule tagged
  graph:'Metagraph', at least one HAS_BODY atom, at least one HAS_HEAD atom, and every one of
  those atoms ALSO tagged graph:'Metagraph' (the exact nuance the real UAT case hit — a Rule
  node's own tag and its atoms' tags are checked independently, since a rule could pass the
  first and still fail the second). On any failure, raises a structured 409 with code
  `RULE_NOT_PUBLISHABLE`, an actionable hint naming which precondition failed, and writes
  NOTHING — the old rule's SUPERSEDED_BY state is provably unchanged since the write happens
  strictly after this check. `accept_rule_overlap()` was reviewed and deliberately NOT given the
  same guard: it never creates a SUPERSEDED_BY edge and never touches the old rule (only SETs
  provenance properties on the new rule), so a malformed new rule there degrades to the
  pre-existing, separately-tracked tagging gap, never to loss of the old rule's enforcement —
  documented inline in its docstring.

  Client-side (ui-v2/src/screens/GraphScreen.jsx): `runTurn()` now also returns the turn's `id`
  (not just `createdNodes`), so `runIngestWithConflictCheck()` can `patchTurn()` that same visible
  session turn with a warning if the post-ingest supersede/accept-overlap call fails, instead of
  only `console.warn`-ing. A `RULE_NOT_PUBLISHABLE` refusal specifically is surfaced as
  "Update did not apply — {oldRuleId} is still the rule in force." plus the server's hint text,
  appended to the turn's response the user is already looking at — not a new dialog/toast, reusing
  the existing visible mechanism. `graphApi.js`'s `supersedeRule()` now attaches `code`/`hint`
  from the structured error body onto the thrown Error (previously only the `error` message
  string survived), so the client can distinguish this refusal from a generic/network failure.
  The conflict-check's own fail-open behavior (a check-conflict outage never blocks authoring) is
  explicitly UNCHANGED — only the post-ingest provenance-write failure path was tightened, per
  the coordinator's explicit instruction to keep the two failure modes distinct.

  Regression test added: `data-service/tests/test_rule_conflict.py` (new file, 8 tests) —
  `TestSupersedePublishabilityGuard` reproduces the exact live UAT condition (Rule exists,
  correctly-ordered atoms, missing graph:'Metagraph' tagging at the Rule level, the Atom level,
  and both), asserts refusal + zero writes + old rule's state is untouched, and asserts the happy
  path (fully tagged rule) still succeeds; `TestAcceptOverlapUnaffectedByGuard` asserts
  accept-overlap has no such guard and creates no SUPERSEDED_BY edge even for a
  theoretically-malformed rule, confirming the "different blast radii" reasoning is not just
  asserted but tested.

  Live verification (round 2): reconstructed the exact malformed-rule condition directly via
  Cypher (avoided the flaky LLM provider per the coordinator's suggestion) inside a dedicated
  test project, twice — once immediately after implementing the fix, once again after the FINAL
  data-service rebuild to guarantee the deployed code matches the reviewed diff exactly. Both
  times: `/rules/supersede` refused with 409 RULE_NOT_PUBLISHABLE naming the missing
  graph:'Metagraph' tag; the old rule's SUPERSEDED_BY state stayed FALSE; the old rule remained
  the only rule visible to the exact C# RulesQuery filter run directly against the live database.
  Also independently verified the "Rule tagged, atoms untagged" nuance (a variant the first round
  of manual live testing did not need to construct, but the regression test does) and the
  no-HAS_BODY / no-HAS_HEAD variants, all correctly refused. Happy-path (fully tagged rule)
  verified to still succeed. All test data deleted from the live database after each round.
  Full pytest suite (743 passed / 4 failed / 25 errored, identical pre-existing counts to round 1
  plus exactly +8 for the new test file — zero new failures) and full DG.sln Release build
  (0 warnings/errors, C# side unchanged in round 2) re-confirmed clean. UI rebuilt with
  `--no-cache`; confirmed the new bundle (hash changed: index-k3EVgHUG.js) contains both the
  `RULE_NOT_PUBLISHABLE` handling code and the "Update did not apply" surfaced-warning text.

  NOT verified in round 2: an actual browser click-through of the refused-supersede warning text
  rendering correctly in the session console (verified only that the code paths and exact string
  are present in the deployed bundle, not a rendered screenshot/visual confirmation).

files_changed:
  Round 1:
  - data-service/dg_context.py (new: check_rule_conflict, _resolve_grounding, _resolve_comparator,
    _tokenize, _singularize, fetch_project_rule_vocabulary, _RULE_CONFLICT_QUERY,
    _PROJECT_RULE_VOCAB_QUERY, _clean_description, _COMPARATOR_KEYWORDS; modified:
    _RULES_FOR_SELECTION_QUERY adds WHERE NOT EXISTS SUPERSEDED_BY)
  - data-service/app.py (new endpoints: POST /rules/check-conflict, POST /rules/supersede,
    POST /rules/accept-overlap)
  - DG/src/DG.Core/Data/Neo4jRuleRepository.cs (RulesQuery adds WHERE NOT EXISTS SUPERSEDED_BY)
  - ui-v2/src/lib/graphApi.js (new: checkRuleConflict, supersedeRule, acceptRuleOverlap)
  - ui-v2/src/screens/GraphScreen.jsx (new conflict dialog state/UI, runIngestWithConflictCheck
    gate wired into sendPrompt for ingest mode, runTurn returns createdNodes for provenance calls)
  - spec/RULE-PARTITION-POLICY.md (new addendum: Corpus-Level Authoring-Time Conflict Check)
  - spec/DATABASE.md (SUPERSEDED_BY relationship documented)
  - cypher_template.txt (document-only SUPERSEDED_BY block, explicitly NOT LLM-emitted)
  - training/dataset_schema.json (_supersession_note documenting SUPERSEDED_BY is server-only)
  - .github/copilot-instructions.md (SUPERSEDED_BY documented with LLM-never-emit caveat)
  - README.md (SUPERSEDED_BY documented in Relationships list)

  Round 2 (live browser UAT regression hardening):
  - data-service/app.py (new: _require_publishable_rule, _RULE_PUBLISHABILITY_QUERY; wired into
    supersede_rule() before the SUPERSEDED_BY write; accept_rule_overlap() docstring updated to
    document why it deliberately does NOT get the same guard; soft-hyphen artifacts removed from
    two comments)
  - data-service/tests/test_rule_conflict.py (NEW FILE, 8 tests: TestSupersedePublishabilityGuard
    reproduces the exact live UAT malformed-rule condition and its variants;
    TestAcceptOverlapUnaffectedByGuard confirms accept-overlap has no such guard by design)
  - ui-v2/src/lib/graphApi.js (supersedeRule() now attaches code/hint from the structured error
    body onto the thrown Error, not just the message string)
  - ui-v2/src/screens/GraphScreen.jsx (runTurn() also returns the turn id;
    runIngestWithConflictCheck() surfaces a refused supersede/failed accept-overlap via
    patchTurn() instead of console.warn-only; RULE_NOT_PUBLISHABLE specifically shown as
    "Update did not apply -- {oldRuleId} is still the rule in force" + server hint)
