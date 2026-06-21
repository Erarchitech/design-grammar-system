"""
Phase 2 conceptual export: graphify graph.json -> DG_OBSIDIAN/graphify/communities/.

Replaces the old method-level _export_obsidian.py approach (1772 files, one
per node) with one note per community (>= MIN_COMMUNITY_SIZE nodes), each
listing its top member nodes and cross-linked to existing curated notes in
DG_OBSIDIAN/knowledge/* and DG_OBSIDIAN/atlas/* via keyword overlap.

Idempotent: re-running regenerates all community notes from current graph.json.
Does not touch curated notes' main body — only appends/refreshes a managed
"## Graph connections" section, delimited by markers, so manual edits survive re-runs.

Usage: run after `/graphify` or `/graphify --update` rebuilds graphify-out/graph.json.
    "$(cat graphify-out/.graphify_python)" scripts/export_graphify_conceptual.py
"""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH_JSON = ROOT / "graphify-out" / "graph.json"
COMM_DIR = ROOT / "DG_OBSIDIAN" / "graphify" / "communities"
CURATED_DIRS = [ROOT / "DG_OBSIDIAN" / "knowledge", ROOT / "DG_OBSIDIAN" / "atlas"]
GRAPH_INDEX = ROOT / "DG_OBSIDIAN" / "graphify" / "Graph Index.md"
# Diff index: maps community filename stem -> content hash, so re-runs only
# rewrite notes whose content actually changed (clean git diffs, stable links).
EXPORT_INDEX = ROOT / "graphify-out" / "graphify_export_index.json"

MIN_COMMUNITY_SIZE = 5
TOP_MEMBERS_SHOWN = 12
MARKER_START = "<!-- graphify:connections:start -->"
MARKER_END = "<!-- graphify:connections:end -->"

STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "for", "and", "or", "in", "on",
    "with", "as", "by", "from", "this", "that", "code", "node", "nodes", "file",
    "component", "service", "test", "tests", "cs", "json", "md", "py", "js",
}


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|#^[\]]', "", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:150] if len(cleaned) > 150 else cleaned


def keywords(text: str | None) -> set[str]:
    if not text:
        return set()
    words = re.findall(r"[A-Za-zА-Яа-яёЁ]{3,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def load_graph():
    data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in data["nodes"]}
    edges = data.get("links", data.get("edges", []))
    return data, nodes, edges


def build_communities(nodes: dict) -> dict[int, list[dict]]:
    communities: dict[int, list[dict]] = {}
    for n in nodes.values():
        cid = n.get("community")
        if cid is not None:
            communities.setdefault(int(cid), []).append(n)
    return communities


def community_label(cid: int, members: list[dict]) -> str:
    for m in members:
        if m.get("community_name"):
            return m["community_name"]
    return f"Community {cid}"


def load_curated_notes() -> dict[Path, set[str]]:
    """Map curated note path -> its keyword set (title only — body text is too
    generic across this codebase and produces false-positive overlaps)."""
    notes = {}
    for d in CURATED_DIRS:
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            notes[f] = keywords(f.stem)
    return notes


MIN_KEYWORD_OVERLAP = 2


def match_curated_notes(community_kw: set[str], curated: dict[Path, set[str]], top_n: int = 3) -> list[Path]:
    scored = []
    for path, kw in curated.items():
        overlap = len(community_kw & kw)
        if overlap >= MIN_KEYWORD_OVERLAP:
            scored.append((overlap, path))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:top_n]]


