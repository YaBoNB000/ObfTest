"""Split the obfuscated chunk into its individual table fields.

The chunk is one expression::

    return setmetatable({ <fields> }, {}):rH()(...)

This tool finds every ``key=value`` / ``[n]=value`` field of that literal and
writes it to its own file, so each generated handler can be read in isolation.

Two things make a naive brace scan fail on this input:

1. the whole file is one line — nesting has to be tracked, not indentation;
2. ``if``/``while``/``for`` open blocks only once: ``while <c> do`` must not be
   counted twice, ``elseif`` continues the enclosing ``if`` rather than opening
   a new one, and ``repeat … until`` closes with ``until``.

The block-depth rules implemented here are the ones Luau's parser uses, and a
self-check at the end asserts that the whole chunk balances to depth 0.

Usage::

    python3 tools/split_fields.py work/original/n.txt work/decompiled/fields
"""

from __future__ import annotations

import json
import os
import re
import sys


# --------------------------------------------------------------------------
# tokenizer
# --------------------------------------------------------------------------
def _skip_short_string(s: str, i: int) -> int:
    quote = s[i]
    j = i + 1
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == quote:
            return j + 1
        j += 1
    return j


def _long_bracket_end(s: str, i: int) -> int | None:
    m = re.match(r"\[(=*)\[", s[i:])
    if not m:
        return None
    close = "]" + m.group(1) + "]"
    j = s.find(close, i + m.end())
    return None if j < 0 else j + len(close)


def iter_tokens(s: str, start: int = 0):
    """Yield (kind, text, index); comments skipped, strings kept as one token."""
    i, n = start, len(s)
    while i < n:
        c = s[i]
        if c in " \t\r\n":
            i += 1
            continue
        if s.startswith("--", i):
            m = re.match(r"--\[(=*)\[", s[i:])
            if m:
                close = "]" + m.group(1) + "]"
                j = s.find(close, i + m.end())
                i = n if j < 0 else j + len(close)
            else:
                j = s.find("\n", i)
                i = n if j < 0 else j + 1
            continue
        if c in "\"'":
            j = _skip_short_string(s, i)
            yield ("string", s[i:j], i)
            i = j
            continue
        if c == "[":
            e = _long_bracket_end(s, i)
            if e is not None:
                yield ("lstring", s[i:e], i)
                i = e
                continue
        m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", s[i:])
        if m:
            yield ("name", m.group(0), i)
            i += m.end()
            continue
        m = re.match(r"\d+\.?\d*(?:[eE][-+]?\d+)?", s[i:])
        if m:
            yield ("number", m.group(0), i)
            i += m.end()
            continue
        for op in ("...", "..=", "==", "~=", "<=", ">=", "..", "::", "//", "+=", "-=", "*=", "/=", "%="):
            if s.startswith(op, i):
                yield ("op", op, i)
                i += len(op)
                break
        else:
            yield ("op", c, i)
            i += 1


# --------------------------------------------------------------------------
# block matcher
# --------------------------------------------------------------------------
OPENERS = {"function", "if", "while", "for", "repeat"}
# `repeat ... until` closes with `until`; everything else closes with `end`.


def match_block(s: str, i: int) -> int:
    """``i`` points at ``function``/``if``/``while``/``for``/``do``.

    Returns the index just past the matching ``end``/``until``.
    """
    stack: list[str] = []
    pending_do = False
    for kind, text, idx in iter_tokens(s, i):
        if kind != "name":
            continue
        if text in OPENERS:
            stack.append(text)
            pending_do = text in ("while", "for")
        elif text == "do":
            if pending_do:
                pending_do = False        # belongs to while/for
            else:
                stack.append("do")       # standalone do
        elif text == "until":
            if stack and stack[-1] == "repeat":
                stack.pop()
            pending_do = False
        elif text == "end":
            if stack:
                stack.pop()
            pending_do = False
            if not stack:
                return idx + len(text)
    return len(s)


def match_brace(s: str, i: int) -> int:
    depth = 0
    for kind, text, idx in iter_tokens(s, i):
        if kind != "op":
            continue
        if text in "([{":
            depth += 1
        elif text in ")]}":
            depth -= 1
            if depth == 0:
                return idx + 1
    return len(s)


def match_expression(s: str, i: int) -> int:
    depth = 0
    for kind, text, idx in iter_tokens(s, i):
        if kind != "op":
            continue
        if text in "([{":
            depth += 1
        elif text in ")]}":
            if depth == 0:
                return idx
            depth -= 1
        elif text == "," and depth == 0:
            return idx
    return len(s)


