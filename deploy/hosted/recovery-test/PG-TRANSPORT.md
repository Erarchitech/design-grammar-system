# Bounded PostgreSQL output transport — OFFLINE reference, NOT approved

Status: **reference logic and tests only.** Not wired into the orchestrator, not in the release
allowlist, not a working transport. The production `prepare()` guard
(`independently reviewed runtime profile unavailable`) and the fail-closed PostgreSQL
export/restore refusal stay unchanged. Native flags (`nativeRecoveryProven`,
`remoteCleanupQualified`) stay false.

Files: `multistore_pg_transport.py` (reference sink), `../tests/test_multistore_pg_transport.py`
(18 tests, real synthetic child processes, no PostgreSQL/Docker/network).

## What the synthetic tests exercise (Windows, synthetic children; not qualification)

- The only producer destination is an anonymous pipe; the sink checks the remaining budget
  BEFORE each write, so the result file never exceeds the budget (exact budget accepted,
  one extra byte or an endless producer gives `OVERFLOW`, nothing published).
- Timeout (silent child, stdout-closed-but-alive child), nonzero exit, empty output,
  stderr flood, existing directory and final-name collisions are handled; the direct child is
  reaped, the reader joined, partials removed, a colliding final is preserved.
- Reports carry no child bytes, stderr, paths or environment. The only derived value is the
  `sha256` of the published bytes; it is a function of the child output, so treat the report as
  confidential for low-entropy output and do not publish it with plaintext-sensitive data.
- Invalid budget, seconds, names or parent return `REJECTED` without launching anything; a
  publication that succeeded is reported `COMPLETE` even if removing the partial fails.
- The old `psql --output` / `pg_dump --file` boundary is not bounded by stdout capture
  (regression test documents the 4 MiB + 1 byte direct write).

## Dump budget (owner decision, no default)

`limit` is a mandatory argument without a default; `HARD_CEILING` (1 GiB) is only a safety rail.
Module constants `SNAPSHOT_LIMIT` / `DUMP_LIMIT` were removed on purpose. The 4 MiB (snapshot)
and 64 MiB (dump) values used in the earlier prototype are **test settings, not approved
operational budgets, not measured capacity**. The owner sets the real dump budget after a
size measurement; until then no operational run may be configured.

## What a production supervisor must reproduce (not implemented)

Pre-existing design (`DESIGN.md` of prototype v11, summarised): one static Linux/amd64 executable,
hash-pinned, read-only mounted into a NEW one-shot helper container on the exact PostgreSQL image
already bound for `speckle-postgres`; PID 1 in a private PID namespace; fixed operation enum
(`snapshot-before|dump|snapshot-after|snapshot-destination`, restore enums separate); no Docker
socket, no capabilities, `read_only` rootfs, `no-new-privileges`, explicit CPU/memory/pids limits,
only the exchange volume; fixed environment from `pg_spec()`; container-local 180 s monotonic
deadline independent of the Docker client; host kills and inspects the EXACT owned helper
container on lost control. The Python reference cannot run inside the Alpine PostgreSQL image.

## Owner decisions recorded 2026-10-24 (design level only; nothing authorised to run)

- Architecture: static supervisor + one-shot helper container on the exact PostgreSQL image,
  accepted as a DESIGN decision. No container is added to the model or started; it may appear only
  in a reviewed package and only after a separate approval of a native run.
- Dump budget: measure first (read-only database size on synthetic data in the native run), then
  set budget = measured size x 1.5 rounded up; no operational budget is configured before that.
- Supervisor build: Go, built inside Docker (owner choice), NOT on the development PC, where
  Docker/services stay forbidden. Build location, pinned builder image digest and the run command
  need a reviewed script and a separate approval before anything is pulled or built.

## Open gates (nothing here is claimed)

1. No Go/Rust/C toolchain is installed on the development PC; the supervisor source, a
   reproducible pinned build and its binary hash do not exist. Installing a toolchain needs a
   separate approval.
2. Adding the helper container and executable to the model needs separate owner authorization.
3. Linux permissions, private-PID-namespace cleanup, cgroup kill, blocked-filesystem syscall
   cancellation (the Python deadline cannot interrupt one) and native `pg_dump`/`pg_restore`
   behaviour are unqualified.
4. Restore side (pristine check, `pg_restore` supervision) is not implemented.
5. Dump budget (above).
