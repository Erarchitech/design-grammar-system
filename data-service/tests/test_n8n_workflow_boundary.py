"""Static JSON boundary checks over all five n8n workflows (Phase 1205-05,
D-04/D-08/D-10, ALGN12-17/ALGN12-18).

These tests walk `nodes`/`connections` structurally (json.load) rather than
grepping raw text, so a coincidental substring match inside an unrelated
field -- e.g. graph-query-mcp.json's own workflow `id`
("b2c3d4e5-f6a7-8901-bcde-f12345678901", the live n8n instance's identity
for this workflow per the n8n-draft-vs-published-versions memory and
29-07/29-08's PATCH history -- never changed here) -- never produces a
false positive. The "no committed default password" check only walks each
node's own `parameters` dict, so it never touches that top-level `id` field.

Resolves the repo root via DG_KNOWLEDGE_REPO_ROOT (in-container /mnt/repo),
falling back to this file's repo-relative parents, matching the
dg_knowledge.py / evidence_contract.py idiom.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_REPO_ROOT = Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parents[2])))
WORKFLOWS_DIR = _REPO_ROOT / "n8n" / "workflows"

WORKFLOW_FILES = {
    "rules_ingest": "rules-to-metagraph.json",
    "graph_query": "graph-query-mcp.json",
    "spec_ingest": "spec-ingest.json",
    "spec_query": "spec-query.json",
    "spec_update": "spec-update.json",
}

CALLER_OVERRIDE_FIELDS = (
    "mcp_url",
    "data_service_url",
    "neo4j_url",
    "neo4j_user",
    "neo4j_password",
    "ollama_url",
)
NEO4J_DEFAULT_PASSWORD = "12345678"


def _load(name: str) -> dict:
    path = WORKFLOWS_DIR / WORKFLOW_FILES[name]
    return json.loads(path.read_text(encoding="utf-8"))


def _nodes_by_name(workflow: dict) -> dict:
    return {n["name"]: n for n in workflow["nodes"]}


def _webhook_node(workflow: dict) -> dict:
    webhooks = [n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.webhook"]
    assert len(webhooks) == 1, "expected exactly one webhook node"
    return webhooks[0]


def _downstream_names(workflow: dict, node_name: str) -> list[str]:
    branches = workflow.get("connections", {}).get(node_name, {}).get("main", [])
    names = []
    for branch in branches:
        for edge in branch:
            names.append(edge["node"])
    return names


def _node_code(node: dict) -> str:
    params = node.get("parameters", {})
    return params.get("functionCode") or params.get("jsCode") or ""


def _iter_param_strings(node: dict):
    """Yield every string value found anywhere inside a node's `parameters`
    dict, recursively -- covers url/bodyParametersJson/headerParametersJson/
    functionCode/basicAuthPassword/etc. Deliberately does NOT look at the
    node's own top-level keys (id, name, type, position) or the workflow's
    top-level `id`, so an unrelated GUID never produces a false positive."""

    def _walk(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for v in value.values():
                yield from _walk(v)
        elif isinstance(value, list):
            for v in value:
                yield from _walk(v)

    yield from _walk(node.get("parameters", {}))


@pytest.mark.parametrize("workflow_key", list(WORKFLOW_FILES))
class TestGuardPlacement:
    """Behavior bullet 1: the webhook node's only downstream node is a guard
    whose code references x-dg-service-token and $env.DG_SERVICE_TOKEN and
    contains a throw."""

    def test_webhook_only_downstream_is_guard(self, workflow_key):
        workflow = _load(workflow_key)
        webhook = _webhook_node(workflow)
        downstream = _downstream_names(workflow, webhook["name"])
        assert len(downstream) == 1, (
            f"{workflow_key}: webhook has {len(downstream)} downstream nodes, expected 1 (the guard)"
        )
        guard = _nodes_by_name(workflow)[downstream[0]]
        code = _node_code(guard)
        assert "x-dg-service-token" in code, f"{workflow_key}: guard does not read x-dg-service-token"
        assert "$env.DG_SERVICE_TOKEN" in code, f"{workflow_key}: guard does not compare against $env.DG_SERVICE_TOKEN"
        assert "throw" in code, f"{workflow_key}: guard does not throw on rejection"


@pytest.mark.parametrize("workflow_key", list(WORKFLOW_FILES))
class TestNoCallerOverride:
    """Behavior bullet 2: no node parameter string anywhere matches a
    caller-override read of mcp_url, data_service_url, neo4j_url,
    neo4j_user, neo4j_password or ollama_url from $json, $json.body or
    $json.query."""

    def test_no_caller_override_reads(self, workflow_key):
        workflow = _load(workflow_key)
        for node in workflow["nodes"]:
            for s in _iter_param_strings(node):
                for field in CALLER_OVERRIDE_FIELDS:
                    for prefix in ("$json.%s", "$json.body.%s", "$json.query.%s"):
                        source = prefix % field
                        assert source not in s, (
                            f"{workflow_key}/{node['name']}: caller-override read {source!r} found"
                        )


@pytest.mark.parametrize("workflow_key", list(WORKFLOW_FILES))
class TestNoDefaultNeo4jPassword:
    """Behavior bullet 3: no workflow contains the committed Neo4j default
    password literal. Scoped to each node's `parameters` dict only (see
    _iter_param_strings docstring) so a workflow's own top-level `id` GUID
    never produces a false positive."""

    def test_no_default_neo4j_password(self, workflow_key):
        workflow = _load(workflow_key)
        for node in workflow["nodes"]:
            for s in _iter_param_strings(node):
                assert NEO4J_DEFAULT_PASSWORD not in s, (
                    f"{workflow_key}/{node['name']}: committed Neo4j default password literal found"
                )


@pytest.mark.parametrize("workflow_key", list(WORKFLOW_FILES))
class TestDataServiceNodesLiteralAndHeader:
    """Behavior bullet 4: every httpRequest node whose URL mentions
    data-service has a URL containing the literal http://data-service:8000
    with no $json or $items expression in it, and a header expression
    containing X-DG-Service-Token and $env.DG_SERVICE_TOKEN."""

    def test_data_service_nodes_literal_and_header(self, workflow_key):
        workflow = _load(workflow_key)
        found_any = False
        for node in workflow["nodes"]:
            if node.get("type") != "n8n-nodes-base.httpRequest":
                continue
            params = node.get("parameters", {})
            url = params.get("url", "")
            if "data-service" not in url:
                continue
            found_any = True
            assert "http://data-service:8000" in url, (
                f"{workflow_key}/{node['name']}: URL does not contain the literal http://data-service:8000"
            )
            assert "$json" not in url, f"{workflow_key}/{node['name']}: URL still contains a $json expression"
            assert "$items" not in url, f"{workflow_key}/{node['name']}: URL still contains an $items expression"
            headers = params.get("headerParametersJson", "")
            assert "X-DG-Service-Token" in headers, (
                f"{workflow_key}/{node['name']}: missing X-DG-Service-Token header expression"
            )
            assert "$env.DG_SERVICE_TOKEN" in headers, (
                f"{workflow_key}/{node['name']}: header does not source $env.DG_SERVICE_TOKEN"
            )
        assert found_any, f"{workflow_key}: expected at least one data-service httpRequest node"


class TestRulesIngestSpecifics:
    """Behavior bullet 5 (rules-ingest only)."""

    def test_single_atomic_neo4j_write(self):
        workflow = _load("rules_ingest")
        commit_nodes = [
            n
            for n in workflow["nodes"]
            if n.get("type") == "n8n-nodes-base.httpRequest"
            and "tx/commit" in n.get("parameters", {}).get("url", "")
        ]
        assert len(commit_nodes) == 1, "expected exactly one node posting to neo4j tx/commit"
        body = commit_nodes[0]["parameters"].get("bodyParametersJson", "")
        assert "postProcess" in body, "the single write must include the postProcess statement"
        assert "descriptionStatement" in body, (
            "the single write must include the project-scoped description statement"
        )

    def test_prepare_graph_payload_reads_env_password(self):
        workflow = _load("rules_ingest")
        node = _nodes_by_name(workflow)["Prepare Graph Payload"]
        assert "$env.NEO4J_PASSWORD" in _node_code(node)

    def test_build_response_scans_only_execute_llm_cypher(self):
        workflow = _load("rules_ingest")
        node = _nodes_by_name(workflow)["Build Response"]
        code = _node_code(node)
        assert "Execute LLM Cypher" in code
        assert "Annotate Graph Props" not in code

    def test_annotate_graph_props_node_removed(self):
        workflow = _load("rules_ingest")
        names = {n["name"] for n in workflow["nodes"]}
        assert "Annotate Graph Props" not in names


class TestGraphQuerySpecifics:
    """Behavior bullet 6 (graph-query only)."""

    def test_run_cypher_mcp_project_parameter_unconditional(self):
        workflow = _load("graph_query")
        node = _nodes_by_name(workflow)["Run Cypher (MCP)"]
        body = node["parameters"].get("bodyParametersJson", "")
        assert '"project"' in body
        # The pre-1205-05 shape used a ternary ("... ? { \"project\": ... } : {}")
        # to make the parameter conditional -- assert that pattern is gone.
        assert "? {" not in body, "project parameter must be sent unconditionally, no ternary"

    def test_build_cypher_prompt_states_scope_rule(self):
        workflow = _load("graph_query")
        node = _nodes_by_name(workflow)["Build Cypher Prompt"]
        code = _node_code(node)
        for shared_vocab_label in ("Class", "DatatypeProperty", "ObjectProperty", "Builtin", "Literal"):
            assert shared_vocab_label in code, f"prompt does not name the {shared_vocab_label} label in the scope rule"
        for banned in ("CALL", "UNION", "LOAD CSV", "FOREACH", "USE"):
            assert banned in code, f"missing banned-clause mention for {banned}"


# ── 1205 review iteration 4: WR-04 / WR-05 (statement separators in n8n) ──

import shutil  # noqa: E402
import subprocess  # noqa: E402

_NODE = shutil.which("node")


def _run_node_function(code: str, *, json_input: dict, items: dict | None = None) -> dict:
    """Execute an n8n Function-node body under Node with `$json`, `$items` and
    `$env` stubbed, returning the first returned item's json."""
    harness = (
        "const $json = JSON.parse(process.env.DG_TEST_JSON);\n"
        "const __items = JSON.parse(process.env.DG_TEST_ITEMS || '{}');\n"
        "const $items = (name) => [{ json: __items[name] || {} }];\n"
        "const $env = { NEO4J_USER: 'u', NEO4J_PASSWORD: 'p' };\n"
        "const out = (function () {\n" + code + "\n})();\n"
        "process.stdout.write(JSON.stringify(out[0].json));\n"
    )
    import json as _json
    import os as _os

    env = dict(_os.environ)
    env["DG_TEST_JSON"] = _json.dumps(json_input)
    env["DG_TEST_ITEMS"] = _json.dumps(items or {})
    done = subprocess.run(
        [_NODE, "-e", harness], env=env, capture_output=True, text=True, timeout=30
    )
    assert done.returncode == 0, done.stderr
    return _json.loads(done.stdout)


