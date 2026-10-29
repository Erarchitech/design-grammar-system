# DeGram clean-PC install protocol

Phase 1301, decision D-12. This is the procedure that turns a clean Windows PC into a working
DeGram workstation and the checks that prove each bridge state. It is the DGCL-01 evidence
procedure: the live run of it is plan 1301-16. Nothing in this document is run by the build.

Status of the installer: **unsigned pilot build** (D-04). Windows will warn about it (step 6).
Signing and an update channel are deferred.

## 0. What you need

| Item | Detail |
|---|---|
| PC | Windows 11 x64. The pilot PC is Windows 11 Home 10.0.26200. Windows 10 is not verified. |
| Disk | About 3 GB free for the installer, about 10 GB free for the installed payload (it carries the bundled Python agent and its tools). |
| Revit | Revit 2024, with a project you can open. |
| Rhino | Rhino 8 with Grasshopper. The DG plugin (`DG.gha`) is installed from DeGram (step 2). |
| DG server | A reachable Design Grammar System (the compose stack) and a DG account that is a member of the project you will use. |
| Installer | `DeGram-Setup-<version>.exe` and its SHA-256 from `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-BUILD.md`. Check the hash before running it. |
| Python for the Revit adapter | Nothing to install from DeGram 0.1.15: the installer carries its own Python 3.11 with `mcp` 1.x and `httpx` (step 7). The agent's own Python (3.14, `mcp` 2.x) cannot run the adapter. |
| Security software | It must trust the installed DeGram executables: `DeGram.exe` and `resources\agent-payload\bin\degram.exe` with its Python. On the pilot PC Kaspersky Total Security terminated the installer and reset every connection the installed `DeGram.exe` made to DG (1301-BUILD.md, F-11). Add the exclusion before step 6, or DG is unreachable from DeGram. |

Nothing below touches an installed Hermes. DeGram keeps its own data under `%LOCALAPPDATA%\DeGram`
and never reads `%LOCALAPPDATA%\hermes` or `~/.hermes`.

## 1. pyRevit 6.5.3

DeGram reads Revit through pyRevit Routes. The version this was developed against is **6.5.3**;
other versions are not verified.

1. Download the pyRevit 6.5.3 installer from the pyRevit releases page and install it.
2. Start Revit 2024. A **pyRevit** tab appears in the ribbon.

## 2. DG connectors: install from DeGram (Коннекторы → Установить)

No script is run for this. Do it after DeGram is installed and signed in to DG (step 6).

DeGram carries both add-ins in its installer. The Revit connector is in `resources\revit-mcp`, built
from `apps/dg-revit-connector`. The DG Grasshopper plugin is in `resources\dg-grasshopper`, the
`net48` Release build of `DG/src/DG.Grasshopper`.

1. Open a project in DeGram, then the **Коннекторы** (Connectors) row in the sidebar.
2. The **Установка** (Installed) column shows, for Revit and Grasshopper:
   - **Готов** (Ready): the installed copy matches the one in this DeGram build;
   - **Установить** (Install): not installed, or an older copy is installed;
   - **Сначала установите pyRevit** (Revit only): pyRevit was not found (step 1);
   - **Нет в этой сборке DeGram**: this installer does not carry the add-in.

   Other connectors show «—».
3. Click **Установить**. DeGram asks for confirmation in its own dialog and names the target folder.
   - Revit: the pyRevit half of the connector is copied to
     `%APPDATA%\pyRevit\Extensions\dg-revit-connector.extension` (the same files as
     `apps/dg-revit-connector/install.py`). The same click sets pyRevit Routes in
     `%APPDATA%\pyRevit\pyRevit_config.ini` (`enabled = true`, `host = "127.0.0.1"`; step 3), so nothing is
     edited by hand. Afterwards **restart Revit** (a pyRevit Reload does not restart the Routes server).
     A **DG** ribbon tab appears. From DeGram 0.1.16 the column shows **Установить** again when only the
     Routes settings are wrong, and clicking it repairs just those, leaving the extension files alone.
   - Grasshopper: the plugin is copied to `%APPDATA%\Grasshopper\Libraries\DG`. Close Rhino first.
     If Rhino still holds the plugin, the column says **Закройте Rhino и повторите** and nothing is changed.
     Start Rhino again afterwards.
4. An earlier installation is kept under `%LOCALAPPDATA%\DG\connector-backups\<revit|grasshopper>\<UTC time>`,
   and the previous `pyRevit_config.ini` under `...\connector-backups\revit-settings\<UTC time>`.
   To roll back, delete the installed folder and move the backup copy back.

Do **not** install "MCP Server for Revit Python" from the pyRevit extension manager. The upstream
`revit-mcp.extension` is left untouched, and the DG connector answers under its own Routes name
`dg_revit`. pyRevit 6.5.3 on the pilot PC runs the **IronPython 3.4** engine, so the pyRevit half is
written for IronPython 3.4 and 2.7: no `async`, f-strings or annotations.

