# 05 — Method: how these dumps were produced

Everything in `work/dumps/`, `work/capture/` and `work/rec/` can be regenerated
from this repository.

## 5.1 A Luau host that can run this chunk

The chunk needs `loadstring`, `readfile`/`writefile`, and it needs to be
*compiled from source* (`luau_load` only accepts bytecode). The stock `luau`
CLI has neither `readfile` nor Roblox datatypes, so `tools/host.cpp` provides:

```
readfile(path)              writefile(path, data)     log(str) / logflush()
getupvalue(fn, n)           setupvalue(fn, n, v)     getinfo(level)
loadstring(src, name)                                exit(code)
```

Build (Luau itself from `github.com/luau-lang/luau`, commit `e3275c2`):

```bash
git clone --depth 1 https://github.com/luau-lang/luau.git /tmp/luau-src
cd /tmp/luau-src && make config=release luau luau-compile -j4

g++ -g -O2 -std=c++17 \
  -ICommon/include -IVM/include -IAst/include -ICompiler/include \
  -IConfig/include -IBytecode/include -ICodeGen/include \
  /home/user/ObfTest/tools/host.cpp \
  build/release/libluauvm.a build/release/libluaucompiler.a \
  build/release/libluauast.a build/release/libluaucommon.a \
  build/release/libluaubytecode.a build/release/libluauconfig.a \
  build/release/libluaucodegen.a \
  -o /home/user/ObfTest/tools/luau-host -lpthread
```

Set `LUAU_CODEGEN=1` to enable native code generation at run time
(`Luau::CodeGen::compile` with `CodeGen_ColdFunctions`). Measured on this chunk
it gives no speed-up — see note below.

## 5.2 Making the source readable

`tools/format_luau.py` is a token-aware indenter for Luau (handles nested long
brackets, long strings, `--` comments, and `function/if/while/for/repeat/do …
end` nesting). It turns the single line into `work/n_formatted.luau` (4,448
lines). It is a *display* tool: it does not rename anything, and the flow is
still table-driven, so do not expect it to read like normal code.

## 5.3 Intercepting the payload

Run harnesses (all take the log path as `argv[2]` of the host):

| script | what it does |
| --- | --- |
| `tools/run_full.lua` | plain run; logs every stub API access, progress every 500 k byte writes |
| `tools/run_capture.lua` | intercepts `loadstring` (saves source), `buffer.tostring` (saves buffers) |
| `tools/run_rec.lua` | `record_buffers.lua`: tags each buffer, dumps on a write budget |
| `tools/run_trace.lua` | aborts after two `task.wait` calls to capture start-up only |

The environment shims:

* `tools/sandbox_shim.lua` — inert `Vector3/Vector2/Color3/UDim/UDim2/Rect`,
  `typeof`, `getfenv/setfenv`, `bit32`, `buffer`;
* `tools/roblox_stub.lua` — a proxy object that materialises on any field
  access, logs `GET/SET/CALL/GLOBAL` lines, and provides `task`, `game`,
  `workspace`, `Instance.new`, `Enum`, and ~40 datatype constructors.

Proxy trick used for `roblox_stub.lua`: every datatype global is a table with a
`.new` field installed up-front, because the chunk probes for `.new` before
anything else and a pure `__index` global would not survive `R[nil][.new]`.

## 5.4 Extracting the VM's state

`getupvalue` is enough to walk `tab.rH`'s 32 upvalues. Two harnesses:

* `/tmp/dump2.lua` (session scratch) serialised `uv[6]` and `uv[13]` to Lua —
  these are `work/dumps/proto6.lua` and `work/dumps/uv13.lua`;
* a small tab-separated dumper wrote `work/dumps/tab_uv{6,7,8,12,13}.tsv`
  (`key <tab> type <tab> value`), which is what the Python analysis reads.

Note: `uv13` must be dumped *after* `tab:rH()` has run, because `qH`/`vH` fill
`CH` and `Z` lazily.

## 5.5 Gotchas (things that cost time)

* **`debug.getupvalue` does not exist** in Luau — only `debug.info` and
  `debug.traceback`. Use the C-side `lua_getupvalue` (wrapped in `host.cpp`).
* **`luau_load` needs bytecode**; feeding source yields
  `bytecode version mismatch (expected [3..14], got N)`.
* **`lua_sethook` does not exist**; `lua_callhook` + `lua_singlestep` are the
  only debug hooks, and enabling single-step on this chunk takes the run from
  "slow" to "unusable".
* **The run is not an infinite loop.** It looks like one because there is no
  output and no `task.wait`, but it is doing real work at ~85 k byte writes/s.
  Do not add a watchdog that aborts before ~20 M writes, or you will throw away
  the interesting part.
* **Native codegen does not help.** The hot loop is `while true` over table and
  buffer builtins; measured 47 s vs 42 s per 4 M writes with and without
  `--codegen-cold`.
* **`string.gsub` with a table replacement is sequential**, so the payload
  decode must be modelled as one left-to-right pass (see `02-payload-decoding.md`).
* Large `log()` volumes must be buffered in the host (`host_flush`) or the
  per-call `fopen` dominates the runtime.

## 5.6 Rebuilding every artefact

```bash
cd /home/user/ObfTest

# 1. decoded payload
python3 -c "import tools.vm_tables as v,re;s=open('work/original/n.txt').read();i=s.find('XH=[=[');j=s.find(']=]',i);open('work/dumps/xh_decoded.bin','wb').write(v.xh_decode(s[i+6:j]).encode('latin1'))"

# 2. formatted source
python3 tools/format_luau.py work/original/n.txt work/n_formatted.luau

# 3. VM state tables
./tools/luau-host tools/run_rec.lua work/logs/rec.log          # -> work/rec/*.bin

# 4. full behavioural run (long; stop when work/logs/full_run.log stops growing)
./tools/luau-host tools/run_full.lua work/logs/full_run.log
```
