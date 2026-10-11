import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const panel = await readFile(new URL("../src/screens/DegramGrantsPanel.jsx", import.meta.url), "utf8");
const screen = await readFile(new URL("../src/screens/ConnectorsScreen.jsx", import.meta.url), "utf8");
const client = await readFile(new URL("../src/lib/connectorsApi.js", import.meta.url), "utf8");

// The separate regular-connector reveal must remain; it must never be reachable
// from the DeGram card or from the host's trimmed view.
test("DeGram grant panel never exposes a key or clipboard action", () => {
  assert.doesNotMatch(panel + client, /dgp_|clipboard|TokenRevealPanel|createDegramPairing|localStorage|sessionStorage/);
  assert.match(screen, /<DegramGrantsPanel/);
  assert.doesNotMatch(screen, /\+ Pair DeGram|createDegramPairing|revokeDegramPairing|isDegram=\{isDegram\}/);
  assert.match(screen, /connector\.id === DEGRAM_CONNECTOR_ID\s*\?\s*<DegramGrantsPanel/);
});

test("host renders only the trimmed DeGram panel, not the connector registry", () => {
  assert.match(screen, /if \(hosted\) return <DegramGrantsPanel[^>]*trimmed/);
  assert.match(screen, /if \(active && !hosted\) load\(\)/);
  assert.match(panel, /const administer = !trimmed && canAdminister/);
  assert.match(panel, /listMyGrants\(/);
  assert.match(panel, /requestGrant\(/);
});

test("grant administration is limited to owners/admins in the panel", () => {
  assert.match(panel, /activeRole === "owner" \|\| !!user\?\.isAdmin/);
  assert.match(panel, /!trimmed && canAdminister/);
  assert.match(panel, /listProjectGrants\(/);
  assert.match(panel, /issueGrant\(/);
  assert.match(panel, /revokeGrant\(/);
  assert.match(panel, /GRANT_EXISTS/);
});
