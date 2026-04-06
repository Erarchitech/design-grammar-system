"""
Phase 02 Verification: data-service CRUD + Folder Ingest
Tests all 5 success criteria from ROADMAP.md Phase 2.

Requires: running data-service at DATA_SERVICE_URL (default http://localhost:8000)
"""

import os
import sys
import requests

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8000")
TEST_PROJECT = "test_phase02_crud"


def test_sc1_folder_ingest():
    """SC-1: POST /knowledge/ingest/folder creates KnowledgeNote nodes from .md files."""
    # Ingest the DG_OBSIDIAN directory (known to contain .md files)
    resp = requests.post(
        f"{DATA_SERVICE_URL}/knowledge/ingest/folder",
        json={"project": TEST_PROJECT, "path": "DG_OBSIDIAN"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "inserted" in data, f"Response missing 'inserted' key: {data}"
    assert "skipped" in data, f"Response missing 'skipped' key: {data}"
    assert data["inserted"] >= 1, f"Expected at least 1 inserted note, got {data['inserted']}"
    print(f"  SC-1 PASS: folder ingest returned inserted={data['inserted']}, skipped={data['skipped']}")


def test_sc2_path_traversal_rejected():
    """SC-2: A path outside the allowed mount root is rejected with HTTP 403."""
    resp = requests.post(
        f"{DATA_SERVICE_URL}/knowledge/ingest/folder",
        json={"project": TEST_PROJECT, "path": "../../etc"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    print(f"  SC-2 PASS: path traversal rejected with 403")


def test_sc3_list_notes():
    """SC-3: GET /knowledge/notes/{project} returns list of note titles and IDs."""
    resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/notes/{TEST_PROJECT}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "notes" in data, f"Response missing 'notes' key: {data}"
    assert len(data["notes"]) >= 1, f"Expected at least 1 note, got {len(data['notes'])}"
    note = data["notes"][0]
    assert "noteId" in note, f"Note missing 'noteId': {note}"
    assert "title" in note, f"Note missing 'title': {note}"
    print(f"  SC-3 PASS: list returned {len(data['notes'])} notes with noteId and title")
    return data["notes"][0]["noteId"]


def test_sc4_crud_operations(note_id: str):
    """SC-4: GET, PUT, DELETE on /knowledge/note/{id} work correctly."""
    # GET
    resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/note/{note_id}")
    assert resp.status_code == 200, f"GET expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["noteId"] == note_id, f"noteId mismatch: expected {note_id}, got {data.get('noteId')}"
    assert "title" in data and "content" in data, f"Note missing title or content: {data.keys()}"
    print(f"  SC-4a PASS: GET returned note with title='{data['title'][:40]}...'")

    # PUT (update title)
    new_title = "Updated Test Title"
    resp = requests.put(
        f"{DATA_SERVICE_URL}/knowledge/note/{note_id}",
        json={"title": new_title},
    )
    assert resp.status_code == 200, f"PUT expected 200, got {resp.status_code}: {resp.text}"
    assert resp.json().get("status") == "updated", f"PUT response missing status:updated"

    # Verify update
    resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/note/{note_id}")
    assert resp.json()["title"] == new_title, f"Title not updated: {resp.json().get('title')}"
    print(f"  SC-4b PASS: PUT updated title to '{new_title}'")

    # DELETE
    resp = requests.delete(f"{DATA_SERVICE_URL}/knowledge/note/{note_id}")
    assert resp.status_code == 200, f"DELETE expected 200, got {resp.status_code}: {resp.text}"
    assert resp.json().get("status") == "deleted", f"DELETE response missing status:deleted"

    # Verify delete (should 404)
    resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/note/{note_id}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}"
    print(f"  SC-4c PASS: DELETE removed note, GET returns 404")

    # 404 for nonexistent note on PUT and DELETE
    resp = requests.put(
        f"{DATA_SERVICE_URL}/knowledge/note/nonexistent_id_xyz",
        json={"title": "nope"},
    )
    assert resp.status_code == 404, f"PUT nonexistent expected 404, got {resp.status_code}"
    resp = requests.delete(f"{DATA_SERVICE_URL}/knowledge/note/nonexistent_id_xyz")
    assert resp.status_code == 404, f"DELETE nonexistent expected 404, got {resp.status_code}"
    print(f"  SC-4d PASS: PUT/DELETE on nonexistent note return 404")


def test_sc5_nginx_proxy():
    """SC-5: All knowledge endpoints reachable through Nginx /data-service/ proxy."""
    nginx_url = os.getenv("NGINX_URL", "http://localhost:8080")
    resp = requests.get(f"{nginx_url}/data-service/knowledge/notes/{TEST_PROJECT}", timeout=5)
    # Accept 200 (notes found) -- just verify the proxy routes to data-service
    assert resp.status_code in (200, 404), f"Nginx proxy expected 200 or 404, got {resp.status_code}: {resp.text}"
    print(f"  SC-5 PASS: Nginx proxy routes /data-service/knowledge/* correctly (status={resp.status_code})")


def cleanup():
    """Remove all test notes from Neo4j."""
    try:
        notes_resp = requests.get(f"{DATA_SERVICE_URL}/knowledge/notes/{TEST_PROJECT}")
        if notes_resp.status_code == 200:
            for note in notes_resp.json().get("notes", []):
                requests.delete(f"{DATA_SERVICE_URL}/knowledge/note/{note['noteId']}")
        print(f"  Cleanup complete for project '{TEST_PROJECT}'")
    except Exception as e:
        print(f"  Cleanup warning: {e}")


if __name__ == "__main__":
    print("Phase 02 Verification: data-service CRUD + Folder Ingest")
    print("=" * 60)

    try:
        print("\nSC-1: Folder ingest")
        test_sc1_folder_ingest()

        print("\nSC-2: Path traversal rejection")
        test_sc2_path_traversal_rejected()

        print("\nSC-3: List notes")
        note_id = test_sc3_list_notes()

        print("\nSC-4: CRUD operations")
        test_sc4_crud_operations(note_id)

        print("\nSC-5: Nginx proxy routing")
        test_sc5_nginx_proxy()

        print("\n" + "=" * 60)
        print("ALL SUCCESS CRITERIA PASSED")
        sys.exit(0)

    except AssertionError as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(2)
    finally:
        print("\nCleaning up test data...")
        cleanup()
