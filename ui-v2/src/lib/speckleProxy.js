// Speckle geometry through the DG proxy (Phase 1301 plan 09, D-21, DGCL-03).
//
// The browser holds no Speckle credential. The view payload's `viewerResources` are
// concrete object URLs that already point at the project-authorised DG proxy
// (`/data-service/speckle-proxy/{project}/objects/{speckleProjectId}/{objectId}`). The
// stock `SpeckleLoader` cannot use them: it keeps only the origin of its resource URL,
// takes a token argument and falls back to a stored token. So the viewer uses
// `createProxyObjectLoader` below, which builds the same `ObjectLoader2` the stock loader
// would, but with the proxy prefix as its server URL and a same-origin cookie-credentialed
// fetch. Every request therefore lands on `.../speckle-proxy/{project}/objects/...` or
// `.../speckle-proxy/{project}/api/v2/projects/.../object-stream/`, authorised by the
// session cookie like any other DG call, and never by a token.

import { ObjectLoader2Factory } from "@speckle/objectloader2";
import { CSRF_HEADER } from "./apiClient.js";
import { t } from "../i18n/index.js";

const OBJECT_HASH = "[0-9a-f]{32}";
const RESOURCE_PATTERN = new RegExp(
  `^(/(?:[A-Za-z0-9._~%-]+/)*speckle-proxy/[A-Za-z0-9._~%-]+)/objects/([A-Za-z0-9_-]+)/(${OBJECT_HASH})$`
);
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const FORBIDDEN_HEADERS = new Set(["authorization", "proxy-authorization", "cookie"]);

function hasDotSegment(path) {
  return path.split("/").some((segment) => {
    try {
      const decoded = decodeURIComponent(segment);
      return decoded === "." || decoded === "..";
    } catch {
      return true;
    }
  });
}

// "/data-service/speckle-proxy/P1/objects/<speckleProjectId>/<hash>" ->
// { serverUrl: "/data-service/speckle-proxy/P1", streamId, objectId }, or null for
// anything else (absolute and protocol-relative URLs, Speckle viewer URLs, other paths,
// non-hash object ids, dot segments, queries, fragments).
export function parseViewerResource(value) {
  if (typeof value !== "string") return null;
  const match = RESOURCE_PATTERN.exec(value);
  if (!match || hasDotSegment(value)) return null;
  return { serverUrl: match[1], streamId: match[2], objectId: match[3] };
}

function isProxyPath(url) {
  return (
    typeof url === "string" &&
    url.startsWith("/") &&
    !url.startsWith("//") &&
    !url.includes("://") &&
    !url.includes("\\") &&
    /^\/(?:[^/?#]+\/)*speckle-proxy\//.test(url) &&
    !hasDotSegment(url.split(/[?#]/)[0])
  );
}

function plainHeaders(headers) {
  const entries =
    headers && typeof headers.entries === "function" && !Array.isArray(headers)
      ? [...headers.entries()]
      : Object.entries(headers || {});
  const out = {};
  for (const [key, value] of entries) {
    if (!FORBIDDEN_HEADERS.has(String(key).toLowerCase())) out[key] = value;
  }
  return out;
}

// The one fetch the geometry loader may use: same-origin, cookie credentialed (the DG
// session), CSRF marker on unsafe methods (the object-stream batch fetch is a POST), and
// structurally unable to carry an Authorization or Cookie header or to reach any URL that
// is not under /speckle-proxy/.
export async function speckleProxyFetch(input, init = {}) {
  const url = typeof input === "string" ? input : input && input.url;
  if (!isProxyPath(url)) {
    throw new Error(t("Geometry requests may only target the DG /speckle-proxy/ routes."));
  }
  const method = String(init.method || "GET").toUpperCase();
  const headers = plainHeaders(init.headers);
  if (UNSAFE_METHODS.has(method)) headers[CSRF_HEADER] = "1";
  return fetch(url, { ...init, method: init.method, headers, credentials: "include" });
}

// An ObjectLoader2 over one proxy resource. The loader cache is off on purpose: its
// IndexedDB store would keep project geometry on the device after logout, which the
// session-bound proxy is meant to prevent.
export function createProxyObjectLoader(resourceUrl, { attributeMask, objectTypeMask } = {}) {
  const target = parseViewerResource(resourceUrl);
  if (!target) {
    throw new Error(t("Not a DG Speckle proxy resource URL; refusing to load geometry from it."));
  }
  return ObjectLoader2Factory.createFromUrl({
    serverUrl: target.serverUrl,
    streamId: target.streamId,
    objectId: target.objectId,
    token: undefined,
    headers: undefined,
    attributeMask,
    objectTypeMask,
    options: { fetch: speckleProxyFetch, useCache: false },
  });
}
