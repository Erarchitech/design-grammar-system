# Windows 11 isolated edge fixture — DESKTOP-0S4Q8CP only

This ZIP contains Caddy v2.10.2 (official `windows_amd64` binary), the **actual repository Caddyfile** (byte-for-byte), a PowerShell 5.1 runner, and disposable seven-day self-signed test certificates. It needs no Docker, Git, Python, DNS resolution or internet on the target. Do not add private data, use it on a server, trust/install the test certs globally, or reuse these keys.

Source: https://github.com/caddyserver/caddy/releases/download/v2.10.2/caddy_2.10.2_windows_amd64.zip
Official checksum list: https://github.com/caddyserver/caddy/releases/download/v2.10.2/caddy_2.10.2_checksums.txt
The builder verifies the official release **SHA-512** before extracting `caddy.exe`. `manifest.json` records the source archive SHA-512/SHA-256 and SHA-256 of each extracted file. The runner re-verifies `caddy.exe` and original Caddyfile SHA-256. The ZIP's SHA-256 should be verified separately before transfer.

On that PC, unpack into a new folder, inspect the script, open Windows PowerShell (not PowerShell 7 required), change into the unpacked folder, and run exactly:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Run-Edge-Test.ps1
```

No elevated shell is needed. Runner refuses any machine name other than `DESKTOP-0S4Q8CP`, occupied ports, missing/mutated binary/config/certs, or existing `work` directory. It derives an adapted fixture from the original Caddyfile only by counted replacements of three Docker service addresses, three host tokens, certificate path and port; it adds `bind 127.0.0.1` to all four TLS sites, disables automatic HTTPS redirect/admin, and validates with the real Caddy binary. It starts three PowerShell loopback HTTP responders and Caddy on loopback port 18443, sends HTTPS requests via raw TCP + SNI (no DNS), then checks DG/Speckle route allowlists, synthetic object PUT/GET and query/Host/body preservation, spoofed X-Forwarded-For overwrite, denied methods, unknown host/path and blocked routes. Time cap 15 minutes; it kills its own Caddy process by PID and stops its PowerShell jobs. Do not close the PowerShell process abruptly; if interrupted, inspect/terminate only the PIDs it launched. No public interfaces or target downloads are involved.

Return **only** `edge-report.json` (sanitized check names/booleans, no headers or bodies). A nonzero exit means failure; do not treat static tests or a partial report as live proof. `work/` holds generated Caddyfile and local logs; review and delete it after collecting evidence. If rerunning, remove only this fixture's `work/` after confirming its processes exited. Report passes prove solely synthetic Caddy routing, not production TLS, real Speckle/MinIO signed URL, CORS, ETag, import completion, browser download, or secure public ingress. Upload stays excluded from invited pilot pending those separately authorized tests on pinned images.
