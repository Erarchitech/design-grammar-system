# -*- coding: utf-8 -*-
"""The four DG connector tools: routes, bodies and argument refusal.

A fake ``revit_get``/``revit_post`` records what each tool asks of Revit, so no
Revit and no pyRevit are needed. The tools must refuse an empty or oversized
``unique_ids`` list themselves, before any HTTP call.
"""

import asyncio
import json

import pytest
from mcp.server.fastmcp import FastMCP

from tools.dg_connector_tools import MAX_ELEMENTS, register_dg_connector_tools


def run(coro):
    return asyncio.run(coro)


class FakeRevit(object):
    def __init__(self, reply=None):
        self.gets = []
        self.posts = []
        self.reply = reply if reply is not None else {"status": "ok"}

    async def get(self, path, ctx=None):
        self.gets.append(path)
        return self.reply

    async def post(self, path, data=None, ctx=None):
        self.posts.append((path, data))
        return self.reply


@pytest.fixture
def probe():
    fake = FakeRevit()
    server = FastMCP("probe")
    register_dg_connector_tools(server, fake.get, fake.post)
    return server, fake


def call(server, name, args=None):
    result = run(server.call_tool(name, args or {}))
    content = result[0] if isinstance(result, tuple) else result
    return content[0].text


# --- routes and bodies ----------------------------------------------------------

def test_mapping_status_gets_its_route(probe):
    server, fake = probe
    assert json.loads(call(server, "dg_mapping_status")) == {"status": "ok"}
    assert fake.gets == ["/mapping_status/"]
    assert fake.posts == []


def test_start_mapping_posts_an_empty_body(probe):
    server, fake = probe
    call(server, "dg_start_mapping")
    assert fake.posts == [("/start_mapping/", {})]
    assert fake.gets == []


def test_show_elements_posts_the_unique_ids(probe):
    server, fake = probe
    call(server, "dg_show_elements", {"unique_ids": ["uid-a", "uid-b"]})
    assert fake.posts == [("/show_elements/", {"uniqueIds": ["uid-a", "uid-b"]})]


def test_show_elements_strips_blank_ids(probe):
    server, fake = probe
    call(server, "dg_show_elements", {"unique_ids": [" uid-a ", "", "  "]})
    assert fake.posts == [("/show_elements/", {"uniqueIds": ["uid-a"]})]


def test_clear_mapping_colours_posts_an_empty_body(probe):
    server, fake = probe
    call(server, "dg_clear_mapping_colours")
    assert fake.posts == [("/clear_colours/", {})]
    assert fake.gets == []


def test_route_payload_is_returned_as_json_text(probe):
    server, fake = probe
    fake.reply = {"sessionOpen": True, "sessionId": "ms-1", "questions": 2}
    assert json.loads(call(server, "dg_mapping_status")) == fake.reply


# --- argument refusal: no HTTP call ---------------------------------------------

@pytest.mark.parametrize("ids", [[], [""], ["   ", ""]])
def test_show_elements_refuses_an_empty_list_without_calling_revit(probe, ids):
    server, fake = probe
    outcome = json.loads(call(server, "dg_show_elements", {"unique_ids": ids}))
    assert outcome["status"] == "error"
    assert outcome["code"] == "BAD_REQUEST"
    assert outcome["field"] == "unique_ids"
    assert fake.posts == []


def test_show_elements_refuses_more_than_the_cap_without_calling_revit(probe):
    server, fake = probe
    ids = ["uid-{}".format(i) for i in range(MAX_ELEMENTS + 1)]
    outcome = json.loads(call(server, "dg_show_elements", {"unique_ids": ids}))
    assert outcome["code"] == "BAD_REQUEST"
    assert outcome["count"] == MAX_ELEMENTS + 1
    assert outcome["maxElements"] == MAX_ELEMENTS
    assert fake.posts == []


def test_show_elements_accepts_exactly_the_cap(probe):
    server, fake = probe
    ids = ["uid-{}".format(i) for i in range(MAX_ELEMENTS)]
    call(server, "dg_show_elements", {"unique_ids": ids})
    assert fake.posts[0][1] == {"uniqueIds": ids}


def test_refusal_is_a_structured_outcome_not_free_text(probe):
    server, fake = probe
    text = call(server, "dg_show_elements", {"unique_ids": []})
    assert not text.startswith("Error:")
    payload = json.loads(text)
    assert set(payload) >= {"status", "code", "error"}
