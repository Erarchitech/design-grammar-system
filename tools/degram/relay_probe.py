"""Live probe of the DeGram relay capability matrix (Phase 1301, plan 16).

Four cases against POST <base>/degram/v1/chat/completions with a delegated
token read from an environment variable: a plain stream, a stream with one tool
definition, a follow-up turn carrying assistant tool_calls plus a tool message,
and a cancel after the first chunk. Each case records the outcome, first-byte
latency, streamed chunk count, the served model and the response id. Unknown
stays unknown (servedModel null); there is no retry and no fallback model. The
token is never printed or stored in the report.

    DEGRAM_PROBE_TOKEN=dgd_... python tools/degram/relay_probe.py \
        --base http://localhost:8000

Plan 17 (D-25): with DEGRAM_PROBE_PAIRING set to a DeGram pairing token from
the Connectors tab and --project given, the probe first trades it at
POST <base>/auth/degram/exchange for the delegated token it then uses. The
pairing wins over DEGRAM_PROBE_TOKEN; neither token reaches the report.

    DEGRAM_PROBE_PAIRING=dgp_... python tools/degram/relay_probe.py \
        --base http://localhost:8000 --project v12-hexagonal-facade-01
"""
import argparse
import http.client
import json
import os
import re
import sys
import time
from urllib.parse import urlsplit

ROUTE = '/degram/v1/chat/completions'
EXCHANGE_ROUTE = '/auth/degram/exchange'
PAIRING_ENV = 'DEGRAM_PROBE_PAIRING'
# A pasted value is trimmed, then must have the token shape; neither the value nor a part of it is ever echoed.
PAIRING_SHAPE = re.compile(r'^dgp_[A-Za-z0-9_-]{32,200}$')
DELEGATED_SHAPE = re.compile(r'^dgd_[A-Za-z0-9_-]{8,200}$')
TOOL = {
    'type': 'function',
    'function': {
        'name': 'echo_number',
        'description': 'Return the number it was given.',
        'parameters': {
            'type': 'object',
            'properties': {'n': {'type': 'integer'}},
            'required': ['n'],
        },
    },
}
TOOL_CALL = {
    'id': 'call_probe_1',
    'type': 'function',
    'function': {'name': 'echo_number', 'arguments': '{"n": 7}'},
}


def _cases():
    ask = {'role': 'user', 'content': 'Call echo_number with n=7.'}
    return [
        ('stream', {'messages': [{'role': 'user', 'content': 'Reply with one short word.'}]}, False),
        ('stream-with-tool', {'messages': [ask], 'tools': [TOOL], 'tool_choice': 'auto'}, False),
        ('tool-history-followup', {
            'messages': [
                ask,
                {'role': 'assistant', 'content': None, 'tool_calls': [TOOL_CALL]},
                {'role': 'tool', 'tool_call_id': 'call_probe_1', 'content': '7'},
            ],
            'tools': [TOOL],
        }, False),
        ('cancel-after-first-chunk', {
            'messages': [{'role': 'user', 'content': 'Count from 1 to 200, one number per line.'}],
        }, True),
    ]


def _error_code(raw):
    try:
        body = json.loads(raw)
    except ValueError:
        return None
    detail = body.get('detail', body) if isinstance(body, dict) else None
    return detail.get('code') if isinstance(detail, dict) else None


def _run_case(host, port, scheme, route, token, name, payload, cancel, timeout):
    case = {'case': name, 'outcome': 'UNREACHABLE', 'httpStatus': None, 'firstByteMs': None,
            'chunks': 0, 'servedModel': None, 'responseId': None, 'finishReason': None,
            'sawToolCalls': False}
    factory = http.client.HTTPSConnection if scheme == 'https' else http.client.HTTPConnection
    conn = factory(host, port, timeout=timeout)
    body = json.dumps({**payload, 'stream': True}).encode()
    started = time.monotonic()
    try:
        conn.request('POST', route, body=body, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        })
        response = conn.getresponse()
        case['httpStatus'] = response.status
        if response.status != 200:
            raw = response.read(65536).decode('utf-8', 'replace')
            case['outcome'] = _error_code(raw) or f'HTTP_{response.status}'
            return case
        case['outcome'] = 'COMPLETED'
        pending_event = None
        while True:
            line = response.readline()
            if not line:
                break
            if case['firstByteMs'] is None:
                case['firstByteMs'] = round((time.monotonic() - started) * 1000)
            text = line.decode('utf-8', 'replace').strip()
            if text.startswith('event:'):
                pending_event = text[6:].strip()
                continue
            if not text.startswith('data:'):
                continue
            data = text[5:].strip()
            if data == '[DONE]':
                break
            try:
                parsed = json.loads(data)
            except ValueError:
                continue
            if pending_event == 'degram-error':
                case['outcome'] = parsed.get('code') or 'PROVIDER_ERROR'
                pending_event = None
                continue
            case['chunks'] += 1
            case['servedModel'] = parsed.get('model') or case['servedModel']
            case['responseId'] = parsed.get('id') or case['responseId']
            for choice in parsed.get('choices') or []:
                if (choice.get('delta') or {}).get('tool_calls'):
                    case['sawToolCalls'] = True
                if choice.get('finish_reason'):
                    case['finishReason'] = choice['finish_reason']
            if cancel:
                case['outcome'] = 'CANCELLED'
                break
    except (OSError, http.client.HTTPException):
        if case['httpStatus'] is None:
            case['outcome'] = 'UNREACHABLE'
        elif case['outcome'] == 'COMPLETED':
            case['outcome'] = 'STREAM_BROKEN'
    finally:
        conn.close()
    return case


