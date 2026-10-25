"""Real PowerShell offline preflight; never launch Docker on development PC."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'recovery-test' / 'Collect-MultiStoreInventory.ps1'
SCRATCH = 'C:/Users/Admin/AppData/Local/hermes/cache/scratch'

def quote(value):
    return "'" + str(value).replace("'", "''") + "'"

class TargetInventoryTests(unittest.TestCase):
    def run_ps(self, command):
        ps = shutil.which('powershell.exe')
        self.assertIsNotNone(ps)
        return subprocess.run([ps,'-NoProfile','-NonInteractive','-Command',command],
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)

    def functions(self):
        self.assertTrue(SCRIPT.is_file(), 'bounded target collector absent')
        return ('$t=$null;$e=$null;$a=[System.Management.Automation.Language.Parser]::ParseFile('
                + quote(SCRIPT) + ',[ref]$t,[ref]$e); if($e.Count){throw "parse"};'
                'foreach($f in $a.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false))'
                '{. ([scriptblock]::Create($f.Extent.Text))};')

    def test_preflight_never_uses_docker_and_output_is_exclusive(self):
        self.assertTrue(SCRIPT.is_file(), 'bounded target collector absent')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            report = Path(temp)/'report.json'
            command = '& '+quote(SCRIPT)+' -PreflightOnly -ReportPath '+quote(report)
            result = self.run_ps(command)
            self.assertEqual(result.returncode,0,result.stderr)
            data = json.loads(report.read_text(encoding='utf-8-sig'))
            self.assertEqual(data['status'],'PREFLIGHT_ONLY')
            self.assertIs(data['dockerInvoked'],False)
            self.assertIs(data['releaseAccepted'],False)
            self.assertEqual(data['images'],[])
            before = report.read_bytes()
            self.assertNotEqual(self.run_ps(command).returncode,0)
            self.assertEqual(report.read_bytes(),before)

    def test_fixed_requests_and_observation_projection(self):
        result = self.run_ps(self.functions()+'''$ErrorActionPreference='Stop';
$refs=@(Get-ApprovedImages);$args=@(Get-InventoryArguments 'image' 'minio/minio:latest');
$raw=@{Id=('sha256:'+('a'*64));RepoDigests=@();Os='linux';Architecture='amd64';Env='PRIVATE'}|ConvertTo-Json;
$o=Convert-InventoryImage 'minio/minio:latest' $raw;
@{refs=$refs;argv=$args;image=$o}|ConvertTo-Json -Depth 8''')
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertIn('postgres:16.4-alpine3.20',data['refs'])
        self.assertIn('speckle/speckle-server:latest',data['refs'])
        self.assertEqual(data['argv'][:4],['--host','npipe:////./pipe/docker_engine','image','inspect'])
        self.assertEqual(data['image']['status'],'UNRESOLVED_REGISTRY_DIGEST')
        self.assertEqual(set(data['image']),{'reference','status','configId','repoDigests','os','architecture'})
        self.assertNotIn('PRIVATE',result.stdout)

    def test_process_wrapper_with_real_synthetic_child(self):
        # Load function declarations only; real child is powershell, NEVER Docker.
        result=self.run_ps(self.functions()+'''$ErrorActionPreference='Stop';
function Assert-InventoryTarget([string]$HostName){}
function Get-InventoryArguments([string]$Kind,[string]$Image){
 if($Kind -ceq 'timeout') {return @('-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 30')}
 return @('-NoProfile','-NonInteractive','-Command','Write-Output synthetic-only')
}
# Wrapper always prefixes --config, so test a disposable cmd shim which drops it.
$root=Join-Path $env:TMPDIR ('inventory-child-'+[Guid]::NewGuid().ToString('N'));
[void][IO.Directory]::CreateDirectory($root);
try{
 $script:config=$root;$script:docker=(Get-Command powershell.exe).Source;
 # Exercise ProcessStartInfo/timeout logic with a function-copy test seam removing config args.
 $body=(Get-Command Invoke-InventoryRead).Definition.Replace('$argv=@(''--config'',$activeConfig)+$fixed','$argv=$fixed');
 Set-Item Function:Invoke-InventoryRead ([scriptblock]::Create($body));
 $script:deadline=[DateTime]::UtcNow.AddSeconds(20);$script:report=@{dockerInvoked=$false};
 $value=Invoke-InventoryRead 'synthetic' '';
 @{value=$value.Trim();invoked=$script:report.dockerInvoked}|ConvertTo-Json
}finally{[IO.Directory]::Delete($root,$true)}''')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'value':'synthetic-only','invoked':True})

    def test_complete_collector_with_synthetic_executable_only(self):
        # Exercise original argv, empty child env and JSON parsing without Docker.
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp)
            fake = root/'resources'/'bin'/'synthetic-reader.exe'
            fake.parent.mkdir(parents=True)
            plugin = root/'resources'/'cli-plugins'/'docker-compose.exe'
            plugin.parent.mkdir(); plugin.write_bytes(b'synthetic-plugin-never-executed')
            code = r'''using System; using System.IO; using System.Web.Script.Serialization;
public class Reader {
 public static int Main(string[] a) {
  if(a.Length<5 || a[0]!="--config" || a[2]!="--host" || a[3]!="npipe:////./pipe/docker_engine") return 91;
  string bin=Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
  foreach(string key in Environment.GetEnvironmentVariables().Keys) {
   if(!String.Equals(key,"SystemRoot",StringComparison.OrdinalIgnoreCase) && !String.Equals(key,"PATH",StringComparison.OrdinalIgnoreCase) && !String.Equals(key,"DOCKER_CONFIG",StringComparison.OrdinalIgnoreCase)) return 96;
  }
  if(String.IsNullOrEmpty(Environment.GetEnvironmentVariable("SystemRoot")) || Environment.GetEnvironmentVariable("PATH")!=bin || Environment.GetEnvironmentVariable("DOCKER_CONFIG")!=a[1]) return 96;
  if(Path.GetFullPath(Environment.CurrentDirectory)!=Path.GetFullPath(a[1])) return 97;
  string config=Path.Combine(a[1],"config.json");
  if(a[4]=="compose") {
   if(!File.Exists(config)) {Console.Error.WriteLine("unknown flag: --short PRIVATE-TOKEN");return 125;}
   var d=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,string[]>>(File.ReadAllText(config));
   string expected=Path.GetFullPath(Path.Combine(Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location),"..","cli-plugins"));
   if(d.Count!=1 || !d.ContainsKey("cliPluginsExtraDirs") || d["cliPluginsExtraDirs"].Length!=1 || Path.GetFullPath(d["cliPluginsExtraDirs"][0])!=expected) return 94;
   Console.WriteLine("5.0.1"); return 0;
  }
  if(File.Exists(config)) return 95; // Version and image requests retain empty config.
  if(a[4]=="version") {
   if(a.Length!=7 || a[5]!="--format" || a[6]!="{\"client\":{{json .Client.Version}},\"server\":{{json .Server.Version}}}") return 92;
   Console.WriteLine("{\"client\":\"28.5.1\",\"server\":\"28.5.1\"}"); return 0;
  }
  if(a[4]=="image") {
   if(a.Length!=9 || a[5]!="inspect" || a[6]!="--format" || a[7]!="{\"Id\":{{json .Id}},\"RepoDigests\":{{json .RepoDigests}},\"Os\":{{json .Os}},\"Architecture\":{{json .Architecture}}}") return 93;
   Console.WriteLine("{\"Id\":\"sha256:"+new string('a',64)+"\",\"RepoDigests\":[\"synthetic/repo@sha256:"+new string('b',64)+"\"],\"Os\":\"linux\",\"Architecture\":\"amd64\"}"); return 0;
  }
  return 94;
 }
}'''
            compiled = self.run_ps('Add-Type -TypeDefinition '+quote(code)
                                   +' -ReferencedAssemblies System.Web.Extensions -OutputAssembly '+quote(fake)+' -OutputType ConsoleApplication')
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            source = SCRIPT.read_text(encoding='utf-8')
            source = source.replace("Require-Inventory ($HostName -ceq 'DESKTOP-OS4Q8CP')",'Require-Inventory $true')
            assignment = "$docker=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\\Docker\\resources\\bin\\docker.exe'"
            self.assertIn(assignment,source)
            source = source.replace(assignment,'$docker='+quote(fake))
            import hashlib
            source = source.replace('6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896',hashlib.sha256(fake.read_bytes()).hexdigest())
            source = source.replace('e6176502e836a7fee8d71cab5fcda736c8dacc79ccefdf9659af977f7eae2375',hashlib.sha256(plugin.read_bytes()).hexdigest())
            seed=";".join("$env:"+k+"='SYNTHETIC-OWNER-SEED'" for k in (
                'DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG','DOCKER_TLS_VERIFY',
                'HOME','USERPROFILE','HTTP_PROXY','HTTPS_PROXY'))+';'
            for mode in ('isolated','inherited-environment','wrong-working-directory'):
                with self.subTest(mode=mode):
                    text=source
                    if mode=='inherited-environment':
                        self.assertIn('$psi.EnvironmentVariables.Clear()',text)
                        text=text.replace('$psi.EnvironmentVariables.Clear()','# deliberately broken isolation for regression check')
                    if mode=='wrong-working-directory':
                        self.assertIn('$psi.WorkingDirectory=$activeConfig',text)
                        text=text.replace('$psi.WorkingDirectory=$activeConfig','$psi.WorkingDirectory='+quote(root))
                    script = root/(mode+'.ps1');script.write_text(text,encoding='utf-8')
                    report = root/(mode+'.json')
                    result = self.run_ps(seed+'& '+quote(script)+' -ReportPath '+quote(report)+'; exit $LASTEXITCODE')
                    self.assertEqual(result.returncode,0 if mode=='isolated' else 2,result.stderr+' '+result.stdout)
                    data=json.loads(report.read_text(encoding='utf-8-sig'))
                    self.assertNotIn('SYNTHETIC-OWNER-SEED',report.read_text(encoding='utf-8-sig')+result.stdout+result.stderr)
                    self.assertFalse(list(root.glob('.dg-inventory-*')))
                    self.assertEqual(len(data['images']),12)
                    if mode=='isolated':
                        self.assertEqual(data['status'],'OBSERVED_NOW')
                        self.assertEqual(data['tools']['composeVersion'],'5.0.1')
                        self.assertEqual(data['tools']['composeDiscovery'],'EXPLICIT_PLUGIN_DIR')
                        self.assertTrue(all(i['status']=='OBSERVED_NOW' for i in data['images']))
                    else:
                        self.assertEqual(data['status'],'UNRESOLVED')
                        self.assertEqual(len(data['diagnostics']),14)
                        expected=96 if mode=='inherited-environment' else 97
                        self.assertTrue(all(d['read']['exitCode']==expected for d in data['diagnostics']))

    def test_updated_file_identity_binding_accepts_only_observed_pair(self):
        # Fixed hash declaration seam only; no actual installed files or execution.
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root=Path(temp);fake=root/'resources'/'bin'/'docker.exe'
            fake.parent.mkdir(parents=True);fake.write_bytes(b'inert-cli')
            plugin=root/'resources'/'cli-plugins'/'docker-compose.exe'
            plugin.parent.mkdir();plugin.write_bytes(b'inert-plugin')
            new_cli='6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896'
            new_plugin='e6176502e836a7fee8d71cab5fcda736c8dacc79ccefdf9659af977f7eae2375'
            old_cli='70c9fbdfb6318c2aa910581cdbe1cf4237a600177cabedcd83e95f1dac7f5db5'
            old_plugin='93be120f45f1ef7a5a7c176636933a5ed0fa2e26fd4cb5907303cd395c9149dc'
            cases=[(new_cli,new_plugin),(old_cli,new_plugin),(new_cli,old_plugin),(old_cli,old_plugin)]
            rows=','.join('@('+quote(a)+','+quote(b)+')' for a,b in cases)
            result=self.run_ps(self.functions()+'''$ErrorActionPreference='Stop';
function Get-FileHash([string]$LiteralPath,[string]$Algorithm){
 $script:hashCalls++;
 if([IO.Path]::GetFileName($LiteralPath) -ceq 'docker.exe'){return @{Hash=$script:cliHash}}
 return @{Hash=$script:pluginHash}
}
$rows=@();foreach($pair in @('''+rows+''')){
 $script:cliHash=$pair[0];$script:pluginHash=$pair[1];$script:hashCalls=0;$accepted=$false;
 try{$null=Get-InventoryPlugin '''+quote(fake)+''';$accepted=$true}catch{}
 $rows+=,@{accepted=$accepted;hashCalls=$script:hashCalls}
};ConvertTo-Json -InputObject $rows''')
            self.assertEqual(result.returncode,0,result.stderr)
            d=json.loads(result.stdout)
            self.assertEqual([r['accepted'] for r in d],[True,False,False,False])
            self.assertEqual([r['hashCalls'] for r in d],[2,1,2,1])

    def test_hash_guards_and_existing_config_block_before_launch(self):
        import hashlib
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root=Path(temp);fake=root/'resources'/'bin'/'docker.exe'
            fake.parent.mkdir(parents=True);fake.write_bytes(b'inert-not-executable')
            plugin=root/'resources'/'cli-plugins'/'docker-compose.exe'
            plugin.parent.mkdir();plugin.write_bytes(b'inert-plugin')
            source=SCRIPT.read_text(encoding='utf-8')
            source=source.replace("Require-Inventory ($HostName -ceq 'DESKTOP-OS4Q8CP')",'Require-Inventory $true')
            assignment="$docker=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\\Docker\\resources\\bin\\docker.exe'"
            self.assertIn(assignment,source)
            source=source.replace(assignment,'$docker='+quote(fake))
            source=source.replace('6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896',hashlib.sha256(fake.read_bytes()).hexdigest())
            source=source.replace('e6176502e836a7fee8d71cab5fcda736c8dacc79ccefdf9659af977f7eae2375',hashlib.sha256(plugin.read_bytes()).hexdigest())
            for mode in ('docker-changed','plugin-changed','plugin-missing','config-collision'):
                with self.subTest(mode=mode):
                    fake.write_bytes(b'inert-not-executable');plugin.write_bytes(b'inert-plugin')
                    text=source
                    if mode=='docker-changed':fake.write_bytes(b'changed')
                    if mode=='plugin-changed':plugin.write_bytes(b'changed')
                    if mode=='plugin-missing':plugin.unlink()
                    existing=root/'existing-empty-config'
                    if mode=='config-collision':
                        existing.mkdir()
                        assignment="$config=Join-Path (Split-Path -Parent $file) ('.dg-inventory-'+[Guid]::NewGuid().ToString('N'))"
                        self.assertIn(assignment,text);text=text.replace(assignment,'$config='+quote(existing))
                    script=root/(mode+'.ps1');script.write_text(text,encoding='utf-8')
                    report=root/(mode+'.json')
                    result=self.run_ps('& '+quote(script)+' -ReportPath '+quote(report)+'; exit $LASTEXITCODE')
                    d=json.loads(report.read_text(encoding='utf-8-sig'))
                    self.assertEqual(result.returncode,1)
                    self.assertEqual(d['status'],'BLOCKED')
                    self.assertIs(d['dockerInvoked'],False)
                    if mode=='config-collision':self.assertTrue(existing.is_dir(),'preexisting empty config deleted')

    def test_timeout_diagnostic_reaps_synthetic_child(self):
        result=self.run_ps(self.functions()+'''$ErrorActionPreference='Stop';
function Assert-InventoryTarget([string]$HostName){}
function Get-InventoryArguments([string]$Kind,[string]$Image){return @('-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 30')}
$root=Join-Path $env:TMPDIR ('inventory-timeout-'+[Guid]::NewGuid().ToString('N'));
[void][IO.Directory]::CreateDirectory($root);
try{
 $script:config=$root;$script:docker=(Get-Command powershell.exe).Source;
 $body=(Get-Command Invoke-InventoryRead).Definition.Replace('$argv=@(''--config'',$activeConfig)+$fixed','$argv=$fixed');
 Set-Item Function:Invoke-InventoryRead ([scriptblock]::Create($body));
 $script:deadline=[DateTime]::UtcNow.AddSeconds(25);$script:report=@{dockerInvoked=$false};
 $failed=$false;try{Invoke-InventoryRead 'timeout' ''|Out-Null}catch{$failed=$true}
 @{failed=$failed;read=$script:lastRead}|ConvertTo-Json -Depth 5
}finally{[IO.Directory]::Delete($root,$true)}''')
        self.assertEqual(result.returncode,0,result.stderr)
        d=json.loads(result.stdout)
        self.assertIs(d['failed'],True)
        self.assertIs(d['read']['timedOut'],True)
        self.assertEqual(d['read']['phase'],'WAIT')
        self.assertIsNone(d['read']['exitCode'])
        self.assertGreaterEqual(d['read']['elapsedMs'],9900)
        self.assertLess(d['read']['elapsedMs'],20000)

    def test_failed_native_reads_publish_only_bounded_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root=Path(temp)
            fake=root/'resources'/'bin'/'synthetic-failure.exe'
            fake.parent.mkdir(parents=True)
            plugin=root/'resources'/'cli-plugins'/'docker-compose.exe'
            plugin.parent.mkdir();plugin.write_bytes(b'synthetic-plugin-never-executed')
            compiled=self.run_ps('Add-Type -TypeDefinition '+quote('''using System;
public class Failure { public static int Main(string[] a) {
 Console.Error.WriteLine("unable to get home directory PRIVATE-TOKEN C:/private/owner");
 return 17;
}}''')+' -OutputAssembly '+quote(fake)+' -OutputType ConsoleApplication')
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            source=SCRIPT.read_text(encoding='utf-8')
            source=source.replace("Require-Inventory ($HostName -ceq 'DESKTOP-OS4Q8CP')",'Require-Inventory $true')
            assignment="$docker=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Docker\\Docker\\resources\\bin\\docker.exe'"
            self.assertIn(assignment,source)
            source=source.replace(assignment,'$docker='+quote(fake))
            import hashlib
            source=source.replace('6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896',hashlib.sha256(fake.read_bytes()).hexdigest())
            source=source.replace('e6176502e836a7fee8d71cab5fcda736c8dacc79ccefdf9659af977f7eae2375',hashlib.sha256(plugin.read_bytes()).hexdigest())
            script=root/'synthetic-failure.ps1'
            script.write_text(source,encoding='utf-8')
            report=root/'report.json'
            result=self.run_ps('& '+quote(script)+' -ReportPath '+quote(report)+'; exit $LASTEXITCODE')
            self.assertEqual(result.returncode,2,result.stderr+result.stdout+report.read_text(encoding='utf-8-sig'))
            text=report.read_text(encoding='utf-8-sig')
            self.assertNotIn('PRIVATE-TOKEN',text+result.stdout+result.stderr)
            self.assertNotIn('C:/private/owner',text)
            data=json.loads(text)
            self.assertEqual(len(data['diagnostics']),14)
            self.assertEqual(data['schemaVersion'],3)
            for d in data['diagnostics']:
                self.assertEqual(d['read']['phase'],'EXIT')
                self.assertEqual(d['read']['exitCode'],17)
                self.assertEqual(d['read']['errorCategory'],'HOME_UNAVAILABLE')
                self.assertIs(d['read']['started'],True)
                self.assertIs(d['read']['timedOut'],False)
                self.assertGreaterEqual(d['read']['elapsedMs'],0)
                self.assertGreater(d['read']['stderrChars'],0)
            self.assertFalse(list(root.glob('.dg-inventory-*')))

    def test_sanitized_failure_diagnostics_do_not_publish_stderr(self):
        result=self.run_ps(self.functions()+'''$ErrorActionPreference='Stop';
@(
 (Get-InventoryErrorCategory 'unable to get home directory PRIVATE-TOKEN'),
 (Get-InventoryErrorCategory 'open //./pipe/docker_engine: The system cannot find the file specified. PRIVATE-TOKEN'),
 (Get-InventoryErrorCategory 'permission denied PRIVATE-TOKEN'),
 (Get-InventoryErrorCategory 'No such image: PRIVATE-TOKEN'),
 (Get-InventoryErrorCategory 'PRIVATE-TOKEN unexpected failure')
)|ConvertTo-Json''')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[
            'HOME_UNAVAILABLE','LOCAL_ENDPOINT_UNAVAILABLE','ACCESS_DENIED',
            'IMAGE_NOT_FOUND','UNCLASSIFIED'])
        self.assertNotIn('PRIVATE-TOKEN',result.stdout)

    def test_bad_inputs_and_wrong_host_fail_closed(self):
        result=self.run_ps(self.functions()+'''$ErrorActionPreference='Stop';$n=0;
try{Get-InventoryArguments 'exec' 'minio/minio:latest'|Out-Null}catch{$n++};
try{Get-InventoryArguments 'image' 'foreign:latest'|Out-Null}catch{$n++};
try{Convert-InventoryImage 'minio/minio:latest' '{"Id":"PRIVATE"}'|Out-Null}catch{$n++};
try{Assert-InventoryTarget 'WRONG-HOST'|Out-Null}catch{$n++};$n''')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'4')

if __name__=='__main__':
    unittest.main()
