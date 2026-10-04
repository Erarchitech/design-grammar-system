"""Resolve the shared Design Grammars/DeGram development context, without a server."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

MANIFEST = Path('integration/degram/workspace.json')


def safe_path(base, name):
    relative = Path(name)
    forbidden = {'.env', '.secrets', 'publications', 'credentials', 'auth.json'}
    if (relative.is_absolute() or '..' in relative.parts
            or any(p.lower() in forbidden or p.lower().startswith('.env.') for p in relative.parts)):
        raise ValueError(f'Unsafe context path: {name}')
    result = (base / relative).resolve()
    if not result.is_relative_to(base.resolve()):
        raise ValueError(f'Unsafe context path: {name}')
    return result


def context_report(start):
    start = Path(start).resolve()
    root = next((p for p in (start, *start.parents) if (p / MANIFEST).is_file()), None)
    if root is None:
        raise ValueError('Framework workspace not found; open the Design Grammars checkout')
    manifest = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    component = safe_path(root, manifest['componentPath'])
    files = []
    for base, names in [(root, manifest['contextFiles']),
                        (component, manifest['componentContextFiles'])]:
        for name in names:
            path = safe_path(base, name)
            if not path.is_file():
                raise ValueError(f'Missing context: {path}')
            raw = path.read_bytes()
            files.append({'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()})
    return {'frameworkRoot': str(root), 'componentRoot': str(component),
            'planningRoot': str(root / '.planning'),
            'knowledgeRoot': str(root / 'DG_OBSIDIAN'), 'files': files}


def verify_workspace(start):
    report = context_report(start)
    root = Path(report['frameworkRoot'])
    child = Path(report['componentRoot'])
    manifest = json.loads((root / MANIFEST).read_text(encoding='utf-8'))

    def git(cwd, *args):
        return subprocess.check_output(['git', '-C', str(cwd), *args],
                                       text=True, encoding='utf-8').strip()

    head = git(child, 'rev-parse', 'HEAD')
    entry = git(root, 'ls-files', '--stage', '--', manifest['componentPath'])
    fields = entry.split()
    if len(fields) < 4 or fields[0] != '160000' or fields[1] != head:
        raise ValueError('Submodule gitlink does not match the selected component HEAD')
    origin = git(child, 'remote', 'get-url', 'origin')
    upstream = git(child, 'remote', 'get-url', 'upstream')
    if origin != manifest['fork'] or upstream != manifest['upstream']:
        raise ValueError('Unexpected component origin/upstream')
    if (child / '.planning/STATE.md').exists() or (child / 'DG_OBSIDIAN').exists():
        raise ValueError('Competing framework planning/knowledge authority in component')
    report.update(componentHead=head, gitlinkCommit=fields[1], origin=origin,
                  upstream=upstream, productAccepted=False,
                  pending=['protected-context-installation', 'desktop-runtime-isolation',
                           'product-integration-and-acceptance'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['context', 'verify'])
    parser.add_argument('--from', dest='start', default=str(Path.cwd()))
    args = parser.parse_args()
    try:
        action = {'context': context_report, 'verify': verify_workspace}[args.command]
        print(json.dumps(action(args.start), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
