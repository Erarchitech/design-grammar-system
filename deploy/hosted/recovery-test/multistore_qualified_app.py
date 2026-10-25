"""Pinned Speckle synthetic fixture helper; OFFLINE PREPARATION, not admission.

Source: specklesystems/speckle-server at
51d43b91c4681a75bff8b285da7f443a4599da67. Fixed internal HTTP only. Never pass
credentials/URLs on argv. No upstream application was run during development.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import time
import threading
from urllib.parse import parse_qs, urlsplit

SOURCE_COMMIT = '51d43b91c4681a75bff8b285da7f443a4599da67'
PREPARATION_SCOPE = '''Concrete preparation only: POST /auth/local/register with
session challenge -> fixed frontend 302 access_code (never followed) -> POST
/auth/token using source-defined public spklwebapp identifier -> activeUser ->
private project -> model -> exact Base object -> version. verify reads exact
identity, project, model version count/linkage/content and object data. CLI uses
the fixed /exchange private volume, persisting the fixture
state under exports/api/speckle-fixture/state.json so authenticated archive restore
can carry the token/IDs. No password/refresh token retained; no raw HTTP/log output.
State is trusted private orchestration input, not independent custody or service
ownership proof. A partial attempt reserves its directory; cleanup/retry needs a
fresh disposable stack. This is not a runtime attestation, source authentication,
migration/catalog admission, full API-state recovery, IFC, render, webhook or
notification proof. All native/provenance/recovery flags remain false.'''
# Full-file SHA256 and relevant inclusive lines of the locally retained public
# source at SOURCE_COMMIT. These are PREPARATION references, not image attestation.
SOURCE_REFERENCES = {
    'packages/server/modules/auth/strategies/local.ts': {'lines': '93-164', 'sha256': 'c9205f3fa8af9492b359dc46cb67fbe25d5a5e82ee10508b8622ad7bdc212a19'},
    'packages/server/modules/auth/middleware.ts': {'lines': '85-108', 'sha256': '2fc79f8bceb4d3281ab85c34c6e2b021ce3e4623bfe2832830efa1450deaf360'},
    'packages/server/modules/auth/rest/index.ts': {'lines': '183-207', 'sha256': '6cc531aaa97c539ab89633ee4cdadbf6f66e5452d08dcdc82415be6c94cbef01'},
    'packages/server/modules/auth/defaultApps.ts': {'lines': '15-38', 'sha256': 'c3f6c6ac244d46160c8faa2d5a087458a9a9868f2b337c6d7daaed801af5bcda'},
    'packages/server/assets/core/typedefs/user.graphql': {'lines': '1-18', 'sha256': 'f9795819285cf5c0b94a2d6b0c97c06012861fbc84217fa624499e272618bc96'},
    'packages/server/assets/core/typedefs/projects.graphql': {'lines': '1-202', 'sha256': '622db0171abe4bafce173b40cd8a3d3f7de873d9641db070d49cd7bb4f86c135'},
    'packages/server/assets/core/typedefs/modelsAndVersions.graphql': {'lines': '1-224', 'sha256': '056483e5375c5dd909b3783b16c01aa9c2cfa9b02695f5483c23e9ce26f5fa00'},
    'packages/server/assets/core/typedefs/objects.graphql': {'lines': '8-60', 'sha256': '8312209bd5f58b0a8b4059d180c48b121128d6b6be99d8e98b3d231e65f615a4'},
    'packages/server/modules/core/graph/resolvers/objects.ts': {'lines': '95-134', 'sha256': '681da4c991f4fef29105f7fcce7f4a9bc9f02df6ee17634bfdacba1bd7bf70d6'},
    'packages/server/modules/core/services/objects/management.ts': {'lines': '26-58', 'sha256': 'ba11a01c4156e0e434c9dd6d2867843ffb815bd817846ee6a43ae30172c30490'},
    'packages/server/modules/core/services/commit/management.ts': {'lines': '84-161', 'sha256': 'c232a88f7224c23d7dc12dc1e00c465fdc5833b2fe4fd045fe44c6c4d750993b'},
    'packages/server/modules/core/graph/resolvers/versions.ts': {'lines': '292-354', 'sha256': '1cd9c6a51e387443ab34fa73d884ef6725e539157214a987a82ec2dd21d11181'},
    'packages/server/modules/core/services/taskScheduler.ts': {'lines': '59-88', 'sha256': 'd02292b083ac4127c35d474cadf46bff06a3acd3d89db8484a0b349a0dcfee55'},
    'packages/server/assets/core/typedefs/server.graphql': {'lines': '92-100', 'sha256': '83502e9cebef68e7280385bf60750b40ad17197a0334141912f031cdcb9dc993'},
    'packages/server/modules/fileuploads/index.ts': {'lines': '78-176', 'sha256': '20bfa54e8b16900b0601d37ffbc1779b330efd1c29a2a07a36302ec4b86b26aa'},
    'packages/server/modules/notifications/index.ts': {'lines': '1-49', 'sha256': '200fb2c7f15a02aad394d6ba6b0d313a9e2115ff70a4576aecea82d65d24d464'},
    'packages/server/modules/previews/tasks/tasks.ts': {'lines': '32-102', 'sha256': 'd9564962446fec0ba74d7a6709c9ee8f053a86d54f5dd8f45fd2491579d7ac31'},
    'packages/server/assets/fileuploads/typedefs/fileuploads.graphql': {'lines': '43-197', 'sha256': '46e8b455fd7fe09b9da89e45126d042c62aa5e173f9b5701d5d9f2c37c68bd9d'},
    'packages/server/modules/fileuploads/graph/resolvers/fileUploads.ts': {'lines': '175-314', 'sha256': '44467230dec8123a55d9095dfc5ae1b9a6daf405b0c0fc124c1d03c7443b4337'},
    'packages/ifc-import-service/src/ifc_importer/process_job.py': {'lines': '18-65', 'sha256': '973dde63fb5525364e0e88a37f91204084e64efdee23fae54272abc8079e51cb'},
    'packages/ifc-import-service/src/ifc_importer/job_manager.py': {'lines': '28-212', 'sha256': '510a003e53b729d134badeab08c7a6ba78d85bc76fc909a13768f23ec7180c5f'},
    'packages/server/app.ts': {'lines': '456-475', 'sha256': '4e5e7c72d095d0e3a9a6bf3b4311984a6ac25e0603cbf8f3aac415525aafa431'},
    'packages/server/healthchecks/health.ts': {'lines': '89-136', 'sha256': '1123611e8083a900c95f4cb7a25502a46aabb5e18d4737db58459936ff9f2852'},
}
EMAIL = 'dg-recovery-fixture@example.invalid'
USER_NAME = 'DG synthetic recovery fixture'
MAX_RESPONSE = 65536
STATE_RELATIVE = 'exports/api/speckle-fixture/state.json'
FIXTURE = 'dg-speckle-api-fixture-v1'
FIXTURE_SHA256 = '6f9b3767bfcf965b502c6e626c3363469ab4415acc71e9ca0f60cf4c51504eae'
PROJECT_INPUT = {
    'name': USER_NAME, 'description': 'Disposable synthetic API fixture; no owner data',
    'visibility': 'PRIVATE',
}
MODEL_NAME = 'dg-synthetic-api-fixture'
VERSION_MESSAGE = 'DG exact synthetic fixture v1'
SOURCE_APPLICATION = 'dg-offline-prepared-fixture'
PRODUCER_BARRIER_LIMITATION = '''Unsupported at this pin: taskScheduler.ts:59-88
creates in-process node-cron tasks; ServerInfoUpdateInput (server.graphql:92-100)
has no maintenance/scheduler switch. fileuploads/index.ts:111-117 schedules job
GC even for next-gen IFC. previews/tasks/tasks.ts:32-102 can create tokens and
enqueue retry requests when enabled. Individual module finalizers call stop(),
but shutdown also closes consumers; no reviewed externally callable producer-only
pause/wait primitive was found. Stopping ingress/frontend or returning a Python
boolean cannot stop these tasks. Required: reviewed source patch and build approval
for an authenticated producer-only fence that rejects ingress writes, stops all
scheduled/event producers, waits for in-flight producer callbacks, keeps server
result/notification consumers and IFC/preview/webhook workers alive for bounded
drain, then permits physical stable-empty probes and coordinated writer stop.
Alternative stop/restart ordering needs separately proven no-producer consumer-only
startup. Neither path is implemented or established by this helper.'''
IFC_LIMITATION = '''IFC upload/completion is not implemented by this helper.
fileuploads.graphql:105-197 defines generateUploadUrl -> presigned S3 PUT ->
startFileImport(projectId, modelId, fileId, etag). Model.uploads exposes uploadComplete,
convertedStatus (2=success), convertedVersionId; completion needs a worker-produced
version/object plus matching terminal PG background job, not empty pending lists.
finishFileImport is an internal worker report, NOT a client shortcut to claim
conversion. fileUploads.ts:249-314 updates both file status and queue job; IFC
process_job.py:34-56 downloads and calls open_and_convert_file to publish a version.
A deterministic IFC file, reviewed exact presigned-MinIO URL/path/signature admission,
ETag handling, bounded poll/drain and worker success/physical job linkage tests are
still required. No arbitrary returned URL is followed and no finishFileImport
mutation is fabricated here. API Base fixture success does not prove IFC or queues.'''
# assets/core/typedefs/{user,projects,modelsAndVersions,objects}.graphql.
# The deprecated objectCreate mutation is present at this exact pin; no SDK needed.
OPERATIONS = {
    'RecoveryUser': 'query RecoveryUser { activeUser { id email name } }',
    'RecoveryVerify': '''query RecoveryVerify($projectId: String!, $modelId: String!, $objectId: String!) {
      activeUser { id email name }
      project(id: $projectId) { id name description visibility
        model(id: $modelId) { id name projectId
          versions(limit: 2) { totalCount items { id referencedObject message sourceApplication
            totalChildrenCount model { id } authorUser { id } } } }
        object(id: $objectId) { id data totalChildrenCount }
      } }''',
    'RecoveryCreateProject': '''mutation RecoveryCreateProject($input: ProjectCreateInput!) {
      projectMutations { create(input: $input) { id } } }''',
    'RecoveryCreateModel': '''mutation RecoveryCreateModel($input: CreateModelInput!) {
      modelMutations { create(input: $input) { id } } }''',
    'RecoveryCreateObject': '''mutation RecoveryCreateObject($input: ObjectCreateInput!) {
      objectCreate(objectInput: $input) }''',
    'RecoveryCreateVersion': '''mutation RecoveryCreateVersion($input: CreateVersionInput!) {
      versionMutations { create(input: $input) { id } } }''',
}


class Rejected(Exception):
    """Fixed, non-sensitive failure; remote bodies must never become messages."""


def require(condition):
    if not condition:
        raise Rejected('APPLICATION_CONTRACT_REJECTED')


def encode(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def document(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    def nonfinite(_):
        raise Rejected('APPLICATION_JSON_REJECTED')

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    except Exception:
        raise Rejected('APPLICATION_JSON_REJECTED') from None


HTTP_DEADLINE_SECONDS = 10
HTTP_CLEANUP_SECONDS = 2
MAX_REQUEST = 65536


def _bounded_input(value):
    """Trusted, non-concurrently-mutated builtins only; no arbitrary callbacks.

    Before dumps: <=16 container levels, 4096 nodes (including keys), 8192
    codepoints/string, signed 64-bit integers, finite floats, <=65536 encoded
    bytes (conservative 24-byte float reservation). Reject cycles by depth.
    """
    import math
    nodes = 0
    size = 0

    def visit(item, depth):
        nonlocal nodes, size
        nodes += 1
        require(nodes <= 4096)
        kind = type(item)
        if kind is str:
            require(len(item) <= 8192)
            size += 2
            for char in item:
                code = ord(char)
                size += (2 if char in '\\"\\\\\b\f\n\r\t' else
                         6 if code < 32 or 127 <= code <= 65535 else
                         12 if code > 65535 else 1)
        elif item is None or kind is bool:
            size += 5
        elif kind is int:
            require(-(1 << 63) <= item < (1 << 63))
            size += 21
        elif kind is float:
            require(math.isfinite(item))
            size += 24
        elif kind is list or kind is dict:
            require(depth < 16 and len(item) <= 4096)
            size += 2 + max(0, len(item) - 1)
            require(size <= MAX_REQUEST)
            if kind is dict:
                for key, child in item.items():
                    require(type(key) is str)
                    visit(key, depth + 1)
                    size += 1
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
        else:
            require(False)
        require(size <= MAX_REQUEST)

    visit(value, 0)


def _http_worker():
    # Private stdin protocol, not an additional public CLI mode. No subprocesses
    # are created here, so killing/reaping this child also ends all transport work.
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
        require(len(raw) <= MAX_REQUEST)
        path, payload, token = document(raw)
        status, location, body = Client()._request_direct(path, payload, token)
        require(location is None or len(location) <= MAX_RESPONSE)
        sys.stdout.buffer.write(encode([status, location, body.hex()]))
    except Exception:
        pass  # Empty output is a fixed, secret-safe failure at the parent.


_HTTP_OWNERS = []
_HTTP_TERMINAL = False
_HTTP_LOCK = threading.Lock()
# Deadline covers worker startup/HTTP once Popen returns; not an OS wall-time
# guarantee. Trusted bounded validation/serialization and private file I/O precede
# it. Popen, kill, file close and scheduler latency are not interruptible here.
# Normal outer budget: preprocessing + spawn latency + <=10s transport + <=2s
# wait allowance + OS kill/close latency. Unreaped children retain synchronous
# ownership below; no background reaper or Windows communicate reader exists.


def _cleanup_owner(owner):
    global _HTTP_TERMINAL
    failed = False
    child = owner['child']
    if child is not None and not owner['reaped']:
        try:
            child.kill()
        except BaseException:
            failed = True
        try:
            child.wait(timeout=HTTP_CLEANUP_SECONDS)
            owner['reaped'] = True
        except BaseException:
            failed = True
    # Retain files until termination is established. No reader threads are used.
    if not failed and (owner['reaped'] or child is None):
        for stream in owner['files']:
            try:
                stream.close()
            except BaseException:
                failed = True
    if failed:
        _HTTP_TERMINAL = True
        raise Rejected('APPLICATION_HTTP_OWNERSHIP_RETAINED') from None
    _HTTP_OWNERS.remove(owner)


def cleanup_http_owners():
    """Explicit synchronous operator cleanup; terminal state NEVER resets.

    The embedding orchestrator must keep this module/process alive and call this
    until ownership is empty before exiting. An uninterruptible OS child cannot
    be promised reaped within a bounded return; native supervisor qualification
    (including abrupt interpreter exit) is not implemented by this helper.
    """
    with _HTTP_LOCK:
        for owner in list(_HTTP_OWNERS):
            _cleanup_owner(owner)


class Client:
    def request(self, path, payload=None, token=None):
        # Reject concurrent entry rather than accumulate unbounded waiters/work.
        require(_HTTP_LOCK.acquire(blocking=False))
        owner = None
        try:
            require(not _HTTP_TERMINAL)
            self._validate_request(path, payload, token)
            _bounded_input([path, payload, token])
            raw = encode([path, payload, token])
            require(len(raw) <= MAX_REQUEST)
            owner = {'child': None, 'reaped': False, 'files': []}
            _HTTP_OWNERS.append(owner)
            # Anonymous private stdin/stdout files: no credentials in argv or
            # named exchange paths, no pipe writer/communicate reader threads.
            source = tempfile.TemporaryFile()
            owner['files'].append(source)
            output = tempfile.TemporaryFile()
            owner['files'].append(output)
            source.write(raw)
            source.seek(0)
            child = subprocess.Popen(
                [sys.executable, '-I', '-B', '-c',
                 'import runpy,sys; runpy.run_path(sys.argv[1])["_http_worker"]()',
                 os.path.abspath(__file__)],
                stdin=source, stdout=output, stderr=subprocess.DEVNULL,
                close_fds=True)
            owner['child'] = child
            deadline = time.monotonic() + min(HTTP_DEADLINE_SECONDS, 10)
            child.wait(timeout=max(0, deadline - time.monotonic()))
            owner['reaped'] = True
            require(time.monotonic() < deadline and child.returncode == 0)
            output.seek(0)
            raw_output = output.read(MAX_RESPONSE * 4 + 1)
            require(len(raw_output) <= MAX_RESPONSE * 4)
            status, location, body_hex = document(raw_output)
            body = bytes.fromhex(body_hex)
            require(type(status) is int and 100 <= status <= 599
                    and (location is None or type(location) is str)
                    and len(body) <= MAX_RESPONSE)
            return status, location, body
        except BaseException:
            raise Rejected('APPLICATION_HTTP_REJECTED') from None
        finally:
            try:
                if owner is not None:
                    _cleanup_owner(owner)
            finally:
                _HTTP_LOCK.release()

    @staticmethod
    def _validate_request(path, payload, token):
        require(type(path) is str and len(path) <= 128)
        require(token is None or type(token) is str and len(token) <= 512)
        require(type(path) is str and (
            path in ('/graphql', '/auth/token', '/readiness')
            or re.fullmatch(r'/auth/local/register\?challenge=[0-9a-f]{64}', path)))
        require((path == '/readiness') == (payload is None))
        require((path == '/graphql') == (token is not None))
        if token is not None:
            require(type(token) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,512}', token))

    def _request_direct(self, path, payload=None, token=None):
        self._validate_request(path, payload, token)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Connection': 'close'}
        if token is not None:
            require(type(token) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,512}', token))
            headers['Authorization'] = 'Bearer ' + token
        connection = http.client.HTTPConnection('speckle-server', 3000, timeout=10)
        try:
            connection.request('GET' if payload is None else 'POST', path,
                               body=None if payload is None else encode(payload), headers=headers)
            response = connection.getresponse()
            body = response.read(MAX_RESPONSE + 1)
            require(len(body) <= MAX_RESPONSE)
            return response.status, response.getheader('location'), body
        except Exception:
            raise Rejected('APPLICATION_HTTP_REJECTED') from None
        finally:
            connection.close()

    def register(self):
        # auth/strategies/local.ts:93-164 + auth/middleware.ts:85-108.
        # This is NOT GraphQL registration and the redirect is NOT followed.
        challenge = secrets.token_hex(32)
        status, location, _ = self.request('/auth/local/register?challenge=' + challenge, {
            'email': EMAIL, 'name': USER_NAME, 'company': 'Synthetic recovery only',
            'password': secrets.token_urlsafe(48),
        })
        require(status == 302 and type(location) is str)
        redirect = urlsplit(location)
        require(redirect.scheme == 'http' and redirect.netloc == 'speckle-ingress:8080'
                and redirect.path == '/' and not redirect.fragment)
        query = parse_qs(redirect.query, strict_parsing=True)
        require(set(query) == {'access_code', 'register'} and query['register'] == ['true']
                and len(query['access_code']) == 1)
        access_code = query['access_code'][0]
        require(len(access_code) == 42 and access_code.isascii() and access_code.isalnum())
        # auth/rest/index.ts:183-207 + auth/defaultApps.ts:15-38.
        status, _, body = self.request('/auth/token', {
            'appId': 'spklwebapp', 'appSecret': 'spklwebapp',
            'accessCode': access_code, 'challenge': challenge,
        })
        require(status == 200)
        value = document(body)
        require(type(value) is dict and type(value.get('token')) is str
                and re.fullmatch(r'[A-Za-z0-9_-]{1,512}', value['token']))
        return value['token']

    def graphql(self, operation, variables, token):
        require(operation in OPERATIONS)
        status, _, body = self.request('/graphql', {
            'operationName': operation, 'query': OPERATIONS[operation], 'variables': variables,
        }, token)
        require(status == 200)
        value = document(body)
        require(type(value) is dict and set(value) == {'data'} and type(value['data']) is dict)
        return value['data']


def fixture_object():
    # management.ts:26-58 hashes JSON.stringify(obj) if no id; provide the exact
    # same 32-character digest explicitly, then verify every returned data field.
    value = {'speckle_type': 'Base', 'name': 'DG exact synthetic API fixture',
             'fixture': FIXTURE, 'revision': 1, 'units': 'm',
             'parameters': {'height': 7.25, 'synthetic': True}, '__closure': {}}
    value['id'] = hashlib.md5(encode(value), usedforsecurity=False).hexdigest()
    return value


def report(verified):
    require(not verified or not _HTTP_TERMINAL)
    return {'verified': verified, 'fixture': FIXTURE, 'sourceCommit': SOURCE_COMMIT,
            'nativeRecoveryProven': False, 'nativeExecutionProven': False,
            'authenticatedProvenanceProven': False, 'ifcImportProven': False,
            'producerBarrier': False, 'migrationsProven': False}


def directory(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        info = part.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                and not getattr(info, 'st_file_attributes', 0) & 0x400)
    return path


def identifier(value):
    require(type(value) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', value))
    return value


def seed(exchange):
    # Trusted orchestrator creates a fresh, private exchange and dedicated stores.
    # Claim before *any* API write. A partial run is not retried or silently reused.
    parent = directory(Path(exchange) / 'exports/api')
    target = parent / 'speckle-fixture'
    target.mkdir(mode=0o700)
    client = Client()
    token = client.register()
    user = client.graphql('RecoveryUser', {}, token)['activeUser']
    require(user['email'] == EMAIL and user['name'] == USER_NAME)
    user_id = identifier(user['id'])
    project = identifier(client.graphql('RecoveryCreateProject', {'input': PROJECT_INPUT}, token)
                         ['projectMutations']['create']['id'])
    model = identifier(client.graphql('RecoveryCreateModel', {'input': {
        'projectId': project, 'name': MODEL_NAME, 'description': PROJECT_INPUT['description'],
    }}, token)['modelMutations']['create']['id'])
    obj = fixture_object()
    require(client.graphql('RecoveryCreateObject', {'input': {
        'streamId': project, 'objects': [obj],
    }}, token)['objectCreate'] == [obj['id']])
    version = identifier(client.graphql('RecoveryCreateVersion', {'input': {
        'projectId': project, 'modelId': model, 'objectId': obj['id'],
        'message': VERSION_MESSAGE, 'sourceApplication': SOURCE_APPLICATION, 'totalChildrenCount': 1,
    }}, token)['versionMutations']['create']['id'])
    state = {'schema': 1, 'sourceCommit': SOURCE_COMMIT, 'fixture': FIXTURE,
             'token': token, 'userId': user_id, 'projectId': project, 'modelId': model,
             'objectId': obj['id'], 'versionId': version}
    # Linux container mode bits; Windows inherited DACL is an orchestrator gate,
    # NOT established by chmod. Do not export an unsealed exchange to the host.
    fd = os.open(target / 'state.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encode(state))
    return report(True)


def readiness():
    # app.ts:456-475 + healthchecks/health.ts:89-136. This checks process/store
    # readiness only, not schema, consumers, browser rendering or source identity.
    status, _, body = Client().request('/readiness')
    require(status == 200)
    value = document(body)
    require(type(value) is dict and set(value) == {'details'})
    details = value['details']
    require(type(details) is dict and set(details) == {'redis', 'postgres'}
            and details['redis'] is True and type(details['postgres']) is dict
            and 1 <= len(details['postgres']) <= 8)
    for region in details['postgres'].values():
        require(type(region) is dict and set(region) == {'percentageFreeConnections'})
        percent = region['percentageFreeConnections']
        require(type(percent) is str and re.fullmatch(r'[0-9]{1,3}', percent)
                and 10 <= int(percent) <= 100)
    return report(True)


def main(argv=None):
    try:
        args = sys.argv[1:] if argv is None else argv
        require(type(args) is list and len(args) == 1
                and args[0] in ('seed', 'verify', 'readiness', 'block-producers'))
        if args[0] == 'seed':
            result = seed(Path('/exchange'))
        elif args[0] == 'verify':
            result = verify(Path('/exchange'))
        elif args[0] == 'readiness':
            result = readiness()
        else:
            result = block_producers()
    except (Exception, KeyboardInterrupt):
        result = report(False)
        result['error'] = 'APPLICATION_CONTRACT_REJECTED'
    # Terminal CLI policy sacrifices bounded return rather than discard ownership.
    # This retries ONLY cleanup, never an HTTP request or application write. A
    # permanently uninterruptible child/failed close keeps CLI here indefinitely.
    # Forced interpreter termination still needs an external qualified supervisor.
    while True:
        try:
            if not _HTTP_OWNERS:
                break
            try:
                cleanup_http_owners()
            except BaseException:
                time.sleep(0.1)
        except BaseException:
            # Retry-pause interruptions must not abandon retained ownership.
            # The condition, cleanup and backoff all stay inside this boundary.
            continue
    print(json.dumps(result, sort_keys=True))
    return 0 if result['verified'] is True else 1


def block_producers():
    result = report(False)
    result['error'] = 'UNSUPPORTED_SERVER_PRODUCER_BARRIER'
    return result


def verify(exchange):
    parent = directory((Path(exchange) / STATE_RELATIVE).parent)
    path = parent / 'state.json'
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_RESPONSE
            and not getattr(info, 'st_file_attributes', 0) & 0x400)
    if os.name != 'nt':
        require(info.st_mode & 0o077 == 0)
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1
                and (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
                == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))
        raw = stream.read(MAX_RESPONSE + 1)
        after = os.fstat(stream.fileno())
        require((after.st_size, after.st_mtime_ns, after.st_nlink)
                == (opened.st_size, opened.st_mtime_ns, 1))
    current = path.lstat()
    require((current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
            == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
            and len(raw) == info.st_size and len(raw) <= MAX_RESPONSE)
    state = document(raw)
    require(type(state) is dict and set(state) == {
        'schema', 'sourceCommit', 'fixture', 'token', 'userId', 'projectId', 'modelId', 'objectId', 'versionId',
    } and type(state['schema']) is int and state['schema'] == 1
            and state['sourceCommit'] == SOURCE_COMMIT and state['fixture'] == FIXTURE
            and state['objectId'] == fixture_object()['id'])
    for key in ('userId', 'projectId', 'modelId', 'versionId'):
        identifier(state[key])
    observed = Client().graphql('RecoveryVerify', {
        'projectId': state['projectId'], 'modelId': state['modelId'], 'objectId': state['objectId'],
    }, state['token'])
    expected = {
        'activeUser': {'id': state['userId'], 'email': EMAIL, 'name': USER_NAME},
        'project': {'id': state['projectId'], **PROJECT_INPUT,
            'model': {'id': state['modelId'], 'name': MODEL_NAME, 'projectId': state['projectId'],
                'versions': {'totalCount': 1, 'items': [{
                    'id': state['versionId'], 'referencedObject': state['objectId'],
                    'message': VERSION_MESSAGE, 'sourceApplication': SOURCE_APPLICATION,
                    # versions.ts:338-345 omits requested count; commit/management.ts:
                    # 106-115 sets object.totalChildrenCount || 1, even for Base.
                    'totalChildrenCount': 1, 'model': {'id': state['modelId']},
                    'authorUser': {'id': state['userId']},
                }]}},
            'object': {'id': state['objectId'], 'data': fixture_object(), 'totalChildrenCount': 0},
        },
    }
    # JSON equality is type-sensitive (unlike Python's True == 1).
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)
    require(canonical(observed) == canonical(expected))
    return report(True)


if __name__ == '__main__':
    raise SystemExit(main())
