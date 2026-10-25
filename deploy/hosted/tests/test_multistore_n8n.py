"""Offline synthetic SQLite/parser tests; NOT an n8n migration/decrypt certificate.

No n8n/Docker/network is invoked. SQL fixtures exercise the versioned physical
probe, never pretend to be a database created by a native n8n process.
"""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

HOSTED = Path(__file__).resolve().parents[1]
MODULE = HOSTED / 'recovery-test' / 'multistore_n8n.py'
# Ordered classes from n8n@2.4.8 db/src/migrations/sqlite/index.ts, immutable
# upstream commit e040ab67e5acf63df4438a7f9352ab91cd43ccc4.
MIGRATIONS = '''
InitialMigration1588102412422 WebhookModel1592445003908 CreateIndexStoppedAt1594825041918
AddWebhookId1611071044839 MakeStoppedAtNullable1607431743769 CreateTagEntity1617213344594
UniqueWorkflowNames1620821879465 AddWaitColumn1621707690587 UpdateWorkflowCredentials1630330987096
AddExecutionEntityIndexes1644421939510 CreateUserManagement1646992772331 LowerCaseUserEmail1648740597343
AddUserSettings1652367743993 CommunityNodes1652254514001 AddAPIKeyColumn1652905585850
IntroducePinData1654089251344 AddNodeIds1658930531669 AddJsonKeyPinData1659888469333
CreateCredentialsUserRole1660062385367 CreateWorkflowsEditorRole1663755770892
CreateCredentialUsageTable1665484192211 RemoveCredentialUsageTable1665754637024
AddWorkflowVersionIdColumn1669739707124 WorkflowStatistics1664196174000
AddTriggerCountColumn1669823906993 RemoveWorkflowDataLoadedFlag1671726148419
MessageEventBusDestinations1671535397530 DeleteExecutionsWithWorkflows1673268682475
CreateLdapEntities1674509946020 PurgeInvalidWorkflowConnections1675940580449
AddStatusToExecutions1674138566000 MigrateExecutionStatus1676996103000 UpdateRunningExecutionStatus1677237073720
CreateVariables1677501636752 CreateExecutionMetadataTable1679416281777 AddUserActivatedProperty1681134145996
MigrateIntegerKeysToString1690000000002 SeparateExecutionData1690000000010 RemoveSkipOwnerSetup1681134145997
FixMissingIndicesFromStringIdMigration1690000000020 RemoveResetPasswordColumns1690000000030
CreateWorkflowNameIndex1691088862123 AddMfaColumns1690000000030 CreateWorkflowHistoryTable1692967111175
DisallowOrphanExecutions1693554410387 ExecutionSoftDelete1693491613982 AddWorkflowMetadata1695128658538
ModifyWorkflowHistoryNodesAndConnections1695829275184 AddGlobalAdminRole1700571993961
DropRoleMapping1705429061930 RemoveFailedExecutionStatus1711018413374 MoveSshKeysToDatabase1711390882123
RemoveNodesAccess1712044305787 CreateProject1714133768519 MakeExecutionStatusNonNullable1714133768521
AddActivatedAtUserSetting1717498465931 AddConstraintToExecutionMetadata1720101653148
CreateInvalidAuthTokenTable1723627610222 RefactorExecutionIndices1723796243146
CreateAnnotationTables1724753530828 AddApiKeysTable1724951148974
SeparateExecutionCreationFromStart1727427440136 CreateProcessedDataTable1726606152711
AddMissingPrimaryKeyOnAnnotationTagMapping1728659839644 UpdateProcessedDataValueColumnToText1729607673464
CreateTestDefinitionTable1730386903556 AddDescriptionToTestDefinition1731404028106
MigrateTestDefinitionKeyToString1731582748663 CreateTestMetricTable1732271325258 CreateTestRun1732549866705
AddMockedNodesColumnToTestDefinition1733133775640 AddManagedColumnToCredentialsTable1734479635324
AddProjectIcons1729607673469 AddStatsColumnsToTestRun1736172058779 CreateTestCaseExecutionTable1736947513045
AddErrorColumnsToTestRuns1737715421462 CreateFolderTable1738709609940 CreateAnalyticsTables1739549398681
UpdateParentFolderIdColumn1740445074052 RenameAnalyticsToInsights1741167584277 AddScopesColumnToApiKeys1742918400000
AddWorkflowStatisticsRootCount1745587087521 AddWorkflowArchivedColumn1745934666076 DropRoleTable1745934666077
ClearEvaluation1745322634000 AddProjectDescriptionColumn1747824239000 AddLastActiveAtColumnToUser1750252139166
AddScopeTables1750252139166 AddRolesTables1750252139167 LinkRoleToUserTable1750252139168
AddInputsOutputsToTestCaseExecution1752669793000 CreateDataStoreTables1754475614601 RemoveOldRoleColumn1750252139170
ReplaceDataStoreTablesWithDataTables1754475614602 LinkRoleToProjectRelationTable1753953244168
AddTimestampsToRoleAndRoleIndexes1756906557570 AddProjectIdToVariableTable1758794506893
AddAudienceColumnToApiKeys1758731786132 ChangeValueTypesForInsights1759399811000
CreateChatHubTables1760019379982 CreateChatHubAgentTable1760020000000 UniqueRoleNames1760020838000
CreateWorkflowDependencyTable1760314000000 DropUnusedChatHubColumns1760965142113
AddWorkflowVersionColumn1761047826451 ChangeDependencyInfoToJson1761655473000
AddWorkflowDescriptionColumn1762177736257 CreateOAuthEntities1760116750277
BackfillMissingWorkflowHistoryRecords1762763704614 AddIsGlobalColumnToCredentialsTable1762771954619
AddWorkflowHistoryAutoSaveFields1762847206508 AddToolsColumnToChatHubTables1761830340990
ChangeOAuthStateColumnToUnboundedVarchar1763572724000 AddAttachmentsToChatHubMessages1761773155024
AddActiveVersionIdColumn1763047800000 CreateBinaryDataTable1763716655000 CreateWorkflowPublishHistoryTable1764167920585
ActivateExecuteWorkflowTriggerWorkflows1763048000000 AddCreatorIdToProjectTable1764276827837
CreateDynamicCredentialResolverTable1764682447000 AddDynamicCredentialEntryTable1764689388394
BackfillMissingWorkflowHistoryRecords1765448186933 AddResolvableFieldsToCredentials1764689448000
AddIconToAgentTable1765788427674 AddAgentIdForeignKeys1765886667897
AddWorkflowVersionIdToExecutionData1765892199653 AddWorkflowPublishScopeToProjectRoles1766064542000
AddChatMessageIndices1766068346315
'''


