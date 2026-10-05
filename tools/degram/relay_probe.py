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
"""
import argparse
import http.client
import json
import os
import sys
import time
from urllib.parse import urlsplit

ROUTE = '/degram/v1/chat/completions'
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


def run_probe(base, token_env, route=ROUTE, timeout=120):
    token = os.environ.get(token_env, '')
    if not token:
        raise SystemExit(f'Environment variable {token_env} is empty: mint a delegated token in the signed-in DeGram session.')
    parts = urlsplit(base)
    scheme = parts.scheme or 'http'
    host = parts.hostname or 'localhost'
    port = parts.port or (443 if scheme == 'https' else 80)
    cases = [_run_case(host, port, scheme, route, token, name, payload, cancel, timeout)
             for name, payload, cancel in _cases()]
    return {'probe': 'degram-relay-capability', 'route': route, 'base': base, 'cases': cases}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base', default='http://localhost:8000')
    parser.add_argument('--route', default=ROUTE)
    parser.add_argument('--token-env', default='DEGRAM_PROBE_TOKEN')
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args(argv)
    report = run_probe(args.base, args.token_env, route=args.route, timeout=args.timeout)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