For a build: `python tools/degram/stage_connector_payloads.py --out <empty folder>` builds the plugin
at the current commit and stages both payloads with `connector-manifest.json`. Point the build at the
staged folders with `DEGRAM_DG_GRASSHOPPER_SOURCE` and `DEGRAM_REVIT_MCP_SOURCE`.

## 3. pyRevit Routes: `[routes]`, loopback only

**DeGram 0.1.16 and later write this for you when you click Установить for Revit (step 2)**: it sets
`enabled` and `host` in the `[routes]` section, adding the section or the keys when they are missing, and
keeps the rest of the file as it was (a file that is not UTF-8 is left unchanged and the install reports
a failure). Before 0.1.16, or to check it by hand, in `%APPDATA%\pyRevit\pyRevit_config.ini` (or in
Settings, Routes) the `[routes]` section must read:

```ini
[routes]
enabled = true
host = "127.0.0.1"
port = 48884
```

`host = "127.0.0.1"` is mandatory. pyRevit can listen on every interface with no authentication; the
DeGram extension registers **no routes at all** unless the host is a loopback address, and the DeGram
agent refuses every read while port 48884 answers on a non-loopback address. Enable Routes in
Settings, then restart Revit. The log of the extension reports how many routes it registered (8).

## 4. Grasshopper: DG CANVAS LISTENER

1. Start Rhino 8 and Grasshopper with the DG plugin.
2. Place a **DG CANVAS LISTENER** component on the canvas, connect a Boolean Toggle to its `Run`
   input and set it to true. Its `Status` output shows that it is listening.
3. The listener is loopback-only (`127.0.0.1`, port 8720 by default). Stop it before changing the port
   or closing the document.

## 5. DG origin

DeGram signs in to the DG server in its own embedded window. The origin comes from, in order:

1. the environment variable `DEGRAM_DG_ORIGIN`;
2. `%LOCALAPPDATA%\DeGram\home\degram.json`, for example `{"dgOrigin": "https://dg.example.org"}`;
3. the default `http://localhost:8080` (the local compose stack).

Only a bare `http(s)://host[:port]` origin is accepted. An invalid value is not replaced by the
default: DeGram reports `DG_ORIGIN_INVALID` instead, so a typo cannot send a sign-in to another server.

## 6. Install DeGram and the SmartScreen prompt

1. Run `DeGram-Setup-<version>.exe`. It installs **per user**, needs no administrator rights, and lets
   you choose the folder (default `%LOCALAPPDATA%\Programs\DeGram`).
2. The installer is unsigned. Windows SmartScreen shows "Windows protected your PC": choose
   **More info**, then **Run anyway**. This is expected for the pilot; compare the SHA-256 first.
3. **Identity gate, before the first start.** The packaged main process must carry the DeGram identity.
   On a PC that also has Hermes this is mandatory: a build that baked the stock identity attaches to a running
   Hermes backend and writes to the Hermes home (this happened with the first 1301-15 build, see
   `1301-BUILD.md`). Run, with the install folder of step 6.1:

   ```powershell
   Select-String -Path "$env:LOCALAPPDATA\Programs\DeGram\resources\app.asar.unpacked\dist\electron-main.mjs" -Pattern 'com.erarchitech.degram' -SimpleMatch -Quiet
   ```

   It must print `True`. If it prints `False`, do not start the application.
4. Start **DeGram** from the Start menu. The first screen is the DG sign-in. The data folder
   `%LOCALAPPDATA%\DeGram` appears on that first start (the window title is not verified yet). DeGram has no
   update channel: a new build is a new installer.

5. **Connect DeGram to DG (pairing).** In the DG Web UI open the **Connectors** tab, DeGram card, create a
   pairing and copy the `dgp_` token (it is shown once). In DeGram paste it into the panel «Подключение к DG»
   and press «Подключить». The pairing belongs to your DG user, not to a project, and does not expire; it ends
   when you revoke it on the Connectors tab, change your password or the user is removed (D-25..D-27). The DG
   sign-in of step 6.4 stays for the embedded DG page.

## 7. Adapter interpreter

