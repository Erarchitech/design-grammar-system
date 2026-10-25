"""Full isolated native model contracts; no Docker invocation."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
MODULE = HERE / 'build_multistore_test.py'


class ModelTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(), 'full multi-store package builder absent')
        sys.path.insert(0, str(HERE));self.addCleanup(lambda: sys.path.remove(str(HERE)))
        spec = importlib.util.spec_from_file_location('full_multistore_builder', MODULE)
        m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

    def test_all_application_workers_stores_and_maintenance_roles_are_explicit(self):
        m = self.module()
        model = m.native_model()
        expected = {'neo4j','dg-reasoner','data-service','design-grammars','n8n',
                    'speckle-postgres','speckle-redis','speckle-minio','speckle-server',
                    'speckle-frontend-2','speckle-preview-service','speckle-webhook-service',
                    'speckle-ifc-import-service','speckle-ingress','graph-admin','snapshot','n8n-admin'}
        self.assertEqual(set(model['services']), expected)
        self.assertEqual(model['networks'], {'sandbox': {'internal': True, 'enable_ipv6': False}})
        self.assertEqual(set(model['volumes']), {'graph','graph_logs','api_state','postgres_state','object_state','redis_state','n8n_state','n8n_evidence','exchange'})
        self.assertNotIn('ollama', model['services'])

    def test_every_service_is_exact_id_no_build_no_ports_no_restart_no_host_data(self):
        m = self.module();model = m.native_model()
        for name, service in model['services'].items():
            self.assertRegex(service['image'], '^sha256:[0-9a-f]{64}$', name)
            self.assertEqual(service['pull_policy'], 'never')
            self.assertEqual(service['restart'], 'no')
            self.assertEqual(service['platform'], 'linux/amd64')
            for forbidden in ('build','container_name','ports','extra_hosts','devices','privileged','volumes_from','env_file'):
                self.assertNotIn(forbidden, service, (name,forbidden))
            self.assertLessEqual(service['cpus'], 1)
            self.assertLessEqual(service['pids_limit'], 256)
            for mount in service.get('volumes', []):
                if mount['type'] == 'bind':
                    self.assertTrue(mount['read_only'])
                    self.assertTrue(mount['source'] in ('./support','./tools') or
                                    mount['source'].startswith(('./source/','./support/','./tools/')))
                    self.assertNotIn('bootstrap-local.sql', mount['source'])
                    self.assertNotIn('/var/run/docker.sock', mount['target'])
                else:
                    self.assertIn(mount['source'], model['volumes'])

    def test_snapshot_carries_synthetic_s3_recovery_env_bound_to_each_sides_bucket(self):
        m = self.module()
        for destination, bucket in ((False, 'speckle-source'), (True, 'speckle-destination')):
            model = m.native_model(destination=destination)
            env = model['services']['snapshot']['environment']
            self.assertEqual(env['RECOVERY_S3_ENDPOINT'], 'http://speckle-minio:9000')
            self.assertEqual(env['RECOVERY_S3_BUCKET'], bucket)
            self.assertEqual(env['RECOVERY_S3_ACCESS_KEY'], '${MINIO_ROOT_USER:?required}')
            self.assertEqual(env['RECOVERY_S3_SECRET_KEY'], '${MINIO_ROOT_PASSWORD:?required}')
            self.assertEqual(env['RECOVERY_S3_ALLOW_HTTP'], '1')
            self.assertNotIn('RECOVERY_S3_SESSION_TOKEN', env)
            # Same bucket the Speckle server of this side is configured with.
            self.assertEqual(model['services']['speckle-server']['environment']['S3_BUCKET'], bucket)
            # The pre-existing snapshot variables are unchanged.
            for name in ('MINIO_ROOT_USER', 'MINIO_ROOT_PASSWORD', 'N8N_ENCRYPTION_KEY'):
                self.assertIn(name, env)

    def test_restore_model_keeps_stopped_source_tree_readonly_and_destination_explicit(self):
        m = self.module()
        source, destination = m.native_model(), m.native_model(destination=True)
        for model, readonly in ((source,True),(destination,False)):
            mounts = {v['target']:v for v in model['services']['snapshot']['volumes']}
            self.assertEqual(mounts['/state']['read_only'],readonly)
            self.assertEqual(mounts['/n8n-state']['read_only'],readonly)
            self.assertEqual(mounts['/state']['source'],'api_state')
            self.assertEqual(mounts['/n8n-state']['source'],'n8n_state')
        pg = destination['services']['speckle-postgres']
        self.assertEqual(pg['environment']['POSTGRES_DB'],'speckle')
        self.assertFalse(any('/docker-entrypoint-initdb.d/' in x['target'] for x in pg['volumes']))

    def test_synthetic_database_connections_and_bucket_mapping_are_executable(self):
        m = self.module()
        for destination in (False, True):
            model = m.native_model(destination=destination)
            server = model['services']['speckle-server']['environment']
            worker = model['services']['speckle-webhook-service']['environment']
            importer = model['services']['speckle-ifc-import-service']['environment']
            expected = 'postgresql://speckle:${POSTGRES_PASSWORD:?required}@speckle-postgres/speckle'
            self.assertEqual(server['FILEIMPORT_QUEUE_POSTGRES_URL'], expected)
            self.assertEqual(worker['PG_CONNECTION_STRING'], expected)
            self.assertEqual(importer['FILEIMPORT_QUEUE_POSTGRES_URL'], expected)
            self.assertEqual(server['S3_BUCKET'], 'speckle-destination' if destination else 'speckle-source')
            self.assertNotIn('***', json.dumps(model))

    def test_native_n8n_restore_uses_absent_child_and_matching_native_folder(self):
        m = self.module()
        for destination in (False, True):
            model = m.native_model(destination=destination)
            for role in ('n8n', 'n8n-admin'):
                service = model['services'][role]
                mounts = {item['target']: item for item in service['volumes']}
                self.assertNotIn('/home/node/.n8n', mounts)
                self.assertEqual(mounts['/n8n-state']['source'], 'n8n_state')
                self.assertEqual(service['environment']['N8N_USER_FOLDER'], '/n8n-state')
                self.assertEqual(service['environment']['N8N_BINARY_DATA_STORAGE_PATH'], '/n8n-state/.n8n/binaryData')
                self.assertEqual(service['environment']['DB_SQLITE_DATABASE'], 'database.sqlite')
                self.assertEqual(service['environment']['DB_TABLE_PREFIX'], '')
                self.assertEqual(service['environment']['N8N_COMMUNITY_PACKAGES_ENABLED'], 'false')
                self.assertEqual(service['environment']['N8N_ENCRYPTION_KEY_FILE'], '/exchange/keys/n8n.key')
                self.assertNotIn('N8N_ENCRYPTION_KEY', service['environment'])
                self.assertIn('/exchange', mounts)

    def test_tool_and_image_pins_come_from_distinct_saved_observations(self):
        m = self.module();pins=m.image_bindings()
        controlled=json.loads((HERE/'image-runtime/c82b92b-build-evidence.json').read_bytes())
        observed=json.loads((HERE/'recovery-test/evidence/multistore-inventory-v4-owner-observation.json').read_bytes())
        for role in ('neo4j','dg-reasoner','data-service','design-grammars'):
            self.assertEqual(pins[role]['configId'],controlled['images'][role]['imageId'])
            self.assertEqual(pins[role]['sourceRevision'],controlled['sourceRevision'])
            self.assertIs(pins[role]['registryVerified'],False)
        for role in ('n8n','speckle-postgres','speckle-redis','speckle-minio'):
            record=pins[role]
            source=next(i for i in observed['images'] if i['reference']==record['reference'])
            self.assertEqual(record['configId'],source['configId'])
            self.assertEqual(record['returnedRepoDigests'],source['repoDigests'])
            self.assertIsNone(record['sourceRevision'])
        self.assertEqual(m.TOOL_PINS, {'dockerSha256': observed['tools']['dockerExecutableSha256'],
                                     'composeSha256': observed['tools']['composePluginSha256']})

    def test_six_published_source_images_replace_observed_speckle_generation(self):
        m = self.module()
        expected = {
            'speckle-server': ('053e65b84e5e074f3c094cf31e820af2b5dbae07f8dd97ec3f7504351f1fdbd6', 'eb140b404ac28b285ff768c285cba3cc448c631ff79da87d29026e5ecb6371e9'),
            'speckle-frontend-2': ('07bcf9cc3a38757e215017c038f61885877c744cb9cc34523a02e6e9f3e3181b', 'c51ac7bf6a08e6778d0879a88ad8ff902ae31ff0ebb1a8941a9ece357b91cbba'),
            'speckle-preview-service': ('329450023d4e06ff1c7547184a20fa2ee0d743a4e19a03c8dfda3dc2bcd3a39a', 'c6683615c3dc3e53a9ae05fd5ad93e6afd60944a76e6e0987e1ba53f5cd3d101'),
            'speckle-webhook-service': ('bc1d82729d79f235d54ee46b65b5fdca5eb577c05cd8856fa3d507838c38ee65', 'bea699343e362280b02eaf8e82e5477285ca4ebe6c32a04952d5fc069ac2aa7a'),
            'speckle-ingress': ('5068af7fbf797cc2e7a3d8667fe6107b63777092ac942ddfcf9ac93864387708', 'f034903a0bd1903a417ac6c217e5bf820d24a23caae2f9f8efb5239cc2979ecb'),
            'speckle-ifc-import-service': ('160f70c3cbc5eac375cb1a2bd3dfcb5b29e7d0a7258367db774feaaa8f7c42af', '874b7a43fc24ad011e058fe4d3e05b9d5dbe3c4430b51a0407f3eb81621df4bb'),
        }
        pins = m.image_bindings()
        binding = json.loads((HERE/'recovery-test/speckle-source-binding.json').read_bytes())
        self.assertEqual(set(binding['services']), set(expected))
        self.assertEqual(binding['sourceCommit'], '51d43b91c4681a75bff8b285da7f443a4599da67')
        self.assertEqual(binding['sourceArchiveSha256'], '2c178d568a5cc04a6000d0fc61c5488639c3ea61ce518528f47d634f446e73ba')
        for role, (config, manifest) in expected.items():
            self.assertNotIn(role, m.THIRD_PARTIES)
            self.assertEqual(pins[role]['configId'], 'sha256:'+config)
            self.assertTrue(pins[role]['reference'].endswith('@sha256:'+manifest))
            self.assertEqual(pins[role]['sourceRevision'], binding['sourceCommit'])
            for flag in ('authenticatedProvenance','localCacheVerified','runtimeQualified'):
                self.assertIs(pins[role][flag], False)
            for destination in (False, True):
                self.assertEqual(m.native_model(destination=destination)['services'][role]['image'], 'sha256:'+config)

    def test_source_binding_rejects_schema_type_hash_role_and_trust_mutations(self):
        m = self.module()
        self.assertTrue(callable(getattr(m, 'validate_source_binding', None)))
        good = json.loads((HERE/'recovery-test/speckle-source-binding.json').read_bytes())
        self.assertEqual(m.validate_source_binding(good), good)
        mutations = []
        for key, value in [('extra', None), ('runtimeAdmissible', True), ('runtimeQualified', 0),
                           ('sourceCommit', 'a'*40), ('sourceArchiveSha256', 'G'*64), ('services', [])]:
            item = copy.deepcopy(good); item[key] = value; mutations.append(item)
        for key, value in [('dockerfileSha256', '0'*63), ('configDigest', 1), ('platform', 'linux/arm64'),
                           ('sourceCommit', 'a'*40), ('publishedImage', 'speckle/speckle-server:latest'),
                           ('manifestDigest', 'sha256:'+'0'*64), ('authenticatedProvenance', 0),
                           ('unsignedSourceClaimMatches', 1), ('dockerfile', '../Dockerfile'), ('extra', True)]:
            item = copy.deepcopy(good); item['services']['speckle-server'][key] = value; mutations.append(item)
        item = copy.deepcopy(good); del item['services']['speckle-ifc-import-service']; mutations.append(item)
        item = copy.deepcopy(good); item['services']['speckle-fileimport-service'] = item['services'].pop('speckle-ifc-import-service'); mutations.append(item)
        for item in mutations:
            with self.subTest(item=item), self.assertRaises(ValueError):
                m.validate_source_binding(item)

    def test_ifc_flags_queue_and_bounded_ephemeral_paths_follow_source(self):
        m = self.module()
        for destination in (False, True):
            services = m.native_model(destination=destination)['services']
            env = services['speckle-server']['environment']
            self.assertEqual(env['DISABLE_FILE_UPLOADS'], 'false')
            self.assertEqual(env['FF_NEXT_GEN_FILE_IMPORTER_ENABLED'], 'true')
            for flag in ('FF_LEGACY_FILE_IMPORTS_ENABLED', 'FF_RHINO_FILE_IMPORTER_ENABLED',
                         'FF_WORKSPACES_MULTI_REGION_ENABLED', 'FF_AUTOMATE_MODULE_ENABLED',
                         'FF_GENDOAI_MODULE_ENABLED', 'FF_WORKSPACES_MODULE_ENABLED',
                         'FF_ACC_INTEGRATION_ENABLED', 'FF_RETRY_ERRORED_PREVIEWS_ENABLED'):
                self.assertEqual(env[flag], 'false')
            front = services['speckle-frontend-2']['environment']
            self.assertEqual(front['NUXT_PUBLIC_FF_LEGACY_FILE_IMPORTS_ENABLED'], 'false')
            self.assertEqual(front['NUXT_PUBLIC_FF_NEXT_GEN_FILE_IMPORTER_ENABLED'], 'true')
            self.assertNotIn('FILEIMPORT_SERVICE_REDIS_URL', env)
            importer = services['speckle-ifc-import-service']
            self.assertEqual(set(importer['environment']), {'FILEIMPORT_QUEUE_POSTGRES_URL'})
            self.assertEqual(importer['working_dir'], '/app')
            self.assertNotIn('entrypoint', importer)
            for role in ('speckle-server', 'speckle-preview-service', 'speckle-webhook-service', 'speckle-ifc-import-service'):
                self.assertEqual(services[role]['tmpfs'], ['/tmp:rw,nosuid,nodev,size=268435456,mode=1777'])
            preview = services['speckle-preview-service']
            self.assertIs(preview['read_only'], False)  # Chromium rootfs qualification is pending.
            self.assertEqual(preview['environment']['USER_DATA_DIR'], '/tmp/puppeteer')
            self.assertEqual(preview['environment']['GPU_ENABLED'], 'false')
            self.assertEqual(env['REDIS_URL'], 'redis://speckle-redis:6379/0')
            self.assertEqual(env['PREVIEW_SERVICE_REDIS_URL'], env['REDIS_URL'])
            self.assertEqual(front['NUXT_REDIS_URL'], env['REDIS_URL'])
            self.assertEqual(preview['environment']['REDIS_URL'], env['REDIS_URL'])

    def test_binding_bytes_are_immutable_and_changed_valid_hashes_are_rejected(self):
        m = self.module()
        self.assertTrue(callable(getattr(m, 'parse_source_binding', None)))
        data = (HERE/'recovery-test/speckle-source-binding.json').read_bytes()
        self.assertEqual(m.parse_source_binding(data), json.loads(data))
        altered = json.loads(data)
        altered['services']['speckle-ifc-import-service']['configDigest'] = 'sha256:'+'a'*64
        for bad in (json.dumps(altered).encode(), data+b'\n', data.decode(), None):
            with self.assertRaises(ValueError):
                m.parse_source_binding(bad)

    def test_clean_current_candidate_matches_controlled_product_bytes(self):
        m=self.module()
        import tempfile
        from assemble import assemble
        scratch=Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')
        repo=HERE.parents[1]
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            destination=Path(tmp)/'candidate'
            assemble(repo,m.PREPARATION_BASE,repo/'deploy/hosted/release-allowlist.json',destination)
            manifest=json.loads((destination/'manifest.json').read_bytes())
            source={name:(destination/name).read_bytes() for name in manifest['files']}
            self.assertEqual(m.verify_product_source(repo,m.PRODUCT_REVISION,source),len(source))
            self.assertEqual(len(source),187)
            self.assertEqual(manifest['frameworkRevision'],m.PREPARATION_BASE)
            self.assertNotIn('DG_OBSIDIAN',source)

    def test_manifest_must_not_accept_rehashed_changed_source_as_exact_revision(self):
        m=self.module()
        self.assertTrue(callable(m.verify_product_source), 'exact-commit source verification missing')
        # Repository Git objects are read-only; no checkout mutation is needed.
        blob = m.read_product_blob(HERE.parents[1], m.PRODUCT_REVISION, 'data-service/Dockerfile')
        self.assertTrue(blob)
        self.assertEqual(m.verify_product_source(HERE.parents[1],m.PRODUCT_REVISION,{'data-service/Dockerfile':blob}),1)
        with self.assertRaises(ValueError):
            m.verify_product_source(HERE.parents[1],m.PRODUCT_REVISION,{'data-service/Dockerfile':blob+b'\n# changed'})


if __name__ == '__main__':
    unittest.main()
