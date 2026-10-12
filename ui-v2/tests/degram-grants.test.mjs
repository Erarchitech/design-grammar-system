import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { readFileSync } from "node:fs";

const panel = await readFile(new URL("../src/screens/DegramGrantsPanel.jsx", import.meta.url), "utf8");
const screen = await readFile(new URL("../src/screens/ConnectorsScreen.jsx", import.meta.url), "utf8");
const client = await readFile(new URL("../src/lib/connectorsApi.js", import.meta.url), "utf8");

test("DeGram grant panel never exposes a key or clipboard action", () => {
  assert.doesNotMatch(panel + client, /dgp_|clipboard|TokenRevealPanel|createDegramPairing|localStorage|sessionStorage/);
  assert.match(screen, /<DegramGrantsPanel/);
  assert.match(screen, /connector\.id === DEGRAM_CONNECTOR_ID/);
  assert.doesNotMatch(screen, /\+ Pair DeGram|createDegramPairing|revokeDegramPairing|isDegram=\{isDegram\}/);
});

test("host renders the connector table of every connector, not the trimmed DeGram panel", () => {
  assert.match(screen, /if \(hosted\) return \([\s\S]*<HostedConnectorsTable/);
  assert.doesNotMatch(screen, /<DegramGrantsPanel[^>]*trimmed/);
  assert.match(screen, /if \(active && project\) load\(\)/);
  assert.match(screen, /listConnectors\(project\)/);
  assert.match(panel, /const administer = !trimmed && canAdminister/);
  assert.match(panel, /listMyGrants\(/);
  assert.match(panel, /requestGrant\(/);
});

test("hosted table: one row per connector, access cell, shared language and colored dots", () => {
  const table = readFileSync(new URL("../src/screens/HostedConnectorsTable.jsx", import.meta.url), "utf8");
  const colors = readFileSync(new URL("../src/styles/tokens/colors.css", import.meta.url), "utf8");
  assert.match(table, /<table/);
  assert.match(table, /connectors\.map\(\(connector\)/);
  assert.match(table, /useT\(/);
  assert.match(table, /connector\.status === "active"/);
  assert.match(table, /var\(--status-on\)/);
  assert.match(table, /var\(--status-fail\)/);
  assert.match(table, /t\("Available"\)/);
  assert.match(table, /t\("Request access"\)/);
  assert.match(table, /t\("Request sent"\)/);
  assert.match(table, /const cell = \{[^}]*border: "none"/);
  assert.match(table, /borderCollapse: "collapse", border: "none"/);
  assert.match(colors, /--status-on:/);
  assert.doesNotMatch(screen, /var\(--status-on\)/);
  assert.match(screen, /status === "active" \? "var\(--status-pass\)" : "var\(--status-base\)"/);
});

test("hosted and regular screens expose no connector credential action", () => {
  assert.doesNotMatch(screen + client, /TokenRevealPanel|createCredential|revokeCredential|renderReveal=/);
  assert.doesNotMatch(screen, /localStorage|sessionStorage/);
  assert.match(screen, /active_sessions/);
});

test("grant administration is limited to owners/admins in the panel", () => {
  assert.match(panel, /activeRole === "owner" \|\| !!user\?\.isAdmin/);
  assert.match(panel, /!trimmed && canAdminister/);
  assert.match(panel, /listProjectGrants\(/);
  assert.match(panel, /issueGrant\(/);
  assert.match(panel, /revokeGrant\(/);
  assert.match(panel, /GRANT_EXISTS/);
});
