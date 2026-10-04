"""Rebuild offline code indexes; no global graph or installed profile mutation."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SCOPES = {'desktop': 'apps/desktop', 'shared': 'apps/shared',
          'gateway': 'tui_gateway', 'agent': 'agent'}


def commands():
    inputs = [f'.degram/index/{name}/graphify-out/graph.json' for name in SCOPES]
    result = [['graphify', 'update', '.', '--no-cluster']]
    for name, source in SCOPES.items():
        result.append(['graphify', 'extract', f'apps/degram/{source}', '--code-only',
                       '--no-cluster', '--out', f'.degram/index/{name}', '--max-workers', '4'])
    result.append(['graphify', 'merge-graphs', *inputs, '--out', '.degram/index/component.json'])
    # Merge raw scoped graphs directly so per-scope source roots remain attributable.
    result.append(['graphify', 'merge-graphs', 'graphify-out/graph.json', *inputs,
                   '--out', '.degram/index/framework.json'])
    return result


def main():
    executable = shutil.which('graphify')
    if not executable:
        raise SystemExit('graphify is not installed; no automatic installation performed')
    for command in commands():
        subprocess.run([executable, *command[1:]], cwd=ROOT, check=True)
    rows = []
    paths = ['graphify-out/graph.json', '.degram/index/component.json',
             '.degram/index/framework.json']
    for name in paths:
        raw = (ROOT / name).read_bytes()
        graph = json.loads(raw)
        if not graph['nodes']:
            raise ValueError(f'Empty code graph: {name}')
        rows.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                     'nodes': len(graph['nodes']), 'edges': len(graph.get('links', []))})
    component_head = subprocess.check_output(
        ['git', '-C', str(ROOT / 'apps/degram'), 'rev-parse', 'HEAD'], text=True).strip()
    report = {'builtAt': datetime.now(timezone.utc).isoformat(),
              'componentHead': component_head, 'componentScope': SCOPES,
              'graphs': rows, 'paidInference': False,
              'limitations': ['Component index covers four selected source areas, not the whole upstream.',
                              'DG graph preserves existing semantic history; docs not semantically refreshed.',
                              'SQL extraction may be incomplete when optional tree_sitter_sql is missing.',
                              'Graph navigation does not prove API/IPC integration or product acceptance.']}
    out = ROOT / '.degram/index/manifest.json'
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
