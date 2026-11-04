#!/usr/bin/env python3
"""Evaluate field [49]'s dispatch tree: opcode number -> executed code.

`tools/isa_extract.py` only finds *leaf* guards.  That is not enough, because
the obfuscator expresses intervals with paired tests rather than one `==`:

    if h<71 then <body> else if h==72 then <body> else <body> end end

so a leaf like `if h==72 then` answers for exactly one value while
`if h<71 then` answers for everything below it.  Recursing down this tree
requires carrying the interval, and the *empty* branches the obfuscator
loves (`if h<96 then if h~=95 then else ... end end`) change which branch
runs without contributing any code.

This tool walks the tree with the real Luau AST spans
(`tools/astdump.cpp` output), keeps the interval state, and records, for every
opcode value, the source text of the deepest `then` branch that actually ran.

Usage
-----
    astdump wrapped.luau > ast.tsv
    python3 tools/vm_isatree.py ast.tsv wrapped.luau --var h --json opcodes_h.json

Notes on the data model
-----------------------
* A node's `then` branch may start with a nested guard on the same register;
  nested guards are found by source containment, which is exact because the
  spans come from Luau's own parser.
* `if X ~= N then A else B` is the same shape as `X == N` with the branches
  swapped, so `~=` flips the interval.
* A branch with no nested guard is the payload: its text is the opcode body.
"""
from __future__ import annotations

import json
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, "tools")
import isa_extract as ie  # noqa: E402  (offsets, tsv parsing, guard regex)


def contains(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return a[0] >= 0 and b[0] >= 0 and a[0] <= b[0] and b[1] <= a[1]


def children(node: dict, all_nodes: List[dict]) -> Tuple[List[dict], List[dict]]:
    """Nested same-register guards inside the then / else branches."""
    thens, elses = [], []
    for other in all_nodes:
        if other is node or other["var"] != node["var"]:
            continue
        if contains(node["then"], (other["start"], other["then"][1])):
            thens.append(other)
        elif node["else"][0] >= 0 and contains(node["else"], (other["start"], other["then"][1])):
            elses.append(other)
    return thens, elses


def branch_body(src: str, span: Tuple[int, int]) -> str:
    if span[0] < 0:
        return ""
    return " ".join(src[span[0] : span[1]].split())


def split_node(node: dict, all_nodes: List[dict]) -> bool:
    """True when the then-branch is a guard rather than code."""
    thens, _ = children(node, all_nodes)
    # the nested guard must be the FIRST thing in the branch: its start must be
    # the branch start modulo whitespace
    return any(t["start"] <= node["then"][0] + 2 for t in thens)


def walk(
    src: str,
    node: dict,
    lo: int,
    hi: int,
    all_nodes: List[dict],
    out: Dict[int, List[str]],
    depth: int = 0,
) -> None:
    """Recurse through `node` restricted to [lo, hi], recording bodies."""
    if lo > hi:
        return
    op, num = node["op"], node["num"]
    thens, elses = children(node, all_nodes)
    then_child = next((t for t in thens if t["start"] <= node["then"][0] + 2), None)
    # An `elseif` is parsed by Luau as a nested `if` that IS the else branch, so
    # it must always be followed even though its start does not sit exactly at
    # the else-branch start (the else span begins at `elseif`).
    # The else branch starts at `else`, which Luau reports *including* the
    # keyword, so a nested `elseif` node starts 5 bytes later ("else" + "if").
    # Anything further in is a guard inside a non-empty else body, not the
    # else-chain continuation.
    # Only adopt an else-continuation when it is *strictly inside* the else
    # span and its guard keyword is the first token of that branch.  Luau
    # reports the else span with a lot of leading whitespace / stray `end`s for
    # the obfuscator's empty branches, so a proximity test is not enough: the
    # test must be containment.
    else_child = None
    if elses:
        first = min(elses, key=lambda e: e["start"])
        e_lo, e_hi = node["else"]
        if e_lo < first["start"] and first["then"][1] <= e_hi:
            else_child = first

    def emit(span: Tuple[int, int], a: int, b: int) -> None:
        """Record a branch that contains no further guard.

        An empty branch is a *valid* answer here: `if h~=95 then else <body>`
        reaches this point with an empty then-branch, and an empty branch means
        "no code runs for these values", not "fall through to the parent".  If
        we dropped it the parent's body would leak over the whole interval.
        """
        if a > b or span[0] < 0:
            return
        body = branch_body(src, span)
        for v in range(a, b + 1):
            out.setdefault(v, []).append(body)

    def descend(child, span: Tuple[int, int], a: int, b: int) -> None:
        """Follow a nested guard, or record this branch as the answer."""
        if a > b:
            return
        if child is None:
            emit(span, a, b)
        else:
            walk(src, child, a, b, all_nodes, out, depth + 1)

    # ---- empty branches ---------------------------------------------------
    # `if X~=95 then else <body> end` is how the obfuscator writes "X == 95".
    # Handled by the generic ~= rule below, which swaps the branches.

    # ---- equality / inequality against a single value ---------------------
    if op in ("==", "~="):
        eq = (max(lo, num), min(hi, num))
        below = (lo, min(hi, num - 1))
        above = (max(lo, num + 1), hi)
        if op == "==":
            descend(then_child, node["then"], *eq)
            descend(else_child, node["else"], *below)
            descend(else_child, node["else"], *above)
        else:
            descend(then_child, node["then"], *below)
            descend(then_child, node["then"], *above)
            descend(else_child, node["else"], *eq)
        return

    # ---- half-open interval tests ----------------------------------------
    if op == "<":
        hit, miss = (lo, min(hi, num - 1)), (max(lo, num), hi)
    elif op == "<=":
        hit, miss = (lo, min(hi, num)), (max(lo, num + 1), hi)
    elif op == ">":
        hit, miss = (max(lo, num + 1), hi), (lo, min(hi, num))
    elif op == ">=":
        hit, miss = (max(lo, num), hi), (lo, min(hi, num - 1))
    else:  # pragma: no cover - unknown comparison shape
        return

    descend(then_child, node["then"], *hit)
    descend(else_child, node["else"], *miss)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    tsv, field = sys.argv[1], sys.argv[2]
    var = "h"
    if "--var" in sys.argv:
        var = sys.argv[sys.argv.index("--var") + 1]
    out_json = None
    if "--json" in sys.argv:
        out_json = sys.argv[sys.argv.index("--json") + 1]

    src, starts = ie.load_offsets(field)
    all_nodes = ie.build_nodes(src, starts, ie.parse_tsv(tsv))
    cand = [n for n in all_nodes if n["var"] == var]
    if not cand:
        print(f"no guards on register {var}", file=sys.stderr)
        return 1

    root = min(cand, key=lambda n: n["start"])
    out: Dict[int, List[str]] = {}
    walk(src, root, 0, 255, all_nodes, out)

    filled = sorted(out)
    missing = [v for v in range(256) if v not in out]
    print(f"register {var}: root `{root['text']}`")
    print(f"values with a body: {len(filled)}")
    print(f"gaps ({len(missing)}): {missing}")
    multi = {v: b for v, b in out.items() if len(b) > 1}
    print(f"values with multiple bodies: {len(multi)}")

    for v in filled[:6]:
        print(f"  {v}: {out[v][-1][:90]}")

    if out_json:
        payload = {str(v): out[v][-1] for v in filled}
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
