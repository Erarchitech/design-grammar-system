"""Offline synthetic-only Compose diagnostic checks; no Docker invocation."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'recovery-test'/'Collect-ComposeDiagnostic.ps1'
SCRATCH='C:/Users/Admin/AppData/Local/hermes/cache/scratch'

def q(s):
    return "'"+str(s).replace("'","''")+"'"

class ComposeDiagnosticTests(unittest.TestCase):
    def ps(self,args):
        return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive']+args,
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)

    def test_preflight_exclusive_without_native_calls(self):
        self.assertTrue(SCRIPT.exists(),'compose diagnostic absent')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            report=Path(tmp)/'p.json'
            args=['-File',str(SCRIPT),'-PreflightOnly','-ReportPath',str(report)]
            p=self.ps(args)
            self.assertEqual(p.returncode,0,p.stderr)
            d=json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertFalse(d['dockerInvoked'])
            self.assertEqual(d['status'],'PREFLIGHT_ONLY')
            before=report.read_bytes()
            self.assertNotEqual(self.ps(args).returncode,0)
            self.assertEqual(report.read_bytes(),before)

    def test_synthetic_cli_and_fixed_plugin_presence(self):
        self.assertTrue(SCRIPT.exists(),'compose diagnostic absent')
        cases=[('ok','2.40.0','VERSION_OBSERVED',0),
               ('stderr','docker: compose is not a docker command. PRIVATE-TOKEN','COMPOSE_COMMAND_UNAVAILABLE',125),
               ('stderr','unknown flag: --short PRIVATE-TOKEN','CLI_ARGUMENT_REJECTED',125),
               ('stderr','PRIVATE-TOKEN unknown issue','UNCLASSIFIED',7),
               ('ok','PRIVATE-TOKEN invalid version',None,0),
               ('timeout','','TIMEOUT',None)]
        for mode,text,category,exitcode in cases:
            with self.subTest(category=category), tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
                root=Path(tmp); fake=root/'reader.exe'; install=root/'install'
                (install/'resources'/'bin').mkdir(parents=True)
                plugin=install/'resources'/'cli-plugins'/'docker-compose.exe'
                plugin.parent.mkdir(); plugin.write_bytes(b'synthetic-plugin-never-executed')
                cs='''using System; public class Reader {public static int Main(string[] a) {
if(a.Length!=7 || a[0]!="--config" || a[2]!="--host" || a[3]!="npipe:////./pipe/docker_engine" || a[4]!="compose" || a[5]!="version" || a[6]!="--short") return 99;
REPLY
}}'''
                reply=('System.Threading.Thread.Sleep(30000);return 0;' if mode=='timeout' else
                       ('Console.WriteLine('+json.dumps(text)+');' if mode=='ok' else 'Console.Error.WriteLine('+json.dumps(text)+');')+'return '+str(exitcode)+';')
                cs=cs.replace('REPLY',reply)
                p=self.ps(['-Command','Add-Type -TypeDefinition '+q(cs)+' -OutputType ConsoleApplication -OutputAssembly '+q(fake)])
                self.assertEqual(p.returncode,0,p.stderr)
                source=SCRIPT.read_text(encoding='utf-8')
                source=source.replace("Require-CD ($Name -ceq 'DESKTOP-OS4Q8CP')",'Require-CD $true')
                assignment="$install=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\\Docker'"
                self.assertIn(assignment,source)
                source=source.replace(assignment,'$install='+q(install))
                source=source.replace("$docker=Join-Path $install 'resources\\bin\\docker.exe'",'$docker='+q(fake))
                script=root/'test.ps1'; script.write_text(source,encoding='utf-8')
                report=root/'r.json'
                p=self.ps(['-File',str(script),'-ReportPath',str(report)])
                self.assertEqual(p.returncode,0 if category=='VERSION_OBSERVED' else 2,p.stderr+p.stdout)
                raw=report.read_text(encoding='utf-8-sig'); d=json.loads(raw)
                self.assertNotIn('PRIVATE-TOKEN',raw+p.stdout+p.stderr)
                self.assertEqual(d['read']['category'],category)
                self.assertEqual(d['read']['exitCode'],exitcode)
                self.assertEqual([v['present'] for v in d['pluginCandidates']],[True,False])
                self.assertEqual(d['nativeCommandsStarted'],1)
                self.assertFalse(list(root.glob('.dg-compose-*')))

    def test_wrong_host_no_native_call(self):
        self.assertTrue(SCRIPT.exists())
        source=SCRIPT.read_text(encoding='utf-8').replace("Require-CD ($Name -ceq 'DESKTOP-OS4Q8CP')",'Require-CD $false')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp); script=root/'blocked.ps1'; script.write_text(source,encoding='utf-8')
            report=root/'r.json'; p=self.ps(['-File',str(script),'-ReportPath',str(report)])
            self.assertEqual(p.returncode,1)
            d=json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertFalse(d['dockerInvoked'])
            self.assertEqual(d['failureStage'],'HOST')

if __name__=='__main__': unittest.main()
