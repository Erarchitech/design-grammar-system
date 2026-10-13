"""Run INSIDE the named data-service container. No credentials or response bodies printed."""
import hashlib
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request

from neo4j import GraphDatabase

PROJECT = 'dg1309-synthetic-capability'
BASE = 'http://127.0.0.1:8000'


def request(opener, path, body, csrf=False):
    headers = {'Content-Type': 'application/json'}
    if csrf:
        headers['X-DG-CSRF'] = '1'
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers=headers, method='POST')
    try:
        with opener.open(req, timeout=15) as response:
            return response.status, json.loads(response.read(65536))
    except urllib.error.HTTPError as error:
        return error.code, {}  # deliberately no echoed error body


def run():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    user = os.environ['DG_BOOTSTRAP_ADMIN_USER']
    password = os.environ['DG_BOOTSTRAP_ADMIN_PASSWORD']
    code, result = request(opener, '/auth/login', {'username': user, 'password': password}, csrf=True)
    if code != 200 or result.get('isAdmin') is not True or not any(c.name == 'dg_session' for c in jar):
        raise RuntimeError('admin login refused')
    body = {'project': PROJECT, 'path': 'hosted-ingest'}
    code, result = request(opener, '/knowledge/ingest/folder', body)
    if code not in (401, 403):
        raise RuntimeError('missing CSRF unexpectedly accepted')
    code, result = request(opener, '/knowledge/ingest/folder', body, csrf=True)
    if code != 200 or result.get('inserted') != 1 or result.get('skipped') != 0:
        raise RuntimeError('authenticated ingest failed')
    for path, expected in [('absent-synthetic-1309', 400), ('DG_OBSIDIAN', 400),
                           ('.secrets', 400), ('../../etc', 403)]:
        code, result = request(opener, '/knowledge/ingest/folder', {'project': PROJECT, 'path': path}, csrf=True)
        if code != expected:
            raise RuntimeError('negative ingest route anomaly')
    source = 'hosted-ingest/README.md'
    note_id = hashlib.sha256(f'{PROJECT}:{source}'.encode()).hexdigest()[:16]
    driver = GraphDatabase.driver(os.environ['NEO4J_URI'], auth=('neo4j', os.environ['NEO4J_PASSWORD']))
    try:
        with driver.session(database='neo4j') as session:
            rows = list(session.run('MATCH (n:SpecNote {project:$project}) RETURN n.noteId AS id, n.source AS source, n.title AS title',
                                    project=PROJECT))
            if len(rows) != 1 or rows[0]['id'] != note_id or rows[0]['source'] != source or rows[0]['title'] != 'Hosted synthetic ingest fixture':
                raise RuntimeError('scoped Neo4j note mismatch')
            other = session.run('MATCH (n:SpecNote) WHERE n.project <> $project RETURN count(n) AS count', project=PROJECT).single()
            if other['count'] != 0:
                raise RuntimeError('other project graph is nonempty')
    finally:
        driver.close()
    return {'admin_login': True, 'csrf_denied': True, 'ingest_inserted': 1,
            'neo4j_scoped_notes': 1, 'denied_paths': 4}


if __name__ == '__main__':
    try:
        print(json.dumps(run(), sort_keys=True))
    except Exception:
        print('{"error":"data-service capability failed"}', file=sys.stderr)
        sys.exit(1)
