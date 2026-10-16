"""Reconcile one issued four-image smoke report, without invoking any service.

A successful semantic report with a lost process exit is explicitly incomplete
process evidence, not a failed smoke and never release acceptance. The input
report is an owner-chat transcription, not original file bytes or a signature.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from build_image_runtime import verify

ZIP_SHA = '6fc3b7ad060db3e79a1452e2a2868f87e339aed8bfa70c39b2f3c82b1fa8199f'
BUILD_REPORT_SHA = '783d9b077ddac21c75d5c748f58bead460d2c1b223fb3d926a9d042eaa252b75'


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def reconcile(report, archive, *, exit_code):
    if exit_code is not None and (type(exit_code) is not int or exit_code != 0):
        raise ValueError('exit must be explicitly unknown or observed zero')
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != ZIP_SHA or verify(archive) != ZIP_SHA:
        raise ValueError('issued ZIP mismatch')
    with zipfile.ZipFile(archive) as bundle:
        job = json.loads(bundle.read('image-runtime-manifest.json'))
    expected = {
        'schemaVersion': 1, 'kind': job['kind'], 'status': 'LOAD_AND_ISOLATED_SMOKE_COMPLETE',
        'failureStage': None, 'dockerInvoked': True, 'releaseAccepted': False,
        'archiveBytesVerified': True, 'crossDaemonPortabilityProven': False,
        'fullHostedAcceptance': False, 'cleanup': 'project-down-volumes-removed',
        'checks': {name: True for name in ('packageIntegrity', 'buildReportBoundToIssuedPackage',
            'daemonPreflight', 'composeIsolation', 'projectVacant', 'readiness', 'cleanupVerified',
            'imagesAndArchivesRetained')},
        'images': {name: {'imageId': image['imageId'], 'status': 'LOADED_AND_VERIFIED',
            'os': image['os'], 'architecture': image['architecture'], 'revision': job['sourceRevision']}
            for name, image in job['images'].items()},
        'packageZipSha256': ZIP_SHA, 'sourceRevision': job['sourceRevision'],
        'sourceManifestSha256': job['sourceManifestSha256'], 'buildReportSha256': BUILD_REPORT_SHA,
    }
    expected['checks']['smoke'] = {
        'api': {'admin_login': True, 'csrf_denied': True, 'ingest_inserted': 1,
                'neo4j_scoped_notes': 1, 'denied_paths': 4},
        'uiAssets': 2, 'uiHeaders': True, 'uiProxyTombstones': True,
        'uiRuntimeConfig': True, 'reasonerNeo4jUp': True, 'selfRegistrationDisabled': True,
    }
    raw = Path(report).read_bytes()
    if canonical(json.loads(raw)) != canonical(expected):
        raise ValueError('typed report/checks/identity mismatch')
    return {
        'schemaVersion': 1,
        'status': ('OWNER_REPORTED_SMOKE_COMPLETE_EXIT_UNKNOWN' if exit_code is None
                   else 'OWNER_REPORTED_SMOKE_COMPLETE_EXIT_ZERO'),
        'reportProvenance': 'owner-chat-transcription-not-original-file',
        'reportTranscriptionSha256': hashlib.sha256(raw).hexdigest(),
        'packageZipSha256': ZIP_SHA, 'sourceRevision': job['sourceRevision'],
        'sourceManifestSha256': job['sourceManifestSha256'],
        'buildReportSha256': BUILD_REPORT_SHA, 'processExitCode': exit_code,
        'runtimeTimestamp': None, 'reportChecksMatched': True,
        'evidenceComplete': exit_code == 0, 'independentlyObservedRuntime': False,
        'releaseAccepted': False, 'fullHostedAcceptance': False,
        'crossDaemonPortabilityProven': False,
        'gaps': ['process-exit-not-captured'] if exit_code is None else [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--zip', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--exit-code', type=int)
    group.add_argument('--exit-unknown', action='store_true')
    args = parser.parse_args()
    try:
        result = reconcile(args.report, args.zip, exit_code=args.exit_code)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile):
        print('EVIDENCE_REJECTED: report/package/exit mismatch', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    # 2 distinguishes valid report with incomplete process evidence from both
    # malformed evidence (1) and a complete matching process/report pair (0).
    return 0 if result['evidenceComplete'] else 2


if __name__ == '__main__':
    sys.exit(main())