class TestStatementSeparatorsInN8n:
    def test_prepare_graph_payload_no_longer_scans_for_separators(self):
        code = _node_code(_nodes_by_name(_load("rules_ingest"))["Prepare Graph Payload"])
        assert "stripStatementSeparators" not in code
        assert "inQuote" not in code, "a quote-tracking scanner would need the lexer's quoting rules"
        assert "dropTrailingSemicolon" in code

    def test_parse_cypher_strips_trailing_separator_and_appends_limit_only_when_needed(self):
        code = _node_code(_nodes_by_name(_load("graph_query"))["Parse Cypher"])
        assert r"[\s;]+$" in code
        assert r"LIMIT\s+" in code

    @pytest.mark.skipif(_NODE is None, reason="node is not available")
    @pytest.mark.parametrize(
        "cypher, expected",
        [
            ("MATCH (r:Rule {project: $project}) RETURN r", "MATCH (r:Rule {project: $project}) RETURN r LIMIT 50"),
            ("MATCH (r:Rule {project: $project}) RETURN r;", "MATCH (r:Rule {project: $project}) RETURN r LIMIT 50"),
            ("MATCH (r:Rule {project: $project}) RETURN r ; \n", "MATCH (r:Rule {project: $project}) RETURN r LIMIT 50"),
            ("MATCH (r:Rule {project: $project}) RETURN r;;", "MATCH (r:Rule {project: $project}) RETURN r LIMIT 50"),
            ("MATCH (r:Rule {project: $project}) RETURN r LIMIT 5", "MATCH (r:Rule {project: $project}) RETURN r LIMIT 5"),
            ("MATCH (r:Rule {project: $project}) RETURN r LIMIT 5;", "MATCH (r:Rule {project: $project}) RETURN r LIMIT 5"),
            ("MATCH (r:Rule {project: $project}) RETURN r limit $limit", "MATCH (r:Rule {project: $project}) RETURN r limit $limit"),
            (
                "MATCH (r:Rule {project: $project}) RETURN r ORDER BY r.x SKIP 2 LIMIT 7;",
                "MATCH (r:Rule {project: $project}) RETURN r ORDER BY r.x SKIP 2 LIMIT 7",
            ),
            # a `limit` property or string must not suppress the default LIMIT
            ("MATCH (r:Rule {project: $project}) RETURN r.limit", "MATCH (r:Rule {project: $project}) RETURN r.limit LIMIT 50"),
            (
                "MATCH (r:Rule {project: $project, SWRL: 'LIMIT 3'}) RETURN r",
                "MATCH (r:Rule {project: $project, SWRL: 'LIMIT 3'}) RETURN r LIMIT 50",
            ),
        ],
    )
    def test_parse_cypher_behaviour(self, cypher, expected):
        code = _node_code(_nodes_by_name(_load("graph_query"))["Parse Cypher"])
        result = _run_node_function(
            code,
            json_input={"valid": True, "cypher": cypher},
            items={"Build Cypher Prompt": {"project_name": "P1"}},
        )
        assert result["cypher"] == expected
        assert ";" not in result["cypher"].replace("'LIMIT 3'", "")

    @pytest.mark.skipif(_NODE is None, reason="node is not available")
    @pytest.mark.parametrize(
        "cypher, expected",
        [
            ("MERGE (r:Rule {Rule_Id: 'R_X', project: $project});", "MERGE (r:Rule {Rule_Id: 'R_X', project: $project})"),
            ("MERGE (r:Rule {Rule_Id: 'R_X', project: $project}) ;\n  ", "MERGE (r:Rule {Rule_Id: 'R_X', project: $project})"),
            ("MERGE (r:Rule {Rule_Id: 'R_X', project: $project})", "MERGE (r:Rule {Rule_Id: 'R_X', project: $project})"),
            # a `;` inside a string is content: kept, single- and double-quoted
            (
                "MERGE (r:Rule {Rule_Id: 'R_X', project: $project}) SET r.a = 'x;y'",
                "MERGE (r:Rule {Rule_Id: 'R_X', project: $project}) SET r.a = 'x;y'",
            ),
            (
                'MERGE (r:Rule {Rule_Id: \'R_X\', project: $project}) SET r.a = "x;y";',
                'MERGE (r:Rule {Rule_Id: \'R_X\', project: $project}) SET r.a = "x;y"',
            ),
            (
                "MERGE (r:Rule {Rule_Id: 'R_X', project: $project}) SET r.a = \"it's; fine\"",
                "MERGE (r:Rule {Rule_Id: 'R_X', project: $project}) SET r.a = \"it's; fine\"",
            ),
        ],
    )
    def test_prepare_graph_payload_only_drops_one_trailing_separator(self, cypher, expected):
        code = _node_code(_nodes_by_name(_load("rules_ingest"))["Prepare Graph Payload"])
        result = _run_node_function(
            code, json_input={"cypher": cypher, "project_name": "P1", "rules_text": "t"}
        )
        assert result["cypher"] == expected

    def test_both_prompts_teach_the_separator_rule(self):
        read_prompt = _node_code(_nodes_by_name(_load("graph_query"))["Build Cypher Prompt"])
        assert "semicolons" in read_prompt
        assert "pattern predicates" in read_prompt
        assert "label syntax with IS" in read_prompt
        write_prompt = _node_code(_nodes_by_name(_load("rules_ingest"))["Build LLM Prompt"])
        assert "ONE chained statement" in write_prompt
        assert "no backslash" in write_prompt
