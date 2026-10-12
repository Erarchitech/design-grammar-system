// Pure helpers for the Members panel role Select (Phase 1308, D-16). The server stays the
// control (409 LAST_OWNER); these only decide what the UI offers.

// True when `username` is an owner and no other member is. The Select of that member is disabled.
export function isSoleOwner(members, username) {
  if (!Array.isArray(members)) return false;
  const owners = members.filter((member) => member && member.role === "owner");
  return owners.length === 1 && owners[0].username === username;
}

function identity(user) {
  const value = user?.username ?? user?.email ?? user?.name;
  return typeof value === "string" && value ? value : null;
}

// A non-admin owner who lowers their own role loses the Members panel at once, so the UI asks first.
export function needsSelfDemotionConfirm({ user, username, from, to } = {}) {
  if (!user || user.isAdmin) return false;
  const self = identity(user);
  if (!self || typeof username !== "string" || self !== username) return false;
  return from === "owner" && to !== "owner";
}
