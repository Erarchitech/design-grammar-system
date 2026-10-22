# Phase 1303 deferred items

Out-of-scope discoveries logged by executors. Not fixed by the plan that found them.

## Found during 1303-16 (2026-10-22)

- `data-service/tests/test_static_proxy_boundary.py::test_nginx_proxies_only_to_data_service` and `::test_nginx_config_is_fully_clean` fail on HEAD of `feature/mapping-mvp`. Cause: plan 1303-15 (commit `4b03c61`, "no mid-solution expiry; the check answers inside the proxy limit") added the nginx location `/data-service/scripts/` (timeout 240 s) to `ui-v2/nginx.conf`, and the test's allow-list of proxy locations does not contain it (`unexpected-proxy-location:/data-service/scripts/`). 1303-16 changes no nginx file. Fix belongs with the 1303-15 follow-up or 1303-18: add the location to the allow-list in that test, after confirming the location is intended.
