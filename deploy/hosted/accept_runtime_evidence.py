"""Match an owner-returned report to the issued ZIP; never attests runtime independently."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

REVISION = '2dedbfb3e138c2b437e781696197105dca93342a'
ZIP_HASH = '1e032824fbb3006d3e001a3460185a97e1d4661941910671f6f4f62ecc4af87e'
MANIFEST_HASH = '864878de1e60aadc79211f20e574f32cb5f97a096c06dac696a1f52215f04810'
KIND = 'hosted-candidate-capability-test-not-release'
EXPECTED = {
    'schemaVersion': 1, 'kind': KIND, 'candidateManifestSha256': MANIFEST_HASH,
    'target': 'DESKTOP-OS4Q8CP', 'status': 'PASS', 'failureStage': None,
    'frameworkRevision': REVISION, 'zipSha256': ZIP_HASH,
    'checks': {'packageHash': True, 'candidateIntegrity': True, 'diskPreflight': True,
               'composeVersion': True, 'projectVacant': True, 'composeIsolation': True,
               'dataService': {'admin_login': True, 'csrf_denied': True,
                               'ingest_inserted': 1, 'neo4j_scoped_notes': 1, 'denied_paths': 4},
               'n8nNamedRead': True, 'n8nDeniedRead': True, 'cleanupVerified': True},
    'cleanup': 'project-down-volumes-removed',
}


def accept(report, archive, *, exit_code):
    raw = Path(report).read_bytes()
    value = json.loads(raw)
    if (json.dumps(value, sort_keys=True) != json.dumps(EXPECTED, sort_keys=True) or
            type(exit_code) is not int or exit_code != 0):
        raise ValueError('owner report or process exit mismatch')
    archive = Path(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ZIP_HASH:
        raise ValueError('issued ZIP mismatch')
    with zipfile.ZipFile(archive) as bundle:
        package = json.loads(bundle.read('bundle-test-manifest.json'))
        manifest = bundle.read('candidate/manifest.json')
        if (package['frameworkRevision'] != REVISION or package['kind'] != KIND or
                package['candidateManifestSha256'] != MANIFEST_HASH or
                hashlib.sha256(manifest).hexdigest() != MANIFEST_HASH):
            raise ValueError('candidate identity mismatch')
        for name, expected in package['files'].items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != expected:
                raise ValueError('package member mismatch')
    return {'schemaVersion': 1, 'status': 'OWNER_REPORTED_CAPABILITY_PASS',
            'frameworkRevision': REVISION, 'zipSha256': ZIP_HASH,
            'candidateManifestSha256': MANIFEST_HASH,
            'reportFileSha256': hashlib.sha256(raw).hexdigest(), 'processExitCode': exit_code,
            'independentlyObservedRuntime': False, 'releaseAccepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--zip', required=True)
    parser.add_argument('--exit-code', type=int, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(accept(args.report, args.zip, exit_code=args.exit_code), sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile):
        print('Owner report BLOCKED: identity/checks/exit mismatch', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
