// Single authenticated transport for every data-service call made by the UI
// (phase 1205, D-01). The browser holds no graph credential: identity is the
// HttpOnly dg_session cookie, and every unsafe request carries a CSRF marker
// header that a cross-site form post cannot set.

export const AUTH_EXPIRED_EVENT = "dg-auth-expired";
export const CSRF_HEADER = "X-DG-CSRF";

const DEFAULTS = {
  dataServiceUrl: "/data-service",
  speckleBaseUrl: "http://localhost:8090"
};

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

// D-12: the runtime config carries only the two non-secret endpoints. Anything
// else present on window.GRAPH_CONFIG (legacy credential keys from an old
// config.js) is deliberately ignored. The Speckle read token arrives only in
// the project-authorised /validation/view response.
export function getConfig() {
  const runtime = (typeof window !== "undefined" && window.GRAPH_CONFIG) || {};
  return {
    dataServiceUrl: runtime.dataServiceUrl || DEFAULTS.dataServiceUrl,
    speckleBaseUrl: runtime.speckleBaseUrl || DEFAULTS.speckleBaseUrl
  };
}

export function dataServiceBase() {
  return String(getConfig().dataServiceUrl || DEFAULTS.dataServiceUrl).replace(/\/+$/, "");
}

export class ApiError extends Error {
  constructor(message, { status = 0, code = "", hint = "" } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.hint = hint;
  }
}

async function readBody(res) {
  const text = await res.text().catch(() => "");
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function messageFrom(body, res) {
  const detail = body && typeof body === "object" ? body.detail : undefined;
  if (detail && typeof detail === "object" && !Array.isArray(detail) && detail.error) {
    return String(detail.error);
  }
  if (typeof detail === "string" && detail) return detail;
  if (typeof body === "string" && body) return body;
  return res.statusText || `HTTP ${res.status}`;
}

// apiFetch(url, { method, body, headers, allow404, signal, passthrough })
//   - returns the parsed JSON body; null for 204 (and for 404 when allow404)
//   - throws ApiError({status, code, hint}) for any other non-2xx status
//   - dispatches AUTH_EXPIRED_EVENT on window for 401 before throwing
//   - passthrough: never throws on non-2xx, resolves { ok, status, body }
//     (still dispatches AUTH_EXPIRED_EVENT on 401); for callers that branch on
//     the response shape rather than the status code
export async function apiFetch(
  url,
  { method = "GET", body, headers, allow404 = false, signal, passthrough = false } = {}
) {
  const verb = String(method).toUpperCase();
  const finalHeaders = { ...(headers || {}) };
  const init = { method: verb, credentials: "include", headers: finalHeaders };
  if (signal) init.signal = signal;
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    finalHeaders["Content-Type"] = "application/json";
  }
  if (UNSAFE_METHODS.has(verb)) finalHeaders[CSRF_HEADER] = "1";

  const res = await fetch(url, init);

  if (res.status === 401 && typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
  }

  if (passthrough) {
    return { ok: res.ok, status: res.status, body: (await readBody(res)) ?? {} };
  }
  if (res.status === 204) return null;
  if (res.status === 404 && allow404) return null;

  const parsed = await readBody(res);
  if (!res.ok) {
    const detail = parsed && typeof parsed === "object" ? parsed.detail : undefined;
    throw new ApiError(messageFrom(parsed, res), {
      status: res.status,
      code: (detail && typeof detail === "object" && detail.code) || "",
      hint: (detail && typeof detail === "object" && detail.hint) || ""
    });
  }
  return parsed;
}
