# -*- coding: utf-8 -*-
"""DG data-service client of the Revit connector (D-47, contract sections 3-5, 8).

Mirrors ``DG/src/DG.Core/Data/ConnectorSessionClient.cs``: sign in as the
``revit`` connector with the account login plus a best-effort logout, then use
the returned ``dgk_`` token as a Bearer token for the mapping session routes.

Sign-in sequence::

    POST /auth/login              {username, password}       -> Set-Cookie dg_session
    POST /auth/connector-session  {project, connector_id}     -> {token, project, expiresAt}
                                  Cookie: dg_session=...       (X-DG-CSRF: 1)
    POST /auth/logout             {}                          (always, best effort)

The ``dg_session`` cookie is captured and replayed by hand: a ``Secure``
cookie issued over a loopback ``http://`` URL would otherwise be dropped by a
cookie jar. The response may also carry a ``neo4j`` block with a database
password; it is never read, kept or returned.

Safety rules that no caller can switch off:

* plain ``http://`` to a host that is not loopback is refused *before* any
  request, so the password and the token never travel unencrypted off-machine;
* every request carries a timeout (15 s; 60 s for a mapping session call);
* no proxy, no redirect following;
* the password and the token never appear in an exception message, a return
  value other than the token field, or a log line. Server-supplied text is
  scrubbed of both before it reaches an exception.

Standard library only; Python 2.7 / 3 syntax (pyRevit's IronPython 2.7 under Revit).
"""

import json
import socket

try:  # CPython 3 and IronPython 3
    import http.client as _http_client
    import urllib.error as _url_error
    import urllib.parse as _url_parse
    import urllib.request as _url_request
    _url_quote = _url_parse.quote
except ImportError:  # pyRevit Revit 2024: IronPython 2.7
    import httplib as _http_client
    import urllib2 as _url_request
    import urllib2 as _url_error
    import urlparse as _url_parse
    import urllib as _url_legacy
    _url_quote = _url_legacy.quote

try:
    import ipaddress as _ipaddress
except ImportError:  # IronPython 2.7 standard library does not ship ipaddress
    _ipaddress = None

try:
    _UNICODE_TYPE = unicode
    _TEXT_TYPES = (basestring,)
    # In IronPython 2 ``bytes`` may be a CLR type instead of ``str``.
    _BINARY_TYPES = (str, bytearray)
except NameError:
    _UNICODE_TYPE = str
    _TEXT_TYPES = (str,)
    _BINARY_TYPES = (bytes, bytearray)

try:
    _TIMEOUT_ERRORS = (socket.timeout, TimeoutError)
except NameError:
    _TIMEOUT_ERRORS = (socket.timeout,)

_IO_ERRORS = (IOError, OSError, ValueError, _http_client.HTTPException)

#: DG data service of the local Docker stack (CONNECTOR ``DataServiceUrl``).
DEFAULT_BASE_URL = "http://localhost:8000"

#: Seconds per sign-in request; mapping session calls may take much longer.
DEFAULT_TIMEOUT_SECONDS = 15.0
SESSION_TIMEOUT_SECONDS = 60.0

#: Prefix of a connector session token (``DataServiceRequestAuth.TokenPrefix``).
TOKEN_PREFIX = "dgk_"

#: Anti-forgery header the data service requires on state-changing requests.
CSRF_HEADER = "X-DG-CSRF"
CSRF_VALUE = "1"

#: Name of the account session cookie the mint request has to replay.
SESSION_COOKIE_NAME = "dg_session"

#: Replacement text for a secret that a server put into an error message.
REDACTED = "[redacted]"

#: Codes of :class:`DgClientError`.
ERROR_CODES = frozenset([
    "REJECTED",           # 401 - wrong credentials, expired or revoked token
    "FORBIDDEN",          # 403 - connector access not granted / wrong project
    "PROJECT_REQUIRED",   # 422 - the connector session needs a project
    "THROTTLED",          # 429 - too many attempts
    "INSECURE_TRANSPORT", # refused before any request
    "UNREACHABLE",        # network failure, timeout, malformed response
    "HTTP_ERROR",         # any other status
])

