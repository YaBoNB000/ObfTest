# 01 — Architecture of the obfuscated chunk

`work/original/n.txt` is a single 286,180 byte line. It has six nesting layers.

```
layer 0  the visible Luau source            (286 KB, one line)
layer 1  handler table + setmetatable({...}, {}):rH()(...)
layer 2  rH  = generated state machine that rebuilds 128 bytecode blobs
layer 3  the blobs = a register VM's code + constants
layer 4  that VM = 170 closures in uv13 of rH
layer 5  the payload the VM runs = Roblox script with its own bytecode cipher
```

## Layer 0 — the file itself

```lua
return setmetatable({ <180 entries>, I = {} }, {}):rH()(...)
```

The table literal holds 60 array slots and 120 short-string keys
(`A`, `B`, `BH`, … `XH`, `Y`, `Z`, `_`). The `...` at the end is a vararg call;
with no arguments the chunk simply returns the value produced by the VM.

Everything visible is *one* table literal plus a handful of functions written
directly in it (`tH`, `O`, `Q`, `qH`, `WH`, `X`, `K`, `G`, `M`, `c`, `g`, `h`,
`_`, `z`, `B`, `E`, …). There are no statements, no loops, no strings except the
two blobs `XH` and `DH`, and no numbers except the nine in `C` and the tables.

Printable version: `work/n_formatted.luau` (4,448 lines, produced by
`tools/format_luau.py`). Even formatted, the code is meaningless until you know
what the generated functions do, because every variable name is one character
and the control flow is table-driven.

## Layer 1 — entry point

`setmetatable({...}, {}):rH()(...)` calls `rH`, a closure over **32 upvalues**
that are *shared with the returned function*:

| upvalue | content |
| --- | --- |
| 1, 3, 9, 10, 11, 14–17, 22, 24–31 | helper closures |
| 2, 4, 5 | scalars `175`, `31`, `10546` |
| **6, 7, 8, 12** | flat numeric tables, 10,557 / 10,560 / 10,560 / 10,559 entries |
| **13** | the VM's "world": 170 closures + `CH` S-box + `Z` state table + `XH`/`DH`/`kH` + 2 buffers |
| 18, 19, 21, 32 | one-element tables `{[0]=…}` (deserialiser scratch space) |
| 23 | `{[4]=buffer(157168 bytes), [5]=tables, [6]=metatable, [7]=false}` |

`rH` itself returns a **new closure** whose upvalues are exactly this set, with
`uv[2] = 175` — i.e. the initial program counter of the deserialiser.

## Layer 2 — `rH` is a compiled state machine

`rH` is not written as a loop. It is a chain of *handler functions* each of which
takes the current state tuple, does a small piece of work, and returns the next
state tuple, e.g.

```lua
dH = function(R,F,Y,d,L,O,k)
  if k<=2 then
    local v=R[53](F,3+L)                      -- read byte
    local y,K,c,s,r=2097152*(d-128),(Y-128)*128,(O-128)*16384,v%128,v%128
    local Y=2097152*(v-r); v=K+(c+s)+(Y+y)    -- 4 x 7-bit LEB128 decode
    return 2,20,4+L,v,O                       -- next handler + new state
  elseif k<=3 then ...
```

`rH`'s body is the dispatcher:

```lua
while F do
  if N<=20 then if N<=9 then ... N,J,m,x=R:PH(J,z,x,N,m,M,W,a) ...
```

with 30 distinct continuations (`PH`, `dH`, `EH`, `JH`, `eH`, `hH`, `lH`,
`SH`, `HH`, `qH`, `KH`, `WH`, `aH`, `M`, `O`, `Q`, …). This is a
**continuation-passing interpreter over LEB128-encoded records** — a standard
"virtualise the loader" trick.

The records come from `uv[6]`, `uv[7]`, `uv[8]`, `uv[12]`. All four are flat
`{[i]=number}` tables with no gaps, values in `0…536,870,911` (2²⁹−1), and
`uv[18..21]` hold the cursors. Byte-level helpers used: `buffer.readu8`,
`buffer.readu16`, `buffer.readu32`, `buffer.readi32`, `buffer.readf64`,
`buffer.readstring`.

**What it produces:** bytecode buffers. Caught at run time with
`tools/record_buffers.lua` (see `work/rec/`):

| buffer | size | first bytes | meaning |
| --- | --- | --- | --- |
| `b007` | 2,311 | `\n\t\t\t\t .@%(/*,...` | **ASCII-art logo** (materialised as a string) |
| `b002` | 199,880 | arbitrary | the decoded `XH` payload buffer |
| `b003` | 157,168 | arbitrary | `uv23[4]`, the VM's data buffer |
| `b004` | 53,749 | `02 81 2f 1f …` | proto #129, length 47 |
| `b028` | 7,788 | `02 2b 1f …` | proto #43 |
| `b050` | 4,644 | `02 38 1f …` | proto #56 |
| `b030` | 3,559 | `02 35 1f …` | proto #53 |
| `b045` | 836 | `02 27 1f …` | proto #39 |
| `b043` | 754 | `02 14 1f …` | proto #20 |
| `b026` | 537 | `02 13 1f …` | proto #19 |
| `b024` | 234 | `02 0e 1f …` | proto #14 |
| `b039` | 182 | `02 0a 1f …` | proto #10 |
| `b037` | 281 | `02 0f 1f …` | proto #15 |
| `b041` | 651 | `02 1e 1f …` | proto #30 |
| `b047` | 329 | `02 22 1f …` | proto #34 |
| `b025/29/40` | 5 | `02 84 71/75/79` | tiny stubs (indices 132) |
| many | 3–16 | — | scratch buffers |

