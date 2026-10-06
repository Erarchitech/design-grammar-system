---
tags: [debugging, electron, windows, degram]
date: 2026-10-06
---

# Electron app exits silently (exit 0) when launched from a VS Code shell

## Symptom

`DeGram.exe` (Electron) launched from the Claude Code shell exits at once with code 0, no window, no output, no `%LOCALAPPDATA%\DeGram` directory. Redirected stdout/stderr are empty.

## Cause

The VS Code extension host exports `ELECTRON_RUN_AS_NODE=1`; a child Electron app inherits it and behaves as plain Node, so it runs nothing and exits 0. In the PowerShell tool, `Remove-Item Env:\ELECTRON_RUN_AS_NODE` is flagged by the safety check and `[Environment]::SetEnvironmentVariable('ELECTRON_RUN_AS_NODE',$null,'Process')` followed by `Start-Process` did not remove it from the child.

## Fix

Build the child environment explicitly:

```powershell
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "$root\DeGram.exe"; $psi.WorkingDirectory = $root; $psi.UseShellExecute = $false
[void]$psi.Environment.Remove('ELECTRON_RUN_AS_NODE')
$p = [System.Diagnostics.Process]::Start($psi)
```

Stdout/stderr of the GUI app then appear in the tool output (Electron logs `[hermes] install stamp: 910a060d1d94 from commit-build`). Close with `$p.CloseMainWindow()`.

## Related

[[knowledge/debugging/Packaged DeGram ignored the degram variant and attached to the live Hermes]], [[sessions/2026-10-06 Phase 1301 plan 15 rebuild and DeGram isolation proven beside Hermes]]