#: HTTP status -> error code (the server ``code`` text stays in the message).
_STATUS_CODES = {
    401: "REJECTED",
    403: "FORBIDDEN",
    422: "PROJECT_REQUIRED",
    429: "THROTTLED",
}


# --- error type ---------------------------------------------------------------

class DgClientError(Exception):
    """A DG data-service call failed.

    ``code`` is one of :data:`ERROR_CODES`; ``status`` is the HTTP status or
    None when no response arrived; ``server_code`` is the ``code`` text of the
    server error envelope (``MAPPING_INPUT_INVALID``, ``AUTH_INVALID``, ...)
    when the answer carried one. ``message`` never holds the password or the
    token: those are scrubbed before the error is built.
    """

    def __init__(self, code, message, status=None, server_code=None):
        self.code = str(code)
        self.message = _text(message)
        self.status = status
        self.server_code = None if server_code is None else str(server_code)
        text = self.code if not self.message else "{}: {}".format(self.code, self.message)
        super(DgClientError, self).__init__(text)

    def __repr__(self):
        return "DgClientError(code={!r}, status={!r}, server_code={!r}, message={!r})".format(
            self.code, self.status, self.server_code, self.message)


# --- small helpers ------------------------------------------------------------

def _text(value):
    """Text for JSON, URL and diagnostics without losing Python-2 Unicode."""
    if value is None:
        return u""
    if isinstance(value, _UNICODE_TYPE):
        return value
    if isinstance(value, _BINARY_TYPES):
        try:
            return value.decode("utf-8", "replace")
        except Exception:
            pass
    try:
        return _UNICODE_TYPE(value)
    except Exception:
        return _UNICODE_TYPE(str(value), "utf-8", "replace")


def _scrub(text, secrets):
    """``text`` with every secret replaced, so no message can carry one."""
    result = _text(text)
    for secret in secrets or ():
        if secret:
            result = result.replace(_text(secret), REDACTED)
    return result


def _error(code, message, status=None, secrets=(), server_code=None):
    return DgClientError(code, _scrub(message, secrets), status, server_code)


# --- transport hygiene --------------------------------------------------------

def _host_is_loopback(host):
    """True only for a literal local address or localhost.

    ``ipaddress`` is present on CPython 3 but absent from pyRevit's
    IronPython 2.7 standard library. The compact fallback deliberately accepts
    only the loopback forms needed by this connector; it never DNS-resolves a
    host, so a deceptive public name cannot be turned into a local address.
    """
    text = _text(host).strip().strip("[]").lower()
    if not text:
        return False
    if text == "localhost":
        return True
    if text.startswith("::ffff:"):  # IPv4-mapped IPv6
        text = text[len("::ffff:"):]
    if _ipaddress is not None:
        try:
            return _ipaddress.ip_address(text).is_loopback
        except ValueError:
            return False
    if text == "::1":
        return True
    parts = text.split(".")
    if len(parts) != 4:
        return False
    try:
        octets = [int(part) for part in parts]
    except (TypeError, ValueError):
        return False
    return all(0 <= octet <= 255 for octet in octets) and octets[0] == 127


def normalize_base_url(base_url):
    """``base_url`` without a trailing slash; the default DG URL when empty."""
    text = _text(base_url).strip()
    if not text:
        return DEFAULT_BASE_URL
    return text.rstrip("/")


def _checked_base_url(base_url):
    """Normalised base URL, or ``DgClientError`` before any request is sent.

    A plain ``http://`` URL to a non-loopback host would put the password and
    the token on the wire unencrypted, so it is refused here (D-47 / pitfall 7).
    """
    url = normalize_base_url(base_url)
    parts = _url_parse.urlsplit(url)
    scheme = _text(parts.scheme).lower()
    # Checked before any message echoes the URL, so an embedded password can
    # never reach one.
    if parts.username or parts.password:
        raise _error("UNREACHABLE", "the DG URL must not embed a user name or password")
    if parts.query or parts.fragment:
        raise _error("UNREACHABLE", "the DG URL must not carry a query or a fragment")
    if scheme not in ("http", "https"):
        raise _error("UNREACHABLE",
                     "DG URL must start with http:// or https://, got {!r}".format(url))
    if scheme == "http" and not _host_is_loopback(parts.hostname):
        raise _error("INSECURE_TRANSPORT",
                     "refusing to send credentials to {!r} over plain http: "
                     "use https:// or a loopback host (localhost, 127.0.0.1, ::1)".format(url))
    return url


