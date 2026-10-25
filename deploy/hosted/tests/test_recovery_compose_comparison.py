"""Real synthetic children only; never invoke Docker on development PC."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'recovery-test'/'Compare-ComposeDiscovery.ps1'
SCRATCH='C:/Users/Admin/AppData/Local/hermes/cache/scratch'
DOCKER_HASH='70c9fbdfb6318c2aa910581cdbe1cf4237a600177cabedcd83e95f1dac7f5db5'
PLUGIN_HASH='93be120f45f1ef7a5a7c176636933a5ed0fa2e26fd4cb5907303cd395c9149dc'

def q(value):
    return "'"+str(value).replace("'","''")+"'"

class ComposeComparisonTests(unittest.TestCase):
    def ps(self,args):
        return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive']+args,
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)

    def fixture(self,root,reply=None,wrong_hash=False,missing_plugin=False):
        self.assertTrue(SCRIPT.exists(),'A/B collector absent')
        install=root/'install'; binary=install/'resources'/'bin'/'docker.exe'
        binary.parent.mkdir(parents=True)
        plugin=install/'resources'/'cli-plugins'/'docker-compose.exe'
        plugin.parent.mkdir(); plugin.write_bytes(b'synthetic-plugin-not-executed')
        # This executable checks the actual command/env/config and logs launches.
        cs=r'''using System; using System.IO; using System.Web.Script.Serialization;
public class Reader {public static int Main(string[] a) {
 if(a.Length!=7 || a[0]!="--config" || a[2]!="--host" || a[3]!="npipe:////./pipe/docker_engine" || a[4]!="compose" || a[5]!="version" || a[6]!="--short") return 91;
 if(Directory.GetCurrentDirectory()!=a[1] || Environment.GetEnvironmentVariable("DOCKER_CONFIG")!=a[1]) return 92;
 if(Environment.GetEnvironmentVariable("USERPROFILE")!=null || Environment.GetEnvironmentVariable("DOCKER_HOST")!=null || Environment.GetEnvironmentVariable("ProgramFiles")!=null) return 93;
 var config=Path.Combine(a[1],"config.json"); bool explicitDir=File.Exists(config);
 File.AppendAllText(Path.Combine(Path.GetDirectoryName(a[1]),"synthetic-launches.txt"),explicitDir?"B\n":"A\n");
 if(explicitDir) {
  var d=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,string[]>>(File.ReadAllText(config));
  var expected=Path.Combine(Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location),"..","cli-plugins");
  if(d.Count!=1 || !d.ContainsKey("cliPluginsExtraDirs") || d["cliPluginsExtraDirs"].Length!=1 || Path.GetFullPath(d["cliPluginsExtraDirs"][0])!=Path.GetFullPath(expected)) return 94;
 } else if(Directory.GetFileSystemEntries(a[1]).Length!=0) return 95;
 REPLY
}}
'''
        reply=reply or '''if(explicitDir) {Console.WriteLine("2.40.0");return 0;}
Console.Error.WriteLine("unknown flag: --short PRIVATE-TOKEN");return 125;'''
        cs=cs.replace('REPLY',reply)
        p=self.ps(['-Command','Add-Type -ReferencedAssemblies System.Web.Extensions -TypeDefinition '+q(cs)+' -OutputType ConsoleApplication -OutputAssembly '+q(binary)])
        self.assertEqual(p.returncode,0,p.stderr)
        source=SCRIPT.read_text(encoding='utf-8')
        host="Require-CC ($Name -ceq 'DESKTOP-OS4Q8CP')"
        assignment="$install=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\\Docker'"
        self.assertIn(host,source); self.assertIn(assignment,source)
        source=source.replace(host,'Require-CC $true').replace(assignment,'$install='+q(install))
        source=source.replace(DOCKER_HASH,'0'*64 if wrong_hash else hashlib.sha256(binary.read_bytes()).hexdigest())
        source=source.replace(PLUGIN_HASH,hashlib.sha256(plugin.read_bytes()).hexdigest())
        if missing_plugin: plugin.unlink()
        script=root/'comparison-test.ps1'; script.write_text(source,encoding='utf-8')
        return script

    def test_comparison_changes_only_private_plugin_directory(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp); script=self.fixture(root); report=root/'report.json'
            p=self.ps(['-File',str(script),'-ReportPath',str(report)])
            self.assertEqual(p.returncode,0,p.stderr+p.stdout)
            raw=report.read_text(encoding='utf-8-sig'); d=json.loads(raw)
            self.assertEqual(d['status'],'COMPARISON_COMPLETE')
            self.assertEqual(d['dockerClientLaunches'],2)
            self.assertEqual([v['mode'] for v in d['observations']],['EMPTY_CONFIG','EXPLICIT_PLUGIN_DIR'])
            self.assertEqual([v['read']['exitCode'] for v in d['observations']],[125,0])
            self.assertEqual(d['observations'][1]['composeVersion'],'2.40.0')
            self.assertEqual((root/'synthetic-launches.txt').read_text().splitlines(),['A','B'])
            self.assertFalse(list(root.glob('.dg-compose-compare-*')))
            self.assertNotIn('PRIVATE-TOKEN',raw+p.stdout+p.stderr)
            self.assertNotIn(str(root),raw)
            self.assertIs(d['nativeRecoveryProven'],False)

    def test_preflight_is_native_free_and_report_is_exclusive(self):
        self.assertTrue(SCRIPT.exists())
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            report=Path(tmp)/'report.json'
            args=['-File',str(SCRIPT),'-PreflightOnly','-ReportPath',str(report)]
            p=self.ps(args)
            self.assertEqual(p.returncode,0,p.stderr)
            d=json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertEqual(d['status'],'PREFLIGHT_ONLY')
            self.assertEqual(d['dockerClientLaunches'],0)
            self.assertEqual(d['observations'],[])
            before=report.read_bytes()
            self.assertNotEqual(self.ps(args).returncode,0)
            self.assertEqual(report.read_bytes(),before)

    def test_identity_or_missing_plugin_blocks_before_launch(self):
        for flags in [{'wrong_hash':True},{'missing_plugin':True}]:
            with self.subTest(flags=flags), tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
                root=Path(tmp); script=self.fixture(root,**flags); report=root/'report.json'
                p=self.ps(['-File',str(script),'-ReportPath',str(report)])
                self.assertEqual(p.returncode,1,p.stderr)
                d=json.loads(report.read_text(encoding='utf-8-sig'))
                self.assertEqual(d['failureStage'],'IDENTITY')
                self.assertEqual(d['dockerClientLaunches'],0)
                self.assertFalse((root/'synthetic-launches.txt').exists())
                self.assertFalse(list(root.glob('.dg-compose-compare-*')))

    def test_timeout_stops_comparison_before_second_launch(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp)
            script=self.fixture(root,'System.Threading.Thread.Sleep(30000);return 0;')
            report=root/'report.json'; p=self.ps(['-File',str(script),'-ReportPath',str(report)])
            self.assertEqual(p.returncode,1,p.stderr)
            d=json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertEqual(d['dockerClientLaunches'],1)
            self.assertEqual(d['failureStage'],'INCOMPLETE_SAMPLE')
            self.assertEqual((root/'synthetic-launches.txt').read_text().splitlines(),['A'])
            self.assertIs(d['observations'][0]['read']['timedOut'],True)
            self.assertIsNone(d['observations'][0]['read']['exitCode'])
            self.assertFalse(list(root.glob('.dg-compose-compare-*')))

    def test_unresolved_b_retains_sanitized_pair_and_cleans_config(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp)
            script=self.fixture(root,'Console.Error.WriteLine("PRIVATE-TOKEN arbitrary error");return 17;')
            report=root/'report.json'; p=self.ps(['-File',str(script),'-ReportPath',str(report)])
            self.assertEqual(p.returncode,2,p.stderr)
            raw=report.read_text(encoding='utf-8-sig');d=json.loads(raw)
            self.assertEqual(d['status'],'UNRESOLVED')
            self.assertEqual([v['read']['category'] for v in d['observations']],['UNCLASSIFIED','UNCLASSIFIED'])
            self.assertEqual([v['read']['exitCode'] for v in d['observations']],[17,17])
            self.assertEqual(d['dockerClientLaunches'],2)
            self.assertNotIn('PRIVATE-TOKEN',raw+p.stdout+p.stderr)
            self.assertFalse(list(root.glob('.dg-compose-compare-*')))

    def test_config_collision_preserves_preexisting_bytes(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp); script=self.fixture(root); collision=root/'collision'
            collision.mkdir(); marker=collision/'marker';marker.write_bytes(b'preserve')
            old="'.dg-compose-compare-'+[Guid]::NewGuid().ToString('N')"
            source=script.read_text(encoding='utf-8');self.assertIn(old,source)
            script.write_text(source.replace(old,"'collision'"),encoding='utf-8')
            report=root/'report.json';p=self.ps(['-File',str(script),'-ReportPath',str(report)])
            self.assertEqual(p.returncode,1,p.stderr)
            self.assertEqual(marker.read_bytes(),b'preserve')
            d=json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertEqual(d['dockerClientLaunches'],0)

if __name__=='__main__': unittest.main()
