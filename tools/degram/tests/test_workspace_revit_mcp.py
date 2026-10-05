"""Offline fail-closed contracts for the second workspace component (apps/revit-mcp, D-09).

Fixtures are temporary git repositories; they are not product acceptance evidence.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'workspace.py'
SCRATCH = Path.home() / 'AppData/Local/hermes/cache/scratch'

DEGRAM_FORK = 'https://github.com/Erarchitech/degram.git'
DEGRAM_UPSTREAM = 'https://github.com/NousResearch/hermes-agent.git'
REVIT_FORK = 'https://github.com/Erarchitech/revit-mcp-server.git'
REVIT_UPSTREAM = 'https://github.com/Demolinator/revit-mcp-server.git'


def load_module():
    spec = importlib.util.spec_from_file_location('degram_workspace', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_git(cwd, *args):
    return subprocess.check_output(
        ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
         '-C', str(cwd), *args], text=True, encoding='utf-8').strip()


def make_child(path, origin, upstream):
    path.mkdir(parents=True)
    run_git(path, 'init', '-q')
    (path / 'README.md').write_text('child\n')
    run_git(path, 'add', 'README.md')
    run_git(path, 'commit', '-q', '-m', 'init')
    run_git(path, 'remote', 'add', 'origin', origin)
    run_git(path, 'remote', 'add', 'upstream', upstream)
    return run_git(path, 'rev-parse', 'HEAD')


def register_gitlink(root, rel, sha):
    run_git(root, 'update-index', '--add', '--cacheinfo', f'160000,{sha},{rel}')


def make_workspace(temp, with_revit=True):
    """Framework repo with apps/degram and (optionally) apps/revit-mcp registered as gitlinks."""
    root = Path(temp)
    run_git(root, 'init', '-q')
    (root / 'integration/degram').mkdir(parents=True)
    manifest = {'schemaVersion': 1, 'componentPath': 'apps/degram',
                'upstream': DEGRAM_UPSTREAM, 'fork': DEGRAM_FORK,
                'contextFiles': [], 'componentContextFiles': []}
    if with_revit:
        manifest['additionalComponents'] = [{
            'name': 'revit-mcp', 'componentPath': 'apps/revit-mcp',
            'fork': REVIT_FORK, 'upstream': REVIT_UPSTREAM,
            'upstreamBaseCommit': '0' * 40, 'license': 'MIT'}]
    (root / 'integration/degram/workspace.json').write_text(json.dumps(manifest))
    degram = make_child(root / 'apps/degram', DEGRAM_FORK, DEGRAM_UPSTREAM)
    register_gitlink(root, 'apps/degram', degram)
    revit = None
    if with_revit:
        revit = make_child(root / 'apps/revit-mcp', REVIT_FORK, REVIT_UPSTREAM)
        register_gitlink(root, 'apps/revit-mcp', revit)
    return root, revit


class RevitMcpComponentTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.module = load_module()

    def test_verify_ok_and_lists_both_components(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root, revit = make_workspace(temp)
            report = self.module.verify_workspace(root)
            self.assertEqual(report['origin'], DEGRAM_FORK)  # apps/degram contract unchanged
            names = [c['name'] for c in report['components']]
            self.assertEqual(names, ['degram', 'revit-mcp'])
            row = next(c for c in report['components'] if c['name'] == 'revit-mcp')
            self.assertEqual(row['componentHead'], revit)
            self.assertEqual(row['gitlinkCommit'], revit)
            self.assertEqual(row['origin'], REVIT_FORK)
            self.assertEqual(row['upstream'], REVIT_UPSTREAM)

    def test_manifest_without_additional_components_still_verifies(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root, _ = make_workspace(temp, with_revit=False)
            report = self.module.verify_workspace(root)
            self.assertEqual([c['name'] for c in report['components']], ['degram'])

    def test_fails_when_gitlink_differs_from_child_head(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root, _ = make_workspace(temp)
            child = root / 'apps/revit-mcp'
            (child / 'more.txt').write_text('x\n')
            run_git(child, 'add', 'more.txt')
            run_git(child, 'commit', '-q', '-m', 'drift')
            with self.assertRaisesRegex(ValueError, r'revit-mcp.*gitlink'):
                self.module.verify_workspace(root)

    def test_fails_on_wrong_origin_or_upstream(self):
        for remote, bad in [('origin', 'https://example.invalid/other.git'),
                            ('upstream', 'https://github.com/someone/else.git')]:
            with self.subTest(remote=remote), \
                    tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
                root, _ = make_workspace(temp)
                run_git(root / 'apps/revit-mcp', 'remote', 'set-url', remote, bad)
                with self.assertRaisesRegex(ValueError, r'revit-mcp.*origin/upstream'):
                    self.module.verify_workspace(root)

    def test_fails_on_missing_upstream_remote(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root, _ = make_workspace(temp)
            run_git(root / 'apps/revit-mcp', 'remote', 'remove', 'upstream')
            with self.assertRaises(ValueError):
                self.module.verify_workspace(root)

    def test_fails_on_competing_planning_authority(self):
        for rel in ['.planning/STATE.md', '.planning/ROADMAP.md', 'ROADMAP.md',
                    'DG_OBSIDIAN']:
            with self.subTest(rel=rel), \
                    tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
                root, _ = make_workspace(temp)
                target = root / 'apps/revit-mcp' / rel
                if rel == 'DG_OBSIDIAN':
                    target.mkdir(parents=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('x\n')
                with self.assertRaisesRegex(ValueError, r'revit-mcp.*Competing'):
                    self.module.verify_workspace(root)

    def test_fails_when_component_path_is_not_registered_gitlink(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root, _ = make_workspace(temp)
            run_git(root, 'update-index', '--force-remove', 'apps/revit-mcp')
            with self.assertRaisesRegex(ValueError, r'revit-mcp.*gitlink'):
                self.module.verify_workspace(root)

    def test_rejects_unsafe_additional_component_path(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root, _ = make_workspace(temp)
            path = root / 'integration/degram/workspace.json'
            manifest = json.loads(path.read_text())
            manifest['additionalComponents'][0]['componentPath'] = '../outside'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Unsafe context path'):
                self.module.verify_workspace(root)

    def test_repository_manifest_registers_revit_mcp(self):
        root = MODULE.parents[2]
        manifest = json.loads((root / 'integration/degram/workspace.json').read_text())
        self.assertEqual(manifest['schemaVersion'], 1)
        self.assertEqual(manifest['componentPath'], 'apps/degram')
        entries = {c['name']: c for c in manifest['additionalComponents']}
        entry = entries['revit-mcp']
        self.assertEqual(entry['componentPath'], 'apps/revit-mcp')
        self.assertEqual(entry['fork'], REVIT_FORK)
        self.assertEqual(entry['upstream'], REVIT_UPSTREAM)
        self.assertRegex(entry['upstreamBaseCommit'], r'^74a8ddca[0-9a-f]{32}$')
        self.assertEqual(entry['license'], 'MIT')


if __name__ == '__main__':
    unittest.main()
