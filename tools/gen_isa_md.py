#!/usr/bin/env python3
"""Generate work/decompiled/vm_isa.md from work/decompiled/vm_opcodes.json.

The JSON holds, for each of field [49]'s three dispatch tables, the verbatim
Luau source of the handler for every reachable opcode value.  This script adds
a *mnemonic* to each row, derived mechanically from the shape of the handler
body, so the table is reproducible and the body column stays the authority.

Semantics inferred from the tables
----------------------------------
`h` (0..95) is the bytecode interpreter. Its handlers read the instruction
words `L`/`O`/`s`/`k`/`r`/`c`/`Y`/`e`, so the mnemonics are the usual Lua/Luau
ones (MOVE, LOADK, GETUPVAL, ADD, CALL, ...).

`v` (0..49) and `Z` (0..29) are *not* the interpreter loop: they are the
secondary dispatchers reached when `g` is set to a continuation marker. Their
handlers use the same register file but different operand registers, which is
why their bodies overlap with `h` without being duplicates.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Dict, List, Tuple

# (regex, replacement) applied to a normalized handler body. Ordered: the first
# match wins, so put the specific shapes before the generic ones.
OPS3 = {"+": "ADD", "-": "SUB", "*": "MUL", "//": "IDIV", "%": "MOD", "^": "POW", "..": "CONCAT"}
REGS = "sOL"


def classify(b: str) -> str:
    """Return a mnemonic for a handler body, or "--" when the shape is complex."""
    if not b:
        return "NOP"

    # --- plain register-to-register arithmetic / comparisons ---------------
    m = re.fullmatch(r"e\[([sOL])\[I\]\]=(-?)e\[([sOL])\[I\]\]"
                     r"(\+|-|\*|//|%|\^|\.\.|==|~=|<=|>=|<|>)"
                     r"e?\[?([sOL]?)\[?I?\]?\]?$", b)
    if m:
        d, neg, a, op, c = m.groups()
        if op in ("==", "~=", "<=", ">=", "<", ">"):
            return f"CMP {d} {a} {op} {c}" + (" (negated)" if neg else "")
        return f"{OPS3.get(op, op)} {d} {a} {c}" + (" (negated)" if neg else "")

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=(-?)e\[([sOL])\[I\]\]", b)
    if m:
        d, neg, a = m.groups()
        return f"UNM {d} {a}" if neg else f"MOVE {d} {a}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=#e\[([sOL])\[I\]\]", b)
    if m:
        return f"LEN {m.group(1)} {m.group(2)}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=not e\[([sOL])\[I\]\]", b)
    if m:
        return f"NOT {m.group(1)} {m.group(2)}"

    # --- register op constant ---------------------------------------------
    m = re.fullmatch(r"e\[([sOL])\[I\]\]=e\[([sOL])\[I\]\](\+|-|\*|/)([sOc])\[I\]", b)
    if m:
        d, a, op, src = m.groups()
        kind = {"s": "K", "c": "C", "O": "L"}[src]
        return f"{OPS3.get(op, op)} {d} {a} {kind}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=([sOcL])\[I\]\+e\[([sOL])\[I\]\]", b)
    if m:
        d, src, a = m.groups()
        kind = {"s": "K", "c": "C", "O": "L", "L": "I"}[src]
        return f"ADD {d} {kind} {a}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=e\[([sOL])\[I\]\]+([sOcL])\[I\]", b)
    if m:
        d, a, src = m.groups()
        kind = {"s": "K", "c": "C", "O": "L", "L": "I"}[src]
        return f"ADD {d} {a} {kind}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=([sOcL])\[I\]\*e\[([sOL])\[I\]\]", b)
    if m:
        d, src, a = m.groups()
        return f"MUL {d} {'K' if src == 's' else src.upper()} {a}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=e\[([sOL])\[I\]\]\+([sOc])\[I\]", b)
    if m:
        return f"ADD {m.group(1)} {m.group(2)} K"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=([sOcL]?)\[?I?\]?\+c\[I\]", b)
    if m:
        return f"ADD {m.group(1)} K"

    # --- calls ------------------------------------------------------------
    m = re.fullmatch(r"e\[([sOL])\[I\]\]\((.*?)\)", b)
    if m:
        d, args = m.group(1), m.group(2)
        if not args:
            return f"CALL0 {d}"
        n = args.count(",") + 1
        return f"CALL{n} {d}"

    # --- tables -----------------------------------------------------------
    if re.fullmatch(r"e\[([sOL])\[I\]\]=\{\}", b):
        return b and "NEWTABLE " + re.match(r"e\[([sOL])", b).group(1)

    m = re.fullmatch(r"e\[([OL])\[I\]\]\[(.*?)\]=e\[([sOL])\[I\]\]", b)
    if m:
        t, key, src = m.groups()
        return f"SETTABLE {t} [key] {src}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]\[(.*?)\]", b)
    if m:
        return f"GETTABLE {m.group(1)}"

    # --- upvalues ---------------------------------------------------------
    if re.fullmatch(r"m=X\[[sOL]\[I\]\];e\[[sOL]\[I\]\]=m\[6\]\[m\[5\]\]", b):
        return "GETUPVAL"
    if re.fullmatch(r"m=X\[[sOL]\[I\]\];m\[6\]\[m\[5\]\]=e\[[sOL]\[I\]\]", b):
        return "SETUPVAL"
    if re.fullmatch(r"m=X\[[sOL]\[I\]\];m\[6\]\[m\[5\]\]\[.*$", b):
        return "SETUPVALIDX"

    # --- control flow -----------------------------------------------------
    m = re.fullmatch(r"I=e\[([sOL])\[I\]\]", b)
    if m:
        return f"JUMP {m.group(1)}"
    if b == "I=O[I]":
        return "JUMPI O"
    if re.match(r"I=if ", b):
        rel = re.search(r"\]\s*(<=|>=|==|~=|~=|<|>)", b)
        return f"JUMPIF {rel.group(1) if rel else ''}".strip()

    # --- VM internals -----------------------------------------------------
    if b.startswith("m,H={...},L[I]"):
        return "VARARG"
    if b.startswith("m,H,M=O[I],L[I],s[I]"):
        return "CALLVAR"
    if b.startswith("m,H,M=s[I],O[I],L[I]"):
        return "RETURN/CALLVAR"
    if b.startswith("a,m,H={[5]=F"):
        return "CLOSURE"
    if b.startswith("m=s[I];H,M,N="):
        return "CALL R M N"
    if b.startswith("k[I]=94"):
        return "SUPEROP/prefetch"
    if b.startswith("H,m=(mul32(O[I]"):
        return "SUPEROP/decode"
    if b.startswith("H,m=s[I],O[I]+1"):
        return "SUPEROP/load"
    if b.startswith("g=") and b.endswith("break"):
        return "TAILCALL/JUMP"
    if b.startswith("local T=L[I];if A"):
        return "CLOSEUPVAL"
    if b.startswith("local K=O[I];if A"):
        return "CLOSEUPVAL T"
    if b.startswith("D=e[L[I]]"):
        return "LOADK D"
    m = re.fullmatch(r"e\[([sOL])\[I\]\]=u\((.*?)\)", b)
    if m:
        return f"TOSTRING {m.group(1)}"
    m = re.fullmatch(r"e\[([sOL])\[I\]\]=R\[(.*?)\]", b)
    if m:
        return f"GETIMPORT {m.group(1)}"
    m = re.fullmatch(r"e\[([sOL])\[I\]\]=((?:s|O|L|c|r|k|D|B|J)?)\[?I?\]?", b)
    if m:
        return f"LOAD {m.group(1)} {m.group(2)}".strip()

    # --- remaining simple shapes -----------------------------------------
    m = re.fullmatch(r"e\[([sOL])\[I\]\]=([sOcY])\[I\]\+([sOcL])\[I\]", b)
    if m:
        return f"ADD {m.group(1)} C K"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=([sOcL])\[\?I?\]?\.\.e\[([sOL])\[I\]\]", b)
    if m:
        return f"CONCAT {m.group(1)}"

    m = re.fullmatch(r"e\[([sOL])\[I\]\]=([sOcL])\[I\]", b)
    if m:
        return f"LOAD {m.group(1)} {m.group(2)}"

    if re.fullmatch(r"e\[[sOL]\[I\]\]\(\)", b):
        return "CALL0"

    # `e[L[I]] = e[s[I]] ~= O[I]` and friends compare against a bare constant
    m = re.fullmatch(r"e\[([sOL])\[I\]\]=e\[([sOL])\[I\]\](==|~=|<=|>=|<|>)([sOcLkB])\[?I?\]?", b)
    if m:
        return f"CMP {m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}"

    if b.startswith("local T,Rq,Fq="):
        return "FLOOR/tonumber"
    if b.startswith("local K,T,h=") or b.startswith("local K,T,h") :
        return "BITOP32"
    if b.startswith("local K,T,h="):
        return "BITOP32"
    if "mul32(" in b and b.startswith("local K,"):
        return "BITOP32"
    if b.startswith("local K") and "4294967295" in b:
        return "BITOP32"
    if b.startswith("local T") and "4294967295" in b:
        return "BITOP32"
    if b.startswith("m,H,M,N="):
        return "CALL/UNPACK"
    if b.startswith("m=L[I];local T,Rq,Fq=F()"):
        return "CALLVAR/unc"
    if b.startswith("m=") and "e[m]=H(M,N)" in b:
        return "CALL2 R"
    if b.startswith("m=") and "i(m,1," in b:
        return "VARARG"
    if b.startswith("H,m=") and "for T=1," in b:
        return "SUPEROP/decode"
    if b.startswith("local ") and "repeat" in b:
        return "NUMFLOOR"
    if b.startswith("e[") and ";" in b:
        return "MULTI"

    return "--"


def mnemonic(body: str) -> str:
    return classify(normalize(body))


def normalize(body: str) -> str:
    return " ".join(body.split()).rstrip(";").strip()


def sanitize(body: str) -> str:
    return normalize(body).replace("`", "'") or "(empty)"


def write_table(lines: List[str], key: str, title: str, count: int, tab: Dict[str, str]) -> None:
    lines += [f"## {title}", "", "| # | mnemonic | handler body (verbatim from `[49]`) |",
              "|---:|---|---|"]
    named = 0
    for v in range(count):
        body = tab.get(str(v), "")
        mn = mnemonic(body)
        named += mn != "--"
        lines.append(f"| {v} | `{mn}` | `{sanitize(body)}` |")
    lines += ["", f"*{named} of {count} rows have an inferred mnemonic; the rest are "
                  f"genuine multi-step handlers listed verbatim.*", ""]


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "work/decompiled/vm_opcodes.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "work/decompiled/vm_isa.md"
    data = json.load(open(src, encoding="utf-8"))

    lines = [
        "# Payload VM instruction set",
        "",
        "Recovered mechanically from field `[49]` of the obfuscated chunk by",
        "`tools/isa_extract.py` + `tools/vm_isatree.py` (which walk the real Luau",
        "AST produced by `tools/astdump.cpp`). Nothing here is hand-transcribed:",
        "every body is quoted from the source, so it can be re-derived and checked.",
        "",
        "## How the dispatcher is layered",
        "",
        "`[49]` is **not** one `if`-tree. It contains a main interpreter loop plus",
        "three secondary dispatch loops, switched by a continuation marker `g`:",
        "",
        "```lua",
        "while true do local h=k[I]; ... end          -- h: the bytecode interpreter",
        "if g==150 then while true do local v=k[I]   -- v: continuation loop",
        "if g==102 then while true do local v=O[I]   -- v: second variant",
        "if g==160 then while true do local Z=k[I]   -- Z: constant-pool loop",
        "```",
        "",
        "## Ranges that actually exist",
        "",
        "The tables were rebuilt by walking each dispatch tree with the real value",
        "interval, so we can say exactly which opcode values are reachable:",
        "",
        "| dispatcher | reachable range | distinct opcodes | above the range |",
        "|---|---|---:|---|",
        "| `h` (interpreter) | 0..95 | **96**, all distinct | 96..255 collapse onto 2 padding bodies |",
        "| `Z` (constant pool) | 0..29 | **30**, all distinct | 30..255 collapse onto 1 body |",
        "| `v` (continuation) | 0..49 | **50**, all distinct | 50..255 collapse onto a few bodies |",
        "",
        "96 real opcodes is exactly what an 8-bit opcode byte with a *sparse*",
        "encoding looks like: the loader never emits a value it has no handler for,",
        "and the obfuscator filled the unused tail of the tree with a couple of",
        "junk branches so that the tree still spans 0..255 and hides the real",
        "extent. `h=94` is a deliberate hole (its handler body is empty).",
        "",
        "## Register file",
        "",
        "Instruction words are unpacked into parallel arrays by the loader",
        "(`k[I]` is the opcode byte; the `SUPEROP/*` handlers below do the",
        "unpacking with the 32-bit multiply helper). Handlers read:",
        "",
        "| word | role |",
        "|---|---|",
        "| `L`,`O`,`s`,`k` | operand fields of the current instruction |",
        "| `r`,`c`,`Y` | constant-pool / upvalue indices |",
        "| `e` | the register stack (values) |",
        "| `X` | upvalue objects (`X[n][6][n][5]` is the captured cell) |",
        "| `I` | instruction pointer |",
        "| `g` | continuation marker (150 / 102 / 160) |",
        "",
    ]

    write_table(lines, "h", "Dispatcher `h` — bytecode interpreter (0..95)", 96, data["h"])
    write_table(lines, "Z", "Dispatcher `Z` — constant-pool loop (0..29)", 30, data["Z"])
    write_table(lines, "v", "Dispatcher `v` — continuation loop (0..49)", 50, data["v"])

    with open(dst, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    for key, n in (("h", 96), ("Z", 30), ("v", 50)):
        named = sum(mnemonic(data[key].get(str(i), "")) != "--" for i in range(n))
        print(f"{key}: {named}/{n} named")
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