Two-byte prefix `\x02 <index>` followed by `\x1f` (a length/flag marker) recurs
across the bigger buffers: **the deserialiser walks a proto table of ≈128
entries keyed by index 10…132** and copies each proto's code into its own buffer.
The 53,749 byte buffer contains 319 occurrences of `\x02`, i.e. it packs many
smaller records into one allocation.

## Layer 3 — the blobs are VM code + constants

The VM's code stream is *itself encrypted* and is decoded on the fly. Inside the
innermost dispatch loop (in the `[26]` closure, see layer 4) there is:

```lua
local Y,k,E = y[s], O[s], v[5]
local J = C(E[Y], 535359694)   -- bit32.bxor with key 0x1FE6_... 
E[Y] = J
E,Y = v[4], J+1                -- next block = previous result + 1
local v,H
if J<128 then v,H=J,Y+1
else ... 4-byte LEB128 ... end -- length of the block to decode
Y,J = k*16843009, H+v
local X = J - v%4
for u=H,X-1,4 do z(E,u,(C(x(E,u),Y))) end   -- decrypt 4-byte words
for z=X,J-1,1 do a(E,z,(C(m(E,z),k))) end   -- decrypt tail bytes
```

That is a **block cipher over the payload buffer**: XOR the 4-byte length prefix
with a key, read a block, XOR each 32-bit word with a keystream word derived from
the block index, and XOR the tail byte-wise. The keys are visible in the
extracted tables (`work/dumps/tab_uv6.tsv` … `tab_uv12.tsv`), e.g.

```
535359694  0x1FE6_...    <- per-block key used in the dispatcher
535300123 … 535483773    <- the family of per-block keys (± 2^16 range)
536869725, 536870809, 536870911 (0x1FFFFFFF)  <- masks
```

## Layer 4 — the VM is 170 generated closures

`uv13` (`work/dumps/uv13.lua`) contains:

* **170 closures**, numeric keys 0…182 and names `A, B, C, D, E, F, …, z, BH, CH, DH, …`
  — these are the opcode handlers, called as `R[opcode](state…)`;
* `CH` — a 256-entry byte permutation (S-box), a true bijection;
* `Z` — a 256-entry table of 32-bit constants (`3710832576`, `2654941297`, … every
  value ≡ 0 mod 4 in a regular lattice: `0xDD34_xxxx`, `0xB6AE_xxxx`, …);
* `XH`, `DH`, `kH` — the payload blob and its substitution table;
* `F` and `Y` — buffers used as the VM's memory.

The S-box and `Z` are *generated*, not literal: `qH` (and `vH`) fill them with

```lua
qH = function(R,F,Y,d,L,O,k,v)
  if k<=29 then
    local y=(d+v*F)%256
    local K=(d+v*y)%256
    local c=(d+v*K)%256
    local s,r,G,N=(c*v+d)%256,R.Z,K*256,65536*c
    r[F]=s*16777216+N+(G+y)      -- Z[F] = packed 4-byte word
    R.CH[F]=s                    -- CH[F] = S-box byte
    return 12,Y,L
```

i.e. an iterated multiply-add chain producing both tables from three seeds. A
Python re-implementation is in `tools/vm_tables.py` (`sbox_step`) and the
extracted tables are reproduced there verbatim, verified to be a bijection over
0…255.

The payload is executed by this VM after `WH` produces it — `WH` is the handler
that closes the bootstrap:

```lua
WH = function(R,F,Y,d,L,O,k,v,y,K,c)
  ...
  else
    local Y,d = c[2], R[39](R[73](R.XH,5),R.DH,R.kH)   -- string.gsub(sub(XH,5),DH,kH)
    local O,k,v = R[91](d), #d-1, 5+0                  -- buffer.fromstring
    d = 0-v
    return 30,{v,Y,k+0,nil,d},0,{},O,F,L
```

## Layer 5 — the payload

The final layer is a Roblox script. Its observable behaviour is documented in
`04-payload-behaviour.md`; the short version is that it prints an ASCII-art logo
into a buffer, then enters a long per-byte decryption loop that never calls
`task.wait` (so it is a *batch* decode of ≈20 MB, not a frame loop), and it
touches only `buffer`, `bit32`, `table`, `string`, `coroutine`, `math` from the
standard library plus `typeof` / `Vector3` / `Color3` / `UDim2` / `Rect` from
Roblox.
