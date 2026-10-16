"""Shared fail-closed path and file policies for hosted bundle preparation."""
import fnmatch
import hashlib
from pathlib import Path
import re

DEFAULT_FORBIDDEN = frozenset({'.secrets', 'dg_obsidian', 'publications', '.git', '.planning',
    '.degram', 'graphify-out', 'node_modules', '__pycache__', '.pytest_cache',
    'bin', 'obj', '.venv', 'profiles', 'personal-cv', 'personal-graph',
    '.env', 'credentials', 'secrets', 'private', 'id_rsa'})
HASH = re.compile(r'^[0-9a-f]{64}$')
SHA = re.compile(r'^[0-9a-f]{40}$')
IMAGE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[0-9a-f]{64}$')


def safe_path(value, forbidden=()):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value or ':' in value:
        raise ValueError('unsafe relative path')
    parts = value.split('/')
    banned = DEFAULT_FORBIDDEN | {str(x).casefold() for x in forbidden}
    if value.startswith('/') or any(not part or part in ('.', '..') or part.casefold() in banned for part in parts):
        raise ValueError('unsafe relative path')
    if any(part.casefold().startswith(('personal-cv', 'personal-graph', '.env')) for part in parts):
        raise ValueError('private path')
    if any(part.casefold().endswith(('.pem', '.key', '.p12', '.pfx', '.kdbx')) for part in parts):
        raise ValueError('private filename')
    return value


def pattern(value, forbidden=()):
    safe_path(value, forbidden)
    return value


def matches(path, glob):
    # Match components: ** consumes zero or more whole directories, while
    # fnmatch wildcards in any other component never cross a slash.
    parts, patterns = path.split('/'), glob.split('/')

    def match_from(i, j):
        if j == len(patterns):
            return i == len(parts)
        if patterns[j] == '**':
            return any(match_from(k, j + 1) for k in range(i, len(parts) + 1))
        return (i < len(parts) and fnmatch.fnmatchcase(parts[i], patterns[j]) and
                match_from(i + 1, j + 1))

    return match_from(0, 0)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scan_tree(root):
    """Return every regular file, rejecting links, junctions and case collisions."""
    found = {}
    folds = set()
    def walk(directory):
        for entry in directory.iterdir():
            relative = entry.relative_to(root).as_posix()
            safe_path(relative)
            folded = relative.casefold()
            if folded in folds:
                raise ValueError('case-fold collision')
            folds.add(folded)
            if entry.is_symlink() or entry.is_junction():
                raise ValueError('link in bundle')
            if entry.is_dir():
                walk(entry)
            elif entry.is_file():
                found[relative] = digest(entry.read_bytes())
            else:
                raise ValueError('unsupported bundle entry')
    walk(root)
    return dict(sorted(found.items()))
