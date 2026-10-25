"""Offline synthetic HTTP wire tests. No upstream server/service is started."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest

# Child bootstrap uses only local socketpairs, never a listener or connect().
DEADLINE_BOOTSTRAP = r'''
import importlib.util, socket, sys, threading, time
spec = importlib.util.spec_from_file_location('deadline_app', sys.argv[1])
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
mode = sys.argv[2]
client, peer = socket.socketpair()
real_connection = app.http.client.HTTPConnection
class Connection(real_connection):
    def connect(self):
        self.sock = client
        self.sock.settimeout(self.timeout)
        if mode == 'connect':
            self.sock.recv(1)

    def send(self, data):
        if mode == 'send':
            self.connect()
            self.sock.recv(1)
        else:
            super().send(data)
app.http.client.HTTPConnection = Connection
stop = threading.Event()
def feed():
    try:
        if mode in ('connect', 'send'):
            stop.wait()
            return
        if mode == 'chunked-success':
            peer.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\nX-Done: yes\r\n\r\n')
            return
        if mode == 'headers':
            peer.sendall(b'HTTP/1.1 200 OK\r\nX-Slow: ')
            chunk = b'x'
        elif mode == 'body':
            peer.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 65536\r\n\r\n')
            chunk = b'x'
        elif mode == 'trailers':
            peer.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\n')
            chunk = b'X-Slow: x\r\n'
        else:
            peer.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}')
            return
        while not stop.wait(0.02):
            peer.sendall(chunk)
    except OSError:
        pass
thread = threading.Thread(target=feed)
thread.start()
try:
    if len(sys.argv) > 3:
        app._http_worker()
    else:
        real_popen = app.subprocess.Popen if hasattr(app, 'subprocess') else None
        children = []
        def launch(argv, **kwargs):
            assert 'synthetic-token' not in str(argv)
            child = real_popen([sys.executable, '-B', '-c', BOOTSTRAP, sys.argv[1], mode, 'worker'], **kwargs)
            children.append(child)
            return child
        # Bootstrap text arrives on stdin; no credentials in command arguments.
        BOOTSTRAP = sys.stdin.read()
        if real_popen:
            app.subprocess.Popen = launch
        app.HTTP_DEADLINE_SECONDS = 0.4
        started = time.monotonic()
        try:
            result = app.Client().request('/graphql', {'query': 'synthetic'}, 'synthetic-token')
            assert mode in ('success', 'chunked-success'), 'deadline did not reject slow response'
            assert result == (200, None, b'{}')
        except app.Rejected as error:
            assert mode not in ('success', 'chunked-success'), 'ordinary response rejected'
            assert str(error) == 'APPLICATION_HTTP_REJECTED'
        assert time.monotonic() - started < 2, 'deadline exceeded test bound'
        assert len(children) == 1, 'request must use one bounded child'
        assert children[0].poll() is not None, 'HTTP child leaked'
        assert thread.is_alive() or mode in ('success', 'chunked-success')
        print('deadline and reaping verified')
finally:
    stop.set()
    client.close()
    peer.close()
    thread.join(1)
    assert not thread.is_alive()
'''

SOCKET_FIXTURE = r'''
import socket, threading
mode = MODE_VALUE
ack_path = Path(ACK_PATH)
base_connection = http.client.HTTPConnection
class SocketConnection(base_connection):
    def connect(self):
        assert (self.host, self.port) == ('speckle-server', 3000)
        client, peer = socket.socketpair()
        self.sock = client
        self.sock.settimeout(10)
        def feed():
            if mode == 'send':
                ack_path.write_text(mode)
                threading.Event().wait()
            # HTTPConnection sends headers and body separately. Drain the fixed
            # fixture request before replying/closing, including fragmented input.
            request = b''
            while b'\r\n\r\n' not in request:
                part = peer.recv(65536)
                assert part, 'incomplete fixture request headers'
                request += part
                assert len(request) <= 131072, 'oversize fixture request'
            headers, body = request.split(b'\r\n\r\n', 1)
            lengths = [line.split(b':', 1)[1] for line in headers.split(b'\r\n')
                       if line.lower().startswith(b'content-length:')]
            assert len(lengths) <= 1
            length = int(lengths[0]) if lengths else 0
            assert 0 <= length <= MAX_REQUEST
            while len(body) < length:
                part = peer.recv(length - len(body))
                assert part, 'incomplete fixture request body'
                body += part
            if mode == 'blocked-recv-seam':
                ack_path.write_text(mode)
                threading.Event().wait()
            elif mode == 'headers':
                peer.sendall(b'HTTP/1.1 200 OK\r\nX-Slow: ')
                chunk = b'x'
            elif mode == 'body':
                peer.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 65536\r\n\r\nx')
                chunk = b'x'
            elif mode == 'trailers':
                peer.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\n')
                chunk = b'X-Slow: x\r\n'
            else:
                status, extra, body = b'200 OK', b'', b'{}'
                if mode == 'contracts':
                    line = request.split(b'\r\n', 1)[0]
                    if b'/auth/local/register?' in line:
                        assert line.startswith(b'POST ')
                        status = b'302 Found'
                        extra = b'Location: http://speckle-ingress:8080/?access_code=' + b'a'*42 + b'&register=true\r\n'
                    elif b'/auth/token' in line:
                        assert line.startswith(b'POST ')
                        body = b'{"token":"synthetic-token"}'
                    else:
                        assert line == b'GET /readiness HTTP/1.1'
                        body = b'{"details":{"redis":true,"postgres":{"main":{"percentageFreeConnections":"90"}}}}'
                ack_path.write_text(mode)
                if mode == 'chunked-success':
                    peer.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\nX-Done: yes\r\n\r\n')
                else:
                    peer.sendall(b'HTTP/1.1 ' + status + b'\r\n' + extra + b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
                peer.close()
                return
            while True:
                time.sleep(0.02)
                peer.sendall(chunk)
        threading.Thread(target=feed, daemon=True).start()
    def send(self, data):
        if mode == 'send':
            if not self.sock:
                self.connect()
            # Actual sendall blocks on an undrained socketpair, not recv.
            self.sock.sendall(b'x' * (8 * 1024 * 1024))
        else:
            super().send(data)
base_response = http.client.HTTPResponse
class PhaseResponse(base_response):
    def begin(self):
        if mode == 'headers':
            ack_path.write_text(mode)
        return super().begin()
    def read(self, *args):
        if mode == 'body':
            ack_path.write_text(mode)
        return super().read(*args)
    def _read_and_discard_trailer(self):
        if mode == 'trailers':
            ack_path.write_text(mode)
        return super()._read_and_discard_trailer()
SocketConnection.response_class = PhaseResponse
http.client.HTTPConnection = SocketConnection
if mode == 'failure':
    def fail(*args, **kwargs):
        ack_path.write_text(mode)
        raise OSError('synthetic-private')
    Client._request_direct = fail
'''

from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'recovery-test/multistore_qualified_app.py'


def load_app(direct=True):
    spec = importlib.util.spec_from_file_location('qualified_app_under_test', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Existing contract fixtures exercise the same worker-side HTTP path in
    # process. The socketpair regression separately exercises public request(),
    # the real child protocol, expiration, and reaping end to end.
    if direct:
        module.Client.request = module.Client._request_direct
    return module


class Response:
    def __init__(self, status, body=b'', headers=None):
        self.status = status
        self.body = body
        self.headers = headers or {}

    def read(self, amount):
        result, self.body = self.body[:amount], self.body[amount:]
        return result

    def getheader(self, name, default=None):
        return self.headers.get(name.lower(), default)


def encoded(value):
    return json.dumps(value, separators=(',', ':')).encode('utf-8')


class Wire:
    """A no-socket HTTPConnection seam; rejects unexpected wire operations."""
    def __init__(self, test, replies):
        self.test = test
        self.replies = list(replies)
        self.requests = []
        self.closed = 0

    def connection(self, host, port, timeout):
        self.test.assertEqual((host, port), ('speckle-server', 3000))
        self.test.assertGreater(timeout, 0)
        self.test.assertLessEqual(timeout, 10)
        wire = self

        class Connection:
            def request(self, method, path, body=None, headers=None):
                wire.requests.append((method, path, json.loads(body) if body else None, headers or {}))

            def getresponse(self):
                wire.test.assertTrue(wire.replies, 'unexpected additional HTTP request')
                return wire.replies.pop(0)

            def close(self):
                wire.closed += 1

        return Connection()


class QualifiedAppTests(unittest.TestCase):
    def test_path_and_token_lengths_are_rejected_before_regex(self):
        app = load_app(direct=False)
        for path, token in (('/auth/local/register?challenge=' + 'a' * 100000, None),
                            ('/graphql', 'x' * 100000)):
            with patch.object(app.re, 'fullmatch', side_effect=AssertionError('unbounded regex')) as match:
                with self.assertRaises(app.Rejected):
                    app.Client().request(path, {}, token)
                match.assert_not_called()

    def test_cli_does_not_exit_and_drop_retained_ownership(self):
        app = load_app(direct=False)
        owner = {'child': object()}
        def fail():
            app._HTTP_TERMINAL = True
            app._HTTP_OWNERS.append(owner)
            raise app.Rejected('fixed')
        attempts = []
        def cleanup():
            attempts.append(1)
            if len(attempts) == 1:
                raise app.Rejected('fixed')
            app._HTTP_OWNERS.clear()
        out = io.StringIO()
        with patch.object(app, 'readiness', fail), patch.object(app, 'cleanup_http_owners', cleanup), patch.object(app.time, 'sleep'), patch('sys.stdout', out):
            self.assertEqual(app.main(['readiness']), 1)
        self.assertEqual(len(attempts), 2)
        self.assertFalse(json.loads(out.getvalue())['verified'])
        self.assertEqual(app._HTTP_OWNERS, [])

    def test_cli_retry_sleep_interrupt_keeps_real_child_and_files_owned_until_reaped(self):
        app = load_app(direct=False)
        out = io.StringIO()
        children, files, sleeps = [], [], []
        real_popen = subprocess.Popen

        def launch(argv, **kwargs):
            child = real_popen([sys.executable, '-I', '-B', '-c',
                                'import time; time.sleep(60)'], **kwargs)
            children.append(child)
            files.extend((kwargs['stdin'], kwargs['stdout']))
            real_kill, real_wait = child.kill, child.wait
            attempts = {'kill': 0, 'wait': 0}

            def kill():
                attempts['kill'] += 1
                if attempts['kill'] <= 3:
                    raise OSError('synthetic cleanup refusal')
                return real_kill()

            def wait(timeout):
                attempts['wait'] += 1
                if attempts['wait'] <= 4:
                    raise subprocess.TimeoutExpired('synthetic', timeout)
                return real_wait(timeout=timeout)

            child.kill, child.wait = kill, wait
            return child

        def interrupt_sleep(delay):
            self.assertEqual(delay, 0.1)
            self.assertEqual(out.getvalue(), '', 'report emitted before cleanup')
            self.assertEqual(len(app._HTTP_OWNERS), 1)
            self.assertIs(app._HTTP_OWNERS[0]['child'], children[0])
            self.assertIsNone(children[0].poll(), 'child must still be live at interruption')
            self.assertTrue(all(not stream.closed for stream in files))
            self.assertTrue(app._HTTP_TERMINAL)
            with self.assertRaises(app.Rejected):
                app.report(True)
            sleeps.append(delay)
            raise KeyboardInterrupt('synthetic retry pause interruption')

        try:
            with patch.object(app.subprocess, 'Popen', launch), patch.object(app.time, 'sleep', interrupt_sleep), patch('sys.stdout', out):
                self.assertEqual(app.main(['readiness']), 1)
            self.assertEqual(sleeps, [0.1, 0.1])
            self.assertEqual(len(children), 1, 'cleanup must not retry the HTTP request')
            self.assertIsNotNone(children[0].returncode)
            self.assertTrue(all(stream.closed for stream in files))
            self.assertEqual(app._HTTP_OWNERS, [])
            self.assertTrue(app._HTTP_TERMINAL)
            self.assertFalse(json.loads(out.getvalue())['verified'])
        finally:
            # Test hygiene even when the pre-fix CLI escapes on KeyboardInterrupt.
            for child in children:
                if child.poll() is None:
                    subprocess.Popen.kill(child)
                subprocess.Popen.wait(child, timeout=3)
            for stream in files:
                stream.close()

    def test_exact_isolated_bootstrap_acknowledged_transport_and_public_contracts(self):
        import threading
        for mode in ('headers', 'body', 'trailers', 'blocked-recv-seam', 'send',
                     'success', 'chunked-success', 'failure', 'contracts'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                app = load_app(direct=False)
                fixture = Path(td) / 'fixture.py'
                ack = Path(td) / 'phase'
                fixture.write_text(MODULE.read_text(encoding='utf-8') + '\n' +
                                   SOCKET_FIXTURE.replace('ACK_PATH', repr(str(ack))).replace('MODE_VALUE', repr(mode)), encoding='utf-8')
                children = []
                real_popen = subprocess.Popen
                def launch(argv, **kwargs):
                    self.assertEqual(argv[:5], [sys.executable, '-I', '-B', '-c',
                        'import runpy,sys; runpy.run_path(sys.argv[1])["_http_worker"]()'])
                    self.assertNotIn('synthetic-token', str(argv))
                    self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
                    # Only fixed module-file substitution; production endpoint,
                    # isolated bootstrap and stdin protocol are unchanged.
                    argv = [*argv[:-1], str(fixture)]
                    child = real_popen(argv, **kwargs)
                    children.append(child)
                    return child
                with patch.object(app.subprocess, 'Popen', launch), patch.object(app, 'HTTP_DEADLINE_SECONDS', 1.0):
                    start = time.monotonic()
                    if mode == 'contracts':
                        self.assertEqual(app.Client().register(), 'synthetic-token')
                        self.assertTrue(app.readiness()['verified'])
                    elif mode in ('success', 'chunked-success'):
                        self.assertEqual(app.Client().request('/graphql', {}, 'synthetic-token'), (200, None, b'{}'))
                    else:
                        with self.assertRaises(app.Rejected) as error:
                            app.Client().request('/graphql', {}, 'synthetic-token')
                        self.assertEqual(str(error.exception), 'APPLICATION_HTTP_REJECTED')
                        self.assertNotIn('synthetic-private', str(error.exception))
                    elapsed = time.monotonic() - start
                    self.assertLess(elapsed, 4)
                    if mode in ('headers', 'body', 'trailers', 'blocked-recv-seam', 'send'):
                        self.assertGreaterEqual(elapsed, 0.95, 'rejected before transport deadline')
                self.assertTrue(ack.exists(), 'worker did not reach intended phase')
                self.assertEqual(ack.read_text(), mode)
                self.assertTrue(all(c.returncode is not None for c in children))
                self.assertTrue(all(not hasattr(c, '_stdout_thread') for c in children))
                self.assertEqual(app._HTTP_OWNERS, [])

    def test_isolated_success_fixture_accepts_delayed_request_body(self):
        app = load_app(direct=False)
        with tempfile.TemporaryDirectory() as td:
            fixture = Path(td) / 'fixture.py'
            ack = Path(td) / 'phase'
            delayed_body = r'''
original_send = SocketConnection.send
def delayed_send(self, data):
    if data == b'{}':
        time.sleep(0.1)
    return original_send(self, data)
SocketConnection.send = delayed_send
'''
            fixture.write_text(MODULE.read_text(encoding='utf-8') + '\n' +
                               SOCKET_FIXTURE.replace('ACK_PATH', repr(str(ack))).replace(
                                   'MODE_VALUE', repr('success')) + delayed_body, encoding='utf-8')
            children = []
            real_popen = subprocess.Popen
            def launch(argv, **kwargs):
                child = real_popen([*argv[:-1], str(fixture)], **kwargs)
                children.append(child)
                return child
            with patch.object(app.subprocess, 'Popen', launch), patch.object(app, 'HTTP_DEADLINE_SECONDS', 1.0):
                try:
                    self.assertEqual(app.Client().request('/graphql', {}, 'synthetic-token'),
                                     (200, None, b'{}'))
                finally:
                    self.assertEqual(len(children), 1)
                    self.assertIsNotNone(children[0].returncode)
                    self.assertEqual(app._HTTP_OWNERS, [])
            self.assertEqual(ack.read_text(), 'success')

    def test_bounded_input_exact_limits_and_private_file_success(self):
        app = load_app(direct=False)
        for value in ('x' * 8192, [None] * 4095, -(1 << 63), (1 << 63) - 1,
                      {'x': '\U0001f600' * 100}, [0.1, -1e300, True, None]):
            app._bounded_input(value)
        nested = None
        for _ in range(16):
            nested = [nested]
        app._bounded_input(nested)
        with self.assertRaises(app.Rejected):
            app._bounded_input([nested])
        # Exact byte boundary with eight bounded strings and delimiters.
        values = ['x' * 8192] * 7 + ['x' * (65536 - 7 * 8192 - 25)]
        self.assertEqual(len(app.encode(values)), 65536)
        app._bounded_input(values)
        values[-1] += 'x'
        with self.assertRaises(app.Rejected):
            app._bounded_input(values)

    def test_lifecycle_retains_terminal_ownership_without_communicate_or_poll(self):
        for fault in ('kill', 'wait', 'wait-error', 'close', 'poll', 'communicate', 'none'):
            with self.subTest(fault=fault):
                app = load_app(direct=False)
                class Child:
                    returncode = None
                    def __init__(self):
                        self.waits = 0
                        self.kills = 0
                    def communicate(self, *a, **kw):
                        raise AssertionError('communicate reader threads forbidden')
                    def poll(self):
                        raise AssertionError('poll forbidden')
                    def wait(self, timeout):
                        self.waits += 1
                        if self.waits == 1 or fault == 'wait':
                            raise subprocess.TimeoutExpired('synthetic', timeout)
                        if fault == 'wait-error':
                            raise OSError('synthetic-secret')
                        self.returncode = -9
                        return -9
                    def kill(self):
                        self.kills += 1
                        if fault == 'kill':
                            raise OSError('synthetic-secret')
                child = Child()
                files = []
                real_temp = tempfile.TemporaryFile
                class File:
                    def __init__(self):
                        self.inner = real_temp()
                        files.append(self)
                    def __getattr__(self, name):
                        return getattr(self.inner, name)
                    def close(self):
                        if fault == 'close':
                            raise OSError('synthetic-secret')
                        self.inner.close()
                try:
                    with patch.object(app.subprocess, 'Popen', return_value=child) as spawn, patch.object(tempfile, 'TemporaryFile', File):
                        with self.assertRaises(app.Rejected) as error:
                            app.Client().request('/graphql', {}, 'synthetic-token')
                        self.assertNotIn('synthetic-secret', str(error.exception))
                        self.assertEqual(child.waits, 2)
                        self.assertEqual(child.kills, 1)
                        terminal = fault in ('kill', 'wait', 'wait-error', 'close')
                        self.assertEqual(bool(getattr(app, '_HTTP_TERMINAL', False)), terminal)
                        if terminal:
                            self.assertEqual(len(app._HTTP_OWNERS), 1)
                            self.assertIs(app._HTTP_OWNERS[0]['child'], child)
                            with self.assertRaises(app.Rejected):
                                app.Client().request('/graphql', {}, 'synthetic-token')
                            with self.assertRaises(app.Rejected):
                                app.report(True)
                            self.assertEqual(spawn.call_count, 1)
                            if fault in ('kill', 'wait'):
                                self.assertTrue(all(not f.inner.closed for f in files))
                            # Explicit synchronous cleanup retains terminal state,
                            # never revives a partially failed orchestrator.
                            fault = 'none'
                            app.cleanup_http_owners()
                            self.assertTrue(app._HTTP_TERMINAL)
                        self.assertEqual(app._HTTP_OWNERS, [])
                        self.assertTrue(all(f.inner.closed for f in files))
                finally:
                    for f in files:
                        f.inner.close()

    def test_public_request_rejects_unbounded_or_callback_input_before_encoding(self):
        app = load_app(direct=False)
        class Hostile(dict):
            def items(self):
                self.fail('callback must not run')
        cyclic = []
        cyclic.append(cyclic)
        deep = None
        for _ in range(18):
            deep = [deep]
        invalid = [Hostile(), (1,), {1: 'x'}, {'x': object()}, iter([1]),
                   cyclic, deep, 'x' * 8193, ['x'] * 4097, 1 << 65,
                   float('nan'), float('inf'), {'x': ['\u0000' * 8192] * 2}]
        for value in invalid:
            with self.subTest(kind=type(value).__name__):
                with patch.object(app, 'encode', side_effect=AssertionError('serialization reached')) as dump, patch.object(app.subprocess, 'Popen') as spawn:
                    with self.assertRaises(app.Rejected):
                        app.Client().request('/graphql', value, 'synthetic-token')
                    dump.assert_not_called()
                    spawn.assert_not_called()

    def test_whole_request_deadline_interrupts_blocking_socket_reads_and_reaps(self):
        for mode in ('headers', 'body', 'trailers', 'connect', 'send', 'success', 'chunked-success'):
            with self.subTest(mode=mode):
                try:
                    result = subprocess.run(
                        [sys.executable, '-B', '-c', DEADLINE_BOOTSTRAP, str(MODULE), mode],
                        input=DEADLINE_BOOTSTRAP, text=True, capture_output=True, timeout=3)
                except subprocess.TimeoutExpired:
                    self.fail('whole-request deadline did not interrupt blocking ' + mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('deadline and reaping verified', result.stdout)

    def test_register_uses_rest_oauth_redirect_exchange_not_graphql_registration(self):
        self.assertTrue(MODULE.is_file(), 'concrete pinned application helper is absent')
        app = load_app()
        wire = Wire(self, [
            Response(302, headers={'location': 'http://speckle-ingress:8080/?access_code=' + 'a' * 42 + '&register=true'}),
            Response(200, encoded({'token': 'synthetic-api-token', 'refreshToken': 'synthetic-refresh-token'})),
        ])
        with patch.object(app.http.client, 'HTTPConnection', wire.connection):
            token = app.Client().register()
        self.assertEqual(token, 'synthetic-api-token')
        self.assertEqual(len(wire.requests), 2)
        first, second = wire.requests
        self.assertEqual(first[0], 'POST')
        self.assertRegex(first[1], r'^/auth/local/register\?challenge=[0-9a-f]{64}$')
        self.assertEqual(first[2]['email'], 'dg-recovery-fixture@example.invalid')
        self.assertEqual(first[2]['name'], 'DG synthetic recovery fixture')
        self.assertGreaterEqual(len(first[2]['password']), 32)
        self.assertEqual(second[:2], ('POST', '/auth/token'))
        self.assertEqual(second[2], {
            'appId': 'spklwebapp', 'appSecret': 'spklwebapp',
            'accessCode': 'a' * 42, 'challenge': first[1].split('=')[1],
        })
        self.assertNotIn('Authorization', first[3])
        self.assertNotIn('Authorization', second[3])
        self.assertEqual(wire.closed, 2)
        self.assertEqual(wire.replies, [])


    def test_seed_creates_project_model_object_version_and_private_exact_state(self):
        app = load_app()
        self.assertTrue(hasattr(app, 'seed'), 'API fixture seeding is missing')
        object_id = app.fixture_object()['id']
        wire = Wire(self, [
            Response(302, headers={'location': 'http://speckle-ingress:8080/?access_code=' + 'a' * 42 + '&register=true'}),
            Response(200, encoded({'token': 'synthetic-api-token', 'refreshToken': 'synthetic-refresh-token'})),
            Response(200, encoded({'data': {'activeUser': {'id': 'user123456', 'email': app.EMAIL, 'name': app.USER_NAME}}})),
            Response(200, encoded({'data': {'projectMutations': {'create': {'id': 'proj123456'}}}})),
            Response(200, encoded({'data': {'modelMutations': {'create': {'id': 'model12345'}}}})),
            Response(200, encoded({'data': {'objectCreate': [object_id]}})),
            Response(200, encoded({'data': {'versionMutations': {'create': {'id': 'vers123456'}}}})),
        ])
        with tempfile.TemporaryDirectory() as td:
            exchange = Path(td)
            (exchange / 'exports/api').mkdir(parents=True)
            with patch.object(app.http.client, 'HTTPConnection', wire.connection):
                result = app.seed(exchange)
            self.assertTrue(result['verified'])
            for key in ('nativeRecoveryProven', 'nativeExecutionProven', 'authenticatedProvenanceProven', 'ifcImportProven', 'producerBarrier'):
                self.assertIs(result[key], False)
            state_path = exchange / 'exports/api/speckle-fixture/state.json'
            state = json.loads(state_path.read_bytes())
            self.assertEqual(state, {
                'schema': 1, 'sourceCommit': app.SOURCE_COMMIT, 'fixture': 'dg-speckle-api-fixture-v1',
                'token': 'synthetic-api-token', 'userId': 'user123456', 'projectId': 'proj123456',
                'modelId': 'model12345', 'objectId': object_id, 'versionId': 'vers123456',
            })
            self.assertNotIn('synthetic-api-token', json.dumps(result))
            self.assertNotIn('password', state)
            self.assertNotIn('refreshToken', state)
            self.assertEqual(len(wire.requests), 7)
            self.assertEqual(wire.replies, [])
            graph = wire.requests[2:]
            self.assertEqual([r[2]['operationName'] for r in graph], [
                'RecoveryUser', 'RecoveryCreateProject', 'RecoveryCreateModel',
                'RecoveryCreateObject', 'RecoveryCreateVersion',
            ])
            self.assertTrue(all(r[0:2] == ('POST', '/graphql') for r in graph))
            self.assertTrue(all(r[3]['Authorization'] == 'Bearer synthetic-api-token' for r in graph))
            self.assertEqual(graph[1][2]['variables']['input'], {
                'name': 'DG synthetic recovery fixture', 'description': 'Disposable synthetic API fixture; no owner data',
                'visibility': 'PRIVATE',
            })
            self.assertEqual(graph[2][2]['variables']['input']['projectId'], 'proj123456')
            self.assertEqual(graph[3][2]['variables'], {
                'input': {'streamId': 'proj123456', 'objects': [app.fixture_object()]},
            })
            self.assertEqual(graph[4][2]['variables']['input'], {
                'projectId': 'proj123456', 'modelId': 'model12345', 'objectId': object_id,
                'message': 'DG exact synthetic fixture v1', 'sourceApplication': 'dg-offline-prepared-fixture',
                'totalChildrenCount': 1,
            })
            if os.name != 'nt':
                self.assertEqual(state_path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(state_path.parent.stat().st_mode & 0o777, 0o700)


    def test_verify_reads_exact_identity_model_version_and_object_not_self_asserted_state(self):
        app = load_app()
        self.assertTrue(hasattr(app, 'verify'), 'API fixture readback verification is missing')
        state = {
            'schema': 1, 'sourceCommit': app.SOURCE_COMMIT, 'fixture': app.FIXTURE,
            'token': 'synthetic-api-token', 'userId': 'user123456', 'projectId': 'proj123456',
            'modelId': 'model12345', 'objectId': app.fixture_object()['id'], 'versionId': 'vers123456',
        }
        observed = {
            'activeUser': {'id': state['userId'], 'email': app.EMAIL, 'name': app.USER_NAME},
            'project': {'id': state['projectId'], **app.PROJECT_INPUT,
                'model': {'id': state['modelId'], 'name': app.MODEL_NAME, 'projectId': state['projectId'],
                    'versions': {'totalCount': 1, 'items': [{
                        'id': state['versionId'], 'referencedObject': state['objectId'],
                        'message': app.VERSION_MESSAGE, 'sourceApplication': app.SOURCE_APPLICATION,
                        # Pinned createCommitByBranchId uses object count || 1;
                        # zero-child object still produces version count one.
                        'totalChildrenCount': 1, 'model': {'id': state['modelId']},
                        'authorUser': {'id': state['userId']},
                    }]}},
                'object': {'id': state['objectId'], 'data': app.fixture_object(), 'totalChildrenCount': 0},
            },
        }
        with tempfile.TemporaryDirectory() as td:
            exchange = Path(td)
            state_path = exchange / app.STATE_RELATIVE
            state_path.parent.mkdir(parents=True)
            state_path.write_bytes(encoded(state))
            os.chmod(state_path, 0o600)
            wire = Wire(self, [Response(200, encoded({'data': observed}))])
            with patch.object(app.http.client, 'HTTPConnection', wire.connection):
                result = app.verify(exchange)
            self.assertTrue(result['verified'])
            self.assertIs(result['nativeRecoveryProven'], False)
            self.assertIs(result['ifcImportProven'], False)
            self.assertEqual(len(wire.requests), 1)
            self.assertEqual(wire.requests[0][2]['operationName'], 'RecoveryVerify')
            self.assertEqual(wire.requests[0][2]['variables'], {
                'projectId': state['projectId'], 'modelId': state['modelId'], 'objectId': state['objectId'],
            })
            self.assertEqual(state_path.read_bytes(), encoded(state))
            # Actual response content must be checked, including exact scalar types.
            changes = [
                ('user', lambda x: x['activeUser'].__setitem__('id', 'wrong')),
                ('visibility', lambda x: x['project'].__setitem__('visibility', 'PUBLIC')),
                ('model', lambda x: x['project']['model'].__setitem__('id', 'wrong')),
                ('version', lambda x: x['project']['model']['versions']['items'][0].__setitem__('referencedObject', 'f' * 32)),
                ('count', lambda x: x['project']['model']['versions'].__setitem__('totalCount', 2)),
                ('bool-as-int', lambda x: x['project']['object']['data'].__setitem__('revision', True)),
                ('extra-object-field', lambda x: x['project']['object']['data'].__setitem__('owner-data', 'not-fixture')),
            ]
            for label, mutate in changes:
                with self.subTest(label=label):
                    bad = json.loads(encoded(observed))
                    mutate(bad)
                    wire = Wire(self, [Response(200, encoded({'data': bad}))])
                    with patch.object(app.http.client, 'HTTPConnection', wire.connection):
                        with self.assertRaises(app.Rejected):
                            app.verify(exchange)
                    self.assertEqual(len(wire.requests), 1)


    def test_block_producers_fails_closed_without_http_or_caller_boolean_escape(self):
        app = load_app()
        self.assertTrue(hasattr(app, 'block_producers'), 'honest producer barrier mode is missing')
        with patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no HTTP allowed')):
            result = app.block_producers()
        self.assertIs(result['verified'], False)
        self.assertIs(result['producerBarrier'], False)
        self.assertEqual(result['error'], 'UNSUPPORTED_SERVER_PRODUCER_BARRIER')
        self.assertIs(result['nativeRecoveryProven'], False)
        with self.assertRaises(TypeError):
            app.block_producers(producers_blocked=True)
        self.assertIn('source patch', app.PRODUCER_BARRIER_LIMITATION)
        self.assertIn('consumers', app.PRODUCER_BARRIER_LIMITATION)
        self.assertIn('build approval', app.PRODUCER_BARRIER_LIMITATION)
        self.assertIn('generateUploadUrl', app.IFC_LIMITATION)
        self.assertIn('finishFileImport', app.IFC_LIMITATION)
        self.assertIn('not implemented', app.IFC_LIMITATION)


    def test_readiness_is_one_fixed_bounded_probe_not_migration_or_native_acceptance(self):
        app = load_app()
        self.assertTrue(hasattr(app, 'readiness'), 'bounded readiness probe is missing')
        # app.ts verbatim:true returns the readiness handler's details, not the
        # /liveness route's separately injected status:'ok' field.
        wire = Wire(self, [Response(200, encoded({'details': {'redis': True, 'postgres': {'main': {'percentageFreeConnections': '90'}}}}))])
        with patch.object(app.http.client, 'HTTPConnection', wire.connection):
            result = app.readiness()
        self.assertTrue(result['verified'])
        self.assertIs(result['migrationsProven'], False)
        self.assertIs(result['nativeRecoveryProven'], False)
        self.assertEqual(wire.requests[0][0:3], ('GET', '/readiness', None))
        self.assertNotIn('Authorization', wire.requests[0][3])
        self.assertEqual(wire.closed, 1)
        for response in (Response(503, b'synthetic-sensitive-body'), Response(200, encoded({'status': 'error'})),
                         Response(302, headers={'location': 'http://owner.invalid/'})):
            wire = Wire(self, [response])
            with patch.object(app.http.client, 'HTTPConnection', wire.connection):
                with self.assertRaises(app.Rejected):
                    app.readiness()
            self.assertEqual(len(wire.requests), 1)

    def test_cli_modes_are_fixed_sanitized_no_endpoints_credentials_or_barrier_override(self):
        app = load_app()
        self.assertTrue(hasattr(app, 'main'), 'fixed orchestrator CLI is missing')
        for args, mode, expected in [(['seed'], 'seed', 0), (['verify'], 'verify', 0),
                                     (['readiness'], 'readiness', 0)]:
            with self.subTest(mode=mode):
                out, err = io.StringIO(), io.StringIO()
                with patch.object(app, mode, return_value=app.report(True)) as action, patch('sys.stdout', out), patch('sys.stderr', err):
                    status = app.main(args)
                self.assertEqual(status, expected)
                self.assertTrue(json.loads(out.getvalue())['verified'])
                self.assertEqual(err.getvalue(), '')
                action.assert_called_once_with(Path('/exchange')) if mode != 'readiness' else action.assert_called_once_with()
        for args, code in [(['block-producers'], 'UNSUPPORTED_SERVER_PRODUCER_BARRIER'),
                            (['seed', '--token', 'synthetic-secret'], 'APPLICATION_CONTRACT_REJECTED'),
                            (['verify', '--endpoint', 'http://owner.invalid'], 'APPLICATION_CONTRACT_REJECTED'),
                            (['--help'], 'APPLICATION_CONTRACT_REJECTED'),
                            ([], 'APPLICATION_CONTRACT_REJECTED')]:
            with self.subTest(args=args):
                out, err = io.StringIO(), io.StringIO()
                with patch('sys.stdout', out), patch('sys.stderr', err), patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no HTTP')):
                    self.assertEqual(app.main(args), 1)
                value = json.loads(out.getvalue())
                self.assertFalse(value['verified'])
                self.assertEqual(value['error'], code)
                self.assertNotIn('synthetic-secret', out.getvalue() + err.getvalue())
                self.assertNotIn('owner.invalid', out.getvalue() + err.getvalue())
                self.assertEqual(err.getvalue(), '')
        for exc in (RuntimeError('synthetic-secret'), KeyboardInterrupt('synthetic-secret')):
            out, err = io.StringIO(), io.StringIO()
            with patch.object(app, 'seed', side_effect=exc), patch('sys.stdout', out), patch('sys.stderr', err):
                self.assertEqual(app.main(['seed']), 1)
            self.assertNotIn('synthetic-secret', out.getvalue() + err.getvalue())
            self.assertEqual(err.getvalue(), '')


    def test_graphql_rejects_duplicate_json_nonfinite_and_unexpected_envelopes(self):
        app = load_app()
        bad = [
            b'{"data":{"activeUser":null},"data":{"activeUser":{"id":"spoof"}}}',
            b'{"data":{"number":NaN}}',
            b'{"data":{"number":Infinity}}',
            encoded({'data': {'id': 'ok'}, 'errors': []}),
            encoded({'data': {'id': 'ok'}, 'errors': [{'message': 'synthetic-sensitive-body'}]}),
            encoded({'data': None}),
            encoded({'data': [], 'extra': 'synthetic-sensitive-body'}),
            b'<html>synthetic-sensitive-body</html>',
            b'x' * (app.MAX_RESPONSE + 1),
        ]
        for body in bad:
            with self.subTest(body=body[:30]):
                wire = Wire(self, [Response(200, body)])
                with patch.object(app.http.client, 'HTTPConnection', wire.connection):
                    with self.assertRaises(app.Rejected) as error:
                        app.Client().graphql('RecoveryUser', {}, 'synthetic-token')
                self.assertNotIn('synthetic-sensitive-body', str(error.exception))
                self.assertEqual(len(wire.requests), 1)
                self.assertEqual(wire.closed, 1)
        # Unknown query/endpoint must fail before connection creation.
        with patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no HTTP')):
            for path in ('http://owner.invalid/path', '//owner.invalid', '/auth/logout', '/graphql?token=not-allowed'):
                with self.subTest(path=path), self.assertRaises(app.Rejected):
                    app.Client().request(path, {})

    def test_auth_rejects_foreign_redirect_duplicate_code_and_invalid_tokens_without_following(self):
        app = load_app()
        locations = [
            'http://owner.invalid/?access_code=' + 'a' * 42 + '&register=true',
            'https://speckle-ingress:8080/?access_code=' + 'a' * 42 + '&register=true',
            'http://speckle-ingress:8080/?access_code=' + 'a' * 42 + '&access_code=' + 'b' * 42 + '&register=true',
            'http://speckle-ingress:8080/?access_code=' + 'a' * 42 + '&register=true#fragment',
        ]
        for location in locations:
            with self.subTest(location=location[:45]):
                wire = Wire(self, [Response(302, headers={'location': location})])
                with patch.object(app.http.client, 'HTTPConnection', wire.connection), self.assertRaises(app.Rejected):
                    app.Client().register()
                self.assertEqual(len(wire.requests), 1)
        for token in ('', '\r\nsynthetic-secret', 'x' * 513, None):
            wire = Wire(self, [
                Response(302, headers={'location': 'http://speckle-ingress:8080/?access_code=' + 'a' * 42 + '&register=true'}),
                Response(200, encoded({'token': token})),
            ])
            with patch.object(app.http.client, 'HTTPConnection', wire.connection), self.assertRaises(app.Rejected):
                app.Client().register()
            self.assertEqual(len(wire.requests), 2)


    def test_private_state_rejects_duplicates_wrong_profile_hardlinks_and_name_collision_before_http(self):
        app = load_app()
        state = {
            'schema': 1, 'sourceCommit': app.SOURCE_COMMIT, 'fixture': app.FIXTURE,
            'token': 'synthetic-api-token', 'userId': 'user123456', 'projectId': 'proj123456',
            'modelId': 'model12345', 'objectId': app.fixture_object()['id'], 'versionId': 'vers123456',
        }
        with tempfile.TemporaryDirectory() as td:
            exchange = Path(td)
            path = exchange / app.STATE_RELATIVE
            path.parent.mkdir(parents=True)
            raw = encoded(state)
            bad = [raw[:-1] + b',"schema":1}', raw.replace(b'"schema":1', b'"schema":true'),
                   raw.replace(app.SOURCE_COMMIT.encode(), b'f' * 40),
                   raw.replace(b'"fixture":"dg-speckle-api-fixture-v1"', b'"fixture":"owner"'),
                   raw.replace(b'"modelId":"model12345"', b'"modelId":"../owner"'),
                   b'x' * (app.MAX_RESPONSE + 1)]
            for content in bad:
                with self.subTest(content=content[:30]):
                    path.write_bytes(content)
                    os.chmod(path, 0o600)
                    with patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no HTTP')):
                        with self.assertRaises(app.Rejected):
                            app.verify(exchange)
            path.write_bytes(raw)
            linked = exchange / 'hardlink'
            os.link(path, linked)
            with patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no HTTP')):
                with self.assertRaises(app.Rejected):
                    app.verify(exchange)
                with self.assertRaises((app.Rejected, FileExistsError)):
                    app.seed(exchange)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(linked.read_bytes(), raw)
            # Existing partial attempt is intentionally preserved, not erased/retried.
            path.unlink()
            with patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no HTTP')):
                with self.assertRaises((app.Rejected, FileExistsError)):
                    app.seed(exchange)
            self.assertTrue(path.parent.is_dir())


    def test_preparation_embeds_exact_source_references_without_runtime_attestation(self):
        app = load_app()
        self.assertTrue(hasattr(app, 'SOURCE_REFERENCES'), 'source-hashed preparation contract is absent')
        refs = app.SOURCE_REFERENCES
        expected = {
            'packages/server/modules/auth/strategies/local.ts': ('93-164', 'c9205f3fa8af9492b359dc46cb67fbe25d5a5e82ee10508b8622ad7bdc212a19'),
            'packages/server/modules/auth/middleware.ts': ('85-108', '2fc79f8bceb4d3281ab85c34c6e2b021ce3e4623bfe2832830efa1450deaf360'),
            'packages/server/modules/auth/rest/index.ts': ('183-207', '6cc531aaa97c539ab89633ee4cdadbf6f66e5452d08dcdc82415be6c94cbef01'),
            'packages/server/modules/core/services/commit/management.ts': ('84-161', 'c232a88f7224c23d7dc12dc1e00c465fdc5833b2fe4fd045fe44c6c4d750993b'),
            'packages/server/modules/core/graph/resolvers/versions.ts': ('292-354', '1cd9c6a51e387443ab34fa73d884ef6725e539157214a987a82ec2dd21d11181'),
            'packages/server/modules/core/services/taskScheduler.ts': ('59-88', 'd02292b083ac4127c35d474cadf46bff06a3acd3d89db8484a0b349a0dcfee55'),
            'packages/server/assets/core/typedefs/server.graphql': ('92-100', '83502e9cebef68e7280385bf60750b40ad17197a0334141912f031cdcb9dc993'),
            'packages/server/assets/fileuploads/typedefs/fileuploads.graphql': ('43-197', '46e8b455fd7fe09b9da89e45126d042c62aa5e173f9b5701d5d9f2c37c68bd9d'),
        }
        for path, (lines, digest) in expected.items():
            self.assertEqual(refs[path], {'lines': lines, 'sha256': digest})
        self.assertGreaterEqual(len(refs), 18)
        for path, reference in refs.items():
            self.assertTrue(path.startswith('packages/'))
            self.assertNotIn('..', path.split('/'))
            self.assertRegex(reference['sha256'], r'^[0-9a-f]{64}$')
            self.assertRegex(reference['lines'], r'^\d+-\d+$')
        self.assertEqual(app.SOURCE_COMMIT, '51d43b91c4681a75bff8b285da7f443a4599da67')
        self.assertIn('POST /auth/local/register', app.PREPARATION_SCOPE)
        self.assertIn('not a runtime', app.PREPARATION_SCOPE)
        # Type names and nesting come from the pinned schemas, not a stub register mutation.
        for name, signature in {
            'RecoveryCreateProject': 'ProjectCreateInput!', 'RecoveryCreateModel': 'CreateModelInput!',
            'RecoveryCreateObject': 'ObjectCreateInput!', 'RecoveryCreateVersion': 'CreateVersionInput!',
        }.items():
            self.assertIn(signature, app.OPERATIONS[name])
        self.assertFalse(any('register' in query.lower() for query in app.OPERATIONS.values()))


    def test_readiness_rejects_duplicate_status_and_non_json_with_fixed_exception(self):
        app = load_app()
        for body in (b'{"status":"error","status":"ok"}', b'<html>synthetic-private</html>', b'[]'):
            with self.subTest(body=body):
                wire = Wire(self, [Response(200, body)])
                with patch.object(app.http.client, 'HTTPConnection', wire.connection):
                    with self.assertRaises(app.Rejected) as error:
                        app.readiness()
                self.assertNotIn('synthetic-private', str(error.exception))

    def test_verify_closes_over_open_file_identity_not_a_replaceable_path(self):
        app = load_app()
        state = {
            'schema': 1, 'sourceCommit': app.SOURCE_COMMIT, 'fixture': app.FIXTURE,
            'token': 'synthetic-api-token', 'userId': 'user123456', 'projectId': 'proj123456',
            'modelId': 'model12345', 'objectId': app.fixture_object()['id'], 'versionId': 'vers123456',
        }
        with tempfile.TemporaryDirectory() as td:
            exchange = Path(td)
            path = exchange / app.STATE_RELATIVE
            path.parent.mkdir(parents=True)
            path.write_bytes(encoded(state))
            os.chmod(path, 0o600)
            # A path replacement between lstat and open must be rejected before HTTP.
            replacement = exchange / 'replacement'
            replacement.write_bytes(encoded(state))
            original_open = Path.open
            def swap_then_open(p, *args, **kwargs):
                if p == path:
                    os.replace(replacement, path)
                return original_open(p, *args, **kwargs)
            with patch.object(Path, 'open', swap_then_open), patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no HTTP')):
                with self.assertRaises(app.Rejected):
                    app.verify(exchange)


    def test_transport_failure_never_retries_or_leaks_response_and_partial_seed_is_reserved(self):
        app = load_app()
        wire = Wire(self, [
            Response(302, headers={'location': 'http://speckle-ingress:8080/?access_code=' + 'a' * 42 + '&register=true'}),
            Response(200, encoded({'token': 'synthetic-api-token'})),
            Response(200, encoded({'data': {'activeUser': {'id': 'user123456', 'email': app.EMAIL, 'name': app.USER_NAME}}})),
            Response(500, b'synthetic-sensitive-server-body'),
        ])
        with tempfile.TemporaryDirectory() as td:
            exchange = Path(td)
            (exchange / 'exports/api').mkdir(parents=True)
            out, err = io.StringIO(), io.StringIO()
            with patch.object(app.http.client, 'HTTPConnection', wire.connection), patch('sys.stdout', out), patch('sys.stderr', err):
                with self.assertRaises(app.Rejected) as error:
                    app.seed(exchange)
            self.assertEqual(len(wire.requests), 4)
            self.assertEqual(wire.closed, 4)
            self.assertNotIn('synthetic-sensitive-server-body', str(error.exception))
            self.assertEqual(out.getvalue() + err.getvalue(), '')
            self.assertFalse((exchange / app.STATE_RELATIVE).exists())
            self.assertTrue((exchange / app.STATE_RELATIVE).parent.is_dir())
            with patch.object(app.http.client, 'HTTPConnection', side_effect=AssertionError('no retry')):
                with self.assertRaises(FileExistsError):
                    app.seed(exchange)

    def test_prepared_fixture_has_golden_content_and_sha256_not_arbitrary_observed_data(self):
        app = load_app()
        self.assertTrue(hasattr(app, 'FIXTURE_SHA256'), 'exact prepared fixture fingerprint is absent')
        self.assertEqual(app.fixture_object(), {
            'speckle_type': 'Base', 'name': 'DG exact synthetic API fixture',
            'fixture': 'dg-speckle-api-fixture-v1', 'revision': 1, 'units': 'm',
            'parameters': {'height': 7.25, 'synthetic': True}, '__closure': {},
            'id': 'e1e47073e0c498b39310ece57580c46b',
        })
        import hashlib
        self.assertEqual(app.FIXTURE_SHA256, hashlib.sha256(encoded(app.fixture_object())).hexdigest())
        self.assertRegex(app.FIXTURE_SHA256, r'^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
