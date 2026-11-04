#!/usr/bin/env python3
"""End-to-end reproduction of the payload VM's instruction set.

Runs the whole pipeline from the stored field file to the published artefacts:

    field_49.luau --[wrap]--> wrapped chunk --[astdump]--> ast.tsv
                                          --[isa_extract]--> leaf table
                                          --[vm_isatree]---> full opcode tables
                                          --[gen_isa_md]---> vm_isa.md

Prerequisites
-------------
* `astdump` built from tools/astdump.cpp against a Luau checkout:
      g++ -std=c++17 -O2 -I $LUAU/Ast/include -I $LUAU/Common/include \\
          tools/astdump.cpp $LUAU/Ast/src/*.cpp $LUAU/Common/src/*.cpp -o /tmp/astdump
  (set LUAU_ASTDUMP=/tmp/astdump, or put `astdump` on PATH.)
* `$LUAU` defaults to /tmp/luau-src; see work/notes/05-method.md for the fetch.

Usage:  python3 tools/build_isa.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

FIELD = "work/decompiled/fields/field_49.luau"
TMP = "/tmp/isa_build"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=True, **kw)


def main() -> int:
    if not os.path.exists(FIELD):
        print(f"missing {FIELD}; run tools/split_fields.py first", file=sys.stderr)
        return 1
    os.makedirs(TMP, exist_ok=True)

    # 1. wrap: the stored field is `[49]=function(...)...end` -- drop the key
    #    prefix and make it a loadable chunk.
    raw = open(FIELD, encoding="utf-8").read()
    body = raw[raw.index("function"):]
    wrapped = os.path.join(TMP, "f49.luau")
    with open(wrapped, "w", encoding="utf-8") as fh:
        fh.write("local t=" + body + "\nreturn t\n")

    # 2. AST dump with the real Luau parser
    astdump = os.environ.get("LUAU_ASTDUMP") or shutil.which("astdump")
    if not astdump:
        print("astdump not found: set LUAU_ASTDUMP or build tools/astdump.cpp",
              file=sys.stderr)
        return 1
    tsv = os.path.join(TMP, "ast.tsv")
    with open(tsv, "w", encoding="utf-8") as fh:
        run([astdump, wrapped], stdout=fh)

    # 3. leaf guards (sanity view of the three dispatchers)
    run([sys.executable, "tools/isa_extract.py", tsv, wrapped])

    # 4. full opcode tables -- only the reachable ranges are kept: h 0..95,
    #    Z 0..29, v 0..49. Everything above those ranges is padding the
    #    obfuscator added so the tree spans 0..255 (see note 07).
    ranges = {"h": 96, "Z": 30, "v": 50}
    tables = {}
    for var, n in ranges.items():
        out = os.path.join(TMP, f"ops_{var}.json")
        run([sys.executable, "tools/vm_isatree.py", tsv, wrapped, "--var", var,
             "--json", out])
        tab = json.load(open(out, encoding="utf-8"))
        tables[var] = {str(k): tab.get(str(k), "") for k in range(n)}

    final = {
        "_note": (
            "Recovered from field [49] by tools/build_isa.py. Only these ranges "
            "are reachable: h 0..95 (96 distinct opcodes), Z 0..29, v 0..49. "
            "Values above each range collapse onto a couple of padding bodies "
            "in the dispatcher and are never emitted by the loader."
        ),
        "h": tables["h"],
        "Z": tables["Z"],
        "v": tables["v"],
    }
    with open("work/decompiled/vm_opcodes.json", "w", encoding="utf-8") as fh:
        json.dump(final, fh, indent=1)

    # 5. human-readable ISA document
    run([sys.executable, "tools/gen_isa_md.py"])
    print("\nOK: work/decompiled/vm_opcodes.json + work/decompiled/vm_isa.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
