---
tags: [decision, security, authentication]
date: 2026-04-05
---

# Passwords Hashed Client-Side with SubtleCrypto SHA-256

## Decision

User passwords are hashed in the browser using `SubtleCrypto.digest('SHA-256')` with a `"dg_salt_"` prefix, then stored in `localStorage`.

## Implementation

```javascript
async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode("dg_salt_" + password);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0')).join('');
}
```

Stored in `localStorage.dg_users[email].passwordHash`.

## Rationale

- **No backend auth service** — entire auth is client-side for rapid prototyping
- **Better than plaintext** — at least hashed before storage
- **Browser-native** — SubtleCrypto is available in all modern browsers

## Known Weaknesses

- **Client-side only** — anyone with localStorage access can read/modify user data
- **Static salt** — `"dg_salt_"` is hardcoded and same for all users
- **SHA-256 is fast** — not designed for password hashing (bcrypt/scrypt preferred)
- **No rate limiting** — brute force possible in browser console
- **No server verification** — trust is entirely client-side

## Future Direction

Server-side authentication with proper password hashing (bcrypt), session tokens, and rate limiting should replace this as the product matures.

## Related

- [[UI is a single-file React 18 SPA with no build step]]
