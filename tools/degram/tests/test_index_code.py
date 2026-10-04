"""Assert graph rebuild uses only offline, framework-local commands."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'index_code.py'


class IndexCommandsTests(unittest.TestCase):
    def test_scoped_code_extraction_and_local_merge(self):
        self.assertTrue(SCRIPT.is_file(), 'repeatable indexing entry point missing')
        spec = importlib.util.spec_from_file_location('index_code', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        commands = module.commands()
        extracts = [cmd for cmd in commands if cmd[1] == 'extract']
        self.assertEqual(len(extracts), 4)
        for cmd in extracts:
            self.assertIn('--code-only', cmd)
            self.assertIn('--no-cluster', cmd)
            self.assertIn('--out', cmd)
        self.assertEqual(commands[-1][1], 'merge-graphs')
        self.assertEqual(commands[-1][-1], '.degram/index/framework.json')
        self.assertFalse(any('global' in cmd for cmd in commands))


if __name__ == '__main__':
    unittest.main()
