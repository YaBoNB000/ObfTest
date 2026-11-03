# 03 — VM internals

This is the deepest layer that has been mapped. It documents the generated
state machine `rH`, the bytecode buffers it builds, the payload VM, and the
cipher that VM uses to decode its own instructions at run time.

## 3.1 `rH`: a generated state machine

`tab.rH` has **32 upvalues**; they are the machine's registers *and* its
program. `tab.rH()` returns a **new closure** with the same upvalue array (a
`mH`-style entry thunk: `mH=function(R) return true,18,nil,nil,… end`), so the
starting state is `(18, nil, …)` with `uv[2]=175` as the first instruction
pointer.

The dispatch body is a binary search over state ids, e.g.

```lua
while F do
  if N<=20 then
    if N<=9 then
      if N<=4 then
        if N<=1 then N,J,m,x = R:PH(J,z,x,N,m,M,W,a);
        else s,Y,v,y,d = R:dH(M,z,m,J,x,N); if s==2 then N,J,m,x=Y,v,y,d elseif s==1 then return M end
      ...
```

Each `*H` helper is a *continuation*: it receives the whole register file as
arguments, performs one LEB128-sized decode step, and returns
`(nextStateId, newReg1, newReg2, …)`.

### The register file is the data

| upvalue | count | role |
| --- | --- | --- |
| `uv[6]` | 10,557 | record stream A (`{[i]=number}`, values ≤ 0x1FFFFFFF) |
| `uv[7]` | 10,560 | record stream B |
| `uv[8]` | 10,560 | record stream C |
| `uv[12]` | 10,559 | record stream D |
| `uv[18]`,`uv[19]`,`uv[21]` | 1 each | `{[0]=cursorTable}` read head |
| `uv[20]` | 0 | empty table, filled during the run |
| `uv[32]` | 1 | `{[0]=…}` write head |
| `uv[13]` | 181 | the payload VM's world (see 3.3) |
| `uv[23]` | 4 | `{[4]=buffer(157,168), [5]=tables, [6]=metatable, [7]=false}` |

`uv[6]` is byte-identical to `uv18[0]` at start-up, i.e. the deserialiser's
cursor table *is* the first record stream. Because all four streams are flat
`{[1..n]=int}` arrays of 29-bit numbers, they are best read as **packed bytes**,
not as Luau tokens.

### What it emits

Caught with `tools/record_buffers.lua` (dump in `work/rec/`, table repeated in
`01-architecture.md`): 128-ish bytecode buffers, index-prefixed

```
02 <protoIndex> 1f <length> <…code…>
```

with proto indices spread over 10…132, e.g. `b004 = 02 81 2f 1f …` (index 129,
length 47 — but the buffer as a whole is 53,749 bytes, so several records share
one allocation and the first `0x1f` is *not* the record length; the 4th byte is
part of the code).

Two buffers are special:

* `b007` (2,311 bytes) — the **ASCII-art logo**, converted to a string and
  written to the screen area;
* `b002` (199,880 bytes) — the `XH` payload after `WH`'s `gsub`+`fromstring`.

## 3.2 The payload VM's dispatch loop

The `[26]` entry of the handler table is a function that **returns** a closure
`W`; `W` is the interpreter entry. Its inner loop is:

```lua
local function c(...)
  local s,r,G = k,D
  local k = e()            -- host: allocate a frame
  local N = r(F)           -- host: get the payload's register bank
  local D,e,A,b,Z = H(function(...)
    local H,X,u
    while true do
      local j = L[s]                  -- opcode class table (uv13 world)
      local i = j<3
      if i then
        -- classes 0,1,2: call / tail-call / return
        ...
      else
        local Y = j>=4
        if Y then
          ...   -- class 4/5: host calls, error unwinding, buffer copies
        else
          local Y,k,E = y[s],O[s],v[5]
          local J = C(E[Y],535359694)   -- 0x1FE6xxxx : per-block XOR key
          E[Y] = J
          E,Y = v[4], J+1
          local v,H
          if J<128 then v,H=J,Y+1
          else ... end                  -- 4-byte LEB128 length
          Y,J = k*16843009, H+v         -- 0x01010101 * key
          local X = J - v%4
          for u=H,X-1,4 do z(E,u,(C(x(E,u),Y))) end     -- word decrypt
          for z=X,J-1,1 do a(E,z,(C(m(E,z),k))) end     -- byte decrypt
          y[s]=99; O[X]=144; d[v]=228; L[Y]=3           -- self-patch to "decoded"
        end
      end
      s += 1
    end
  end, ...)
```

Three things follow from this and they are all verifiable in the source:

1. **The VM is self-modifying.** `L[s]` is read first and *rewritten* to `3`
   after a block has been decoded, `y[s]` becomes `99`, `O[X]` becomes `144`,
   `d[v]` becomes `228`. That is the standard "decode each instruction block
   exactly once" pattern; it also means a static dump of the tables is *not*
   the final code image.
