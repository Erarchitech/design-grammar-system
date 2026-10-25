"""Pure restore model generation. Never invokes Compose or a daemon."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'recovery_pg_init.py'


class PostgresInitTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(), 'isolated restore-specific PostgreSQL init is absent')
        spec = importlib.util.spec_from_file_location('pginit', MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_virgin_restore_has_only_pgdata_no_app_init_or_public_ports(self):
        m = self.module()
        model = m.restore_model(project='dg-recovery-' + '2' * 32,
                                image='postgres@sha256:' + '3' * 64)
        self.assertEqual(set(model['services']), {'speckle-postgres'})
        pg = model['services']['speckle-postgres']
        self.assertEqual(pg['volumes'], ['pgdata:/var/lib/postgresql/data'])
        self.assertNotIn('ports', pg)
        self.assertNotIn('build', pg)
        self.assertEqual(pg['restart'], 'no')
        self.assertEqual(pg['pull_policy'], 'never')
        self.assertEqual(pg['networks'], ['restore'])
        self.assertEqual(model['networks']['restore'], {'internal': True})
        self.assertNotIn('bootstrap-local.sql', str(model))
        self.assertNotIn('container_name', pg)
        self.assertEqual(pg['environment']['POSTGRES_DB'], 'speckle')
        self.assertEqual(pg['environment']['POSTGRES_USER'], 'speckle')
        self.assertIn('${', pg['environment']['POSTGRES_PASSWORD'])
        self.assertEqual(model['volumes']['pgdata']['labels']['dg.recovery.project'], model['name'])
        for bad in ('postgres:16.4-alpine3.20', 'postgres:latest', 'evil@sha256:' + '3' * 64):
            with self.assertRaises(m.InitError):
                m.restore_model(project=model['name'], image=bad)
        with self.assertRaises(m.InitError):
            m.restore_model(project='owner-stack', image=pg['image'])

    def test_pristine_catalog_admission_requires_exact_version_and_empty_app_state(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'admit_pristine_catalog'), 'restore catalog admission is absent')
        catalog = {'serverVersionNum':160004, 'database':'speckle', 'role':'speckle',
                   'schemas':['public'], 'extensions':['plpgsql'],
                   'userObjects':[], 'otherConnections':0, 'preparedTransactions':0,
                   'databaseOwner':'speckle', 'roleSuperuser':True}
        result = m.admit_pristine_catalog(catalog)
        self.assertIs(result['nativeRecoveryProven'], False)
        self.assertIs(result['readyForRestoreDeclared'], True)
        for key, value in (
            ('serverVersionNum',160005), ('serverVersionNum',True),
            ('database','postgres'), ('role','owner'), ('databaseOwner','owner'),
            ('schemas',['public','app']), ('extensions',['plpgsql','hstore']),
            ('userObjects',['public.some_table']), ('otherConnections',1),
            ('preparedTransactions',1), ('roleSuperuser',False),
            ('otherConnections',False), ('preparedTransactions',False)):
            with self.subTest(key=key, value=value), self.assertRaises(m.InitError):
                m.admit_pristine_catalog(catalog | {key:value})
        for bad in ({}, catalog | {'extra':0}, None):
            with self.assertRaises(m.InitError):
                m.admit_pristine_catalog(bad)


if __name__ == '__main__':
    unittest.main()
