---
phase: 1303-pravilo-gh-obekt
plan: "14"
status: blocked
updated: 2026-10-18
blocker: "Owner pyRevit installation/open/sign-in checkpoint; previous installation command denied"
---

# Revit live checkpoint — act 3 has not run

## Ready

- Framework branch `feature/mapping-mvp`, worktree `C:\Users\Admin\source\repos\dg-mapping`.
- DG connector source: `apps/dg-revit-connector`; 400 offline tests passed.
- Running data-service image `82378ca11829692c03d7839b67380327bb9cd5cc58bbb4e360e448b050fd1f45`, built from committed source; mapping tests 63 passed.
- DeGram component `1aa3b39c`, successful unpacked build, launched with a scrubbed environment. Bundled DG adapter exports 54 tools; read-only status probe returns `BRIDGE_OFF` (Revit not running). Full launch evidence: `1303-13-SUMMARY.md`.
- Local model copy already prepared:
  `D:\dgb\revit-models\AdaptComponent_V18-dg-mapping.rvt`
- Original and initial copy SHA-256:
  `380684791776B3F6F6E9C4D53A05989B288270942F0A94595DAB246FD8B3D9E8`
  (8,876,032 bytes; original LastWriteTime 2026-09-02 17:58:13 at copying).
- Read-only transfer proof script is at `test/v12-hexagonal-facade-01/mapping-demo/dgmap_revit_transfer.py` (not the historical `rhinocode/` path in the plan).

## Blocked human action

The permission mechanism denied the previous actual installation command as `Unauthorized Persistence`. No actual installation was performed by that command; no retry through another tool/process is authorized by this note.

The owner can perform the installation locally, or explicitly allow it through the permission mechanism:

```powershell
python C:\Users\Admin\source\repos\dg-mapping\apps\dg-revit-connector\install.py
```

Then, per plan 14:
1. Open **only the local test copy** in Revit 2024 for this rehearsal; do not write the shared-drive original.
2. Reload pyRevit. Keep the old `revit-mcp.extension` as the fallback; the DG extension uses the separate `dg_revit` API.
3. Use **DG → Вход** and choose project `v12-hexagonal-facade-01`. Password entry is owner-only; do not log/read it.
4. Read-only controller check: `/dg_revit/status/`, then `dg_mapping_status` signedIn true and the correct copy identity.

## Remaining acceptance (not PASS)

- Real read 1: families/types, counts, adaptive-point counts, questions per group, source population session, runtime.
- Owner-confirmed gold: HexagonalUnit, not optional FacadeModule.
- Answers/apply; model colours, DG_Class/DG_MappingState and row selection/zoom in the **copy**.
- Read-only GH-profile transfer recompute from the real session. The earlier synthetic 375-element result is not a live Revit proof.
- Real read 2 with zero questions, measured precision/recall.
- Retire every profile created/reactivated by this test; verify zero active profiles and restore demo cold start.
- Update PROTOCOL act 3, UAT test 12, test guide and plan-14 summary only with actual evidence.

No Revit session, live gold or acceptance evidence is fabricated. No additional GH reopen/paid LLM call is needed for this checkpoint.
