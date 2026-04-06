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