class MultistoreN8nTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.tree = self.base / 'tree'
        self.tree.mkdir()
        self.scratch = self.base / 'scratch'
        self.scratch.mkdir()
        self.key = self.base / 'key'
        self.key.write_bytes(b'synthetic-key-not-owner-data')
        (self.tree / 'config').write_text(json.dumps({'encryptionKey': self.key.read_text()}))

    def module(self):
        self.assertTrue(MODULE.is_file(), 'native n8n helper is absent')
        spec = importlib.util.spec_from_file_location('multistore_n8n', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_unknown_or_missing_schema_never_becomes_empty_execution_state(self):
        m = self.module()
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute('CREATE TABLE workflow (id TEXT)')
            db.commit()
        for version in ('2.4.8', '2.4.9', None):
            with self.subTest(version=version), self.assertRaisesRegex(m.ProbeError, '^n8n recovery check failed$'):
                m.inspect_tree(self.tree, version=version, key_file=self.key, scratch=self.scratch)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def fixture(self):
        # Explicit source-derived structural fixture, NOT native-created state.
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.executescript('''
                CREATE TABLE workflow_entity (id varchar(36) PRIMARY KEY NOT NULL,
                    name varchar(128) NOT NULL, active boolean NOT NULL,
                    activeVersionId varchar(36), nodes text, connections text NOT NULL,
                    settings text, staticData text, versionId varchar(36));
                CREATE TABLE credentials_entity (id varchar(36) PRIMARY KEY NOT NULL,
                    name varchar(128) NOT NULL, type varchar(128) NOT NULL, data text NOT NULL);
                CREATE TABLE execution_entity (id integer PRIMARY KEY NOT NULL,
                    workflowId varchar(36), finished boolean NOT NULL, mode varchar NOT NULL,
                    retryOf varchar, retrySuccessId varchar, startedAt datetime,
                    stoppedAt datetime, waitTill datetime, status varchar NOT NULL,
                    deletedAt datetime, createdAt datetime NOT NULL);
                CREATE TABLE execution_data (executionId int PRIMARY KEY NOT NULL,
                    workflowData text NOT NULL, data text NOT NULL, workflowVersionId varchar(36));
                CREATE TABLE settings (key varchar PRIMARY KEY NOT NULL,
                    value varchar NOT NULL, loadOnStartup boolean NOT NULL);
                CREATE TABLE migrations (id integer PRIMARY KEY NOT NULL,
                    timestamp bigint NOT NULL, name varchar NOT NULL);
            ''')
            for i, name in enumerate(MIGRATIONS.split(), 1):
                db.execute('INSERT INTO migrations VALUES (?, ?, ?)', (i, int(name[-13:]), name))
            db.commit()

    def test_versioned_schema_returns_real_counters_without_modifying_source(self):
        self.fixture()
        m = self.module()
        before = {p.name: p.read_bytes() for p in self.tree.iterdir()}
        result = m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
        self.assertEqual(result['executions'], {'pending': 0, 'running': 0, 'waiting': 0})
        self.assertEqual(result['schemaVersion'], 1)
        self.assertIs(result['nativeRecoveryProven'], False)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.tree.iterdir()})
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_schema_history_columns_and_unknown_status_fail_closed(self):
        self.fixture()
        m = self.module()
        mutations = [
            ('UPDATE migrations SET name=\'invented\' WHERE id=1', 'UPDATE migrations SET name=? WHERE id=1',
             (MIGRATIONS.split()[0],)),
            ('ALTER TABLE execution_entity RENAME COLUMN status TO invented',
             'ALTER TABLE execution_entity RENAME COLUMN invented TO status', ()),
            ('DROP TABLE execution_data', None, ()),
        ]
        for mutate, undo, params in mutations:
            with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
                db.execute(mutate)
                db.commit()
            with self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
            if undo:
                with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
                    db.execute(undo, params)
                    db.commit()
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_unknown_status_and_inconsistent_terminal_state_are_not_drained(self):
        self.fixture()
        m = self.module()
        for status, stopped, wait in [('unknown', None, None), ('queued', None, None),
                                      ('success', None, None), ('success', '2026-01-02', '2026-02-01')]:
            with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
                db.execute('DELETE FROM execution_entity')
                db.execute('INSERT INTO execution_entity (id,finished,mode,status,createdAt,stoppedAt,waitTill) '
                           'VALUES (1,1,\'manual\',?,\'2026-01-01\',?,?)', (status, stopped, wait))
                db.commit()
            with self.subTest(status=status, stopped=stopped, wait=wait), self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)

    def test_prepare_only_writes_native_import_files_never_database_tables(self):
        m = self.module()
        exchange = self.base / 'exchange'
        result = m.prepare_fixture(exchange)
        self.assertIs(result['nativeRecoveryProven'], False)
        self.assertEqual(set(p.name for p in exchange.iterdir()), {'fixture-state.json', 'workflow.json', 'credentials.json'})
        state = json.loads((exchange / 'fixture-state.json').read_bytes())
        workflow = json.loads((exchange / 'workflow.json').read_bytes())
        credentials = json.loads((exchange / 'credentials.json').read_bytes())
        self.assertIs(workflow[0]['active'], False)
        self.assertIs(workflow[0]['nodes'][1]['disabled'], True)
        self.assertEqual(workflow[0]['nodes'][1]['credentials']['httpHeaderAuth']['id'], credentials[0]['id'])
        self.assertEqual(credentials[0]['data'], state['credential']['data'])
        self.assertNotIn(credentials[0]['data']['value'], json.dumps(result))
        with self.assertRaises(m.ProbeError):
            m.prepare_fixture(exchange)
        self.assertEqual(json.loads((exchange / 'fixture-state.json').read_bytes()), state)

    def imported_fixture(self, m):
        self.fixture()
        exchange = self.base / 'exchange'
        m.prepare_fixture(exchange)
        state = json.loads((exchange / 'fixture-state.json').read_bytes())
        w, c = state['workflow'], state['credential']
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute('INSERT INTO workflow_entity (id,name,active,nodes,connections,settings,versionId) '
                       'VALUES (?,?,0,?,?,?,?)', (w['id'], w['name'], json.dumps(w['nodes']),
                        json.dumps(w['connections']), json.dumps(w['settings']), w['versionId']))
            # This is deliberately NOT real ciphertext; no native crypto is claimed.
            db.execute('INSERT INTO credentials_entity VALUES (?,?,?,?)',
                       (c['id'], c['name'], c['type'], 'offline-opaque-not-n8n-crypto'))
            db.execute('INSERT INTO settings VALUES (\'synthetic.setting\',\'kept\',1)')
            db.commit()
        decrypted = self.base / 'decrypted.json'
        decrypted.write_text(json.dumps([c]))
        return exchange / 'fixture-state.json', decrypted, state

    def test_persisted_workflow_and_credential_semantics_require_decrypted_export(self):
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        result = m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch,
                                fixture_state=state_file, decrypted_export=decrypted)
        self.assertIs(result['workflowMatched'], True)
        self.assertIs(result['credentialExportMatched'], True)
        self.assertIs(result['nativeRecoveryProven'], False)
        self.assertEqual(result['workflowCount'], 1)
        self.assertNotIn(state['credential']['data']['value'], json.dumps(result))
        decrypted.write_text(json.dumps([{**state['credential'], 'data': {'wrong': 'value'}}]))
        with self.assertRaises(m.ProbeError):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch,
                           fixture_state=state_file, decrypted_export=decrypted)
        with self.assertRaises(m.ProbeError):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch,
                           fixture_state=state_file)

    def test_changed_workflow_and_missing_credential_reference_are_rejected(self):
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        for sql in ["UPDATE workflow_entity SET settings='{}'", 'DELETE FROM credentials_entity']:
            with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
                db.execute(sql)
                db.commit()
            with self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch,
                               fixture_state=state_file, decrypted_export=decrypted)

    def test_snapshot_restore_copies_complete_tree_with_independent_digest_and_key_reference(self):
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        binary = self.tree / 'binaryData' / 'workflows' / state['workflow']['id'] / 'executions' / '1'
        binary.mkdir(parents=True)
        (binary / 'synthetic-data').write_bytes(b'\x00\xffwhole-tree-fixture')
        (self.tree / 'empty').mkdir()
        package = self.base / 'package'
        observation = m.snapshot_tree(self.tree, package, version='2.4.8', key_file=self.key,
                    key_reference='synthetic-key-v1', scratch=self.scratch,
                    fixture_state=state_file, decrypted_export=decrypted)
        destination = self.base / 'destination'
        result = m.restore_tree(package, destination, version='2.4.8', key_file=self.key,
                    key_reference='synthetic-key-v1', scratch=self.scratch, expected=observation,
                    fixture_state=state_file, decrypted_export=decrypted)
        self.assertIs(result['treeRestored'], True)
        self.assertIs(result['nativeRecoveryProven'], False)
        self.assertTrue((destination / 'empty').is_dir())
        for path in self.tree.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (destination / path.relative_to(self.tree)).read_bytes())
        with self.assertRaises(m.ProbeError):
            m.restore_tree(package, self.base / 'bad-ref', version='2.4.8', key_file=self.key,
                    key_reference='wrong-key-ref', scratch=self.scratch, expected=observation,
                    fixture_state=state_file, decrypted_export=decrypted)
        self.assertFalse((self.base / 'bad-ref').exists())
        (package / 'tree' / 'config').write_text('{}')
        with self.assertRaises(m.ProbeError):
            m.restore_tree(package, self.base / 'corrupt', version='2.4.8', key_file=self.key,
                    key_reference='synthetic-key-v1', scratch=self.scratch, expected=observation,
                    fixture_state=state_file, decrypted_export=decrypted)
        self.assertFalse((self.base / 'corrupt').exists())

    def test_snapshot_refuses_pending_execution_before_publishing(self):
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute("INSERT INTO execution_entity (id,finished,mode,status,createdAt) VALUES (1,0,'manual','new','2026-01-01')")
            db.commit()
        with self.assertRaises(m.ProbeError):
            m.snapshot_tree(self.tree, self.base / 'unsafe-package', version='2.4.8', key_file=self.key,
                    key_reference='synthetic-key-v1', scratch=self.scratch,
                    fixture_state=state_file, decrypted_export=decrypted)
        self.assertFalse((self.base / 'unsafe-package').exists())

    def test_cli_emits_only_sanitized_json_and_exercises_prepare_inspect_snapshot_restore(self):
        import subprocess
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        common = ['--version', '2.4.8', '--key-file', str(self.key), '--scratch', str(self.scratch)]
        semantic = ['--fixture-state', str(state_file), '--decrypted-export', str(decrypted)]
        def run(*args):
            return subprocess.run([sys.executable, '-B', str(MODULE), *args], capture_output=True, text=True)
        p = run('inspect', '--tree', str(self.tree), *common)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['executions'], {'pending': 0, 'running': 0, 'waiting': 0})
        package = self.base / 'cli-package'
        p = run('snapshot', '--tree', str(self.tree), '--package', str(package),
                '--key-reference', 'synthetic-key-v1', *common, *semantic)
        self.assertEqual(p.returncode, 0, p.stderr)
        expected = self.base / 'expected.json'
        expected.write_text(p.stdout)
        p = run('restore', '--package', str(package), '--destination', str(self.base / 'cli-dest'),
                '--expected', str(expected), '--key-reference', 'synthetic-key-v1', *common, *semantic)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIs(json.loads(p.stdout)['treeRestored'], True)
        p = run('verify', '--tree', str(self.base / 'cli-dest'), '--expected', str(expected),
                '--key-reference', 'synthetic-key-v1', *common, *semantic)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIs(json.loads(p.stdout)['restoredStateMatched'], True)
        p = run('prepare', '--exchange', str(self.base / 'cli-exchange'))
        self.assertEqual(p.returncode, 0, p.stderr)
        p = run('unexpected-private-value', '--password=private-token')
        self.assertEqual(p.returncode, 1)
        self.assertEqual(p.stdout, '')
        self.assertEqual(p.stderr.strip(), 'n8n recovery check failed')
        self.assertNotIn(state['credential']['data']['value'], p.stderr)

    def test_native_timestamp_order_ledger_is_accepted_with_exact_membership(self):
        self.fixture()
        m = self.module()
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute('DELETE FROM migrations')
            # TypeORM MigrationExecutor sorts timestamps, not the source array.
            for i, name in enumerate(sorted(MIGRATIONS.split(), key=lambda n: int(n[-13:])), 1):
                db.execute('INSERT INTO migrations VALUES (?,?,?)', (i, int(name[-13:]), name))
            db.commit()
        self.assertEqual(m.inspect_tree(self.tree, version='2.4.8', key_file=self.key,
                                      scratch=self.scratch)['executions']['pending'], 0)

    def test_live_wal_bytes_are_read_only_on_full_copy_not_ignored(self):
        import shutil
        self.fixture()
        m = self.module()
        frozen = self.base / 'wal-source'
        frozen.mkdir()
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone(), ('wal',))
            db.execute("INSERT INTO execution_entity (id,finished,mode,status,createdAt) VALUES (1,0,'manual','waiting','2026-01-01')")
            db.commit()
            # Freeze all SQLite bytes from our synthetic producer, then close it
            # BEFORE invoking the helper on the copied, no-writer tree.
            for path in self.tree.iterdir():
                shutil.copyfile(path, frozen / path.name)
        before = {p.name: p.read_bytes() for p in frozen.iterdir()}
        self.assertTrue(before['database.sqlite-wal'])
        result = m.inspect_tree(frozen, version='2.4.8', key_file=self.key, scratch=self.scratch)
        self.assertEqual(result['executions']['waiting'], 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in frozen.iterdir()})
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_wrong_key_rejects_without_leaking_key_or_preserving_plaintext_scratch(self):
        self.fixture()
        m = self.module()
        self.key.write_bytes(b'wrong-private-value')
        with self.assertRaisesRegex(m.ProbeError, '^n8n recovery check failed$'):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_execution_physical_column_type_is_validated_not_merely_named(self):
        self.fixture()
        m = self.module()
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute('ALTER TABLE execution_entity RENAME COLUMN status TO old_status')
            db.execute('ALTER TABLE execution_entity ADD COLUMN status BLOB')
            db.commit()
        with self.assertRaises(m.ProbeError):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)

    def test_any_active_workflow_blocks_snapshot_even_when_fixture_itself_is_inactive(self):
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute("INSERT INTO workflow_entity (id,name,active,activeVersionId,nodes,connections,settings) "
                       "VALUES ('other','other',1,'published','[]','{}','{}')")
            db.commit()
        with self.assertRaises(m.ProbeError):
            m.snapshot_tree(self.tree, self.base / 'active', version='2.4.8', key_file=self.key,
                    key_reference='synthetic-key-v1', scratch=self.scratch,
                    fixture_state=state_file, decrypted_export=decrypted)
        self.assertFalse((self.base / 'active').exists())

    def test_verify_matches_logical_database_and_binary_state_after_native_cli_open(self):
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        package = self.base / 'verify-package'
        observation = m.snapshot_tree(self.tree, package, version='2.4.8', key_file=self.key,
                    key_reference='synthetic-key-v1', scratch=self.scratch,
                    fixture_state=state_file, decrypted_export=decrypted)
        # Same-count setting change must not be masked by the focused fixture.
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute("UPDATE settings SET value='changed'")
            db.commit()
        with self.assertRaises(m.ProbeError):
            m.verify_tree(self.tree, expected=observation, key_reference='synthetic-key-v1',
                    version='2.4.8', key_file=self.key, scratch=self.scratch,
                    fixture_state=state_file, decrypted_export=decrypted)

    def test_scratch_inside_source_is_refused_without_mutating_source(self):
        self.fixture()
        m = self.module()
        inside = self.tree / 'scratch'
        inside.mkdir()
        with self.assertRaises(m.ProbeError):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=inside)
        self.assertEqual(list(inside.iterdir()), [])

    def test_changed_source_during_sql_probe_cannot_mix_database_and_binary_observations(self):
        self.fixture()
        m = self.module()
        from unittest.mock import patch
        original = m._inspect_database
        def change_after_copy(db):
            (self.tree / 'new-binary-content').write_bytes(b'changed-after-copy')
            return original(db)
        with patch.object(m, '_inspect_database', side_effect=change_after_copy):
            with self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_flat_helper_mount_layout_loads_existing_archive_modules(self):
        import shutil
        import subprocess
        flat = self.base / 'flat'
        flat.mkdir()
        for path in (MODULE, HOSTED / 'recovery_n8n.py', HOSTED / 'recovery_filesystem.py'):
            shutil.copyfile(path, flat / path.name)
        p = subprocess.run([sys.executable, '-B', str(flat / MODULE.name), 'prepare',
                            '--exchange', str(self.base / 'flat-fixture')], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIs(json.loads(p.stdout)['fixturePrepared'], True)

    def test_snapshot_cannot_bypass_semantic_gate_with_null_file_arguments(self):
        self.fixture()
        m = self.module()
        with self.assertRaises(m.ProbeError):
            m.snapshot_tree(self.tree, self.base / 'no-semantic', version='2.4.8', key_file=self.key,
                    key_reference='synthetic-key-v1', scratch=self.scratch,
                    fixture_state=None, decrypted_export=None)
        self.assertFalse((self.base / 'no-semantic').exists())

    def test_each_nonterminal_execution_including_soft_deleted_is_counted(self):
        self.fixture()
        m = self.module()
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            for i, status in enumerate(('new', 'running', 'waiting'), 1):
                db.execute('INSERT INTO execution_entity (id,finished,mode,status,createdAt,deletedAt) '
                           'VALUES (?,0,\'manual\',?,\'2026-01-01\',\'2026-01-02\')', (i, status))
            db.commit()
        result = m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
        self.assertEqual(result['executions'], {'pending': 1, 'running': 1, 'waiting': 1})


    def test_sqlite_materialization_and_catalog_fetches_are_bounded(self):
        self.fixture()
        m = self.module()
        from unittest.mock import patch
        original = m._inspect_database
        observed = []
        def inspect(db):
            observed.append((db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),
                             db.getlimit(sqlite3.SQLITE_LIMIT_COLUMN)))
            return original(db)
        with patch.object(m, '_inspect_database', side_effect=inspect):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
        self.assertLessEqual(observed[0][0], 1048576 // 12)
        self.assertLessEqual(observed[0][1], 256)

    def test_migration_ledger_never_uses_unbounded_fetch(self):
        self.fixture()
        m = self.module()
        unbounded = []
        class Cursor(sqlite3.Cursor):
            def fetchall(inner):
                unbounded.append(inner.description)
                return super().fetchall()
            def fetchmany(inner, size=None):
                self.assertIsNotNone(size)
                self.assertLessEqual(size, 513)
                if inner.description and [c[0] for c in inner.description] == ['name', 'timestamp']:
                    self.assertLessEqual(size, 129)
                return super().fetchmany(size)
        class Connection(sqlite3.Connection):
            def execute(inner, sql, parameters=()):
                return inner.cursor(Cursor).execute(sql, parameters)
        with closing(sqlite3.connect(self.tree / 'database.sqlite', factory=Connection)) as db:
            m._inspect_database(db)
        self.assertEqual(unbounded, [], 'unbounded fetchall during inspection')

    def test_large_catalog_is_rejected(self):
        self.fixture()
        m = self.module()
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            for i in range(513):
                db.execute('CREATE TABLE extra_%d (id INTEGER)' % i)
            db.commit()
        with self.assertRaises(m.ProbeError):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)

    def test_large_sqlite_text_blob_and_ledger_are_rejected(self):
        self.fixture()
        m = self.module()
        for value in ('x' * 1048577, b'x' * 1048577, '\x00' * 200000):
            with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
                db.execute('INSERT OR REPLACE INTO settings VALUES (?,?,1)', ('large', value))
                db.commit()
            with self.subTest(kind=type(value).__name__, length=len(value)), self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute('DELETE FROM settings')
            db.executemany('INSERT INTO migrations VALUES (?,?,?)',
                           ((i, 0, 'extra') for i in range(129, 2000)))
            db.commit()
        with self.assertRaises(m.ProbeError):
            m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)

    def test_finished_storage_and_success_consistency(self):
        self.fixture()
        m = self.module()
        with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
            db.execute('DROP TABLE execution_entity')
            # Keep required types/PK but allow NULL to test stored values independently.
            db.execute('CREATE TABLE execution_entity (id INTEGER PRIMARY KEY, workflowId varchar, '
                       'finished boolean, mode varchar, status varchar, createdAt datetime, '
                       'startedAt datetime, stoppedAt datetime, deletedAt datetime, waitTill datetime, '
                       'retryOf varchar, retrySuccessId varchar)')
            db.commit()
        for status, finished in [('success', 0), ('success', None), ('error', 2),
                                 ('canceled', -1), ('crashed', 'bad'), ('error', 0.5)]:
            with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
                db.execute('DELETE FROM execution_entity')
                db.execute("INSERT INTO execution_entity (id,status,finished,stoppedAt) VALUES (1,?,?, '2026-01-02')",
                           (status, finished))
                db.commit()
            with self.subTest(status=status, finished=finished), self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, version='2.4.8', key_file=self.key, scratch=self.scratch)
        for status, finished in [('success', 1), ('error', 0), ('canceled', 0), ('crashed', 0)]:
            with closing(sqlite3.connect(self.tree / 'database.sqlite')) as db:
                db.execute('UPDATE execution_entity SET status=?,finished=?', (status, finished))
                db.commit()
            self.assertEqual(m.inspect_tree(self.tree, version='2.4.8', key_file=self.key,
                                            scratch=self.scratch)['executions'],
                             {'pending': 0, 'running': 0, 'waiting': 0})

    def test_strict_json_fixture_and_recursive_semantic_types(self):
        import copy
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        options = dict(version='2.4.8', key_file=self.key, scratch=self.scratch,
                       fixture_state=state_file, decrypted_export=decrypted)
        mutations = [lambda s: s.update(schemaVersion=True),
                     lambda s: s['workflow']['nodes'][0].update(typeVersion=True),
                     lambda s: s['workflow']['nodes'][0].update(typeVersion=1.0),
                     lambda s: s['workflow'].update(active=0),
                     lambda s: s['workflow']['nodes'][1].update(disabled=1),
                     lambda s: s.update(extra='unexpected')]
        for i, mutate in enumerate(mutations):
            bad = copy.deepcopy(state)
            mutate(bad)
            state_file.write_text(json.dumps(bad))
            with self.subTest(case=i), self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, **options)
        state_file.write_text(json.dumps(state))
        # Independent export with an added nested boolean/number equality trap.
        state['credential']['data']['nested'] = [True, {'number': 1}]
        state_file.write_text(json.dumps(state))
        for nested in ([1, {'number': 1}], [True, {'number': True}], [True, {'number': 1.0}]):
            bad = copy.deepcopy(state['credential'])
            bad['data']['nested'] = nested
            decrypted.write_text(json.dumps([bad]))
            with self.subTest(nested=nested), self.assertRaises(m.ProbeError):
                m.inspect_tree(self.tree, **options)

    def test_json_duplicates_nonfinite_and_nonstandard_constants_are_rejected(self):
        m = self.module()
        path = self.base / 'bad.json'
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '[Infinity]', '[-Infinity]', '{"x":1e999}'):
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                m._read_json(path)

    def test_both_expected_envelopes_reject_malformed_types_and_fields(self):
        import copy
        m = self.module()
        state_file, decrypted, state = self.imported_fixture(m)
        package = self.base / 'report-package'
        opts = dict(version='2.4.8', key_file=self.key, scratch=self.scratch,
                    fixture_state=state_file, decrypted_export=decrypted, key_reference='synthetic-v1')
        report = m.snapshot_tree(self.tree, package, **opts)
        mutations = [lambda r: r.pop('schemaVersion'), lambda r: r.update(schemaVersion=True),
                     lambda r: r.update(nativeRecoveryProven=True), lambda r: r.pop('nativeRecoveryProven'),
                     lambda r: r.update(nativeRecoveryProven=0), lambda r: r.update(extra=1),
                     lambda r: r.update(manifestSha256='bad'), lambda r: r.update(manifestSha256=True),
                     lambda r: r['observation'].update(schemaVersion=True),
                     lambda r: r['observation'].update(workflowCount=True),
                     lambda r: r['observation'].update(workflowCount=1.0),
                     lambda r: r['observation'].update(nativeRecoveryProven=0),
                     lambda r: r['observation'].update(workflowMatched=1),
                     lambda r: r['observation']['executions'].update(pending=False),
                     lambda r: r['observation'].update(logicalStateSha256=0),
                     lambda r: r['observation'].pop('credentialExportMatched')]
        for i, mutate in enumerate(mutations):
            bad = copy.deepcopy(report)
            mutate(bad)
            with self.subTest(case=i, mode='verify'), self.assertRaises(m.ProbeError):
                m.verify_tree(self.tree, expected=bad, **opts)
            dest = self.base / ('bad-dest-%d' % i)
            with self.subTest(case=i, mode='restore'), self.assertRaises(m.ProbeError):
                m.restore_tree(package, dest, expected=bad, **opts)
            self.assertFalse(dest.exists())

if __name__ == '__main__':
    unittest.main()
