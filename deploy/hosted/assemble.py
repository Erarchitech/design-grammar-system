"""Create a clean, allowlisted hosted candidate from an exact git commit.

This produces a BLOCKED candidate, never an immutable release: real registry
image digests and a pinned effective Compose model must be supplied separately.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

from release_core import SHA, digest, matches, pattern, safe_path, scan_tree


def assemble(repo, revision, allowlist_file, output):
    if not SHA.fullmatch(revision):
        raise ValueError('exact framework commit required')
    repo, output = Path(repo).resolve(), Path(output).absolute()
    policy_path = Path(allowlist_file).resolve()
    try:
        policy_relative = policy_path.relative_to(repo).as_posix()
    except ValueError:
        policy_relative = None
    if output.exists() or output.is_symlink():
        raise ValueError('output already exists')
    # Refuse to generate inside the source checkout, even in an ignored dir.
    if output == repo or repo in output.parents:
        raise ValueError('output must be outside the source repository')
    actual = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--verify', revision + '^{commit}'],
                                     stderr=subprocess.DEVNULL, text=True).strip()
    if actual != revision:
        raise ValueError('revision did not resolve to exact commit')
    config = json.loads(Path(allowlist_file).read_text(encoding='utf-8'))
    if config.get('schemaVersion') != 1 or not isinstance(config.get('inputs'), list) or not config['inputs']:
        raise ValueError('invalid allowlist')
    if not isinstance(config.get('includeDegram'), bool):
        raise ValueError('component inclusion policy required')
    if policy_relative == 'deploy/hosted/release-allowlist.json' and not any(
        isinstance(entry, dict) and entry.get('path') == policy_relative for entry in config['inputs']
    ):
        raise ValueError('release policy must include itself')
    # Release policy belongs to the exact commit, not this dirty checkout.
    if policy_relative == 'deploy/hosted/release-allowlist.json':
        try:
            committed_policy = subprocess.check_output(['git', '-C', str(repo), 'show', f'{revision}:{policy_relative}'],
                                                        stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            raise ValueError('selection policy absent from exact commit') from None
        if committed_policy.replace(b'\r\n', b'\n') != policy_path.read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('selection policy differs from exact commit')
        # Interpret only the committed blob, never checkout-converted policy
        # bytes. The selected policy exported below remains byte-exact.
        config = json.loads(committed_policy)
    if config.get('includeDegram') is True:
        raise ValueError('component-bearing bundle requires separate approved child artifact allowlist')
    forbidden = config.get('forbiddenComponents', [])
    if not isinstance(forbidden, list) or any(not isinstance(x, str) for x in forbidden):
        raise ValueError('invalid forbidden components')
    entries = config['inputs']
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('purpose'), str) or not entry['purpose']:
            raise ValueError('unexplained allowlist input')
        if set(entry) - {'path', 'purpose', 'exclude'}:
            raise ValueError('unsupported allowlist input field')
        pattern(entry['path'], forbidden)
        excludes = entry.get('exclude', [])
        if not isinstance(excludes, list):
            raise ValueError('invalid exclusion list')
        for exclusion in excludes:
            pattern(exclusion, forbidden)
    # ls-tree enumerates names/modes only. Archive ONLY approved paths; neither
    # checkout nor archive of unrelated vault/publication bytes is ever read.
    tree = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-rz', '--full-tree', revision])
    tracked = {}
    for row in tree.split(b'\0'):
        if not row:
            continue
        header, raw = row.split(b'\t', 1)
        name = raw.decode('utf-8', 'strict')
        try:
            safe_path(name, forbidden)
        except ValueError:
            if any(matches(name, entry['path']) for entry in entries):
                raise ValueError('unsafe selected source path')
            continue
        tracked[name] = header.split()[0].decode('ascii')
    # Enumerate commit entries by metadata before archiving only selected blobs.
    selected = set()
    for entry in entries:
        glob = entry['path']
        hits = [p for p in tracked if matches(p, glob)]
        if not hits:
            raise ValueError('allowlist input unmatched')
        excluded = set()
        for exclusion in entry.get('exclude', []):
            excluded.update(p for p in hits if matches(p, exclusion))
        for name in hits:
            if name in excluded:
                continue
            if tracked[name] not in ('100644', '100755'):
                raise ValueError('link or unsupported selected source')
            if (glob.startswith('ui-v2/src/') and
                    not name.endswith(('.jsx', '.js', '.css', '.woff2')) and
                    not (glob == name == 'ui-v2/src/styles/tokens/fonts/alnst-400-normal.ttf')):
                raise ValueError('unknown UI source suffix')
            selected.add(name)
    if not selected:
        raise ValueError('empty bundle')
    if policy_relative != 'deploy/hosted/release-allowlist.json' and any(
        name.endswith('/release-allowlist.json') for name in selected
    ):
        raise ValueError('external policy cannot supersede bundled policy')
    folds = [name.casefold() for name in selected]
    if len(set(folds)) != len(folds):
        raise ValueError('selected case-fold collision')
    # Export committed blob bytes, not checkout-filtered CRLF on Windows.
    archive = subprocess.run(['git', '-C', str(repo), '-c', 'core.autocrlf=input',
                              'archive', '--format=tar', revision,
                              '--', *sorted(selected)], capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory(prefix='dg-hosted-clean-export-') as scratch:
        clean = Path(scratch) / 'export'
        clean.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            seen = set()
            for member in tar:
                value = member.name.removesuffix('/')
                if member.isdir():
                    continue
                if value not in selected or not member.isfile() or value in seen:
                    raise ValueError('unexpected archive entry')
                seen.add(value)
                destination = clean / value
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, destination.open('wb') as target:
                    shutil.copyfileobj(source, target)
            if seen != selected:
                raise ValueError('missing archive input')
        files = scan_tree(clean)
        if set(files) != set(selected):
            raise ValueError('unexpected export output')
        # Gitlink is metadata only; no component source is copied.
        gitlink = subprocess.run(['git', '-C', str(repo), 'ls-tree', revision, 'apps/degram'],
                                 capture_output=True, text=True, check=True).stdout.strip()
        if gitlink:
            fields = gitlink.split(None, 3)
            if len(fields) != 4 or fields[0:2] != ['160000', 'commit'] or not SHA.fullmatch(fields[2]):
                raise ValueError('invalid component gitlink')
        if config.get('includeDegram') not in (None, False):
            raise ValueError('invalid component inclusion policy')
        manifest = {'schemaVersion': 1, 'status': 'BLOCKED', 'frameworkRevision': revision,
                    'degramGitlink': None, 'files': files, 'images': {},
                    'unresolved': ['Real image digests for every service and pinned merged Compose model']}
        (clean / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        output.parent.mkdir(parents=True, exist_ok=True)
        # Same-volume rename from temp sibling, no partially exposed bundle.
        staging = Path(tempfile.mkdtemp(prefix='.dg-hosted-staging-', dir=output.parent))
        try:
            shutil.rmtree(staging)
            shutil.copytree(clean, staging)
            staging.rename(output)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--allowlist', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        count = assemble(args.repo, args.revision, args.allowlist, args.output)
        print(f'BLOCKED candidate: {count} hashed files; no image provenance')
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError, KeyError, TypeError) as error:
        print(f'ASSEMBLY BLOCKED: {type(error).__name__}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
