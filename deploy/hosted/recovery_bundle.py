"""Read-only n8n/object subset bundle verifier. NOT a five-store checkpoint.

Caller supplies independently authenticated manifest hashes. No keys, services,
SQLite connections, filesystem writes or restore calls. This verifies only the
n8n/objects pair; Neo4j/Postgres/API consistency and crypto are NOT covered.
Trusted private filesystem without concurrent mutation remains required.
"""
import hashlib
import json
import re
try:
    from . import recovery_n8n as n8n
    from . import recovery_objects as objects
except ImportError:
    import recovery_n8n as n8n
    import recovery_objects as objects


class BundleError(ValueError):
    pass


def _require(value):
    if not value:
        raise BundleError('subset bundle rejected')


def _entries(path, expected):
    # Bound enumeration before sorting/materializing all directory entries.
    import os
    names = set()
    with os.scandir(path) as entries:
        for entry in entries:
            _require(entry.name in expected and entry.name not in names)
            names.add(entry.name)
    _require(names == expected)


def verify_bundle(package, *, expected_objects_sha256, expected_n8n_sha256, version):
    try:
        _require(version == '2.4.8')
        _require(all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value)
                     for value in (expected_objects_sha256, expected_n8n_sha256)))
        package = n8n._root(package)
        _entries(package, {'objects', 'n8n'})
        object_root = n8n._root(package / 'objects')
        objects._verify(object_root, expected_objects_sha256)
        state = n8n._root(package / 'n8n')
        _entries(state, {'tree', 'state-manifest.json'})
        marker = state / 'state-manifest.json'
        _require(n8n._regular(marker).st_size <= n8n.MAX_MANIFEST)
        raw = marker.read_bytes()
        _require(hashlib.sha256(raw).hexdigest() == expected_n8n_sha256)
        declaration = json.loads(raw, object_pairs_hook=n8n._pairs)
        _require(type(declaration) is dict and set(declaration) ==
                 {'schemaVersion','version','files','directories','nativeRecoveryProven'})
        _require(type(declaration['schemaVersion']) is int and declaration['schemaVersion'] == 1
                 and declaration['version'] == version and declaration['nativeRecoveryProven'] is False)
        inventory = n8n._inventory(n8n._root(state / 'tree'))
        _require(declaration['files'] == inventory['files']
                 and declaration['directories'] == inventory['directories'])
        return {'status': 'OBJECT_N8N_SUBSET_VERIFIED_NOT_RECOVERY',
                'verifiedClasses': ['objects','n8n'], 'nativeRecoveryProven': False,
                'releaseAccepted': False}
    except Exception:
        raise BundleError('subset bundle rejected') from None
