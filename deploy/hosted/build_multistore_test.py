"""Exact-image isolated multi-store candidate preparation, no native invocation.

Product images bind the previously controlled exact c82b92b product source;
535eb30 adds preparation/evidence only on the selected product runtime paths.
Current-cache observations for third parties are continuity candidates, not
registry/source verification. Native qualification is performed by a later
separately approved owner-manual runner. This module does not grant permission.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

from build_image_runtime import runtime_model, bind

HERE = Path(__file__).resolve().parent
PRODUCT_REVISION = 'c82b92b29423c515e353e3fa4f9c17e9b0d83438'
PREPARATION_BASE = '535eb3020532a00f7405b02f0c791d8fe1b5522c'
KIND = 'isolated-full-multistore-native-candidate-not-release'
TOOL_PINS = {
    'dockerSha256': '6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896',
    'composeSha256': 'e6176502e836a7fee8d71cab5fcda736c8dacc79ccefdf9659af977f7eae2375',
}
THIRD_PARTIES = {
    'n8n': 'n8nio/n8n:2.4.8',
    'speckle-postgres': 'postgres:16.4-alpine3.20',
    'speckle-redis': 'valkey/valkey:8.1-alpine',
    'speckle-minio': 'minio/minio:latest',
}
SPECKLE_ROLES = (
    'speckle-server', 'speckle-frontend-2', 'speckle-preview-service',
    'speckle-webhook-service', 'speckle-ingress', 'speckle-ifc-import-service',
)


def validate_source_binding(binding):
    """Validate the data-only, deliberately inadmissible public source candidate."""
    def reject():
        raise ValueError('Speckle source binding rejected')

    def digest(value, pattern):
        if type(value) is not str or re.fullmatch(pattern, value) is None:
            reject()

    flags = {'authenticatedProvenance', 'localCacheVerified', 'runtimeQualified'}
    top = {'kind', 'sourceCommit', 'sourceArchiveUrl', 'sourceArchiveSha256',
           'trust', 'runtimeAdmissible', 'services'} | flags
    if type(binding) is not dict or set(binding) != top:
        reject()
    commit = '51d43b91c4681a75bff8b285da7f443a4599da67'
    if (binding['kind'] != 'offline-speckle-source-binding/v1'
            or binding['sourceCommit'] != commit
            or binding['sourceArchiveUrl'] != 'https://codeload.github.com/specklesystems/speckle-server/tar.gz/'+commit
            or binding['sourceArchiveSha256'] != '2c178d568a5cc04a6000d0fc61c5488639c3ea61ce518528f47d634f446e73ba'
            or binding['trust'] != 'unsigned-registry-hosted-BuildKit-source-claims-not-authenticated-provenance'
            or any(binding[key] is not False for key in flags | {'runtimeAdmissible'})):
        reject()
    services = binding['services']
    if type(services) is not dict or set(services) != set(SPECKLE_ROLES):
        reject()
    fields = {'sourceCommit', 'dockerfile', 'dockerfileSha256', 'publishedImage',
              'indexDigest', 'manifestDigest', 'configDigest', 'platform',
              'unsignedSourceClaimMatches'} | flags
    for role, item in services.items():
        if type(item) is not dict or set(item) != fields:
            reject()
        package = role.removeprefix('speckle-')
        dockerfile = ('utils/docker-compose-ingress/Dockerfile' if role == 'speckle-ingress'
                      else 'packages/'+package+'/Dockerfile')
        repository = 'speckle/'+('speckle-docker-compose-ingress' if role == 'speckle-ingress' else role)
        if (item['sourceCommit'] != commit or item['dockerfile'] != dockerfile
                or item['platform'] != 'linux/amd64'
                or item['unsignedSourceClaimMatches'] is not True
                or any(item[key] is not False for key in flags)):
            reject()
        digest(item['dockerfileSha256'], r'[0-9a-f]{64}')
        for key in ('indexDigest', 'manifestDigest', 'configDigest'):
            digest(item[key], r'sha256:[0-9a-f]{64}')
        if item['publishedImage'] != repository+'@'+item['manifestDigest']:
            reject()
    return binding


def parse_source_binding(data):
    """Pin exact reviewed data bytes; this integrity check is not provenance."""
    if (type(data) is not bytes or hashlib.sha256(data).hexdigest()
            != '69c6b618b6740ff74e917d8967b7c7c281f9606747305ee316207d03af5b7d3d'):
        raise ValueError('Speckle source binding bytes rejected')
    return validate_source_binding(json.loads(data))


def image_bindings():
    built = json.loads((HERE/'image-runtime/c82b92b-build-evidence.json').read_bytes())
    observed = json.loads((HERE/'recovery-test/evidence/multistore-inventory-v4-owner-observation.json').read_bytes())
    if built['sourceRevision'] != PRODUCT_REVISION or observed['reportedStatus'] != 'OBSERVED_NOW':
        raise ValueError('candidate evidence identity rejected')
    images = {}
    for role in ('neo4j','dg-reasoner','data-service','design-grammars'):
        item = built['images'][role]
        images[role] = {'configId': item['imageId'], 'reference': item['tag'],
                        'sourceRevision': PRODUCT_REVISION, 'registryVerified': False,
                        'returnedRepoDigests': [], 'archiveSha256': item['archiveSha256']}
    for role, reference in THIRD_PARTIES.items():
        matches = [i for i in observed['images'] if i['reference'] == reference]
        if len(matches) != 1 or matches[0]['os'] != 'linux' or matches[0]['architecture'] != 'amd64':
            raise ValueError('candidate image rejected')
        item = matches[0]
        images[role] = {'configId': item['configId'], 'reference': reference,
                        'sourceRevision': None, 'registryVerified': False,
                        'returnedRepoDigests': list(item['repoDigests'])}
    binding = parse_source_binding((HERE/'recovery-test/speckle-source-binding.json').read_bytes())
    for role, item in binding['services'].items():
        images[role] = {'configId': item['configDigest'], 'reference': item['publishedImage'],
                        'sourceRevision': item['sourceCommit'], 'registryVerified': False,
                        'returnedRepoDigests': [], 'indexDigest': item['indexDigest'],
                        'manifestDigest': item['manifestDigest'],
                        'authenticatedProvenance': False, 'localCacheVerified': False,
                        'runtimeQualified': False}
    if not all(re.fullmatch('sha256:[0-9a-f]{64}', i['configId']) for i in images.values()):
        raise ValueError('candidate image identity rejected')
    return images


def volume(name, target, readonly=False):
    result = {'type':'volume','source':name,'target':target}
    if readonly:
        result['read_only'] = True
    return result


def native_model(*, destination=False):
    pins = image_bindings()
    controlled = {role:{'imageId':pins[role]['configId']}
                  for role in ('neo4j','dg-reasoner','data-service','design-grammars')}
    result = runtime_model(controlled)
    services = result['services']
    for role in (*THIRD_PARTIES, *SPECKLE_ROLES):
        services[role] = {'image':pins[role]['configId'],'pull_policy':'never',
                         'platform':'linux/amd64','networks':['sandbox'],'restart':'no',
                         'mem_limit':'1250m' if role in ('n8n','speckle-server','speckle-ifc-import-service') else '512m',
                         'cpus':1.0,'pids_limit':256,'security_opt':['no-new-privileges:true']}
    neo = services['neo4j']
    neo['volumes'].append(volume('graph_logs','/logs'))
    api = services['data-service']
    api['environment'].update({'SPECKLE_INTERNAL_URL':'http://speckle-ingress:8080',
                               'N8N_INTERNAL_URL':'http://n8n:5678'})
    api['volumes'] = [v for v in api['volumes'] if v['target'] not in ('/app/image_runtime_probe.py','/app/sandbox_probe.py')]
    api['volumes'] += [bind('./support/probe.py','/app/recovery_probe.py'),
                       bind('./support/smoke_probe.py','/app/image_runtime_probe.py'),
                       bind('./support/sandbox_probe.py','/app/sandbox_probe.py'),
                       volume('exchange','/exchange')]
    n8n = services['n8n']
    n8n['environment'] = {'N8N_DIAGNOSTICS_ENABLED':'false','N8N_VERSION_NOTIFICATIONS_ENABLED':'false',
        'N8N_TEMPLATES_ENABLED':'false','N8N_PERSONALIZATION_ENABLED':'false',
        'N8N_DEFAULT_BINARY_DATA_MODE':'filesystem','N8N_BLOCK_ENV_ACCESS_IN_NODE':'true',
        'N8N_RESTRICT_FILE_ACCESS_TO':'/files/workflows;/files/evidence',
        'N8N_RUNNERS_ENABLED':'false','EXECUTIONS_MODE':'regular','DB_TYPE':'sqlite',
        'DB_SQLITE_DATABASE':'database.sqlite','DB_TABLE_PREFIX':'',
        'N8N_USER_FOLDER':'/n8n-state','N8N_BINARY_DATA_STORAGE_PATH':'/n8n-state/.n8n/binaryData',
        'N8N_COMMUNITY_PACKAGES_ENABLED':'false',
        'N8N_ENCRYPTION_KEY_FILE':'/exchange/keys/n8n.key',
        'N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS':'true'}
    # Restore publishes a previously absent .n8n child, never an existing mount root.
    n8n['volumes'] = [volume('n8n_state','/n8n-state'),volume('exchange','/exchange'),
                      volume('n8n_evidence','/files/evidence'),bind('./source/n8n/workflows','/files/workflows')]
    pg = services['speckle-postgres']
    pg['environment'] = {'POSTGRES_DB':'speckle','POSTGRES_USER':'speckle',
                         'POSTGRES_PASSWORD':'${POSTGRES_PASSWORD:?required}'}
    # No application's first-init SQL: migrations run with the actual pinned server.
    pg['volumes'] = [volume('postgres_state','/var/lib/postgresql/data'),volume('exchange','/exchange')]
    pg['healthcheck'] = {'test':['CMD-SHELL','pg_isready -U speckle -d speckle >/dev/null 2>&1'],
        'interval':'5s','timeout':'5s','retries':36,'start_period':'20s'}
    redis = services['speckle-redis']
    redis['volumes'] = [volume('redis_state','/data')]
    redis['command'] = ['valkey-server','--save','','--appendonly','no']
    minio = services['speckle-minio']
    minio['environment'] = {'MINIO_ROOT_USER':'${MINIO_ROOT_USER:?required}',
                            'MINIO_ROOT_PASSWORD':'${MINIO_ROOT_PASSWORD:?required}'}
    minio['command'] = ['server','/data','--console-address',':9001']
    minio['volumes'] = [volume('object_state','/data')]
    server = services['speckle-server']
    server['environment'] = {'CANONICAL_URL':'http://speckle-ingress:8080',
        'PRIVATE_OBJECTS_SERVER_URL':'http://speckle-server:3000',
        'SESSION_SECRET':'${SPECKLE_SESSION_SECRET:?required}', 'STRATEGY_LOCAL':'true',
        'LOG_LEVEL':'warn','LOG_PRETTY':'false','POSTGRES_URL':'speckle-postgres',
        'POSTGRES_USER':'speckle','POSTGRES_PASSWORD':'${POSTGRES_PASSWORD:?required}','POSTGRES_DB':'speckle',
        'REDIS_URL':'redis://speckle-redis:6379/0', 'PREVIEW_SERVICE_REDIS_URL':'redis://speckle-redis:6379/0',
        'PREVIEW_SERVICE_USE_PRIVATE_OBJECTS_SERVER_URL':'true',
        'FILEIMPORT_SERVICE_USE_PRIVATE_OBJECTS_SERVER_URL':'true',
        'S3_ENDPOINT':'http://speckle-minio:9000','S3_PUBLIC_ENDPOINT':'http://speckle-minio:9000',
        'S3_ACCESS_KEY':'${MINIO_ROOT_USER:?required}','S3_SECRET_KEY':'${MINIO_ROOT_PASSWORD:?required}',
        'S3_BUCKET':('speckle-destination' if destination else 'speckle-source'),
        'S3_CREATE_BUCKET':'true','FILE_SIZE_LIMIT_MB':'10',
        'EMAIL_FROM':'no-reply@example.invalid','EMAIL_SECURE':'false','EMAIL_REQUIRE_TLS':'false',
        'FRONTEND_ORIGIN':'http://speckle-ingress:8080',
        'FILEIMPORT_QUEUE_POSTGRES_URL':'postgresql://speckle:${POSTGRES_PASSWORD:?required}@speckle-postgres/speckle',
        'DISABLE_FILE_UPLOADS':'false', 'FF_NEXT_GEN_FILE_IMPORTER_ENABLED':'true',
        'FF_LEGACY_FILE_IMPORTS_ENABLED':'false', 'FF_RHINO_FILE_IMPORTER_ENABLED':'false',
        'FF_WORKSPACES_MULTI_REGION_ENABLED':'false', 'FF_AUTOMATE_MODULE_ENABLED':'false',
        'FF_GENDOAI_MODULE_ENABLED':'false', 'FF_WORKSPACES_MODULE_ENABLED':'false',
        'FF_ACC_INTEGRATION_ENABLED':'false', 'FF_RETRY_ERRORED_PREVIEWS_ENABLED':'false'}
    server['depends_on'] = {'speckle-postgres':{'condition':'service_healthy'},
                            'speckle-redis':{'condition':'service_started'},
                            'speckle-minio':{'condition':'service_started'}}
    front = services['speckle-frontend-2']
    front['environment'] = {'NUXT_PUBLIC_SERVER_NAME':'synthetic-recovery',
        'NUXT_PUBLIC_API_ORIGIN':'http://speckle-ingress:8080',
        'NUXT_PUBLIC_BASE_URL':'http://speckle-ingress:8080',
        'NUXT_PUBLIC_BACKEND_API_ORIGIN':'http://speckle-server:3000',
        'NUXT_REDIS_URL':'redis://speckle-redis:6379/0','LOG_LEVEL':'warn','LOG_PRETTY':'false',
        'NUXT_PUBLIC_FF_LEGACY_FILE_IMPORTS_ENABLED':'false',
        'NUXT_PUBLIC_FF_LARGE_FILE_IMPORTS_ENABLED':'true','NUXT_PUBLIC_FF_NEXT_GEN_FILE_IMPORTER_ENABLED':'true'}
    front['depends_on'] = {'speckle-server':{'condition':'service_started'}}
    services['speckle-preview-service']['environment'] = {
        'HOST':'127.0.0.1','PORT':'3001','LOG_LEVEL':'warn','LOG_PRETTY':'false','REDIS_URL':'redis://speckle-redis:6379/0'}
    services['speckle-webhook-service']['environment'] = {
        'LOG_LEVEL':'warn','LOG_PRETTY':'false',
        'PG_CONNECTION_STRING':'postgresql://speckle:${POSTGRES_PASSWORD:?required}@speckle-postgres/speckle'}
    services['speckle-ifc-import-service']['environment'] = {
        'FILEIMPORT_QUEUE_POSTGRES_URL':'postgresql://speckle:${POSTGRES_PASSWORD:?required}@speckle-postgres/speckle'}
    services['speckle-ifc-import-service']['working_dir'] = '/app'
    # Bounded ephemeral scratch only. These are model candidates, not rootfs proofs.
    for role in ('speckle-server', 'speckle-preview-service', 'speckle-webhook-service', 'speckle-ifc-import-service'):
        services[role]['tmpfs'] = ['/tmp:rw,nosuid,nodev,size=268435456,mode=1777']
    # Upstream explicitly leaves Chromium's rootfs writable; /tmp-only is unqualified.
    services['speckle-preview-service']['read_only'] = False
    services['speckle-preview-service']['environment'].update({
        'GPU_ENABLED':'false', 'USER_DATA_DIR':'/tmp/puppeteer'})
    for role in ('speckle-preview-service','speckle-webhook-service','speckle-ifc-import-service'):
        services[role]['depends_on'] = {'speckle-server':{'condition':'service_started'}}
    services['speckle-ingress']['environment'] = {'FILE_SIZE_LIMIT_MB':'10','NGINX_ENVSUBST_OUTPUT_DIR':'/etc/nginx'}
    services['speckle-ingress']['depends_on'] = {role:{'condition':'service_started'} for role in ('speckle-server','speckle-frontend-2')}
    common = {'pull_policy':'never','platform':'linux/amd64','restart':'no','cpus':1.0,
        'pids_limit':128,'mem_limit':'768m','security_opt':['no-new-privileges:true'],
        'entrypoint':['/bin/sh','-c','exec sleep 5400'],'user':'0:0','profiles':['maintenance']}
    services['graph-admin'] = dict(copy.deepcopy(common),image=pins['neo4j']['configId'],network_mode='none',
        volumes=[volume('graph','/data'),volume('graph_logs','/logs'),volume('exchange','/exchange')])
    services['snapshot'] = dict(copy.deepcopy(common),image=pins['data-service']['configId'],networks=['sandbox'],
        environment={'MINIO_ROOT_USER':'${MINIO_ROOT_USER:?required}',
            'MINIO_ROOT_PASSWORD':'${MINIO_ROOT_PASSWORD:?required}',
            'N8N_ENCRYPTION_KEY':'${N8N_ENCRYPTION_KEY:?required}',
            # Isolated synthetic network only; same bucket as this side's speckle-server.
            'RECOVERY_S3_ENDPOINT':'http://speckle-minio:9000','RECOVERY_S3_ALLOW_HTTP':'1',
            'RECOVERY_S3_ACCESS_KEY':'${MINIO_ROOT_USER:?required}',
            'RECOVERY_S3_SECRET_KEY':'${MINIO_ROOT_PASSWORD:?required}',
            'RECOVERY_S3_BUCKET':('speckle-destination' if destination else 'speckle-source')},
        volumes=[dict(volume('api_state','/state'),read_only=not destination),
                 dict(volume('n8n_state','/n8n-state'),read_only=not destination),
                 volume('exchange','/exchange'),bind('./support','/opt/recovery'),bind('./tools','/opt/tools')])
    services['n8n-admin'] = dict(copy.deepcopy(common),image=pins['n8n']['configId'],network_mode='none',
        environment=copy.deepcopy(n8n['environment']),volumes=copy.deepcopy(n8n['volumes']))
    result['volumes'] = {name:{} for name in ('graph','graph_logs','api_state','postgres_state',
                        'object_state','redis_state','n8n_state','n8n_evidence','exchange')}
    return result


def read_product_blob(repo, revision, name):
    if not re.fullmatch('[0-9a-f]{40}',revision) or not re.fullmatch(r'[A-Za-z0-9_./-]+',name) or '..' in name.split('/'):
        raise ValueError('source identity rejected')
    return subprocess.check_output(['git','-C',str(repo),'show',revision+':'+name],stderr=subprocess.DEVNULL)


def verify_product_source(repo, revision, files):
    if type(files) is not dict or not files:
        raise ValueError('source identity rejected')
    for name, data in files.items():
        if type(data) is not bytes or read_product_blob(repo,revision,name) != data:
            raise ValueError('source identity rejected')
    return len(files)