def write_community_note(cid: int, members: list[dict], curated: dict[Path, set[str]], edges_count: int, fname: str):
    label = community_label(cid, members)
    note_path = COMM_DIR / f"{fname}.md"

    member_kw: set[str] = set()
    for m in members:
        member_kw |= keywords(m.get("label", ""))
        member_kw |= keywords(m.get("source_file", ""))

    matches = match_curated_notes(member_kw, curated)

    ftypes = Counter(m.get("file_type", "unknown") for m in members)
    top_members = sorted(members, key=lambda m: len(m.get("label", "")), reverse=True)[:TOP_MEMBERS_SHOWN]

    lines = [
        "---",
        f"community_id: {cid}",
        f"nodes_count: {len(members)}",
        f"tags: [graphify/community, {_obsidian_tag(label)}]",
        "graphify_snapshot: graphify-2026-06-22",
        "---",
        "",
        f"# {label}",
        "",
        f"> Автоматически сгенерировано graphify. **{len(members)} nodes**, типы: "
        + ", ".join(f"{k}={v}" for k, v in ftypes.most_common()),
        "",
        "## Ключевые узлы",
        "",
    ]
    for m in top_members:
        loc = f" `{m.get('source_location', '')}`" if m.get("source_location") else ""
        src = f" — {m.get('source_file')}" if m.get("source_file") else ""
        lines.append(f"- **{m.get('label', m['id'])}**{loc}{src}")
    if len(members) > TOP_MEMBERS_SHOWN:
        lines.append(f"- ... и ещё {len(members) - TOP_MEMBERS_SHOWN} узлов")

    lines += ["", "## Связанные curated notes", ""]
    if matches:
        for p in matches:
            lines.append(f"- [[{p.stem}]]")
    else:
        lines.append("_Автоматических совпадений не найдено._")

    lines += [
        "",
        "## Смотрите также",
        "",
        "- [[../Graph Index|Graph Index]] — все сообщества",
        "",
        "---",
        "",
        "*Сгенерировано: export_graphify_conceptual.py · Источник: graphify community detection*",
        "",
    ]

    content = "\n".join(lines)
    return note_path, label, matches, content


def _obsidian_tag(label: str) -> str:
    tag = re.sub(r"[^A-Za-zА-Яа-яёЁ0-9]+", "-", label.lower()).strip("-")
    return tag[:50] if tag else "community"


def _set_frontmatter_list(text: str, key: str, values: list[str]) -> str:
    """Set a flat YAML list key in the note's frontmatter (forward mapping).

    Line-based, no pyyaml dependency. Removes any existing block for `key`
    (the key line + its `  - item` children) and inserts a fresh inline list.
    Creates a frontmatter block if the note has none.
    """
    inline = "[" + ", ".join(f'"{v}"' for v in values) + "]"
    new_line = f"{key}: {inline}"

    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            fm = text[4:end]
            rest = text[end + 4:]
            # Drop existing key (inline form or block form with `  -` children)
            fm_lines = fm.split("\n")
            cleaned = []
            skip_children = False
            for ln in fm_lines:
                if re.match(rf"^{re.escape(key)}\s*:", ln):
                    skip_children = True
                    continue
                if skip_children and re.match(r"^\s+-\s", ln):
                    continue
                skip_children = False
                cleaned.append(ln)
            cleaned = [ln for ln in cleaned if ln.strip() != ""]
            cleaned.append(new_line)
            return "---\n" + "\n".join(cleaned) + "\n---" + rest

    # No frontmatter — create one
    return f"---\n{new_line}\n---\n\n" + text


def backlink_curated_notes(community_to_curated: dict[tuple[str, str], list[Path]]):
    """Insert/refresh a managed '## Graph connections' section in curated notes,
    AND set a `graphify_communities` frontmatter key (forward mapping).

    community_to_curated keys are (fname, display_label) pairs so disambiguated
    filenames (collision suffix) don't leak into the link's display text.
    """
    curated_to_communities: dict[Path, list[tuple[str, str]]] = {}
    for (fname, label), paths in community_to_curated.items():
        for p in paths:
            curated_to_communities.setdefault(p, []).append((fname, label))

    updated = 0
    for path, comm_entries in curated_to_communities.items():
        text = path.read_text(encoding="utf-8")

        ordered = sorted(set(comm_entries), key=lambda x: x[1])
        block_lines = [MARKER_START, "## Graph connections", ""]
        for fname, label in ordered:
            block_lines.append(f"- [[graphify/communities/{fname}|{label}]]")
        block_lines.append(MARKER_END)
        block = "\n".join(block_lines)

        if MARKER_START in text and MARKER_END in text:
            text = re.sub(
                re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
                block,
                text,
                flags=re.DOTALL,
            )
        else:
            text = text.rstrip() + "\n\n" + block + "\n"

        # Forward mapping: graphify_communities frontmatter key
        text = _set_frontmatter_list(text, "graphify_communities", [label for _, label in ordered])

        path.write_text(text, encoding="utf-8")
        updated += 1
    return updated


