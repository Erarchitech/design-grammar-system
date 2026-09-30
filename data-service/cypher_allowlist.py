"""Fail-closed allowlist guard for LLM-written Cypher (Phase 1205, CR-03/CR-04).

Two earlier rounds tried to prove tenant isolation by pattern-matching model
text with regexes and then blocklisting each bypass the reviewer found. Both
rounds were bypassed again (WITH re-binding, Unicode identifiers, string
concatenation in a merge key, unlabeled writes). This module replaces that
approach: the Cypher is tokenised with a small lexer and parsed against a tiny
grammar, and anything the grammar does not positively recognise is a violation.
There is no "skip what we cannot read" path.

Two profiles share the lexer:

* read (`graph_query`, and the `/mcp` `neo4j_query` tool): `MATCH`,
  `OPTIONAL MATCH`, `WHERE`, `RETURN` (`DISTINCT`, `AS`), `ORDER BY`, `SKIP`,
  `LIMIT`, plus a fixed list of scalar/aggregate functions. Every node pattern
  must bind a variable and carry the map entry `project: $project` at its
  declaration (bare references to an already declared variable are the only
  other form). No `WITH`/`UNWIND`/`CALL`/`UNION`/`FOREACH`/`LOAD`, no
  subquery blocks, no writes, no procedures, no variable-length paths.
* write (`rule_ingest`, `rule_edit`): `MERGE`, `MATCH` (no `WHERE`) and `SET`
  only. Every declared node has exactly one label from the schema set, a
  complete single string-literal identity key and `project: $project`; `SET`
  is limited to `var.prop = <literal>` on a bound variable and never touches
  `project` or `graph`; relationships are one of the four ingest types between
  bound nodes with literal properties.

Lexical rules (both profiles): only ASCII letters/digits/underscore in
identifiers, standard punctuation, and string contents. Backticks, comments,
non-ASCII outside string literals, control characters and unterminated strings
are violations, never stripped and trusted. String literals follow Neo4j's own
backslash-escape rules, so this lexer and the server agree on where a string
ends.

All functions are pure and return the `{code, message, path}` violation shape
used by every other check in `dg_context.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Violation = dict[str, Any]

_LETTERS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_DIGITS = frozenset("0123456789")
_IDENT_PART = _LETTERS | _DIGITS
_WHITESPACE = frozenset(" \t\r\n")
# `|` only survives the lexer so relationship-type alternatives can be read;
# both grammars reject it everywhere else.
_PUNCT = frozenset("()[]{}:,.=<>+-*/%^|;~")


def _violation(code: str, what: str, where: str, how: str) -> Violation:
    return {
        "code": code,
        "message": f"{what}. Where: {where}. How to fix: {how}.",
        "path": where,
    }


class _Fatal(Exception):
    """A violation the parser cannot recover from -- parsing stops."""

    def __init__(self, violation: Violation) -> None:
        super().__init__(violation["message"])
        self.violation = violation


@dataclass(frozen=True)
class Tok:
    kind: str  # IDENT | NUMBER | STRING | PARAM | PUNCT
    text: str  # raw source text (STRING: without the quotes)
    pos: int

    @property
    def upper(self) -> str:
        return self.text.upper()


_READ_HOW = (
    "write a plain read-only query: MATCH/OPTIONAL MATCH ... WHERE ... RETURN "
    "... ORDER BY ... SKIP ... LIMIT, every node bound to a variable and "
    "declared as (v:Label {project: $project}), with no WITH, UNWIND, CALL, "
    "UNION, subquery blocks, comments, backticks or procedures"
)
_WRITE_HOW = (
    "emit only MERGE (v:Label {<key>: '<literal>', project: $project, graph: "
    "'<graph>'}), relationship MERGEs between those variables, and SET "
    "v.prop = '<literal>' -- no comments, backticks, WITH, DELETE, CALL, "
    "concatenation or functions"
)


def tokenize(cypher: str, how: str) -> list[Tok]:
    """Lex `cypher`, raising `_Fatal` on the first character or construct the
    guard does not allow."""
    toks: list[Tok] = []
    i, n = 0, len(cypher)

    def fail(code: str, what: str, where: str) -> _Fatal:
        return _Fatal(_violation(code, what, where, how))

    while i < n:
        ch = cypher[i]
        if ch in _WHITESPACE:
            i += 1
            continue
        if ch in ("'", '"'):
            quote, j = ch, i + 1
            while j < n:
                cj = cypher[j]
                if cj == "\\":
                    j += 2
                    continue
                if cj == quote:
                    break
                if ord(cj) < 0x20 and cj not in _WHITESPACE:
                    raise fail(
                        "unsupported_syntax",
                        "A control character inside a string literal is not permitted",
                        f"offset {j}",
                    )
                j += 1
            if j >= n:
                raise fail(
                    "unsupported_syntax",
                    "An unterminated string literal is not permitted",
                    cypher[i : i + 40],
                )
            toks.append(Tok("STRING", cypher[i + 1 : j], i))
            i = j + 1
            continue
        if ch == "`":
            raise fail(
                "unsupported_syntax",
                "A backtick-quoted identifier is not permitted",
                "`",
            )
        if ch == "/" and i + 1 < n and cypher[i + 1] in ("/", "*"):
            raise fail("unsupported_syntax", "A comment is not permitted", "comment")
        if ch in _LETTERS:
            j = i + 1
            while j < n and cypher[j] in _IDENT_PART:
                j += 1
            toks.append(Tok("IDENT", cypher[i:j], i))
            i = j
            continue
        if ch in _DIGITS:
            j = i + 1
            while j < n and cypher[j] in _DIGITS:
                j += 1
            if j + 1 < n and cypher[j] == "." and cypher[j + 1] in _DIGITS:
                j += 1
                while j < n and cypher[j] in _DIGITS:
                    j += 1
            if j < n and cypher[j] in ("e", "E"):
                k = j + 1
                if k < n and cypher[k] in ("+", "-"):
                    k += 1
                if k < n and cypher[k] in _DIGITS:
                    while k < n and cypher[k] in _DIGITS:
                        k += 1
                    j = k
            if j < n and cypher[j] in _LETTERS:
                raise fail(
                    "unsupported_syntax",
                    "A malformed number is not permitted",
                    cypher[i : j + 1],
                )
            toks.append(Tok("NUMBER", cypher[i:j], i))
            i = j
            continue
        if ch == "$":
            j = i + 1
            while j < n and cypher[j] in _IDENT_PART:
                j += 1
            if j == i + 1:
                raise fail(
                    "unsupported_syntax",
                    "A parameter reference without a plain ASCII name is not permitted",
                    cypher[i : i + 10],
                )
            toks.append(Tok("PARAM", cypher[i + 1 : j], i))
            i = j
            continue
        if ch in _PUNCT:
            toks.append(Tok("PUNCT", ch, i))
            i += 1
            continue
        shown = ch if ch.isascii() and ch.isprintable() else f"U+{ord(ch):04X}"
        raise fail(
            "unsupported_syntax",
            "A character outside the allowed ASCII Cypher set is not permitted "
            "(non-ASCII identifiers included)",
            shown,
        )
    return toks


# ── shared parser machinery ─────────────────────────────────────────────────

# Words that begin a clause or statement part this guard never allows. Seen at
# a clause boundary, or anywhere inside an expression, they are reported as
# `forbidden_clause` (never analysed).
FORBIDDEN_CLAUSE_WORDS: frozenset[str] = frozenset(
    {
        "WITH", "UNWIND", "CALL", "UNION", "FOREACH", "LOAD", "CSV", "CREATE",
        "MERGE", "SET", "DELETE", "REMOVE", "DETACH", "NODETACH", "DROP",
        "USE", "YIELD", "START", "ALTER", "GRANT", "DENY", "REVOKE", "SHOW",
        "TERMINATE", "FINISH", "INSERT", "COMMIT", "EXPLAIN", "PROFILE",
    }
)

# Clause words that end an expression at its top level (nested inside
# brackets they are a violation).
_EXPR_STOP_WORDS: frozenset[str] = frozenset(
    {
        "MATCH", "OPTIONAL", "WHERE", "RETURN", "ORDER", "SKIP", "LIMIT", "AS",
        "ASC", "DESC", "ASCENDING", "DESCENDING",
    }
)

# Words after which a `(` is a grouping or a pattern, not a function call.
_PAREN_KEYWORDS: frozenset[str] = frozenset(
    {
        "AND", "OR", "XOR", "NOT", "IN", "WHEN", "THEN", "ELSE", "CASE", "IS",
        "CONTAINS", "STARTS", "ENDS", "WHERE", "RETURN", "MATCH", "BY", "ON",
    }
)

# Words after which a `{` may open a map literal (they are operators, never a
# subquery introducer like EXISTS/COUNT/COLLECT).
_MAP_OK_AFTER: frozenset[str] = frozenset(
    {"AND", "OR", "XOR", "NOT", "IN", "WHEN", "THEN", "ELSE", "CASE", "RETURN", "BY"}
)

# Scalar and aggregate functions a read-only query may call. Namespaced
# functions (`apoc.x.y(...)`, `db.x(...)`) and anything not listed are
# rejected.
READ_FUNCTIONS: frozenset[str] = frozenset(
    {
        "COUNT", "COLLECT", "SUM", "MIN", "MAX", "AVG", "SIZE", "TOLOWER",
        "TOUPPER", "COALESCE", "TOSTRING", "TOINTEGER", "TOFLOAT", "TOBOOLEAN",
        "TRIM", "LTRIM", "RTRIM", "SUBSTRING", "SPLIT", "REPLACE", "LEFT",
        "RIGHT", "HEAD", "LAST", "TAIL", "REVERSE", "ABS", "CEIL", "FLOOR",
        "ROUND", "SQRT", "LABELS", "TYPE", "KEYS", "EXISTS", "ISEMPTY", "RANGE",
        "ID", "ELEMENTID", "PROPERTIES",
    }
)

WRITE_NODE_IDENTITY_KEY: dict[str, str] = {
    "Rule": "Rule_Id",
    "Atom": "Atom_Id",
    "Var": "name",
    "Literal": "lex",
    "Builtin": "iri",
    "Class": "iri",
    "DatatypeProperty": "iri",
    "ObjectProperty": "iri",
}
WRITE_REL_TYPES: frozenset[str] = frozenset({"HAS_BODY", "HAS_HEAD", "REFERS_TO", "ARG"})
_PROTECTED_SET_KEYS: frozenset[str] = frozenset({"project", "graph"})
_LITERAL_WORDS = frozenset({"true", "false", "null"})


class _Parser:
    def __init__(self, toks: list[Tok], *, how: str, mode: str) -> None:
        self.toks = toks
        self.i = 0
        self.how = how
        self.mode = mode  # "read" | "write"
        self.violations: list[Violation] = []
        self.node_vars: set[str] = set()
        self.rel_vars: set[str] = set()
        self.saw_project_param = False

    # -- token helpers ----------------------------------------------------
    def peek(self, offset: int = 0) -> Tok | None:
        j = self.i + offset
        return self.toks[j] if j < len(self.toks) else None

    def next(self) -> Tok:
        tok = self.peek()
        if tok is None:
            raise self.unsupported("The query ends where more Cypher is required", "end of query")
        self.i += 1
        return tok

    def is_punct(self, text: str, offset: int = 0) -> bool:
        tok = self.peek(offset)
        return tok is not None and tok.kind == "PUNCT" and tok.text == text

    def is_word(self, word: str, offset: int = 0) -> bool:
        tok = self.peek(offset)
        return tok is not None and tok.kind == "IDENT" and tok.upper == word

    def accept_punct(self, text: str) -> bool:
        if self.is_punct(text):
            self.i += 1
            return True
        return False

    def expect_punct(self, text: str) -> Tok:
        if not self.is_punct(text):
            raise self.unsupported(
                f"Expected '{text}' here", self.describe(self.peek())
            )
        return self.next()

    def describe(self, tok: Tok | None) -> str:
        if tok is None:
            return "end of query"
        return tok.text if tok.kind != "STRING" else "'" + tok.text[:30] + "'"

    # -- violation builders -------------------------------------------------
    def unsupported(self, what: str, where: str) -> _Fatal:
        return _Fatal(_violation("unsupported_syntax", what, where, self.how))

    def forbidden(self, word: str) -> _Fatal:
        return _Fatal(
            _violation(
                "forbidden_clause",
                f"'{word}' is not permitted in this Cypher",
                word,
                self.how,
            )
        )

    def record(self, code: str, what: str, where: str) -> None:
        self.violations.append(_violation(code, what, where, self.how))

    def reject_clause_word(self, tok: Tok | None) -> _Fatal:
        if tok is not None and tok.kind == "IDENT" and tok.upper in FORBIDDEN_CLAUSE_WORDS:
            return self.forbidden(tok.upper)
        return self.unsupported(
            "This construct is not on the allowlist", self.describe(tok)
        )

    # -- literals and property maps ----------------------------------------
    def read_literal(self, *, key: str, code: str = "unsupported_syntax") -> Tok:
        """One literal token (string, number, optionally negated, true/false/
        null) or a `$param`; anything else -- concatenation, a function call, a
        property lookup -- is fatal."""
        tok = self.next()
        if tok.kind in ("STRING", "PARAM"):
            if tok.kind == "PARAM" and tok.text == "project":
                self.saw_project_param = True
            return tok
        if tok.kind == "NUMBER":
            return tok
        if tok.kind == "PUNCT" and tok.text == "-" and (self.peek() and self.peek().kind == "NUMBER"):
            return self.next()
        if tok.kind == "IDENT" and tok.text.lower() in _LITERAL_WORDS:
            return tok
        raise _Fatal(
            _violation(
                code,
                f"The value of `{key}` is not a single literal or $parameter",
                self.describe(tok),
                self.how,
            )
        )

    def read_map(self, *, code: str = "unsupported_syntax") -> dict[str, Tok]:
        """`{k: literal, ...}` -- the opening `{` is next."""
        self.expect_punct("{")
        entries: dict[str, Tok] = {}
        if self.accept_punct("}"):
            return entries
        while True:
            key_tok = self.next()
            if key_tok.kind != "IDENT":
                raise self.unsupported("A property map key must be a plain name", self.describe(key_tok))
            self.expect_punct(":")
            value = self.read_literal(key=key_tok.text, code=code)
            if key_tok.text in entries:
                raise self.unsupported(
                    f"The property map repeats the key `{key_tok.text}`", key_tok.text
                )
            entries[key_tok.text] = value
            if self.accept_punct(","):
                continue
            self.expect_punct("}")
            return entries

    # -- node and relationship patterns ---------------------------------------
    def read_node_shape(self) -> tuple[str | None, list[str], dict[str, Tok] | None]:
        self.expect_punct("(")
        var: str | None = None
        labels: list[str] = []
        nxt = self.peek()
        if nxt is not None and nxt.kind == "IDENT":
            var = self.next().text
        while self.is_punct(":"):
            self.i += 1
            label = self.next()
            if label.kind != "IDENT":
                raise self.unsupported("A label must be a plain name", self.describe(label))
            labels.append(label.text)
            if self.is_punct("|"):
                raise self.unsupported("A label expression is not permitted", label.text + "|")
        props: dict[str, Tok] | None = None
        if self.is_punct("{"):
            props = self.read_map(
                code="unanalysable_key" if self.mode == "write" else "unsupported_syntax"
            )
        if not self.is_punct(")"):
            raise self.unsupported(
                "A node pattern may hold only a variable, labels and a literal "
                "property map (no inline WHERE, parameter map or label expression)",
                self.describe(self.peek()),
            )
        self.i += 1
        return var, labels, props

    def check_project_entry(self, props: dict[str, Tok] | None, where: str) -> bool:
        """True when the map carries exactly `project: $project`."""
        if not props or "project" not in props:
            return False
        value = props["project"]
        if value.kind == "PARAM" and value.text == "project":
            return True
        if value.kind == "STRING":
            self.record(
                "project_literal",
                f"`project` is set from the string literal '{value.text}' instead "
                "of the bound $project parameter",
                where,
            )
        else:
            self.record(
                "missing_project_scope",
                "`project` must be exactly the bound $project parameter",
                where,
            )
        return False

    def at_rel_start(self, base: int = 0) -> bool:
        first = self.peek(base)
        if first is None or first.kind != "PUNCT":
            return False
        j = base
        if first.text == "<":
            j += 1
            second = self.peek(j)
            if second is None or not (second.kind == "PUNCT" and second.text == "-"):
                return False
            first = second
        if first.text != "-":
            return False
        after = self.peek(j + 1)
        if after is None or after.kind != "PUNCT":
            return False
        if after.text == "[":
            return True
        if after.text == "-":
            tail = self.peek(j + 2)
            if tail is not None and tail.kind == "PUNCT" and tail.text == ">":
                tail = self.peek(j + 3)
            return tail is not None and tail.kind == "PUNCT" and tail.text == "("
        return False

    def read_rel(self) -> tuple[str | None, list[str], dict[str, Tok] | None]:
        self.accept_punct("<")
        self.expect_punct("-")
        var: str | None = None
        types: list[str] = []
        props: dict[str, Tok] | None = None
        if self.accept_punct("["):
            nxt = self.peek()
            if nxt is not None and nxt.kind == "IDENT":
                var = self.next().text
            if self.accept_punct(":"):
                while True:
                    type_tok = self.next()
                    if type_tok.kind != "IDENT":
                        raise self.unsupported("A relationship type must be a plain name", self.describe(type_tok))
                    types.append(type_tok.text)
                    if self.accept_punct("|"):
                        self.accept_punct(":")
                        continue
                    break
            if self.is_punct("*"):
                raise self.unsupported("A variable-length relationship is not permitted", "*")
            if self.is_punct("{"):
                props = self.read_map(
                    code="unanalysable_key" if self.mode == "write" else "unsupported_syntax"
                )
            self.expect_punct("]")
        self.expect_punct("-")
        self.accept_punct(">")
        return var, types, props

    def read_pattern_chain(self, *, declare: bool) -> None:
        """One pattern: node (rel node)*. In read mode `declare` says whether
        a scoped node here binds its variable for later references (MATCH
        clauses do; pattern predicates inside WHERE do not)."""
        first = self.peek()
        nxt = self.peek(1)
        if first is not None and first.kind == "IDENT" and nxt is not None and nxt.kind == "PUNCT" and nxt.text in ("=", "("):
            raise self.unsupported(
                "A path variable or pattern function is not permitted", first.text
            )
        self.read_node(declare=declare)
        while self.at_rel_start():
            var, types, props = self.read_rel()
            if self.mode == "write":
                self.check_write_rel(var, types, props)
            elif var is not None:
                self.rel_vars.add(var)
            self.read_node(declare=declare)

    def read_node(self, *, declare: bool) -> None:
        var, labels, props = self.read_node_shape()
        shown = "(" + (var or "") + "".join(":" + label for label in labels) + ")"
        if self.mode == "write":
            self.check_write_node(var, labels, props, shown, declare)
            return
        scoped = self.check_project_entry(props, shown)
        if var is None:
            self.record(
                "anonymous_node_pattern",
                "A node pattern without a variable cannot be scope-checked; every "
                "node must bind a variable and carry {project: $project}",
                shown,
            )
            return
        if scoped:
            if declare:
                self.node_vars.add(var)
            return
        if var in self.node_vars:
            return  # reference to an already scoped variable (only narrows)
        if props is not None and "project" in props:
            return  # project_literal / missing_project_scope already recorded
        self.record(
            "missing_project_scope",
            f"Variable `{var}` is not declared with an inline {{project: $project}} "
            "map at its first appearance, so it can match nodes from every "
            "project (a WHERE predicate does not count)",
            var,
        )

    # -- write-profile node/relationship rules ---------------------------------
    def check_write_node(
        self,
        var: str | None,
        labels: list[str],
        props: dict[str, Tok] | None,
        shown: str,
        declare: bool,
    ) -> None:
        if not labels and props is None:
            if var is not None and var in self.node_vars:
                return  # bare reference to a variable bound earlier
            self.record(
                "unlabeled_node_pattern",
                "An unlabeled node pattern is not permitted; only a bare "
                "reference to a variable bound earlier in the statement is",
                shown,
            )
            return
        if var is None:
            self.record(
                "anonymous_node_pattern",
                "A node pattern without a variable is not permitted",
                shown,
            )
        if len(labels) != 1:
            self.record(
                "disallowed_label",
                "A node pattern must carry exactly one label from the schema set",
                shown,
            )
            return
        label = labels[0]
        identity_key = WRITE_NODE_IDENTITY_KEY.get(label)
        if identity_key is None:
            self.record(
                "disallowed_label",
                f"Label '{label}' cannot be written by rule ingest (allowed: "
                f"{', '.join(sorted(WRITE_NODE_IDENTITY_KEY))})",
                label,
            )
            return
        if not self.check_project_entry(props, shown):
            if props is None or "project" not in props:
                self.record(
                    "missing_project_scope",
                    f"The {label} pattern has no {{project: $project}} entry, so "
                    "it could match or overwrite another project's node",
                    shown,
                )
        identity = (props or {}).get(identity_key)
        if identity is None or identity.kind != "STRING" or not identity.text:
            self.record(
                "missing_identity_key",
                f"The {label} pattern needs a complete, non-empty string literal "
                f"`{identity_key}`",
                shown,
            )
        for key, value in (props or {}).items():
            if value.kind == "PARAM" and not (key == "project" and value.text == "project"):
                self.record(
                    "unanalysable_key",
                    f"The property `{key}` must be a literal, not the parameter ${value.text}",
                    shown,
                )
        if var is not None and declare:
            if var in self.node_vars:
                self.record(
                    "rebound_variable",
                    f"The variable `{var}` is declared a second time; a name may be "
                    "bound only once per statement",
                    var,
                )
            self.node_vars.add(var)

    def check_write_rel(
        self, var: str | None, types: list[str], props: dict[str, Tok] | None
    ) -> None:
        if var is not None:
            self.record(
                "unsupported_syntax",
                "A relationship variable is not permitted in rule ingest",
                var,
            )
        if len(types) != 1 or types[0] not in WRITE_REL_TYPES:
            self.record(
                "unknown_relationship",
                "A relationship must have exactly one type from "
                f"{', '.join(sorted(WRITE_REL_TYPES))}",
                "|".join(types) or "(untyped)",
            )
        for key, value in (props or {}).items():
            if value.kind == "PARAM":
                self.record(
                    "unsupported_syntax",
                    f"The relationship property `{key}` must be a literal",
                    key,
                )

    # -- read-profile expressions ---------------------------------------------
    def parse_expr(self, *, closers: str = "", in_index: bool = False) -> int:
        """Consume one expression, stopping (without consuming) at a `,` or a
        closer at this level, at a top-level clause word, or at `;`. Returns
        the number of tokens consumed."""
        start = self.i
        nested = bool(closers)
        prev: Tok | None = None
        while True:
            tok = self.peek()
            if tok is None:
                break
            kind, text = tok.kind, tok.text
            if kind == "PUNCT":
                if text in closers or text == "," or text == ";":
                    break
                if text == "(":
                    self.parse_paren()
                    prev = self.toks[self.i - 1]
                    continue
                if text == "[":
                    self.i += 1
                    if not self.is_punct("]"):
                        while True:
                            if self.parse_expr(closers="]", in_index=True) == 0:
                                raise self.unsupported("An empty list element", "[")
                            if not self.accept_punct(","):
                                break
                    self.expect_punct("]")
                    prev = self.toks[self.i - 1]
                    continue
                if text == "{":
                    self.parse_map_literal(prev)
                    prev = self.toks[self.i - 1]
                    continue
                if text == "|":
                    raise self.unsupported(
                        "A list or pattern comprehension is not permitted", "|"
                    )
                if text in (")", "]", "}"):
                    raise self.unsupported("An unbalanced closing bracket", text)
                if text == ".":
                    nxt = self.peek(1)
                    if in_index and nxt is not None and nxt.kind == "PUNCT" and nxt.text == ".":
                        self.i += 2
                        prev = self.toks[self.i - 1]
                        continue
                    if prev is None or nxt is None or nxt.kind != "IDENT":
                        raise self.unsupported("A property access needs a plain name", ".")
                    after = self.peek(2)
                    if after is not None and after.kind == "PUNCT" and after.text == "(":
                        raise self.unsupported(
                            "A namespaced function or procedure call is not permitted",
                            f"{prev.text}.{nxt.text}(",
                        )
                    # `x.project = '<literal>'` -- a literal project comparison
                    if nxt.text == "project":
                        op = self.peek(2)
                        lit = self.peek(3)
                        if (
                            op is not None and op.kind == "PUNCT" and op.text == "="
                            and lit is not None and lit.kind == "STRING"
                        ):
                            self.record(
                                "project_literal",
                                f"`project` is compared to the string literal '{lit.text}' "
                                "instead of the bound $project parameter",
                                f".project = '{lit.text}'",
                            )
                    self.i += 2
                    prev = nxt
                    continue
                if text == ":":
                    nxt = self.peek(1)
                    if prev is not None and prev.kind == "IDENT" and nxt is not None and nxt.kind == "IDENT":
                        self.i += 2
                        prev = nxt
                        continue
                    raise self.unsupported("A stray ':' is not permitted", ":")
                # arithmetic / comparison operators
                self.i += 1
                prev = tok
                continue
            if kind == "IDENT":
                up = tok.upper
                if up in _EXPR_STOP_WORDS:
                    if nested:
                        raise self.unsupported(
                            "A clause keyword inside brackets is not permitted", up
                        )
                    break
                if up == "WITH":
                    if not (prev is not None and prev.kind == "IDENT" and prev.upper in ("STARTS", "ENDS")):
                        raise self.forbidden("WITH")
                elif up in FORBIDDEN_CLAUSE_WORDS:
                    raise self.forbidden(up)
                elif up == "DISTINCT":
                    if prev is not None:
                        raise self.unsupported("DISTINCT is only allowed at the start of an expression", "DISTINCT")
                nxt = self.peek(1)
                if nxt is not None and nxt.kind == "PUNCT" and nxt.text == "(" and up not in _PAREN_KEYWORDS:
                    if up not in READ_FUNCTIONS:
                        raise _Fatal(
                            _violation(
                                "unsupported_function",
                                f"The function `{tok.text}` is not on the read-only allowlist",
                                tok.text,
                                self.how,
                            )
                        )
                    self.i += 2
                    if not self.is_punct(")"):
                        while True:
                            if self.parse_expr(closers=")") == 0:
                                raise self.unsupported("An empty function argument", tok.text + "(")
                            if not self.accept_punct(","):
                                break
                    self.expect_punct(")")
                    prev = self.toks[self.i - 1]
                    continue
                self.i += 1
                prev = tok
                continue
            # NUMBER / STRING / PARAM
            if kind == "PARAM" and text == "project":
                self.saw_project_param = True
            self.i += 1
            prev = tok
        return self.i - start

    def parse_map_literal(self, prev: Tok | None) -> None:
        if prev is not None and not (
            (prev.kind == "PUNCT" and prev.text in ("(", "[", ",", ":", "=", "<", ">", "+", "-", "*", "/", "%", "^", "~"))
            or (prev.kind == "IDENT" and prev.upper in _MAP_OK_AFTER)
        ):
            raise self.unsupported(
                "A subquery block or map after this token is not permitted",
                (prev.text + " {"),
            )
        self.expect_punct("{")
        if self.accept_punct("}"):
            return
        while True:
            key = self.next()
            if key.kind != "IDENT":
                raise self.unsupported("A map key must be a plain name", self.describe(key))
            self.expect_punct(":")
            if self.parse_expr(closers="}") == 0:
                raise self.unsupported("An empty map value", key.text)
            if not self.accept_punct(","):
                break
        self.expect_punct("}")

    def parse_paren(self) -> None:
        """A `(` inside an expression: a pattern predicate when it reads as a
        node pattern followed by a relationship, else a grouping."""
        save = self.i
        try:
            self.read_node_shape()
            is_pattern = self.at_rel_start()
        except _Fatal:
            is_pattern = False
        self.i = save
        if is_pattern:
            self.read_pattern_chain(declare=False)
            return
        self.i += 1
        if self.parse_expr(closers=")") == 0:
            raise self.unsupported("An empty parenthesis", "()")
        if self.is_punct(","):
            raise self.unsupported("A tuple or argument list here is not permitted", ",")
        self.expect_punct(")")

    # -- read profile ------------------------------------------------------------
    def parse_read(self) -> None:
        while True:
            tok = self.peek()
            if tok is None:
                raise self.unsupported("The query has no RETURN clause", "end of query")
            if tok.kind != "IDENT":
                raise self.reject_clause_word(tok)
            up = tok.upper
            if up == "OPTIONAL":
                self.i += 1
                if not self.is_word("MATCH"):
                    raise self.unsupported("OPTIONAL must be followed by MATCH", "OPTIONAL")
                self.parse_match()
            elif up == "MATCH":
                self.parse_match()
            elif up == "RETURN":
                self.parse_return()
                break
            else:
                raise self.reject_clause_word(tok)
        while self.accept_punct(";"):
            pass
        if self.peek() is not None:
            raise self.reject_clause_word(self.peek())

    def parse_match(self) -> None:
        self.i += 1  # MATCH
        while True:
            self.read_pattern_chain(declare=True)
            if not self.accept_punct(","):
                break
        if self.is_word("WHERE"):
            self.i += 1
            if self.parse_expr() == 0:
                raise self.unsupported("WHERE needs a condition", "WHERE")

    def parse_return(self) -> None:
        self.i += 1  # RETURN
        if self.is_word("DISTINCT"):
            self.i += 1
        if self.is_punct("*"):
            self.i += 1
            if not self.accept_punct(","):
                self.after_return_items()
                return
        while True:
            if self.parse_expr() == 0:
                raise self.unsupported("RETURN needs an expression", "RETURN")
            if self.is_word("AS"):
                self.i += 1
                alias = self.next()
                if alias.kind != "IDENT":
                    raise self.unsupported("An alias must be a plain name", self.describe(alias))
            if not self.accept_punct(","):
                break
        self.after_return_items()

    def after_return_items(self) -> None:
        if self.is_word("ORDER"):
            self.i += 1
            if not self.is_word("BY"):
                raise self.unsupported("ORDER must be followed by BY", "ORDER")
            self.i += 1
            while True:
                if self.parse_expr() == 0:
                    raise self.unsupported("ORDER BY needs an expression", "ORDER BY")
                if self.peek() is not None and self.peek().kind == "IDENT" and self.peek().upper in (
                    "ASC", "DESC", "ASCENDING", "DESCENDING",
                ):
                    self.i += 1
                if not self.accept_punct(","):
                    break
        for word in ("SKIP", "LIMIT"):
            if self.is_word(word):
                self.i += 1
                if self.parse_expr() == 0:
                    raise self.unsupported(f"{word} needs a value", word)

    # -- write profile -------------------------------------------------------------
    def parse_write(self) -> None:
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok.kind == "PUNCT" and tok.text == ";":
                # n8n strips `;` outside quotes and chains the clauses into one
                # statement, so a separator between clauses is whitespace.
                self.i += 1
                continue
            if tok.kind != "IDENT":
                raise self.reject_clause_word(tok)
            up = tok.upper
            if up == "MERGE":
                self.i += 1
                self.read_pattern_chain(declare=True)
                if self.is_word("ON"):
                    raise self.unsupported(
                        "ON CREATE / ON MATCH is not permitted; use a plain SET after the MERGE",
                        "ON",
                    )
            elif up == "MATCH":
                self.i += 1
                while True:
                    self.read_pattern_chain(declare=True)
                    if not self.accept_punct(","):
                        break
                if self.is_word("WHERE"):
                    raise self.unsupported(
                        "WHERE is not permitted; match by complete literal key and {project: $project}",
                        "WHERE",
                    )
            elif up == "SET":
                self.i += 1
                self.parse_set()
            else:
                raise self.reject_clause_word(tok)

    def parse_set(self) -> None:
        while True:
            var = self.next()
            if var.kind != "IDENT":
                raise self.unsupported("SET needs a variable bound in this statement", self.describe(var))
            if var.text not in self.node_vars:
                self.record(
                    "unbound_set_target",
                    f"SET targets `{var.text}`, which is not a node bound in this statement",
                    var.text,
                )
            if self.is_punct(":") or self.is_punct("+"):
                raise self.unsupported("Only `var.prop = literal` is allowed in SET", var.text)
            self.expect_punct(".")
            if self.is_punct("["):
                raise self.unsupported("Dynamic property access is not permitted", "[")
            prop = self.next()
            if prop.kind != "IDENT":
                raise self.unsupported("SET needs a plain property name", self.describe(prop))
            if prop.text.lower() in _PROTECTED_SET_KEYS:
                self.record(
                    "protected_property_set",
                    f"SET must not write `{prop.text}`; put `project` and `graph` in the "
                    "MERGE property map instead",
                    f"{var.text}.{prop.text}",
                )
            self.expect_punct("=")
            value = self.read_literal(key=prop.text, code="unanalysable_value")
            if value.kind == "PARAM":
                self.record(
                    "unanalysable_value",
                    f"SET `{prop.text}` must be assigned a literal, not a parameter",
                    f"{var.text}.{prop.text}",
                )
            if not self.accept_punct(","):
                break


def _run(cypher: str, *, mode: str, how: str) -> tuple[list[Violation], _Parser | None]:
    try:
        toks = tokenize(cypher, how)
    except _Fatal as exc:
        return [exc.violation], None
    parser = _Parser(toks, how=how, mode=mode)
    try:
        if mode == "read":
            parser.parse_read()
        else:
            parser.parse_write()
    except _Fatal as exc:
        return parser.violations + [exc.violation], parser
    return parser.violations, parser


def check_read_allowlist(cypher: str) -> list[Violation]:
    """Allowlist proof for graph_query / `/mcp neo4j_query` Cypher."""
    violations, parser = _run(cypher, mode="read", how=_READ_HOW)
    if parser is not None and not parser.saw_project_param:
        violations.append(
            _violation(
                "missing_project_scope",
                "The query never references $project, so it cannot be proven project-scoped",
                "query",
                _READ_HOW,
            )
        )
    return violations


def check_write_allowlist(cypher: str) -> list[Violation]:
    """Allowlist proof for rule_ingest / rule_edit Cypher."""
    violations, parser = _run(cypher, mode="write", how=_WRITE_HOW)
    if parser is not None and not parser.saw_project_param:
        violations.append(
            _violation(
                "missing_project_scope",
                "The statement never references $project",
                "query",
                _WRITE_HOW,
            )
        )
    return violations
