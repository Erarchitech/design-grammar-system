"""Unit tests for Phase 4 update flow: difflib logic and endpoint contracts."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import word_diff_html


def test_word_diff_html_insertion():
    result = word_diff_html("hello world", "hello beautiful world")
    assert '<span class="diff-ins">beautiful</span>' in result
    assert "hello" in result
    assert "world" in result


def test_word_diff_html_deletion():
    result = word_diff_html("hello beautiful world", "hello world")
    assert '<span class="diff-del">beautiful</span>' in result


def test_word_diff_html_replacement():
    result = word_diff_html("the red fox", "the blue fox")
    assert '<span class="diff-del">red</span>' in result
    assert '<span class="diff-ins">blue</span>' in result


def test_word_diff_html_no_changes():
    result = word_diff_html("identical text", "identical text")
    assert "<span" not in result
    assert result == "identical text"


def test_word_diff_html_empty_original():
    result = word_diff_html("", "new content")
    assert '<span class="diff-ins">new</span>' in result
    assert '<span class="diff-ins">content</span>' in result


def test_word_diff_html_empty_proposed():
    result = word_diff_html("old content", "")
    assert '<span class="diff-del">old</span>' in result
    assert '<span class="diff-del">content</span>' in result


from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


def test_match_returns_candidates():
    """UPDK-01: match returns candidate list ranked by score."""
    mock_rows = [
        {"noteId": "n1", "title": "Note One", "score": 0.9},
        {"noteId": "n2", "title": "Note Two", "score": 0.5},
    ]
    with patch("app.read_many", return_value=mock_rows):
        from app import knowledge_update_match, UpdateMatchRequest
        req = UpdateMatchRequest(prompt="test query", project="proj1")
        result = knowledge_update_match(req)
        assert result["candidates"] == mock_rows
        assert len(result["candidates"]) == 2


def test_match_empty_prompt_returns_400():
    """UPDK-01: empty prompt is rejected."""
    from app import knowledge_update_match, UpdateMatchRequest
    import pytest as _pytest
    from fastapi import HTTPException
    req = UpdateMatchRequest(prompt="   ", project="proj1")
    with _pytest.raises(HTTPException) as exc_info:
        knowledge_update_match(req)
    assert exc_info.value.status_code == 400


def test_confirm_409_on_stale_updatedAt():
    """UPDK-05 / D-08: confirm rejects when updatedAt mismatch."""
    from app import knowledge_update_confirm, UpdateConfirmRequest, NoteConfirmItem
    import pytest as _pytest
    from fastapi import HTTPException
    with patch("app.read_single", return_value={"updatedAt": "2026-01-01T00:00:00+00:00"}):
        req = UpdateConfirmRequest(
            prompt="update prompt",
            project="proj1",
            notes=[NoteConfirmItem(noteId="n1", content="new text", updatedAt="2025-12-31T00:00:00+00:00")],
        )
        with _pytest.raises(HTTPException) as exc_info:
            knowledge_update_confirm(req)
        assert exc_info.value.status_code == 409


def test_confirm_writes_and_creates_session():
    """UPDK-05 + UPDK-06: confirm writes content and creates KnowledgeSession."""
    from app import knowledge_update_confirm, UpdateConfirmRequest, NoteConfirmItem
    written_queries = []
    def mock_write(cypher, params):
        written_queries.append((cypher, params))
    with patch("app.read_single", return_value={"updatedAt": "2026-01-01T00:00:00+00:00"}), \
         patch("app.write_query", side_effect=mock_write):
        req = UpdateConfirmRequest(
            prompt="update prompt",
            project="proj1",
            notes=[NoteConfirmItem(noteId="n1", content="updated content", updatedAt="2026-01-01T00:00:00+00:00")],
        )
        result = knowledge_update_confirm(req)
        assert "n1" in result["affectedNoteIds"]
        assert result["sessionId"].startswith("ks-")
        # Two write_query calls: one SET content, one MERGE session
        assert len(written_queries) == 2
        assert "SET n.content" in written_queries[0][0]
        assert "KnowledgeSession" in written_queries[1][0]


def test_confirm_rejects_oversized_content():
    """Security: content over 100KB is rejected with 413."""
    from app import knowledge_update_confirm, UpdateConfirmRequest, NoteConfirmItem
    import pytest as _pytest
    from fastapi import HTTPException
    big_content = "x" * (100 * 1024 + 1)
    req = UpdateConfirmRequest(
        prompt="update",
        project="proj1",
        notes=[NoteConfirmItem(noteId="n1", content=big_content, updatedAt="2026-01-01T00:00:00+00:00")],
    )
    with _pytest.raises(HTTPException) as exc_info:
        knowledge_update_confirm(req)
    assert exc_info.value.status_code == 413
