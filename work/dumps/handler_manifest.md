# Top-level handlers in the obfuscated chunk

1 handler functions are defined directly in the table literal.

| handler | chars | `return <state>` sites |
| --- | --- | --- |
| `tH` | 81,690 | 180 |

## Note on the entry layout

The table literal is not a plain `name = value` sequence.  Luau allows
semicolon-free concatenation of statements inside a table constructor, and this
chunk mixes table fields with **statements**:

```lua
return setmetatable({[43]=bit32.bxor,[39]=string.gsub,[46]=bit32.countrz,
  tH=function(R,F,Y,d,L,O,k,v) … end,      -- field
  C={39314,…},                             -- field
  O=function(…) … end, Q=function(…) … end,
  ...                                      -- more fields
```

so a naive brace-matching scan sees the *whole literal body* as one "function"
(the first `tH=function(` never closes until the end of the literal).  The
manifest above therefore lists only the outermost span; the real inventory of
handlers is the 180 table entries listed in `01-architecture.md`, and the
per-handler extraction has to be done with a real Luau parser rather than
regex/brace counting.

`work/n_formatted.luau` is the practical way to read them: the pretty printer
tracks `function/if/for/while/do … end` and produces 4,448 lines.