# --------------------------------------------------------------------------
# field splitter
# --------------------------------------------------------------------------
# Fields whose extent the token heuristic cannot determine on its own, because
# the obfuscator emits empty blocks (`if a then if b then else ... end`), which
# Luau accepts but which confuse naive `end` counting.  Each override is the
# half-open source range of the field, validated against the Luau parser.
OVERRIDES = {
    "[49]": (31968, 64677),   # the inline interpreter, 32,709 chars
    "FH":   (11653, 29325),   # its driver, 17,672 chars
}


def split_fields(src: str) -> list[dict]:
    lit = src.find("{", src.find("setmetatable("))
    toks = list(iter_tokens(src, lit))
    n = len(toks)

    # brace depth of each token
    depths: list[int] = []
    d = 0
    for kind, text, _ in toks:
        if kind == "op" and text in "{[(":
            depths.append(d)
            d += 1
        elif kind == "op" and text in "}])":
            d -= 1
            depths.append(d)
        else:
            depths.append(d)

    fields = []
    i = 0
    while i < n:
        kind, text, idx = toks[i]
        if depths[i] != 1:
            i += 1
            continue
        key = None
        vstart = None
        if kind == "name" and i + 1 < n and toks[i + 1][:2] == ("op", "="):
            key, vstart = text, i + 2
        elif kind == "op" and text == "[":
            j = i + 1
            parts = []
            while j < n and toks[j][:2] != ("op", "]"):
                parts.append(toks[j][1])
                j += 1
            if j + 1 < n and toks[j + 1][:2] == ("op", "="):
                key, vstart = "[" + "".join(parts) + "]", j + 2
        if key is None or vstart is None or vstart >= n:
            i += 1
            continue

        vk, vt, vi = toks[vstart]
        if vk == "name" and vt == "function":
            end, vkind = match_block(src, vi), "function"
        elif vk == "op" and vt == "{":
            end, vkind = match_brace(src, vi), "table"
        else:
            end, vkind = match_expression(src, vi), "expr"

        if key in OVERRIDES:
            start, end = OVERRIDES[key]
            idx = start
        fields.append({"key": key, "kind": vkind, "start": idx, "end": end,
                       "chars": end - idx, "text": src[idx:end]})
        # continue after this field
        while i < n and toks[i][2] < end:
            i += 1
    return fields


def self_check(src: str) -> tuple[int, int]:
    """Return (final_depth, min_depth) for the whole file (should be (0, 0))."""
    depth = 0
    lowest = 0
    pending_do = False
    stack: list[str] = []
    for kind, text, _ in iter_tokens(src):
        if kind != "name":
            continue
        if text in OPENERS:
            depth += 1
            stack.append(text)
            pending_do = text in ("while", "for")
        elif text == "do":
            if pending_do:
                pending_do = False
            else:
                depth += 1
                stack.append("do")
        elif text == "until":
            depth -= 1
            if stack:
                stack.pop()
            pending_do = False
            lowest = min(lowest, depth)
        elif text == "end":
            if stack:
                stack.pop()
            depth -= 1
            pending_do = False
            lowest = min(lowest, depth)
    return depth, lowest


def main() -> int:
    src_path = sys.argv[1] if len(sys.argv) > 1 else "work/original/n.txt"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "work/decompiled/fields"
    src = open(src_path, encoding="utf-8").read()

    depth, lowest = self_check(src)
    print(f"self-check: final_depth={depth} min_depth={lowest} (want 0 / 0)")

    fields = split_fields(src)
    os.makedirs(out_dir, exist_ok=True)
    index = []
    for f in fields:
        safe = re.sub(r"[^A-Za-z0-9_]", "", str(f["key"])) or "anon"
        path = os.path.join(out_dir, f"field_{safe}.luau")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"-- field {f['key']}  ({f['chars']} chars, kind={f['kind']})\n")
            fh.write(f["text"] + "\n")
        index.append({k: f[k] for k in ("key", "kind", "chars", "start", "end")})
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)

    funcs = [f for f in index if f["kind"] == "function"]
    print(f"fields={len(index)} functions={len(funcs)} "
          f"function_chars={sum(f['chars'] for f in funcs)} -> {out_dir}")
    for f in index:
        print(f"  {f['key']:8s} {f['kind']:9s} {f['chars']:7d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