def regenerate_graph_index(written: list[tuple[int, str, int, Path]], data: dict, total_communities: int):
    """Rewrite the auto-generated table in Graph Index.md from real export results.
    Keeps the hand-written usage/MCP sections, replaces only the table block."""
    total_nodes = len(data["nodes"])
    total_edges = len(data.get("links", data.get("edges", [])))

    by_size = sorted(written, key=lambda x: -x[2])
    rows = []
    for cid, label, count, path in by_size[:40]:
        rel = f"communities/{path.stem}"
        rows.append(f"| [[{rel}\\|{label}]] | {count} |")

    table = "\n".join(["| Community | Nodes |", "|-----------|-------|"] + rows)

    index_text = GRAPH_INDEX.read_text(encoding="utf-8") if GRAPH_INDEX.exists() else ""
    start_marker = "<!-- graphify:index:start -->"
    end_marker = "<!-- graphify:index:end -->"
    block = (
        f"{start_marker}\n"
        f"> {total_nodes} nodes · {total_edges} edges · {total_communities} communities "
        f"({len(written)} shown, {total_communities - len(written)} thin omitted)\n\n"
        f"{table}\n"
        f"{end_marker}"
    )
    if start_marker in index_text and end_marker in index_text:
        index_text = re.sub(
            re.escape(start_marker) + r".*?" + re.escape(end_marker), block, index_text, flags=re.DOTALL
        )
    else:
        index_text = index_text.rstrip() + "\n\n## Сообщества (топ-40 по размеру)\n\n" + block + "\n"
    GRAPH_INDEX.write_text(index_text, encoding="utf-8")


def main():
    data, nodes, edges = load_graph()
    communities = build_communities(nodes)
    curated = load_curated_notes()

    COMM_DIR.mkdir(parents=True, exist_ok=True)

    edge_count_per_community: dict[int, int] = Counter()
    for e in edges:
        src_c = nodes.get(e.get("source"), {}).get("community")
        tgt_c = nodes.get(e.get("target"), {}).get("community")
        if src_c is not None and src_c == tgt_c:
            edge_count_per_community[int(src_c)] += 1

    eligible = {cid: members for cid, members in communities.items() if len(members) >= MIN_COMMUNITY_SIZE}
    print(f"Total communities: {len(communities)}, eligible (>= {MIN_COMMUNITY_SIZE} nodes): {len(eligible)}")

    # Disambiguate filename collisions (different community_id, same label) by
    # appending the community id, mirroring graphify's own node-filename dedup.
    seen_fnames: dict[str, int] = {}
    cid_fname: dict[int, str] = {}
    for cid, members in sorted(eligible.items()):
        base = safe_filename(community_label(cid, members))
        if base in seen_fnames:
            seen_fnames[base] += 1
            cid_fname[cid] = f"{base} ({cid})"
        else:
            seen_fnames[base] = 0
            cid_fname[cid] = base

    old_index = {}
    if EXPORT_INDEX.exists():
        try:
            old_index = json.loads(EXPORT_INDEX.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            old_index = {}

    community_to_curated: dict[tuple[str, str], list[Path]] = {}
    written = []          # (cid, label, count, path) for ALL eligible (drives index)
    new_index = {}
    n_changed = n_unchanged = 0
    for cid, members in sorted(eligible.items(), key=lambda x: -len(x[1])):
        note_path, label, matches, content = write_community_note(
            cid, members, curated, edge_count_per_community.get(cid, 0), cid_fname[cid]
        )
        written.append((cid, label, len(members), note_path))
        if matches:
            community_to_curated[(cid_fname[cid], label)] = matches

        stem = cid_fname[cid]
        chash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        new_index[stem] = chash
        # Diff-based: only touch disk if content changed or file is missing.
        if old_index.get(stem) != chash or not note_path.exists():
            note_path.write_text(content, encoding="utf-8")
            n_changed += 1
        else:
            n_unchanged += 1

    # Prune community notes whose community disappeared since last run.
    pruned = 0
    for stale_stem in set(old_index) - set(new_index):
        stale_path = COMM_DIR / f"{stale_stem}.md"
        if stale_path.exists():
            stale_path.unlink()
            pruned += 1

    EXPORT_INDEX.write_text(json.dumps(new_index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Community notes: {n_changed} written/changed, {n_unchanged} unchanged, {pruned} pruned ({len(written)} total)")

    backlinked = backlink_curated_notes(community_to_curated)
    print(f"Backlinked {backlinked} curated notes with Graph connections section")

    regenerate_graph_index(written, data, len(communities))
    print(f"Regenerated {GRAPH_INDEX}")

    return written


if __name__ == "__main__":
    main()
