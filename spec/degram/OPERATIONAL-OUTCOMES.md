# DeGram operational outcomes

Status: Phase 1301 (DeGram Agent, v13.0). Owner of the vocabulary: the framework (`data-service/degram_relay.py`, `OPERATIONAL_OUTCOMES`). Checked by `data-service/tests/test_degram_relay.py`.

## What this is

When DeGram talks to the model relay, to the Grasshopper canvas bridge, to the Revit adapter or to its own credential store, each call can end in a *named operational outcome*. An operational outcome says **how the call went** (the provider timed out, the bridge is off, the pinned document is not open). It says nothing about **whether a design satisfies a rule**.

These outcomes are operational outcomes, never evaluator verdicts. The eight canonical evaluator statuses (`passed`, `failed`, `unknown`, `not_evaluated`, `no_population`, `unsupported`, `indeterminate`, `error`, `spec/EVIDENCE-CONTRACT.md`, `spec/evidence-contract.schema.json` `$defs.CanonicalStatus`) are untouched by this document and stay frozen. The two vocabularies are disjoint: a test compares them case-insensitively and fails if any code appears in both. An operational outcome must never be written into an evidence envelope as a status, and a status must never be reported as an operational outcome.

Rules for every outcome:

- It is a closed set. Adding, renaming or removing a code is a change to this file, the `OPERATIONAL_OUTCOMES` constant and the machine-checked block below in the same commit.
- A failed call is reported with its code and is never retried automatically and never replaced by another provider, model or document (no fallback).
- An outcome carries no prompt text, no key and no project data.

## Relay outcomes (plan 1301-08)

Source: `POST /degram/v1/chat/completions`. The HTTP status applies when the outcome is known before any streaming starts; after streaming started the outcome is sent as a final SSE event `event: degram-error` with the same code. Every relayed request writes its outcome to the provenance record.

| Code | HTTP status | Meaning |
|------|-------------|---------|
| `COMPLETED` | 200 | The upstream stream ended normally (provenance only) |
| `CANCELLED` | none | The client disconnected; the upstream stream was closed within one chunk (provenance only) |
| `PROVIDER_TIMEOUT` | 504 | Connect, first-byte (`DEGRAM_RELAY_FIRST_BYTE_TIMEOUT_S`, 60 s) or total (`DEGRAM_RELAY_TOTAL_TIMEOUT_S`, 300 s) limit exceeded |
| `PROVIDER_RATE_LIMITED` | 429 | Upstream 429; `retryAfter` seconds when the upstream sent a numeric `Retry-After`, else `null` |
| `PROVIDER_UNAVAILABLE` | 503 | Upstream unreachable, connection broken, or upstream 5xx |
| `PROVIDER_ERROR` | 502 | Any other upstream non-2xx (including an unfollowed redirect); `upstreamStatus` and an excerpt of at most 2 KiB with the key scrubbed |
| `RELAY_NOT_CONFIGURED` | 503 | No complete operator configuration (`degram-llm.json`) |
| `POLICY_DENY` | 403 | The project's provider-export policy (or whole-definition policy) forbids the request; `reason` names which. Terminal: consent does not override it |
| `CONSENT_REQUIRED` | 428 | Whole-definition scope is allowed by policy but the per-request consent header is missing |

## Bridge outcomes (plans 1301-06, 1301-07, 1301-11)

Source: the DG Canvas bridge (Grasshopper) and the read-only Revit adapter.

| Code | Meaning |
|------|---------|
| `BUSY` | The host's UI thread did not answer within the bounded wait; a client that hit `BUSY` on a mutating command must re-read state |
| `BRIDGE_OFF` | The bridge listener or the host is not reachable |
| `EXTENSION_NOT_LOADED` | The host is running but the DG extension (pyRevit routes, Canvas listener) is not loaded |
| `ROUTES_DISABLED` | The Revit routes server is switched off in its configuration |
| `ROUTES_NOT_LOOPBACK` | The Revit routes server is not bound to a loopback address (reported as `SETUP_INCOMPLETE` with this reason) |
| `SETUP_INCOMPLETE` | A setup precondition is unmet; the reason field says which |
| `IDENTITY_MISMATCH` | The document answering is not the pinned document; no context was read |
| `DOCUMENT_NOT_OPEN` | The pinned document is no longer open |

## Agent outcomes (plans 1301-10, 1301-11)

Source: the local DeGram agent.

| Code | Meaning |
|------|---------|
| `CREDENTIALS_MISSING` | No delegated token is held; the next provider call is refused |
| `CREDENTIALS_EXPIRED` | The held delegated token is past its expiry; refused before any request |
| `DEGRAM_LOCKED` | An attempt to select a model/provider or change locked configuration was refused |
| `SCOPE_NOT_SUPPORTED` | The requested context scope is not available for the host (whole definition for Revit) |

## Machine-checked vocabulary

One code per line. The set must equal `degram_relay.OPERATIONAL_OUTCOMES` exactly, in both directions.

<!-- degram-outcomes:codes:start -->
```
BRIDGE_OFF
BUSY
CANCELLED
COMPLETED
CONSENT_REQUIRED
CREDENTIALS_EXPIRED
CREDENTIALS_MISSING
DEGRAM_LOCKED
DOCUMENT_NOT_OPEN
EXTENSION_NOT_LOADED
IDENTITY_MISMATCH
POLICY_DENY
PROVIDER_ERROR
PROVIDER_RATE_LIMITED
PROVIDER_TIMEOUT
PROVIDER_UNAVAILABLE
RELAY_NOT_CONFIGURED
ROUTES_DISABLED
ROUTES_NOT_LOOPBACK
SCOPE_NOT_SUPPORTED
SETUP_INCOMPLETE
```
<!-- degram-outcomes:codes:end -->
