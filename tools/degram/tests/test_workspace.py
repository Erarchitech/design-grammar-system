"""Offline workspace contracts; fixtures are not product acceptance evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'workspace.py'
SCRATCH = Path.home() / 'AppData/Local/hermes/cache/scratch'


class ContextRoutingTests(unittest.TestCase):
    def test_workspace_verifier_checks_real_gitlink_and_reports_pending_context(self):
        spec = importlib.util.spec_from_file_location('degram_workspace', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, 'verify_workspace'), 'Git workspace verification missing')
        root = MODULE.parents[2]
        report = module.verify_workspace(root)
        self.assertEqual(report['componentHead'], report['gitlinkCommit'])
        self.assertEqual(report['origin'], 'https://github.com/Erarchitech/degram.git')
        self.assertFalse(report['productAccepted'])
        self.assertIn('protected-context-installation', report['pending'])

    def test_rejects_context_escape_and_sensitive_paths_before_read(self):
        spec = importlib.util.spec_from_file_location('degram_workspace', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp)
            (root / 'integration/degram').mkdir(parents=True)
            (root / 'apps/degram').mkdir(parents=True)
            for unsafe in ['../outside.md', '.env', '.secrets/key', 'Publications/draft.md']:
                manifest = {'schemaVersion': 1, 'componentPath': 'apps/degram',
                            'contextFiles': [unsafe], 'componentContextFiles': []}
                (root / 'integration/degram/workspace.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'Unsafe context path'):
                    module.context_report(root)

    def test_context_resolves_both_directions_and_fails_without_framework(self):
        self.assertTrue(MODULE.is_file(), 'workspace context resolver is not implemented')
        spec = importlib.util.spec_from_file_location('degram_workspace', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp)
            child = root / 'apps/degram'
            child.mkdir(parents=True)
            (root / 'integration/degram').mkdir(parents=True)
            manifest = {'schemaVersion': 1, 'componentPath': 'apps/degram',
                        'contextFiles': ['CLAUDE.md', '.planning/STATE.md'],
                        'componentContextFiles': ['AGENTS.md', 'apps/desktop/AGENTS.md']}
            (root / 'integration/degram/workspace.json').write_text(json.dumps(manifest))
            for path in ['CLAUDE.md', '.planning/STATE.md', 'apps/degram/AGENTS.md',
                         'apps/degram/apps/desktop/AGENTS.md']:
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('# ' + path)
            for start in [root, child, child / 'apps/desktop']:
                report = module.context_report(start)
                self.assertEqual(report['frameworkRoot'], str(root.resolve()))
                self.assertEqual(len(report['files']), 4)
                self.assertTrue(all(len(row['sha256']) == 64 for row in report['files']))
            (root / '.planning/STATE.md').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing context'):
                module.context_report(child)
            (root / 'integration/degram/workspace.json').unlink()
            with self.assertRaisesRegex(ValueError, 'Framework workspace not found'):
                module.context_report(child)


if __name__ == '__main__':
    unittest.main()
