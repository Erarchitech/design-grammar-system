"""Immutable full-multistore *candidate*, never a release or runtime approval.

Reads only exact allowlisted Git blobs and named preparation inputs. No Docker,
network, owner configuration, Python installation, index or checkout mutations.
The separately supplied ZIP SHA256 must travel via a trusted owner channel.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from build_multistore_test import PREPARATION_BASE, PRODUCT_REVISION, KIND
from release_core import matches, safe_path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
AGE_DIR = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch/multistore-age121')
MANIFEST = 'multistore-manifest.json'
MAX_FILE = 32_000_000
MAX_TOTAL = 128_000_000
MAX_FILES = 512
SOURCE_MANIFEST_SHA = '10bbde850bfc53fb9e924b76ebac1d8f7abfa20a84fe3cf77ed9a0d2c9b25eaf'
# New preparation bytes are captured afresh for EACH build/verification, never
# labelled as committed product. Explicit membership; no glob auto-enrolment.
SUPPORT = {
    'Run-MultiStore.ps1': 'recovery-test/Run-MultiStore.ps1',
    'Invoke-OwnerMultiStore.ps1': 'recovery-test/Invoke-OwnerMultiStore.ps1',
    'runtime-functions.ps1': 'image-runtime/runtime-execution.ps1',
    'multistore_execution.ps1': 'recovery-test/multistore_execution.ps1',
    'multistore_orchestrator.ps1': 'recovery-test/multistore_orchestrator.ps1',
    'probe.py': 'recovery-test/probe.py',
    'smoke_probe.py': 'image-runtime/probe.py',
    'sandbox_probe.py': 'sandbox/probe.py',
    'multistore_archive.py': 'recovery-test/multistore_archive.py',
    'multistore_native.py': 'recovery-test/multistore_native.py',
    'multistore_n8n.py': 'recovery-test/multistore_n8n.py',
    'multistore_speckle.py': 'recovery-test/multistore_speckle.py',
    'multistore_exchange.py': 'recovery-test/multistore_exchange.py',
    'speckle-source-binding.json': 'recovery-test/speckle-source-binding.json',
    'multistore_qualified_app.py': 'recovery-test/multistore_qualified_app.py',
    'multistore_qualified_queue.py': 'recovery-test/multistore_qualified_queue.py',
    'speckle-physical-contract.json': 'recovery-test/speckle-physical-contract.json',
    **{n + '.py': n + '.py' for n in ('recovery_checkpoint', 'recovery_filesystem',
       'recovery_postgres', 'recovery_pg_init', 'recovery_objects', 'recovery_n8n',
       'recovery_queues', 'recovery_bundle', 'recovery_sequence', 'recovery_transport')},
}
AGE_FILES = {
    'tools/age': ('linux/age', 'aaec874ed903da4b02a9d503778ae05ee5005b2acc0f4a4cf10e5d0f17fd4384'),
    'tools/age-keygen': ('linux/age-keygen', '50f849de5f05dc136de3dba623dd2b7e166e7badb9d4e3d83da88f2dbdb2d439'),
    'tools/LICENSE': ('linux/LICENSE', '32cc8df32709c059f3ee312dc088bae7ddb8b8adc1efdd2b6394cdcb8b6300c8'),
    'tools/windows/age.exe': ('windows/age.exe', '5729bd8f90d5cdf0a69ccd10408f000877ad4ab4bec8e49f80fbd8bd15539cc7'),
    'tools/windows/age-keygen.exe': ('windows/age-keygen.exe', '2c3ac6c083ee68458c39f1a61feaff8c4d754c44e236eaca54a026066a968cd4'),
    'tools/windows/LICENSE': ('windows/LICENSE', '32cc8df32709c059f3ee312dc088bae7ddb8b8adc1efdd2b6394cdcb8b6300c8'),
    'provenance/age/CONTRACT.md': ('CONTRACT.md', 'a92ffe757c2aff2236b475a6106d1478ac40b3e3334aaa09277e514326255f67'),
    'provenance/age/signature-verification.json': ('signature-verification.json', 'd6d6921a52f794d262658a77e9fedf6fc3d1004642e6577123c49302d9cf287a'),
    'provenance/age/download-provenance.json': ('download-provenance.json', '03943e1f455bba2b9133c81a424cee48e52d300a0b0ee021a7d2c37c18b4118b'),
    'provenance/age/extracted-tools.json': ('extracted-tools.json', 'f8efa1bec4ee1fb96d8e5bf3eb127f84c107b9feb77f1fae4595ce4eadd30709'),
    # Full mutable GitHub API snapshots and historical delivery inventories are
    # retained externally, not required inputs or auto-enrolled package members.
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)


def product_source(repo):
    """Select by the committed policy; read raw blobs, never checkout filters."""
    policy_name = 'deploy/hosted/release-allowlist.json'
    policy = json.loads(git(repo, 'show', PREPARATION_BASE + ':' + policy_name))
    if policy['includeDegram'] is not False:
        raise ValueError('component inclusion rejected')
    tree = {}
    for row in git(repo, 'ls-tree', '-rz', PREPARATION_BASE).split(b'\0'):
        if row:
            header, name = row.split(b'\t', 1)
            tree[name.decode('utf-8')] = header.split()
    selected = set()
    for entry in policy['inputs']:
        hits = {n for n in tree if matches(n, entry['path'])}
        if not hits:
            raise ValueError('unmatched source policy')
        selected.update(n for n in hits if not any(matches(n, x) for x in entry.get('exclude', [])))
    if len(selected) != 187 or len({n.casefold() for n in selected}) != 187:
        raise ValueError('source inventory rejected')
    controlled = {}
    for row in git(repo, 'ls-tree', '-rz', PRODUCT_REVISION, '--', *sorted(selected)).split(b'\0'):
        if row:
            header, name = row.split(b'\t', 1)
            controlled[name.decode('utf-8')] = header.split()
    for name in selected:
        safe_path(name, policy['forbiddenComponents'])
        if tree[name][0] not in (b'100644', b'100755') or tree[name][1] != b'blob' or controlled.get(name) != tree[name]:
            raise ValueError('product equivalence rejected')
    # cat-file avoids Git archive export-subst/export-ignore and CRLF filters.
    ordered = sorted(selected)
    stream = subprocess.run(['git', '-C', str(repo), 'cat-file', '--batch'],
                            input=b''.join(tree[n][2] + b'\n' for n in ordered),
                            capture_output=True, check=True).stdout
    payload = {}
    pos = 0
    for name in ordered:
        end = stream.index(b'\n', pos)
        oid, kind, size = stream[pos:end].split()
        size = int(size)
        if oid != tree[name][2] or kind != b'blob' or not 0 <= size <= MAX_FILE:
            raise ValueError('blob rejected')
        start = end + 1
        data = stream[start:start + size]
        pos = start + size + 1
        if len(data) != size or stream[pos - 1:pos] != b'\n':
            raise ValueError('incomplete blob')
        payload['source/' + name] = data
    if pos != len(stream):
        raise ValueError('trailing Git bytes')
    manifest = {'schemaVersion': 1, 'status': 'CANDIDATE_NOT_RELEASE',
                'frameworkRevision': PREPARATION_BASE, 'productRevision': PRODUCT_REVISION,
                'equivalence': '187-exact-git-blobs-identical',
                'files': {n[7:]: sha(b) for n, b in payload.items()}}
    payload['source/manifest.json'] = encoded(manifest)
    return payload


def require_orchestration():
    path = HERE / 'recovery-test/multistore_orchestrator.ps1'
    if not path.is_file() or not re.search(r'(?im)^function Invoke-MultiStoreExercise\s*\(', path.read_text(encoding='utf-8-sig')):
        raise ValueError('complete orchestration required')


def require_reviewed_runtime_profile():
    """No independently reviewed coherent image/probe/schema profile exists yet.

    Main-function presence is not implementation completeness, compatibility or
    review evidence. Keep the production entry point blocked until that exact
    future profile is explicitly integrated and independently reviewed. The raw
    writer is used only for labelled offline lifecycle fixtures, never handoff.
    """
    raise ValueError('independently reviewed runtime profile unavailable')


def prepare(repo, output, age_directory=AGE_DIR):
    require_orchestration()
    require_reviewed_runtime_profile()
    return write_package(build_payload(repo, age_directory), output)


def regular_bytes(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('linked preparation path')
    info = path.stat()
    # Editor snapshots may hardlink preparation inputs. Only raw bytes are
    # copied into new regular ZIP members; this is not a live/owner tree export.
    if not path.is_file() or info.st_size > MAX_FILE:
        raise ValueError('unsafe preparation input')
    return path.read_bytes()


def member_name(name):
    safe_path(name)
    if len(name) > 240 or not re.fullmatch(r'[A-Za-z0-9_./-]+', name):
        raise ValueError('unsafe member')
    for part in name.split('/'):
        if part.endswith(('.', ' ')) or re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', part):
            raise ValueError('unsafe member')
    return name


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON property')
        result[key] = value
    return result


def build_payload(repo, age_directory=AGE_DIR):
    from build_multistore_test import image_bindings, native_model, TOOL_PINS
    payload = product_source(repo)
    if sha(payload['source/manifest.json']) != SOURCE_MANIFEST_SHA:
        raise ValueError('source manifest identity')
    for name, origin in SUPPORT.items():
        payload['support/' + name] = regular_bytes(HERE / origin)
    raw = regular_bytes(HERE / 'image-runtime/Run-ImageRuntime.ps1').decode('utf-8-sig')
    # Actual old builder-defined function-only slice, not a fabricated shim.
    markers = ('function Assert-True', '$root = [IO.Path]')
    if any(raw.count(marker) != 1 for marker in markers):
        raise ValueError('invalid function slice markers')
    start, end = (raw.index(marker) for marker in markers)
    if start >= end:
        raise ValueError('invalid function slice order')
    payload['support/package-functions.ps1'] = raw[start:end].encode('utf-8')
    payload['support/empty-env.txt'] = b'# Deliberately empty; never discover owner .env.\n'
    for name, (origin, pin) in AGE_FILES.items():
        data = regular_bytes(Path(age_directory) / origin)
        if sha(data) != pin:
            raise ValueError('age input pin')
        payload[name] = data
    # New inventory describes only this package's pinned age members. It does
    # not rewrite or import the recovered historical delivery-manifest.json.
    payload['provenance/age/delivery-manifest.json'] = encoded({
        'schemaVersion': 2,
        'kind': 'current-package-age-inputs-not-historical-delivery',
        'verificationEvidence': 'historical-pinned-report-not-reverified',
        'files': {n: sha(payload[n]) for n in sorted(AGE_FILES)},
    })
    for name, origin in {
        'provenance/preparation/build_multistore_package.py': Path(__file__),
        'provenance/preparation/build_multistore_test.py': REPO / 'deploy/hosted/build_multistore_test.py',
        'provenance/preparation/build_image_runtime.py': REPO / 'deploy/hosted/build_image_runtime.py',
        'provenance/images/build-evidence.json': HERE / 'image-runtime/c82b92b-build-evidence.json',
        'provenance/images/owner-observation.json': HERE / 'recovery-test/evidence/multistore-inventory-v4-owner-observation.json',
        'provenance/queues/unqualified-candidates.json': HERE / 'recovery-test/evidence/offline-queue-image-candidates-v1.json',
    }.items():
        payload[name] = regular_bytes(origin)
    payload['source-compose.json'] = encoded(native_model())
    payload['destination-compose.json'] = encoded(native_model(destination=True))
    manifest = {
        'schemaVersion': 2, 'kind': KIND, 'target': 'DESKTOP-OS4Q8CP',
        'preparationBase': PREPARATION_BASE, 'productRevision': PRODUCT_REVISION,
        'sourceRevision': PRODUCT_REVISION, 'sourceFileCount': 187,
        'sourceManifestSha256': SOURCE_MANIFEST_SHA,
        'toolingStatus': 'separately-hashed-current-preparation-not-committed-product',
        'toolPins': TOOL_PINS, 'images': image_bindings(),
        'limits': {'fileBytes': MAX_FILE, 'totalBytes': MAX_TOTAL, 'fileCount': MAX_FILES},
        'budget': {'maxSeconds': 5400, 'maxCommands': 500, 'cleanupSeconds': 300, 'cleanupCommands': 160},
        'queueQualification': {'status': 'UNQUALIFIED', 'nativeApplicationExecutionAllowed': False},
        'approval': 'external-original-owner-decision-required-json-is-not-proof',
        'ageTrust': {'publisherEd25519LeafSignatureVerified': True, 'sigsumQuorumVerified': False,
                     'verificationEvidence': 'historical-pinned-report-not-reverified',
                     'linuxExecuted': False, 'windowsHostToolOptional': True},
        'files': {n: sha(b) for n, b in sorted(payload.items())},
        'preparationFiles': {n: sha(b) for n, b in sorted(payload.items()) if not n.startswith('source/')},
    }
    payload[MANIFEST] = encoded(manifest)
    return payload


def check_payload(payload):
    if not payload or len(payload) > MAX_FILES or sum(map(len, payload.values())) > MAX_TOTAL:
        raise ValueError('package limits')
    folds = set()
    for name, data in payload.items():
        member_name(name)
        if name.casefold() in folds or type(data) is not bytes or len(data) > MAX_FILE:
            raise ValueError('package member limits')
        folds.add(name.casefold())


def write_package(payload, output):
    """Exclusive deterministic publication. No destination is ever overwritten."""
    check_payload(payload)
    output = Path(output).absolute()
    # absolute() retains '..'; reject it without resolving linked ancestors.
    if ('..' in output.parts or output == REPO or REPO in output.parents
            or output.exists() or output.is_symlink()):
        raise ValueError('new external destination required')
    for part in output.parents:
        if part.is_symlink() or part.is_junction():
            raise ValueError('linked destination')
    if not output.parent.is_dir():
        raise ValueError('existing output parent required')
    owned = False
    try:
        with output.open('xb') as file:
            owned = True
            with zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(payload.items()):
                    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = (0o100755 if name in ('tools/age', 'tools/age-keygen') else 0o100644) << 16
                    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
        return sha(output.read_bytes())
    except BaseException:
        if owned:
            output.unlink(missing_ok=True)
        raise


def verify(path, repo=REPO, age_directory=AGE_DIR):
    expected = build_payload(repo, age_directory)
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES or sum(e.file_size for e in entries) > MAX_TOTAL:
            raise ValueError('package limits')
        names = set()
        for entry in entries:
            member_name(entry.filename)
            mode = entry.external_attr >> 16 & 0o170000
            if (entry.filename.casefold() in names or entry.is_dir() or mode not in (0, 0o100000)
                    or entry.external_attr & 1040 or entry.flag_bits & 1 or entry.file_size > MAX_FILE):
                raise ValueError('unsafe ZIP member')
            names.add(entry.filename.casefold())
        if set(archive.namelist()) != set(expected):
            raise ValueError('membership rejected')
        for name, data in expected.items():
            if archive.read(name) != data:
                raise ValueError('exact build input rejected')
    return sha(Path(path).read_bytes())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default=str(REPO))
    parser.add_argument('--age-directory', default=str(AGE_DIR))
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        print(verify(args.output, args.repo, args.age_directory) if args.verify_only
              else prepare(args.repo, args.output, args.age_directory))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile):
        print('MULTISTORE_PACKAGE_BLOCKED (raw input not emitted)', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
