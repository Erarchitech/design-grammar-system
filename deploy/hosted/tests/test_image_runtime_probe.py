"""Container HTTP probe contract using explicit offline response fixtures."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('image_runtime_probe', Path(__file__).resolve().parents[1] / 'image-runtime/probe.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def responses(self, url):
        # Synthetic protocol fixtures, not live application evidence.
        path = url.split('://', 1)[1]
        if path == 'dg-reasoner:8000/health':
            return 200, b'{"status":"ok","neo4j":"up"}', {}
        if path == '127.0.0.1:8000/auth/options':
            return 200, b'{"selfRegistration":false}', {}
        if path == 'design-grammars/':
            return 200, b'<script src="/assets/index.js"></script><link href="/assets/index.css">', {'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY'}
        if path in ('design-grammars/assets/index.js', 'design-grammars/assets/index.css'):
            return 200, b'explicit non-HTML static fixture', {}
        if path == 'design-grammars/config.js':
            return 200, b'dataServiceUrl: "/data-service", speckleBaseUrl: "http://127.0.0.1:9"', {}
        if path in ('design-grammars/neo4j', 'design-grammars/n8n'):
            return 404, b'', {}
        raise AssertionError('unexpected URL ' + url)

    def test_positive_all_fixed_checks(self):
        capability = types.SimpleNamespace(run=lambda: {'admin_login': True, 'csrf_denied': True,
                   'ingest_inserted': 1, 'neo4j_scoped_notes': 1, 'denied_paths': 4})
        with patch.object(probe, 'fetch', self.responses), patch.dict(sys.modules, {'sandbox_probe': capability}):
            result = probe.run()
        self.assertEqual(result['uiAssets'], 2)
        self.assertTrue(result['reasonerNeo4jUp'])
        self.assertTrue(result['uiHeaders'])
        self.assertEqual(capability.BASE, 'http://design-grammars/data-service')

    def test_health_200_with_database_down_is_not_ready(self):
        with patch.object(probe, 'fetch', return_value=(200, b'{"status":"ok","neo4j":"down"}', {})):
            with self.assertRaisesRegex(RuntimeError, 'reasoner not ready'):
                probe.ready()

    def test_missing_false_or_true_registration_is_not_ready(self):
        for payload in ({}, {'selfRegistration': True}, {'selfRegistration': 0}):
            def bad(url):
                return (200, json.dumps(payload).encode(), {}) if url.endswith('/auth/options') else self.responses(url)
            with patch.object(probe, 'fetch', bad):
                with self.assertRaisesRegex(RuntimeError, 'API not ready'):
                    probe.ready()

    def test_asset_html_fallback_fails(self):
        def bad(url):
            return (200, b'<!doctype html>fallback', {}) if '/assets/' in url else self.responses(url)
        with patch.object(probe, 'fetch', bad), patch.dict(sys.modules, {'sandbox_probe': types.SimpleNamespace(run=lambda: {})}):
            with self.assertRaisesRegex(RuntimeError, 'UI asset unavailable'):
                probe.run()

    def test_proxy_tombstone_spa_fallback_fails(self):
        def bad(url):
            return (200, b'fallback', {}) if url.endswith('/neo4j') else self.responses(url)
        with patch.object(probe, 'fetch', bad), patch.dict(sys.modules, {'sandbox_probe': types.SimpleNamespace(run=lambda: {})}):
            with self.assertRaisesRegex(RuntimeError, 'proxy tombstone invalid'):
                probe.run()


if __name__ == '__main__':
    unittest.main()
