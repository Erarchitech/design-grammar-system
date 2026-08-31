---
type: debugging
status: resolved
date: 2026-08-31
tags: [docx, tooling, manuscript, workflow, hazard]
---

# Word silently reverts scripted docx edits while the file is open

## Symptom

A scripted edit to a `.docx` reports success, reads back correctly from the file, and is **gone
minutes later**. No error at any point.

Observed twice on `Publications/T1_ITcon_DG_Draft_R14.3.docx` on 2026-08-31: three C55 edits written
at 19:54 and verified by reading the live file, absent by 20:10. Detected only because a follow-up
`docx_replace.py` run returned **0/1** and the raw `word/document.xml` still held the pre-edit text.

## Cause

Word holds the entire document in memory. Its next save — autosave, Ctrl+S, or close — writes that
in-memory copy over the file, discarding anything another process wrote in the meantime. The write
succeeds; Word simply overwrites it afterwards.

## Detection

A lock file next to the manuscript is the signal, and it is **not advisory**:

```bash
ls Publications/~\$_ITcon_DG_Draft_R14.3.docx    # exists => Word has it open
tasklist | grep -i winword                        # confirm the process
stat -c '%y' Publications/T1_ITcon_DG_Draft_R14.3.docx   # a moving mtime => actively editing
```

Note the leading `~$` file drops the first two characters of the name (`T1_ITcon…` →
`~$_ITcon…`), so a naive `ls ~$<full-name>` misses it.

Stale locks do exist — this project's `Publications/` holds several from crashed sessions — so check
the lock's mtime and whether `WINWORD.EXE` is running before concluding the document is live.

## Rule

**Never write to a `.docx` while a `~$` lock exists.** Prepare and validate the edit on a working
copy, then wait for the lock to clear, then swap. Confirm the lock is gone *immediately before* the
copy, not five minutes earlier.

## The trap in the recovery

The obvious recovery — restore the working copy that had the edits — is wrong if the author was
editing meanwhile. On 2026-08-31 the author had, in that window, promoted the three proposed
cross-layer bridges into the declared set at `[P107]`, deleted `[P109]`, and rewritten the Figure 4
and Figure 5 captions. Restoring the earlier copy would have destroyed all four.

**Rebuild, do not restore.** Copy the current file, re-run the edits against it, and verify the
author's changes survive:

```bash
diff <(dump base.docx) <(dump rebuilt.docx)   # strip paragraph indices first —
                                              # an inserted paragraph renumbers everything after it
```

The content diff should show exactly the paragraphs you intended and nothing else. Paragraph indices
shift, so compare stripped text, not indexed text.

## Related hazard: concurrent sessions

Two Claude sessions were working on this manuscript simultaneously on 2026-08-31 — one on C55, one
on C45/C89 figure work. Both edited the same `.docx` and the same revision log. Consequences:

- The moving file was partly *another agent*, not the human.
- **Do not `git add` the manuscript or the revision log wholesale** when another session has
  uncommitted work in them — you will sweep their changes into your commit. Check
  `git status`/`git diff` for content you did not write before staging.

## Related

- [[../decisions/Cited artefacts go to a separate deposit, not the development repository]]
- [[../../sessions/2026-08-31 T1 R14.3 — C55 repository reference and the ontology deposit|Session where this occurred]]