class _RefuseRedirect(_url_request.HTTPRedirectHandler):
    """A redirect could carry the credentials elsewhere: never follow one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _default_open(request, timeout):
    """Default opener: no proxy, no redirects, one blocking request."""
    opener = _url_request.build_opener(_url_request.ProxyHandler({}), _RefuseRedirect())
    return opener.open(request, timeout=timeout)


class _Response(object):
    """Status, text body and headers of one answer (urllib or an injected fake)."""

    def __init__(self, status, text, headers):
        self.status = status
        self.text = text
        self.headers = headers


def _response_headers(response):
    headers = getattr(response, "headers", None)
    if headers is None:
        info = getattr(response, "info", None)
        if callable(info):
            try:
                headers = info()
            except Exception:
                headers = None
    return headers


def _header_values(response, header_name):
    """Every value of ``header_name`` (case-insensitive) from a response or headers."""
    headers = _response_headers(response)
    if headers is None:
        return []
    wanted = header_name.lower()
    values = []
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        try:
            values.extend([value for value in (get_all(header_name) or []) if value is not None])
        except Exception:
            values = []
    if not values and isinstance(headers, (list, tuple)):
        for item in headers:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                if _text(item[0]).strip().lower() == wanted:
                    values.append(item[1])
            elif isinstance(item, _TEXT_TYPES) and ":" in item:
                name, value = item.split(":", 1)
                if name.strip().lower() == wanted:
                    values.append(value.strip())
    if not values and not isinstance(headers, (list, tuple)):
        items = getattr(headers, "items", None)
        if callable(items):
            try:
                for name, value in items():
                    if _text(name).strip().lower() == wanted and value is not None:
                        values.append(value)
            except Exception:
                pass
    return values


def _session_cookie(response):
    """Value of the ``dg_session`` cookie from ``Set-Cookie``, or None."""
    prefix = SESSION_COOKIE_NAME + "="
    for header in _header_values(response, "Set-Cookie"):
        if isinstance(header, bytes):
            header = header.decode("latin-1", "replace")
        first_pair = _text(header).split(";", 1)[0].strip()
        if first_pair.startswith(prefix):
            value = first_pair[len(prefix):]
            if value:
                return value
    return None


def _status_of(response):
    status = getattr(response, "status", None)
    if status is None:
        getcode = getattr(response, "getcode", None)
        if callable(getcode):
            status = getcode()
    try:
        return int(status)
    except (TypeError, ValueError):
        return None


def _read_text(response, url):
    """Decoded body of a response; closes it. A read failure is UNREACHABLE."""
    try:
        raw = response.read()
    except _TIMEOUT_ERRORS:
        raise _error("UNREACHABLE", "DG did not answer {} in time".format(url))
    except _IO_ERRORS as exc:
        raise _error("UNREACHABLE", "reading the DG answer from {} failed ({})".format(url, _text(exc)))
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
    # HTTPResponse.read() is a byte stream. IronPython 2 exposes both CLR
    # strings and Python unicode as ``str`` / ``unicode`` in isinstance checks,
    # so type-based branching would mistake UTF-8 bytes for decoded text and
    # turn Cyrillic JSON into mojibake. Decode the response boundary first.
    try:
        return raw.decode("utf-8", "replace")
    except (AttributeError, TypeError, UnicodeError):
        return _text(raw)


def _parse_json(text):
    """Parsed JSON of ``text``, or None when it is blank or not JSON."""
    if not _text(text).strip():
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _send(method, url, payload=None, headers=None, timeout=DEFAULT_TIMEOUT_SECONDS, opener=None):
    """One JSON request -> :class:`_Response`; network problems raise UNREACHABLE."""
    request_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        CSRF_HEADER: CSRF_VALUE,
    }
    for name, value in (headers or {}).items():
        request_headers[name] = value
    data = None
    if payload is not None:
        try:
            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            raise _error("UNREACHABLE", "the DG request body cannot be encoded as JSON")
    try:
        request = _build_request(url, data, request_headers, method)
    except (TypeError, ValueError) as exc:
        raise _error("UNREACHABLE", "cannot build the DG request ({})".format(_text(exc)))
    open_request = opener if opener is not None else _default_open
    try:
        response = open_request(request, timeout)
    except _url_error.HTTPError as exc:  # error status, or a refused redirect
        try:
            text = _read_text(exc, url)
        except DgClientError:
            text = ""
        return _Response(exc.code, text, _response_headers(exc))
    except _url_error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), _TIMEOUT_ERRORS):
            raise _error("UNREACHABLE", "DG did not answer {} in {:g} s".format(url, _seconds(timeout)))
        raise _error("UNREACHABLE", "cannot reach the DG data service at {} ({})".format(
            url, _text(getattr(exc, "reason", exc))))
    except _TIMEOUT_ERRORS:
        raise _error("UNREACHABLE", "DG did not answer {} in {:g} s".format(url, _seconds(timeout)))
    except _IO_ERRORS as exc:
        raise _error("UNREACHABLE", "cannot reach the DG data service at {} ({})".format(url, _text(exc)))
    status = _status_of(response)
    text = _read_text(response, url)
    if status is None:
        raise _error("UNREACHABLE", "the DG answer from {} carried no HTTP status".format(url))
    return _Response(status, text, _response_headers(response))


def _build_request(url, data, headers, method):
    """Create a request with the requested verb on Python 2 and 3.

    Python 2's ``urllib2.Request`` has no ``method=`` keyword. Its
    ``get_method`` hook is the supported compatibility seam and preserves the
    DELETE call used for connector-session sign-out.
    """
    try:
        return _url_request.Request(url, data=data, headers=headers, method=method)
    except TypeError:
        request = _url_request.Request(url, data=data, headers=headers)
        if method != "POST" or data is None:
            request.get_method = lambda: method
        return request


def _seconds(timeout):
    try:
        return float(timeout)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


def _server_detail(body):
    """``(code, message)`` of a DG error body ``{code, error, hint}``."""
    if not isinstance(body, dict):
        return "", ""
    code = _text(body.get("code")).strip()
    hint = _text(body.get("hint")).strip()
    error = _text(body.get("error")).strip()
    return code, (hint or error)


def _raise_for_status(status, body, what, secrets=()):
    """Raise the mapped :class:`DgClientError` of a non-2xx answer."""
    code, detail = _server_detail(body)
    parts = [part for part in (code, detail) if part]
    message = "; ".join(parts) if parts else "{} failed (HTTP {})".format(what, status)
    raise _error(_STATUS_CODES.get(status, "HTTP_ERROR"), message, status, secrets,
                 server_code=code or None)


def _succeeded(status):
    return isinstance(status, int) and 200 <= status < 300


def _json_object(response, what, secrets=()):
    """Decoded JSON object of a 2xx :class:`_Response`; UNREACHABLE when malformed."""
    body = _parse_json(response.text)
    if not isinstance(body, dict):
        raise _error("UNREACHABLE", "{} did not answer with a JSON object".format(what), response.status, secrets)
    return body


# --- sign-in and sign-out -----------------------------------------------------

def sign_in(base_url, username, password, project, connector_id="revit", opener=None):
    """Sign in to DG as the connector -> ``{"token", "project", "expiresAt"}``.

    The password goes only into the ``POST /auth/login`` body; the returned
    ``dgk_`` token is the only secret that leaves this function. Any ``neo4j``
    block of the mint response is dropped unread (it may hold a database
    password). The best-effort logout always runs once a session cookie was
    captured, also when minting the connector session fails.
    """
    url = _checked_base_url(base_url)
    user = _text(username).strip()
    if not user or password is None or _text(password) == "":
        raise _error("REJECTED", "DG sign-in needs a user name and a password")
    secrets = [password]

    login = _send("POST", url + "/auth/login",
                  payload={"username": user, "password": _text(password)},
                  timeout=DEFAULT_TIMEOUT_SECONDS, opener=opener)
    if not _succeeded(login.status):
        _raise_for_status(login.status, _parse_json(login.text), "DG sign-in", secrets)
    cookie = _session_cookie(login)
    if cookie is None:
        raise _error("UNREACHABLE", "DG sign-in returned no {} cookie".format(SESSION_COOKIE_NAME),
                     login.status, secrets)
    secrets = [password, cookie]

    cookie_header = {"Cookie": "{}={}".format(SESSION_COOKIE_NAME, cookie)}
    try:
        minted = _send("POST", url + "/auth/connector-session",
                       payload={
                           "project": _text(project).strip() or None,
                           "connector_id": _text(connector_id).strip() or "revit",
                       },
                       headers=cookie_header, timeout=DEFAULT_TIMEOUT_SECONDS, opener=opener)
        if not _succeeded(minted.status):
            _raise_for_status(minted.status, _parse_json(minted.text), "DG connector session", secrets)
        return _signed_in_result(_json_object(minted, "DG connector session", secrets), secrets)
    finally:
        # The connector session does not depend on the account session: end it
        # without letting a failure mask the real outcome.
        try:
            _send("POST", url + "/auth/logout", payload={}, headers=cookie_header,
                  timeout=DEFAULT_TIMEOUT_SECONDS, opener=opener)
        except Exception:  # best effort: nothing may mask the sign-in outcome
            pass


def _signed_in_result(body, secrets):
    """``{token, project, expiresAt}`` of a mint response; only these three keys."""
    token = body.get("token")
    if not isinstance(token, _TEXT_TYPES) or not token.strip().startswith(TOKEN_PREFIX):
        raise _error("UNREACHABLE",
                     "DG connector session returned no {} token".format(TOKEN_PREFIX), 200, secrets)
    project = body.get("project")
    expires_at = body.get("expiresAt")
    # The "neo4j" block of the response is deliberately not read: it may hold a
    # database password, and this connector never talks to Neo4j directly.
    return {
        "token": token.strip(),
        "project": project if isinstance(project, _TEXT_TYPES) else None,
        "expiresAt": expires_at if isinstance(expires_at, _TEXT_TYPES) else None,
    }


def sign_out(base_url, token, opener=None):
    """Delete the connector session -> True on 204. Never raises."""
    try:
        url = _checked_base_url(base_url)
    except DgClientError:
        return False
    session_token = _text(token).strip()
    if not session_token:
        return False
    try:
        response = _send("DELETE", url + "/auth/connector-session",
                         headers={"Authorization": "Bearer " + session_token},
                         timeout=DEFAULT_TIMEOUT_SECONDS, opener=opener)
        return response.status == 204
    except Exception:  # sign-out is best effort by contract: never raises
        return False


# --- mapping session routes ---------------------------------------------------

def _session_token(token):
    session_token = _text(token).strip()
    if not session_token:
        raise _error("REJECTED", "not signed in to DG (no connector token)")
    return session_token


def _quote(text, safe=""):
    """Percent-encode URL text as UTF-8 on both urllib implementations."""
    value = _text(text)
    if isinstance(value, _UNICODE_TYPE):
        value = value.encode("utf-8")
    return _url_quote(value, safe=safe)


def _session_id(session_id):
    text = _text(session_id).strip()
    if not text:
        raise _error("UNREACHABLE", "a mapping session id is required")
    return _quote(text, safe="")


def _authorized(method, url, token, payload, what, opener=None):
    """One mapping session request with the Bearer token -> JSON object."""
    response = _send(method, url, payload=payload,
                     headers={"Authorization": "Bearer " + token},
                     timeout=SESSION_TIMEOUT_SECONDS, opener=opener)
    if not _succeeded(response.status):
        _raise_for_status(response.status, _parse_json(response.text), what, [token])
    return _json_object(response, what, [token])


def create_session(base_url, token, body, opener=None):
    """``POST /mapping/sessions`` -> the created MappingSession dict."""
    url = _checked_base_url(base_url)
    session_token = _session_token(token)
    return _authorized("POST", url + "/mapping/sessions", session_token,
                       body if isinstance(body, dict) else {}, "creating the DG mapping session", opener)


def get_session(base_url, token, project, session_id, opener=None):
    """``GET /mapping/sessions/{id}?project=...`` -> the MappingSession dict."""
    url = _checked_base_url(base_url)
    session_token = _session_token(token)
    target = "{}/mapping/sessions/{}?project={}".format(
        url, _session_id(session_id), _quote(_text(project), safe=""))
    return _authorized("GET", target, session_token, None,
                       "reading the DG mapping session", opener)


def acknowledge_batch(base_url, token, project, session_id, batch_id, delivery, opener=None):
    """Report a completed CAD transaction, never select or commit mappings."""
    url = _checked_base_url(base_url)
    session_token = _session_token(token)
    target = "{}/mapping/sessions/{}/apply".format(url, _session_id(session_id))
    return _authorized("POST", target, session_token,
                       {"project": _text(project), "batchId": batch_id, "delivery": delivery},
                       "acknowledging the DG mapping batch", opener)


def apply_session(base_url, token, project, session_id, opener=None):
    """``POST /mapping/sessions/{id}/apply`` -> the MappingApplyResult dict."""
    url = _checked_base_url(base_url)
    session_token = _session_token(token)
    target = "{}/mapping/sessions/{}/apply".format(url, _session_id(session_id))
    return _authorized("POST", target, session_token, {"project": _text(project)},
                       "applying the DG mapping session", opener)


# --- rule-check jobs (F-01, 2026-10-29) ----------------------------------------
# The server never calls the PC: the connector pulls the rule checks DG queues for this sign-in and answers them.

#: A check answer carries a mesh per box and can take a while to upload on a slow link.
JOB_TIMEOUT_SECONDS = 120.0


def _job_id(job_id):
    text = _text(job_id).strip()
    if not text:
        raise _error("UNREACHABLE", "a job id is required")
    return _quote(text, safe="")


def next_job(base_url, token, project, opener=None):
    """``GET /connector/jobs/next?project=...`` -> ``{"job": {...} | None}``."""
    url = _checked_base_url(base_url)
    session_token = _session_token(token)
    target = "{}/connector/jobs/next?project={}".format(url, _quote(_text(project), safe=""))
    return _authorized("GET", target, session_token, None, "reading the DG check jobs", opener)


def _job_call(target, token, body, what, opener):
    response = _send("POST", target, payload=body, headers={"Authorization": "Bearer " + token},
                     timeout=JOB_TIMEOUT_SECONDS, opener=opener)
    if not _succeeded(response.status):
        _raise_for_status(response.status, _parse_json(response.text), what, [token])
    return _json_object(response, what, [token])


def post_job_result(base_url, token, project, job_id, ok, result=None, error=None, opener=None):
    """``POST /connector/jobs/{id}/result`` with the outcome of a job."""
    url = _checked_base_url(base_url)
    session_token = _session_token(token)
    body = {"project": _text(project), "ok": bool(ok), "result": result,
            "error": None if error is None else _text(error)}
    return _job_call("{}/connector/jobs/{}/result".format(url, _job_id(job_id)), session_token, body,
                     "answering the DG check job", opener)


def post_job_context(base_url, token, project, job_id, elements, done, opener=None):
    """``POST /connector/jobs/{id}/context`` with one chunk of context meshes."""
    url = _checked_base_url(base_url)
    session_token = _session_token(token)
    body = {"project": _text(project), "elements": list(elements or []), "done": bool(done)}
    return _job_call("{}/connector/jobs/{}/context".format(url, _job_id(job_id)), session_token, body,
                     "sending the DG check context", opener)