The adapter must run on an interpreter that carries `mcp` 1.x and `httpx`; the agent payload is CPython 3.14
with `mcp` 2.0.0, which has no `mcp.server.fastmcp`. **From DeGram 0.1.15 the installer carries one:**
`resources\revit-python` is the official embeddable CPython 3.11.9 with `mcp<2` and `httpx` unpacked into its
`Lib\site-packages`, staged by `tools/degram/stage_revit_python.py` (the interpreter's Authenticode signature
must be the Python Software Foundation's). DeGram uses it when nothing else is set, so there is nothing to do.
It does not touch any Python on the machine. A build without the staged folder has no `resources\revit-python`;
then use the fallback below.

The order DeGram resolves the interpreter in: the environment variable `DEGRAM_PYTHON`, then `revitPython` in
`degram.json`, then `resources\revit-mcp\.venv`, then `resources\revit-python\python.exe`.

Fallback for a build without the bundled interpreter, or to use your own: the locked environment of
`resources\revit-mcp\uv.lock` pins `mcp` 1.9.0 and `pydantic-core` 2.33.2, which has wheels for CPython
3.11 to 3.13 only. Create its environment once, next to the installed adapter:

```powershell
cd "$env:LOCALAPPDATA\Programs\DeGram\resources\revit-mcp"
uv sync --frozen --python 3.13
```

DeGram finds `resources\revit-mcp\.venv\Scripts\python.exe` by itself (`DEGRAM_REVIT_MCP_DIR` and
`DEGRAM_PYTHON` are set for the agent from there). To use another interpreter or folder, set
`revitPython` or `revitMcpDir` in `degram.json`, or the environment variables `DEGRAM_PYTHON` and
`DEGRAM_REVIT_MCP_DIR`. Until an interpreter resolves, the Revit group reports **setup-incomplete**.

## 8. Operator steps (DG administrator, once per project)

These are DG admin API calls (admin session); they are not done in DeGram.

| Step | Call | Notes |
|---|---|---|
| Project to company | `PUT /projects/{project}/company` body `{"company": "<name>"}` | The company is part of DeGram's scope (user, company, project; D-20). An unassigned project has `company: null`. Reassigning a project revokes its open delegated tokens. |
| Relay (the one model path) | DG Web UI, LLM settings panel: provider `openai` (OpenAI or an OpenAI-compatible base URL), model, API key | The relay has no configuration of its own (D-24); it uses these settings. The key is stored encrypted and never read back. With another provider, or nothing set, DeGram answers `RELAY_NOT_CONFIGURED`; there is no fallback. |
| Provider-export policy | `PUT /projects/{project}/degram-policy` body `{"providerExportAllowed": true}` | Optional since D-32: export is allowed by default; send `false` to switch it off for a project. Add `"wholeDefinitionAllowed": true` only if the project may send a whole Grasshopper definition; the user still confirms every whole-definition send. |

## 9. Checks, one per bridge state

Run each check with a project selected in DeGram. The wording is the DeGram copy (English first, the
Russian catalog carries the same meaning). Red is never used for a bridge state; a bridge in any state
other than `ready`/`pinned` is shown neutral.

| State | How to produce it | What DeGram must show | Fix |
|---|---|---|---|
| Revit **ready** | Revit 2024 open with a project, Routes on, extension loaded | Revit group lists the open documents; `http://127.0.0.1:48884/revit_mcp/status/` answers `"status": "active"` | none |
| Revit **off** | Close Revit | "Revit isn't responding. Open Revit 2024 with the DeGram pyRevit extension, then refresh." | Start Revit |
| Revit **setup-incomplete: Routes disabled** | `enabled = false` under `[routes]`, restart Revit | "pyRevit Routes are turned off. Enable Routes in pyRevit settings, restart Revit, then refresh." | Step 3 |
| Revit **setup-incomplete: extension not loaded** | Remove the extension folder, restart Revit | "The DeGram extension isn't loaded in pyRevit. Follow the install step "pyRevit extension", then reload pyRevit." | Step 2 |
| Revit **setup-incomplete: extension older than 0.1.6** | Revit runtime log shows "Startup script returned non-zero result for extension: revit-mcp" | The Revit segment «настройка» (setup) | The extension is older than 0.1.6; reinstall it from the 0.1.6 `resources\revit-mcp` (step 2) |
| Revit **setup-incomplete: routes not loopback** | Set `host = "0.0.0.0"` under `[routes]`, restart Revit | The Revit group is setup-incomplete (reason `ROUTES_NOT_LOOPBACK`) and no read is made; the extension logs that it registered no routes | Click Установить for Revit in the Connectors tab (it sets `host = "127.0.0.1"`; step 3), restart Revit |
| Revit **setup-incomplete: no document open** | Revit open on the start screen, no project | The group reports no document open; the picker lists none | Open a project |
| Revit **busy** | Leave a Revit dialog or command open and refresh | "Revit is busy (a command or dialog is open). Finish it in Revit, then retry the request." after at most 30 s | Close the dialog |
| Grasshopper **ready** | Rhino with the DG CANVAS LISTENER running | Grasshopper group lists the open definition | none |
| Grasshopper **off** | Set the listener `Run` to false, or close Rhino | "Grasshopper isn't responding. Place and enable the DG CANVAS LISTENER component on the canvas, then refresh." | Step 4 |
| **pinned** | Pick a document in the document picker | The document segment of the scope strip shows it with the accent dot; the Context card shows project, document, object, parameter and rule counts and the exact payload one caret away | none |
| **identity-mismatch** | Pin a Revit document, then close it or activate another file | "{document} is no longer open, or another file is active in its place. Select the document again - DeGram never switches documents on its own." Reads stop until you pin again | Pin the document again |

Isolation check on the first start: nothing under `%LOCALAPPDATA%\hermes` or `~/.hermes` is created or
changed by DeGram, and `%LOCALAPPDATA%\DeGram` appears (the evidence for the build PC is in
`1301-BUILD.md`).