def _exchange(host, port, scheme, route, pairing, project, timeout):
    """Trade the pairing token for a delegated one. Returns the 201 body or
    raises SystemExit naming the refusal code (never the token)."""
    factory = http.client.HTTPSConnection if scheme == 'https' else http.client.HTTPConnection
    conn = factory(host, port, timeout=timeout)
    try:
        conn.request('POST', route, body=json.dumps({'project': project}).encode(), headers={
            'Authorization': f'Bearer {pairing}',
            'Content-Type': 'application/json',
        })
        response = conn.getresponse()
        raw = response.read(65536).decode('utf-8', 'replace')
    except (OSError, http.client.HTTPException) as exc:
        raise SystemExit(f'Pairing exchange unreachable: {type(exc).__name__}') from None
    except ValueError:
        # http.client puts the rejected header value in its message: never let it reach the output.
        raise SystemExit('Pairing exchange not sent: the pairing token is not a valid header value') from None
    finally:
        conn.close()
    if response.status != 201:
        code = _error_code(raw) or f'HTTP_{response.status}'
        raise SystemExit(f'Pairing exchange refused: {code}')
    body = json.loads(raw)
    if not str(body.get('token', '')).startswith('dgd_'):
        raise SystemExit('Pairing exchange answered without a delegated token')
    return body


def run_probe(base, token_env, route=ROUTE, timeout=120, project=None,
              pairing_env=PAIRING_ENV, exchange_route=EXCHANGE_ROUTE):
    pairing = os.environ.get(pairing_env, '').strip()
    token = os.environ.get(token_env, '').strip()
    if pairing and not PAIRING_SHAPE.match(pairing):
        raise SystemExit(f'{pairing_env} does not look like a DeGram pairing token (dgp_ + 32-200 url-safe characters). '
                         'Copy it again from the Connectors tab.')
    if not pairing and token and not DELEGATED_SHAPE.match(token):
        raise SystemExit(f'{token_env} does not look like a delegated token (dgd_ + url-safe characters).')
    if pairing and not project:
        raise SystemExit(f'{pairing_env} is set: pass --project to exchange the pairing for a delegated token.')
    if not pairing and not token:
        raise SystemExit(f'Environment variables {pairing_env} and {token_env} are empty: create a DeGram pairing '
                         'on the Connectors tab, or mint a delegated token in the signed-in DeGram session.')
    parts = urlsplit(base)
    scheme = parts.scheme or 'http'
    host = parts.hostname or 'localhost'
    port = parts.port or (443 if scheme == 'https' else 80)
    report = {'probe': 'degram-relay-capability', 'route': route, 'base': base,
              'tokenSource': 'delegated', 'project': project, 'company': None}
    if pairing:
        exchanged = _exchange(host, port, scheme, exchange_route, pairing, project, timeout)
        token = exchanged['token']
        report.update(tokenSource='pairing', project=exchanged.get('project'),
                      company=exchanged.get('company'))
    report['cases'] = [_run_case(host, port, scheme, route, token, name, payload, cancel, timeout)
                       for name, payload, cancel in _cases()]
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base', default='http://localhost:8000')
    parser.add_argument('--route', default=ROUTE)
    parser.add_argument('--token-env', default='DEGRAM_PROBE_TOKEN')
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--project', default=None,
                        help=f'project to exchange the {PAIRING_ENV} pairing token for')
    parser.add_argument('--pairing-env', default=PAIRING_ENV)
    parser.add_argument('--exchange-route', default=EXCHANGE_ROUTE)
    args = parser.parse_args(argv)
    report = run_probe(args.base, args.token_env, route=args.route, timeout=args.timeout,
                       project=args.project, pairing_env=args.pairing_env,
                       exchange_route=args.exchange_route)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
