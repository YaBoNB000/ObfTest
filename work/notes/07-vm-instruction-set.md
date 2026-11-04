# 07 — The payload VM's instruction set

Field `[49]` is the payload's virtual machine. This note records how its
instruction set was recovered, what the encoding actually is, and why earlier
attempts recovered almost nothing.

Everything below is reproducible:

```bash
python3 tools/split_fields.py                 # chunk -> work/decompiled/fields/
python3 tools/build_isa.py                    # field_49 -> vm_opcodes.json + vm_isa.md
```

## 1. Why the earlier attempts failed

Three separate mistakes, each of which alone was fatal:

1. **Hand-rolled block counting.** The obfuscator emits *empty* branches:

   ```lua
   if h<96 then if h~=95 then else <body> end end
   ```

   and uses `repeat … until` for numeric coercion. A naive counter that treats
   every `end` as closing an `if` desyncs on both, so the tree was never
   delimited. Any tool here must use a real parser.
2. **Assuming one dispatcher.** `[49]` contains **four** `while true do` loops,
   not one. `h` is the interpreter; `v` (two variants) and `Z` are entered by
   setting a continuation marker `g`.
3. **Reading opcode numbers off `==` tests.** The tree is a binary search over
   an interval. `if h<71 then <A> else if h==72 then <B> else <C> end end`
   means `A` answers for everything below 71, not "no opcode". A correct
   recovery must carry the interval down the tree.

## 2. The method that works

`tools/astdump.cpp` links against the Luau parser (`Luau::Parser::parse`) and
prints every control-flow node with its exact source span. Then:

* `tools/isa_extract.py` finds guards and leaves (a leaf is a guard whose
  `then` branch holds no nested guard on the same register);
* `tools/vm_isatree.py` **walks the tree with the interval**, so every opcode
  value ends up with the branch that actually runs for it. Three rules make
  this exact:

  | shape in the source | meaning |
  |---|---|
  | `if X < N then A else B` | A for `X < N`, B for `X >= N` |
  | `if X == N then A else B` | A only for `X == N` |
  | `if X ~= N then A else B` | branch roles are **swapped** |
  | `if X ~= N then else B` | empty then-branch: B answers for *exactly* `N` |

  The empty-branch case is the one that silently corrupts a na"ive walker: an
  empty branch means "no code runs", not "fall back to the parent body".

## 3. Result: three tables, 96 + 30 + 50 real opcodes

| dispatcher | loop header | reachable | distinct | notes |
|---|---|---|---:|---|
| `h` | `while true do local h=k[I]` | 0..95 | **96** | the bytecode interpreter |
| `Z` | `if g==160 then while true do local Z=k[I]` | 0..29 | **30** | constant-pool loop |
| `v` | `if g==150 / g==102 then … local v=…[I]` | 0..49 | **50** | continuation loop |

For every table, values **above** the range collapse onto two or three junk
branches. That is not a bug in the recovery: the obfuscator padded the search
tree so it still spans 0..255 and the real extent is not visible from the
shape of the code. Evidence that the ranges are the real ones:

* inside its range every value has a **distinct** handler (96 distinct for `h`,
  30 for `Z`, 50 for `v`) — and the "distinct" test uses the verbatim body, so
  two opcodes can only collide if they execute byte-identical code;
* `h == 94` is a deliberate **hole**: its handler body is empty. Opcode 94 is
  instead produced *at runtime* by the superinstruction — handlers `1`, `28`,
  `29`, `95` rewrite the instruction stream and set `k[I]=94`;
* 96 opcodes is what Luau's own 8-bit opcode byte supports as a sparse table.

## 4. Register file and operand encoding

The loader unpacks each instruction into parallel arrays; handlers index them
with the instruction pointer `I`:

| symbol | role |
|---|---|
| `k[I]` | opcode byte |
| `L[I]`,`O[I]`,`s[I]` | operand fields |
| `r[I]`,`c[I]`,`Y[I]` | constant / upvalue indices |
| `e[…]` | the register stack |
| `X[…]` | upvalue objects (`X[n][6][n][5]` is the captured cell) |
| `I` | instruction pointer |
| `g` | continuation marker (150 / 102 / 160) |
| `m`,`H`,`M`,`N` | scratch used by call/vararg handlers |

Bit helpers used by the superinstructions (from `[49]`'s captured builtins):
`P = J` and `Q = z` are the 32×32→32 bit32 multiply split into 16-bit halves,
`U = C` and `w = m` are the two shifts, `T = E` is `table.move`.

## 5. What the opcodes look like

`work/decompiled/vm_isa.md` lists every opcode with a mnemonic and the
verbatim handler. The interpreter's set is a conventional Lua/Luau ISA —
`MOVE`, `LOAD*`, `GET/SETUPVAL`, `NEWTABLE`, `GET/SETTABLE`, `ADD/SUB/MUL/
IDIV/MOD/POW`, `CONCAT`, `LEN`, `UNM`, `NOT`, `CMP`, `CALL*`, `VARARG`,
`CLOSURE`, `JUMP*`, `TAILCALL` — plus the superinstruction handlers that
rewrite the instruction stream in place.

67 % of `h`'s rows carry an inferred mnemonic; the remaining rows are
multi-step handlers and are quoted verbatim rather than guessed at.

## 6. Reproducing

```bash
# once: fetch Luau and build the AST dumper
curl -fsSL https://codeload.github.com/luau-lang/luau/tar.gz/e3275c2 | tar xz
mv luau-e3275c2* /tmp/luau-src
g++ -std=c++17 -O2 -I /tmp/luau-src/Ast/include -I /tmp/luau-src/Common/include \
    tools/astdump.cpp /tmp/luau-src/Ast/src/*.cpp /tmp/luau-src/Common/src/*.cpp \
    -o /tmp/astdump

# every time
python3 tools/build_isa.py
```

`build_isa.py` prints each stage's command line, so the intermediate
`/tmp/isa_build/*.json` tables can be inspected when a row looks wrong.
