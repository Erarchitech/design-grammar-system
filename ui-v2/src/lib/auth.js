// Thin client of the data-service identity endpoints (phase 1205, D-01/D-05).
// The server owns accounts, password hashing and sessions; the browser only
// carries the HttpOnly dg_session cookie it cannot read. Nothing here persists
// a password, hash, session token or invite code in browser storage.

import { apiFetch, dataServiceBase, ApiError } from "./apiClient.js";

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
  return toUser({ username: sessionResponse?.username || "", isAdmin: sessionResponse?.isAdmin });
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
