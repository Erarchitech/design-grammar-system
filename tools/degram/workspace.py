"""Resolve the shared Design Grammars/DeGram development context, without a server."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

MANIFEST = Path('integration/degram/workspace.json')
CONTEXT_TEMPLATE = Path('integration/degram/component-context.md')
CONTEXT_NAME = '.hermes.md'
EXCLUDE_RULE = '/.hermes.md'


def git(cwd, *args):
    return subprocess.check_output(['git', '-C', str(cwd), *args],
                                   text=True, encoding='utf-8').strip()


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
    installed = component_context_installed(root)
    pending = ['desktop-runtime-isolation', 'product-integration-and-acceptance']
    if not installed:
        pending.insert(0, 'protected-context-installation')
    report.update(componentHead=head, gitlinkCommit=fields[1], origin=origin,
                  upstream=upstream, productAccepted=False,
                  componentContextInstalled=installed, pending=pending)
    return report


def component_context_installed(start):
    """True only when the child .hermes.md is byte-identical to the framework template."""
    report = context_report(start)
    target = Path(report['componentRoot']) / CONTEXT_NAME
    template = Path(report['frameworkRoot']) / CONTEXT_TEMPLATE
    return (target.is_file() and template.is_file()
            and target.read_bytes() == template.read_bytes())


def install_context(start):
    """Generate the child .hermes.md from the framework template; keep it out of the fork."""
    report = context_report(start)
    root, child = Path(report['frameworkRoot']), Path(report['componentRoot'])
    target = child / CONTEXT_NAME
    if subprocess.run(['git', '-C', str(child), 'ls-files', '--error-unmatch', CONTEXT_NAME],
                      capture_output=True).returncode == 0:
        raise ValueError(f'{CONTEXT_NAME} is tracked by the component; refusing to overwrite')
    raw = (root / CONTEXT_TEMPLATE).read_bytes()
    target.write_bytes(raw)
    exclude = Path(git(child, 'rev-parse', '--path-format=absolute', '--git-path', 'info/exclude'))
    lines = exclude.read_text(encoding='utf-8').splitlines() if exclude.is_file() else []
    if EXCLUDE_RULE not in lines:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        lines += ['# Generated framework routing context (tools/degram/workspace.py).', EXCLUDE_RULE]
        exclude.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'installed': str(target), 'sha256': hashlib.sha256(raw).hexdigest(),
            'template': str(root / CONTEXT_TEMPLATE), 'exclude': str(exclude)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['context', 'verify', 'install-context'])
    parser.add_argument('--from', dest='start', default=str(Path.cwd()))
    args = parser.parse_args()
    try:
        action = {'context': context_report, 'verify': verify_workspace,
                  'install-context': install_context}[args.command]
        print(json.dumps(action(args.start), ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
