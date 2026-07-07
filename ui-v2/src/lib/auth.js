// Client-side auth, byte-compatible with the legacy SPA's localStorage store
// (graph-viewer/index.html RegisterPage): users live in `dg_users`
// keyed by email with salted SHA-256 password hashes; the active session
// is `dg_current_user`. Existing accounts keep working after the V2 cutover.

export async function hashPassword(password) {
  const data = new TextEncoder().encode("dg_salt_" + password);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function loadUsers() {
  try {
    return JSON.parse(localStorage.getItem("dg_users") || "{}");
  } catch {
    return {};
  }
}

function displayName(u) {
  return [u.name, u.surname].filter(Boolean).join(" ") || "Architect";
}

export function currentUser() {
  const email = localStorage.getItem("dg_current_user");
  if (!email) return null;
  const u = loadUsers()[email];
  if (!u) return null;
  return { email, name: displayName(u) };
}

export async function login(email, password) {
  const users = loadUsers();
  const u = users[email];
  if (!u) throw new Error("User not found.");
  const hash = await hashPassword(password);
  if (hash !== u.passwordHash) throw new Error("Invalid password.");
  localStorage.setItem("dg_current_user", email);
  return { email, name: displayName(u) };
}

export async function register(fullName, email, password) {
  const users = loadUsers();
  if (users[email]) throw new Error("User already exists.");
  const parts = fullName.trim().split(/\s+/);
  const name = parts[0] || "";
  const surname = parts.slice(1).join(" ");
  users[email] = { passwordHash: await hashPassword(password), name, surname, projects: [] };
  localStorage.setItem("dg_users", JSON.stringify(users));
  localStorage.setItem("dg_current_user", email);
  return { email, name: displayName(users[email]) };
}

export function signOut() {
  localStorage.removeItem("dg_current_user");
}
