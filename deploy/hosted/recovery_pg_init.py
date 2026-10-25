"""Pure standalone PostgreSQL restore model; NEVER merge with owner's base.

No mutation/CLI/daemon. Digest syntax is not qualification: the outer runner must
bind the approved PostgreSQL16.4 Alpine server/client, role/extension mapping,
new vacant project/volume and approval before using this model. No app tables
are assumed during first init. Native restore must finish before app/migrations.
Password is resolved only in the later approved target process, never here.
"""
import re


class InitError(ValueError):
    pass


def restore_model(*, project, image):
    if not (type(project) is str and re.fullmatch('dg-recovery-[0-9a-f]{32}', project)
            and type(image) is str and re.fullmatch('postgres@sha256:[0-9a-f]{64}', image)):
        raise InitError('PostgreSQL restore model rejected')
    labels = {'dg.recovery.project': project, 'dg.recovery.role': 'isolated-pg-restore'}
    return {'name': project, 'services': {'speckle-postgres': {
        'image': image, 'pull_policy': 'never', 'restart': 'no',
        'environment': {'POSTGRES_DB': 'speckle', 'POSTGRES_USER': 'speckle',
            'POSTGRES_PASSWORD': '${DG_RECOVERY_POSTGRES_PASSWORD:?approved target secret required}'},
        'volumes': ['pgdata:/var/lib/postgresql/data'], 'networks': ['restore'],
        'labels': dict(labels), 'mem_limit': '512m', 'cpus': 1.0,
        'pids_limit': 128, 'security_opt': ['no-new-privileges:true']}},
        'networks': {'restore': {'internal': True}},
        'volumes': {'pgdata': {'labels': dict(labels)}}}


def admit_pristine_catalog(catalog):
    """Admit independently supplied catalog declaration; no SQL or DB connection.

    The future trusted version-bound probe must enumerate ALL user-owned objects
    (relations/types/functions/etc), non-system schemas/extensions, sessions and
    prepared transactions. pg_isready or public-table count is insufficient.
    Declaration cannot prove a database is empty or owned. Isolation, blocking
    concurrent clients, exact query coverage and runtime observations remain
    prerequisites; this helper alone MUST NOT authorize pg_restore.
    """
    expected = {'serverVersionNum':160004, 'database':'speckle', 'role':'speckle',
                'schemas':['public'], 'extensions':['plpgsql'], 'userObjects':[],
                'otherConnections':0, 'preparedTransactions':0,
                'databaseOwner':'speckle', 'roleSuperuser':True}
    if not (type(catalog) is dict and set(catalog) == set(expected)
            and all(type(catalog[key]) is type(value) and catalog[key] == value
                    for key, value in expected.items())):
        raise InitError('PostgreSQL restore catalog rejected')
    return {'readyForRestoreDeclared':True, 'nativeRecoveryProven':False,
            'authorizationProven':False}

