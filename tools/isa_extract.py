#!/usr/bin/env python3
"""Recover the payload VM instruction set from field [49]'s dispatcher.

Why this tool exists
--------------------
Hand-rolled Luau block counting cannot delimit this code: the obfuscator emits
*empty* branches (`if h<96 then if h~=95 then else ... end end`) and the
`repeat ... until` loops desync a naive `end` counter.  An earlier attempt
therefore recovered 16 of ~200 opcodes and produced a garbage leaf table.

This tool instead uses the **real Luau parser** (`tools/astdump.cpp`, compiled
against the Luau sources) to dump every `if`/`while`/`repeat`/`for` node with
its exact source position, and then reconstructs the dispatch tree by
containment:

    a guard node is a LEAF  <=>  its `then` branch holds no nested guard on the
                                 same subject register

Each leaf's opcode number comes from the guard comparison itself
(`if h==72 then`, or an interval walk `if h<71 then ... else if h==72 ...`).
The `else` chain of a leaf supplies the values the leaf answers for, which is
why intervals must be walked rather than read off a single `==`.

Dispatcher layering (this is the part the old tool missed)
----------------------------------------------------------
[49] holds several *separate* dispatch loops, not one tree:

    if g==150 then while true do local v=k[I]; ...   -- v  (221 guards)
    if g==102 then while true do local v=O[I]; ...   -- v  (221 guards)
    if g==160 then while true do Z=k[I];   ...       -- Z  ( 29 guards)
    while true do local h=...;               ...     -- h  ( 99 guards)

`h` is the main opcode register (0..255); `g` is a continuation/interpreter
marker that switches the loop into the `v`/`Z` sub-dispatchers.

Usage
-----
    astdump <wrapped_field.luau> > ast.tsv
    python3 tools/isa_extract.py ast.tsv <wrapped_field.luau> [--json out.json]

`wrapped_field.luau` must be a full chunk: take field_49.luau, drop the
`[49]=` key prefix and prepend `local t=`.  `tools/make_wrapped.py` does this.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from typing import Dict, List, Tuple

GUARD_RE = re.compile(r"^if\s+([A-Za-z_]\w*)\s*(>=|<=|==|~=|>|<)\s*(\d+)\s+then$")


def load_offsets(path: str) -> Tuple[str, List[int]]:
    """Return the source text plus a line -> byte offset table.

    Luau reports 0-based line numbers and 0-based byte columns, so the
    conversion is simply ``starts[line] + column``.
    """
    with open(path, encoding="utf-8", errors="surrogateescape") as fh:
        src = fh.read()
    starts = [0]
    for i, ch in enumerate(src):
        if ch == "\n":
            starts.append(i + 1)
    return src, starts


def parse_tsv(path: str):
    nodes = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            f = ln.rstrip("\n").split("\t")
            if not f or f[0] == "END":
                continue
            nodes.append((f[0], [int(x) for x in f[1:] if x != ""]))
    return nodes


def build_nodes(src: str, starts: List[int], nodes) -> List[dict]:
    def off(line: int, col: int) -> int:
        return starts[line] + col if line >= 0 else -1

    out = []
    for kind, n in nodes:
        if kind != "IF":
            continue
        cond = (off(n[0], n[1]), off(n[2], n[3]))
        then = (off(n[4], n[5]), off(n[6], n[7]))
        els = (off(n[8], n[9]), off(n[10], n[11])) if n[8] >= 0 else (-1, -1)
        # the `if` keyword sits immediately before the condition span
        start = cond[0]
        while start > 0 and src[start - 1] in " \t\n":
            start -= 1
        start -= 2
        text = " ".join(src[start : then[0]].split())
        m = GUARD_RE.match(text)
        out.append(
            {
                "cond": cond,
                "then": then,
                "else": els,
                "start": start,
                "text": text,
                "var": m.group(1) if m else None,
                "op": m.group(2) if m else None,
                "num": int(m.group(3)) if m else None,
            }
        )
    return out


def is_leaf(node: dict, all_nodes: List[dict]) -> bool:
    """True when the `then` branch contains no nested guard on the same register."""
    if node["var"] is None:
        return False
    lo, hi = node["then"]
    for other in all_nodes:
        if other is node or other["var"] != node["var"]:
            continue
        if lo <= other["start"] and other["then"][1] <= hi:
            return False
    return True


def body_text(src: str, node: dict) -> str:
    """The leaf's action: the `then` branch verbatim."""
    return " ".join(src[node["then"][0] : node["then"][1]].split())


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    tsv, field = sys.argv[1], sys.argv[2]
    out_json = None
    if "--json" in sys.argv:
        out_json = sys.argv[sys.argv.index("--json") + 1]

    src, starts = load_offsets(field)
    nodes = build_nodes(src, starts, parse_tsv(tsv))

    counts = collections.Counter(n["var"] for n in nodes)
    print(f"if nodes: {len(nodes)}")
    print("guards by register (all nodes): " + ", ".join(
        f"{k}={v}" for k, v in counts.most_common()))

    leaves = [n for n in nodes if is_leaf(n, nodes)]
    by_var: Dict[str, List[dict]] = collections.defaultdict(list)
    for n in leaves:
        by_var[n["var"]].append(n)

    print()
    for var, ls in sorted(by_var.items(), key=lambda kv: -len(kv[1])):
        nums = sorted({n["num"] for n in ls})
        ops = collections.Counter(n["op"] for n in ls)
        print(f"  register {var:>2}: {len(ls):3d} leaves  values {nums[0]}..{nums[-1]}"
              f"  distinct {len(nums)}  ops {dict(ops)}")

    if out_json:
        payload = {
            var: {str(n["num"]): body_text(src, n) for n in sorted(ls, key=lambda n: n["num"])}
            for var, ls in by_var.items()
        }
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"\nwrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
