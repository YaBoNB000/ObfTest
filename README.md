# ObfTest — reverse engineering notes for the obfuscated Luau chunk

This repository contains a complete workbench for analysing `work/original/n.txt`,
a 286,180 byte single-line obfuscated Luau chunk, together with everything that
was learned about it.

> **TL;DR** — the file is a *recursive* obfuscator: the visible Luau source is a
> thin bootstrap that (1) decodes a 200 KB payload out of a `string.gsub`
> substitution table, (2) deserialises ~128 bytecode blobs out of five flat
> numeric tables with a generated state machine, and (3) runs the result on a
> custom register VM written *in Luau*, which itself is not readable until you
> reconstruct its tables at run time. The payload that finally executes is a
> Roblox script whose first observable action is drawing a 2,311 byte ASCII-art
> logo into a buffer.

## Repository map

| Path | What it is |
| --- | --- |
| `work/original/n.txt` | pristine copy of the obfuscated chunk |
| `work/n_formatted.luau` | the chunk re-indented into 4,448 readable lines (`tools/format_luau.py`) |
| `work/notes/` | the analysis write-up — **start with `01-architecture.md`** |
| `work/dumps/` | raw data extracted from the running VM (tables, buffers, TSV dumps) |
| `work/capture/` | buffers the payload itself produced at run time (ASCII art, recovered strings) |
| `work/strings/` | plaintext strings recovered from the payload + interpretation |
| `work/decompiled/` | formatted bootstrap source and an annotated excerpt of the VM dispatch loop |
| `tools/luau-host` | purpose-built Luau host binary (see below) |
| `tools/host.cpp` | source of that host: `readfile`/`writefile`/`log`/`getupvalue`/`setupvalue`/`getinfo` + optional native codegen |
| `tools/vm_tables.py` | the extracted cryptographic tables, re-implemented in Python |
| `tools/format_luau.py` | token-aware Luau pretty printer used to make the source readable |
| `tools/sandbox_shim.lua` | minimal Roblox-ish datatype shims (`Vector3`, `Color3`, `UDim`, …) |
| `tools/roblox_stub.lua` | permissive "everything is an object" Roblox environment that logs every API access |
| `tools/capture_payload.lua` | intercepts `loadstring`, `buffer.tostring`, and byte writes |
| `tools/record_buffers.lua` | tags every buffer and dumps its contents so the payload's bytecode can be studied |
| `tools/run_*.lua` | ready-to-run harnesses for the host |

## Reading order

1. `work/notes/01-architecture.md` — the six layers and how they nest.
2. `work/notes/02-payload-decoding.md` — `XH`/`DH`/`kH`, the 199,880 byte result,
   and why a naive `re.sub` gets it wrong.
3. `work/notes/03-vm-internals.md` — the generated state machine in `tab.rH`, the
   run-time bytecode buffers, the S-box / state table, and the bytecode cipher.
4. `work/notes/04-payload-behaviour.md` — what actually executes: the Roblox API
   surface, the ASCII logo, the animation loop.
5. `work/notes/05-method.md` — how the host binary and shims were built, and how
   to reproduce every dump in `work/dumps/`.
6. `work/notes/06-status-and-next-steps.md` — what is proven, what is missing,
   and the effort left.

## Reproducing

```bash
# rebuild the host (Luau is built separately, see work/notes/05-method.md)
cd /tmp/luau-src && g++ -g -O2 -std=c++17 \
  -ICommon/include -IVM/include -IAst/include -ICompiler/include \
  -IConfig/include -IBytecode/include -ICodeGen/include \
  /home/user/ObfTest/tools/host.cpp \
  build/release/libluauvm.a build/release/libluaucompiler.a \
  build/release/libluauast.a build/release/libluaucommon.a \
  build/release/libluaubytecode.a build/release/libluauconfig.a \
  build/release/libluaucodegen.a \
  -o /home/user/ObfTest/tools/luau-host -lpthread

# run the chunk against the logging Roblox stub
cd /home/user/ObfTest && ./tools/luau-host tools/run_full.lua work/logs/full_run.log
```

## Status / honesty note

The *outer* layers are fully understood and reproducible from this repository.
The innermost layer — the payload's own register VM, whose 170 opcode handlers live
in `uv13` of the `rH` closure — is **not** transcribed into readable Luau yet.
What is established about it, including the exact cipher it uses to decode its own
bytecode at run time, is documented in `03-vm-internals.md`; the remaining work is
purely mechanical (a 170-entry dispatch table) and is listed there as next steps.
