// Thin client of the data-service identity endpoints (phase 1205, D-01/D-05).
// The server owns accounts, password hashing and sessions; the browser only
// carries the HttpOnly dg_session cookie it cannot read. Nothing here persists
// a password, hash, session token or invite code in browser storage.

import { apiFetch, dataServiceBase, ApiError } from "./apiClient.js";
import { t } from "../i18n/index.js";

const LEGACY_KEYS = ["dg_users", "dg_current_user"];

function url(path) {
  return `${dataServiceBase()}${path}`;
}

// Deletes the pre-1205 localStorage accounts. Their static-salt SHA-256
// hashes are never migrated (D-05): the only carry-over is deletion.
export function purgeLegacyLocalAuth() {
  try {
    for (const key of LEGACY_KEYS) localStorage.removeItem(key);
  } catch {
    // storage unavailable — nothing to purge
  }
}

// WR-09 (1205 review): tenant content (built graphs, run thumbnails, the last
// project selection, ...) lives under dgv2_* keys. It must not survive a
// logout, an expired session or a change of account in the same browser.
// Only the theme preference is user-agnostic and kept.
const TENANT_KEY_PREFIX = "dgv2_";
const KEPT_KEYS = new Set(["dgv2_theme"]);
export const OWNER_KEY = "dgv2_owner";

export function clearTenantBrowserData() {
  try {
    const doomed = [];
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i);
      if (key && key.startsWith(TENANT_KEY_PREFIX) && !KEPT_KEYS.has(key)) doomed.push(key);
    }
    for (const key of doomed) localStorage.removeItem(key);
  } catch {
    // storage unavailable — nothing was persisted
  }
}

function toUser(me) {
  return {
    email: me.username,
    name: me.username,
    isAdmin: !!me.isAdmin,
    memberships: Array.isArray(me.memberships) ? me.memberships : []
  };
}

// Resolves the signed-in user from the session cookie; null when not signed in.
export async function currentUser() {
  try {
    const me = await apiFetch(url("/auth/me"));
    return me && me.username ? toUser(me) : null;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}

async function establish(sessionResponse) {
  // login / accept-invite answer {username, isAdmin}; /auth/me adds memberships.
  const me = await currentUser();
  if (me) return me;
  // A successful login response is not proof of a still-live session. In
  // particular, a 401 from /auth/me must not resurrect the response identity.
  throw new ApiError(t("Session could not be established. Sign in again."), { status: 401 });
}

export async function login(username, password) {
  const res = await apiFetch(url("/auth/login"), { method: "POST", body: { username, password } });
  return establish(res);
}

export async function acceptInvite(inviteCode, password) {
  const res = await apiFetch(url("/auth/accept-invite"), {
    method: "POST",
    body: { inviteCode, password }
  });
  return establish(res);
}

// Self-registration (amendment of D-05, 2026-09-30): the server offers it in
// the local profile only and answers 404 elsewhere. The account starts with no
// memberships and no admin flag; the user creates their own projects.
export async function register(username, password) {
  const res = await apiFetch(url("/auth/register"), {
    method: "POST",
    body: { username, password }
  });
  return establish(res);
}

// Public, secret-free deployment options. Callers must fail closed: treat a
// rejected call as { selfRegistration: false }.
export async function authOptions() {
  const res = await apiFetch(url("/auth/options"));
  return { selfRegistration: res?.selfRegistration === true };
}

export async function logout() {
  try {
    await apiFetch(url("/auth/logout"), { method: "POST" });
  } catch (err) {
    // an already-expired session is signed out either way
    if (!(err instanceof ApiError && err.status === 401)) throw err;
  }
}

export async function changePassword(currentPassword, newPassword) {
  await apiFetch(url("/auth/password"), {
    method: "POST",
    body: { currentPassword, newPassword }
  });
}
