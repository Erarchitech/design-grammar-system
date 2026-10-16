"""Inside the data-service container only. Fixed sanitized results, no raw bodies."""
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def fetch(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=10) as response:
            return response.status, response.read(2_000_000), response.headers
    except urllib.error.HTTPError as error:
        return error.code, b'', error.headers


def ready():
    code, body, _ = fetch('http://dg-reasoner:8000/health')
    if code != 200 or json.loads(body) != {'status': 'ok', 'neo4j': 'up'}:
        raise RuntimeError('reasoner not ready')
    code, body, _ = fetch('http://127.0.0.1:8000/auth/options')
    if code != 200 or json.loads(body).get('selfRegistration') is not False:
        raise RuntimeError('API not ready')
    code, body, _ = fetch('http://design-grammars/')
    if code != 200 or b'/assets/' not in body:
        raise RuntimeError('UI not ready')


def run():
    ready()
    import sandbox_probe
    sandbox_probe.BASE = 'http://design-grammars/data-service'
    result = sandbox_probe.run()
    code, body, headers = fetch('http://design-grammars/')
    if code != 200 or headers.get('X-Content-Type-Options') != 'nosniff' or headers.get('X-Frame-Options') != 'DENY':
        raise RuntimeError('UI headers invalid')
    assets = re.findall(r'(?:src|href)="(/assets/[^"?#]+\.(?:js|css))"', body.decode('utf-8'))
    if not assets or len(assets) > 20:
        raise RuntimeError('UI assets invalid')
    for path in assets:
        if urlsplit(path).netloc or '..' in path or any(c in path for c in ('\\', '\r', '\n')):
            raise RuntimeError('UI asset path invalid')
        status, value, _ = fetch('http://design-grammars' + path)
        if status != 200 or not value or value.lstrip().lower().startswith(b'<!doctype html'):
            raise RuntimeError('UI asset unavailable')
    for path in ('/neo4j', '/n8n'):
        if fetch('http://design-grammars' + path)[0] != 404:
            raise RuntimeError('proxy tombstone invalid')
    code, body, _ = fetch('http://design-grammars/config.js')
    if code != 200 or b'dataServiceUrl: "/data-service"' not in body or b'speckleBaseUrl: "http://127.0.0.1:9"' not in body:
        raise RuntimeError('runtime config invalid')
    return {'api': result, 'uiAssets': len(assets), 'uiHeaders': True, 'uiProxyTombstones': True,
            'uiRuntimeConfig': True, 'reasonerNeo4jUp': True, 'selfRegistrationDisabled': True}


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['ready']:
            ready()
        elif not sys.argv[1:]:
            print(json.dumps(run(), sort_keys=True))
        else:
            raise ValueError('mode')
    except Exception:
        print('IMAGE_SMOKE_PROBE_FAILED', file=sys.stderr)
        sys.exit(1)