2. **Code is decrypted in 4-byte words**, with a byte tail: keystream word =
   `0x01010101 * blockKey`, block index = `previousResult + 1`.
3. **The opcode space is small** — the class test is `j<3`, `j>=4`, so opcode
   classes are 0…5 and the actual operation is chosen inside each class from
   `uv13`'s closures.

## 3.3 `uv13`: the VM's world

`work/dumps/uv13.lua` and `work/dumps/tab_uv13.tsv`. Composition:

| key(s) | content |
| --- | --- |
| `0…182` (170 present) | opcode handler closures |
| `A … z`, `BH … yH`, `_`, `[0]` | named helper closures (same pool) |
| `C` | `{39314, 3019592665, 268586211, 427097616, 1235795541, 4165977883, 4144480640, 2497155359, 1130321932}` |
| `CH` | 256-entry **S-box** (bijection on 0…255) |
| `Z` | 256-entry table of 32-bit words |
| `DH`, `XH`, `kH` | first-stage payload data |
| `F`, `Y` | buffers (VM memory) |
| `I`, `U` | tables |
| `34` | number (write cursor) |

`C` is used as `R[43](...)`-style XOR keys: `R[43]` is `bit32.bxor`, and the
nine values are 32-bit keys for nine different code paths.

### S-box and state table generation

Both `CH` and `Z` are computed at run time by `qH`:

```lua
qH = function(R,F,Y,d,L,O,k,v)
  if k<=29 then
    local y=(d+v*F)%256
    local K=(d+v*y)%256
    local c=(d+v*K)%256
    local s,r,G,N=(c*v+d)%256,R.Z,K*256,65536*c
    r[F]=s*16777216+N+(G+y)
    R.CH[F]=s
    return 12,Y,L
```

i.e. a four-round multiply-add S-box (`d + v·x mod 256` applied iteratively),
with the packed 4-byte word `s<<24 | c<<16 | k<<8 | y` written to `Z`. `vH`
uses the same tables to *stream-decrypt*:

```lua
vH = function(R,F,Y,d,L,O,k,v,y,K,c)
  if K<=33 then
    R[48](L,Y,(R[43](y,R[70](O,Y+k),R.Z[c])))   -- buffer.writeu32(L, Y, bxor(reg, buffer.readu32(O,Y+k), Z[c]))
    return 35,R.CH[c],F,Y
```

`R[48]=buffer.writeu32`, `R[70]=buffer.readu32`, `R[43]=bit32.bxor`. So each
written word is `read32(src) XOR stateWord[c]`, and the *next* index comes from
the S-box: `CH[c]`. That is an SPN-style **self-indexing XOR stream**: the
S-box byte determines where the next word will be read from, making the cipher
data-dependent rather than a simple keystream.

`tools/vm_tables.py` reproduces `CH` (verified bijection), `Z`'s generator, and
the word/byte helpers, so the cipher can be replayed without the obfuscated chunk.

## 3.4 The per-block key family

The dispatcher uses `535359694` (`0x1FE6_…`). The extracted tables contain a
whole family of neighbours with a ±2¹⁶ spread:

```
535300123  535300182  535300231  535300250
535352003  535352265  535352806  535359665
535359694  535359730  535359761  535360006
535360216  535360293  535360329  535360427
535361338  535363104  535363495  ...
535483773  535480500  535480479  535479461 ...
536869725  536870809  536870911 (0x1FFFFFFF, the mask)
```

All of them live in `uv[6]`/`uv[7]`/`uv[12]` at low indices — they are the
**first words of the record streams**, i.e. the passwords for successive blocks.

## 3.5 Register allocation evidence

From `qH`, `vH` and the `[26]` loop we can see the payload VM is a *register*
machine with an explicit frame array (`N`), a constant pool (`v[5]`), a bytecode
buffer (`E`), a program-counter array (`y`), an operand array (`O`) and a
"class" table (`L`). The `{...}` in the middle of the loop

```lua
H,X,u = O[s],{...},y[s]
M(X,1,H-1,u,N)
N[u+H-1] = E(J(H,...))
```

is a **vararg frame setup** (`M` = `table.move`) followed by a call whose result
is written at `N[u+H-1]`. This is why the profiler sees ~2 M `table.pack` calls:
the VM materialises `{...}` on every call instruction.

## 3.6 What is still missing

* The 170 `uv13` closures are *generated* code (each is a binary search over
  `stateId`) and have not been transcribed into readable Luau. Transcribing them
  is mechanical: for each closure, walk `if k<=N then … else …` and record
  `(bounds, operations, nextState)`.
* The four record streams (`uv6/7/8/12`) decode to the proto table via the `*H`
  continuations, but the *upstream* mapping from proto index to payload function
  is not yet written down.
* Consequently the payload itself is understood behaviourally (see
  `04-payload-behaviour.md`) rather than as source.
