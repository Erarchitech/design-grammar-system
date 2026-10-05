"""Offline relay-probe contracts against a local fake relay; not acceptance evidence."""
import importlib.util
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'relay_probe.py'
TOKEN = 'dgd_SECRET_TOKEN_VALUE'
ROUTE = '/degram/v1/chat/completions'


def load():
    spec = importlib.util.spec_from_file_location('relay_probe', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def chunk(**delta):
    return 'data: ' + json.dumps({'id': 'resp-1', 'model': 'served-x', 'choices': [{'delta': delta}]}) + '\n\n'


class FakeRelay(BaseHTTPRequestHandler):
    mode = 'ok'
    seen = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        FakeRelay.seen.append({'path': self.path, 'auth': self.headers.get('Authorization'), 'body': body})
        history_has_tool = any(m.get('role') == 'tool' for m in body['messages'])
        if FakeRelay.mode == 'history-fails' and history_has_tool:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'detail': {'code': 'PROVIDER_ERROR', 'error': 'bad', 'hint': 'x'}}).encode())
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        pieces = [chunk(content='a'), chunk(content='b'), chunk(content='c'), 'data: [DONE]\n\n']
        try:
            for piece in pieces:
                self.wfile.write(piece.encode())
                self.wfile.flush()
        except OSError:
            pass


class RelayProbeTests(unittest.TestCase):
    def setUp(self):
        FakeRelay.mode = 'ok'
        FakeRelay.seen = []
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), FakeRelay)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'
        os.environ['DEGRAM_PROBE_TOKEN'] = TOKEN
        self.addCleanup(self.server.shutdown)
        self.addCleanup(os.environ.pop, 'DEGRAM_PROBE_TOKEN', None)

    def test_four_cases_report_shape_and_never_the_token(self):
        probe = load()
        report = probe.run_probe(self.base, 'DEGRAM_PROBE_TOKEN', route=ROUTE)
        self.assertEqual([c['case'] for c in report['cases']],
                         ['stream', 'stream-with-tool', 'tool-history-followup', 'cancel-after-first-chunk'])
        for case in report['cases']:
            self.assertEqual(case['outcome'], 'COMPLETED' if case['case'] != 'cancel-after-first-chunk' else 'CANCELLED')
            for key in ('httpStatus', 'firstByteMs', 'chunks', 'servedModel', 'responseId'):
                self.assertIn(key, case)
        stream = report['cases'][0]
        self.assertEqual(stream['servedModel'], 'served-x')
        self.assertEqual(stream['responseId'], 'resp-1')
        self.assertGreaterEqual(stream['chunks'], 3)
        self.assertEqual(report['cases'][3]['chunks'], 1)
        self.assertNotIn(TOKEN, json.dumps(report))

    def test_requests_carry_bearer_tools_and_tool_history(self):
        probe = load()
        probe.run_probe(self.base, 'DEGRAM_PROBE_TOKEN', route=ROUTE)
        self.assertTrue(all(s['auth'] == f'Bearer {TOKEN}' for s in FakeRelay.seen))
        self.assertTrue(all(s['path'] == ROUTE for s in FakeRelay.seen))
        self.assertIn('tools', FakeRelay.seen[1]['body'])
        followup = FakeRelay.seen[2]['body']['messages']
        self.assertEqual([m['role'] for m in followup][-2:], ['assistant', 'tool'])
        self.assertTrue(followup[-2].get('tool_calls'))
        self.assertTrue(all(s['body'].get('stream') is True for s in FakeRelay.seen))

    def test_provider_error_is_recorded_as_a_finding_without_fallback(self):
        probe = load()
        FakeRelay.mode = 'history-fails'
        report = probe.run_probe(self.base, 'DEGRAM_PROBE_TOKEN', route=ROUTE)
        followup = report['cases'][2]
        self.assertEqual(followup['outcome'], 'PROVIDER_ERROR')
        self.assertEqual(followup['httpStatus'], 502)
        self.assertIsNone(followup['servedModel'])
        self.assertEqual(len(FakeRelay.seen), 4, 'no retry, no fallback request')

    def test_missing_token_variable_is_refused_before_any_request(self):
        probe = load()
        del os.environ['DEGRAM_PROBE_TOKEN']
        with self.assertRaises(SystemExit):
            probe.run_probe(self.base, 'DEGRAM_PROBE_TOKEN', route=ROUTE)
        self.assertEqual(FakeRelay.seen, [])

    def test_unreachable_relay_is_unknown_not_a_pass(self):
        probe = load()
        report = probe.run_probe('http://127.0.0.1:9', 'DEGRAM_PROBE_TOKEN', route=ROUTE, timeout=2)
        self.assertTrue(all(c['outcome'] == 'UNREACHABLE' for c in report['cases']))
        self.assertNotIn(TOKEN, json.dumps(report))


if __name__ == '__main__':
    unittest.main()
