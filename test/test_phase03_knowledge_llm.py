"""
Phase 03 Verification: n8n Knowledge Workflows + LLM Ingest and Query
Tests all 5 success criteria from Phase 3 plan.

Requires: running services at BASE_URL (default http://localhost:8080) and
          data-service at DATA_SERVICE_URL (default http://localhost:8080/data-service).

Workflow keys used:
  - knowledge-ingest
  - knowledge-query
"""

import os
import sys
import time
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", f"{BASE_URL}/data-service")
TEST_PROJECT = "test-phase03"

POLL_INTERVAL = 3    # seconds between polls
POLL_TIMEOUT = 90    # maximum seconds to wait for LLM completion


def _poll_execution_result(workflow_key: str, timeout: int = POLL_TIMEOUT) -> dict:
    """Poll /execution-result/latest/{workflow} until status == 'completed' or timeout."""
    url = f"{DATA_SERVICE_URL}/execution-result/latest/{workflow_key}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "completed":
                    return data
        except requests.RequestException:
            pass
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(
        f"Timed out waiting for workflow '{workflow_key}' to complete after {timeout}s"
    )


def test_sc1_ingest_prompt():
    """SC-1: POST to knowledge-ingest webhook creates a KnowledgeNote in Neo4j.

    Sends a NL prompt to /n8n/webhook/dg/knowledge-ingest.
    Asserts ack response has status 'accepted'.
    Polls execution-result until completed, then asserts noteId/title/tags in payload.
    Finally confirms the note appears in /knowledge/notes/{project}.
    """
    ingest_url = f"{BASE_URL}/n8n/webhook/dg/knowledge-ingest"
    resp = requests.post(
        ingest_url,
        json={
            "prompt_text": "The maximum building height in Zone B is 45 meters for residential towers",
            "project_name": TEST_PROJECT,
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"Ingest webhook expected 200, got {resp.status_code}: {resp.text}"
    ack = resp.json()
    assert ack.get("status") == "accepted", f"Expected status='accepted', got: {ack}"

    # Poll for completion
    result = _poll_execution_result("knowledge-ingest")
    assert result.get("status") == "completed", f"Expected completed, got: {result.get('status')}"
    payload = result.get("payload") or {}
    assert "noteId" in payload, f"Payload missing 'noteId': {payload}"
    assert "title" in payload, f"Payload missing 'title': {payload}"
    assert "tags" in payload, f"Payload missing 'tags': {payload}"

    # Confirm note appears in notes list
    notes_resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/notes/{TEST_PROJECT}", timeout=10)
    assert notes_resp.status_code == 200, f"List notes expected 200, got {notes_resp.status_code}"
    notes_data = notes_resp.json()
    assert "notes" in notes_data, f"Response missing 'notes' key: {notes_data}"
    assert len(notes_data["notes"]) >= 1, f"Expected at least 1 note, got {len(notes_data['notes'])}"
    first_note = notes_data["notes"][0]
    assert first_note.get("title"), f"Note title is empty: {first_note}"
    print(f"  SC-1 PASS: ingest created note with title='{first_note['title'][:60]}'")


def test_sc2_query_answer():
    """SC-2: POST to knowledge-query webhook returns an NL answer with Cypher.

    Sends a NL question to /n8n/webhook/dg/knowledge-query.
    Asserts ack response has status 'accepted'.
    Polls execution-result until completed, then asserts 'answer' and 'cypher' in payload.
    Verifies answer is non-empty and cypher contains 'knowledge_note_search'.
    """
    query_url = f"{BASE_URL}/n8n/webhook/dg/knowledge-query"
    resp = requests.post(
        query_url,
        json={
            "prompt_text": "What is the maximum building height?",
            "project_name": TEST_PROJECT,
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"Query webhook expected 200, got {resp.status_code}: {resp.text}"
    ack = resp.json()
    assert ack.get("status") == "accepted", f"Expected status='accepted', got: {ack}"

    # Poll for completion
    result = _poll_execution_result("knowledge-query")
    assert result.get("status") == "completed", f"Expected completed, got: {result.get('status')}"
    payload = result.get("payload") or {}
    assert "answer" in payload, f"Payload missing 'answer': {payload}"
    assert "cypher" in payload, f"Payload missing 'cypher': {payload}"
    assert payload["answer"], f"'answer' must be non-empty: {payload}"
    assert "knowledge_note_search" in payload["cypher"], (
        f"'cypher' must contain 'knowledge_note_search', got: {payload['cypher']}"
    )
    print(f"  SC-2 PASS: query returned answer='{str(payload['answer'])[:80]}'")


def test_sc3_session_insert():
    """SC-3: After SC-1 ingest, GET /knowledge/sessions/{project} contains an insert session.

    Verifies that a KnowledgeSession with mode='insert' was created during SC-1.
    Requires SC-1 to have run first.
    """
    resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/sessions/{TEST_PROJECT}", timeout=10)
    assert resp.status_code == 200, f"Sessions endpoint expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "sessions" in data, f"Response missing 'sessions' key: {data}"
    sessions = data["sessions"]
    assert len(sessions) >= 1, f"Expected at least 1 session, got {len(sessions)}"
    insert_sessions = [s for s in sessions if s.get("mode") == "insert"]
    assert insert_sessions, f"No session with mode='insert' found in: {sessions}"
    assert insert_sessions[0].get("prompt"), f"Insert session has empty prompt: {insert_sessions[0]}"
    print(f"  SC-3 PASS: found {len(insert_sessions)} insert session(s)")


def test_sc4_webhook_ack():
    """SC-4: POST to knowledge-ingest webhook returns HTTP 200 with status='accepted'.

    Verifies the ack response shape without polling for execution completion.
    Validates INFR-02: webhook is active and responds synchronously with accepted status.
    """
    ingest_url = f"{BASE_URL}/n8n/webhook/dg/knowledge-ingest"
    resp = requests.post(
        ingest_url,
        json={
            "prompt_text": "Minimum corridor width for evacuation routes must be at least 1.5 meters",
            "project_name": TEST_PROJECT,
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("status") == "accepted", f"Expected status='accepted', got: {body}"
    print(f"  SC-4 PASS: webhook ack returned status='accepted'")


def test_sc5_sessions_endpoint():
    """SC-5: GET /knowledge/sessions/{project} returns correctly shaped session records.

    Validates that the sessions endpoint returns 200 with project and sessions keys.
    Each session entry must have sessionId, mode, prompt, result, and createdAt fields.
    """
    resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/sessions/{TEST_PROJECT}", timeout=10)
    assert resp.status_code == 200, f"Sessions endpoint expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("project") == TEST_PROJECT, (
        f"Expected project='{TEST_PROJECT}', got '{data.get('project')}'"
    )
    assert "sessions" in data, f"Response missing 'sessions' key: {data}"
    assert isinstance(data["sessions"], list), f"'sessions' must be a list, got: {type(data['sessions'])}"
    for session in data["sessions"]:
        for key in ("sessionId", "mode", "prompt", "result", "createdAt"):
            assert key in session, f"Session missing key '{key}': {session}"
    print(f"  SC-5 PASS: sessions endpoint returned {len(data['sessions'])} session(s) with correct schema")


def cleanup():
    """Remove all test nodes from Neo4j for project 'test-phase03'."""
    try:
        # Delete all KnowledgeNote nodes (and their tags via DETACH DELETE)
        notes_resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/notes/{TEST_PROJECT}", timeout=10)
        if notes_resp.status_code == 200:
            for note in notes_resp.json().get("notes", []):
                requests.delete(f"{DATA_SERVICE_URL}/knowledge/note/{note['noteId']}", timeout=10)
        print(f"  Cleanup: deleted notes for project '{TEST_PROJECT}'")
    except Exception as e:
        print(f"  Cleanup warning (notes): {e}")

    try:
        # Delete KnowledgeSession and KnowledgeTag nodes directly via Neo4j HTTP
        # Using data-service proxy — no direct Neo4j access needed from test runner
        # Sessions are cleaned up by deleting via the graph; we rely on DETACH DELETE above
        # for tags and sessions not linked to notes.
        pass
    except Exception as e:
        print(f"  Cleanup warning (sessions): {e}")


if __name__ == "__main__":
    print("Phase 03 Verification: n8n Knowledge Workflows + LLM Ingest and Query")
    print("=" * 70)

    results = {}

    # SC-4 first — fast ack check, no polling needed
    print("\nSC-4: Webhook ack")
    try:
        test_sc4_webhook_ack()
        results["sc4"] = "PASS"
    except Exception as e:
        print(f"  FAIL: {e}")
        results["sc4"] = "FAIL"

    # SC-1: Ingest prompt — creates notes and insert sessions
    print("\nSC-1: Ingest prompt")
    try:
        test_sc1_ingest_prompt()
        results["sc1"] = "PASS"
    except Exception as e:
        print(f"  FAIL: {e}")
        results["sc1"] = "FAIL"

    # SC-3: Session check for insert — depends on SC-1
    print("\nSC-3: Session insert check")
    try:
        test_sc3_session_insert()
        results["sc3"] = "PASS"
    except Exception as e:
        print(f"  FAIL: {e}")
        results["sc3"] = "FAIL"

    # SC-2: Query answer — needs notes from SC-1
    print("\nSC-2: Query answer")
    try:
        test_sc2_query_answer()
        results["sc2"] = "PASS"
    except Exception as e:
        print(f"  FAIL: {e}")
        results["sc2"] = "FAIL"

    # SC-5: Sessions endpoint schema check
    print("\nSC-5: Sessions endpoint")
    try:
        test_sc5_sessions_endpoint()
        results["sc5"] = "PASS"
    except Exception as e:
        print(f"  FAIL: {e}")
        results["sc5"] = "FAIL"

    print("\n" + "=" * 70)
    print("RESULTS:")
    for k, v in results.items():
        print(f"  {k.upper()}: {v}")

    all_passed = all(v == "PASS" for v in results.values())
    if all_passed:
        print("\nALL SUCCESS CRITERIA PASSED")
    else:
        failed = [k for k, v in results.items() if v != "PASS"]
        print(f"\nFAILED: {', '.join(f.upper() for f in failed)}")

    print("\nCleaning up test data...")
    cleanup()

    sys.exit(0 if all_passed else 1)
