# 02 — Payload decoding (`XH`, `DH`, `kH`, `WH`)

Three table entries do all of the first-stage work:

```lua
DH = "[ v-~]"                       -- a Lua character class: space, v, w, x, y, z, {, |, }, ~
XH = [=[LPH+]smoiX8jLZ!_K?...]=]    -- 199,760 characters
kH = { ["}"]="nVP&F", y="Lj>ZX", x="L./<;", ["{"]="<9ju\\",
       z="#TGWk", ["|"]="uM0-u", [" "]="TbPE7", w='j\\#"A',
       v="Uj(j+", ["~"]="-IK3\\" }
```

and the handler that consumes them is `WH`:

```lua
WH = function(R,F,Y,d,L,O,k,v,y,K,c)
  if K<=34 then ...
  elseif K<=35 then ...
  else
    local Y,d = c[2], R[39](R[73](R.XH,5),R.DH,R.kH)   -- string.gsub(string.sub(XH,5), DH, kH)
    local O,k,v = R[91](d), #d-1, 5+0                  -- buffer.fromstring(d)
    d = 0-v
    return 30,{v,Y,k+0,nil,d},0,{},O,F,L
  end
end
```

`R[73]` is `string.sub`, `R[39]` is `string.gsub`, `R[91]` is `buffer.fromstring`.

## What it produces

```
len(decoded) = 199,880 bytes
first 64 bytes: "]smoiX8jLZ!_K?a_SBaPZH-L`9/K&i-A?Q4'3]`W/;MZ!uCGedk$aZtQK5iW\"AL2"
```

Stored as `work/dumps/xh_decoded.bin`. Byte distribution: all 85 characters
`!` (0x21) … `u` (0x75) appear, 1,854…2,469 times each — i.e. a uniform
85-symbol alphabet, which is why the data initially looks like Ascii85.

**It is not Ascii85.** Grouped into 5-character words and evaluated base-85
from `!`, 1,243 of 39,976 groups overflow 2³², and no 4-byte big-endian
interpretation yields Luau bytecode (no `\x03…\x0e` version byte, no `LBC`
markers). The uniform alphabet is simply the consequence of the substitution
below: every one of the ten pattern characters is replaced by exactly five
characters, so the output stays inside `!`…`u` if the input does.

## The substitution is a single left-to-right pass

`string.gsub(s, "[ v-~]", kH)` in Luau scans `s` once, left to right. Replacement
text inserted by the callback is **not** rescanned. Therefore the transformation
is exactly:

```python
out = "".join(KEYS.get(ch, ch) for ch in XH[4:])
```

This matters because several replacement blobs themselves contain pattern
characters (`v` → `"Uj(j+"` ends in `+`, `x` → `"L./<;"` contains `.`, `/`);
a regex `re.sub` in one pass happens to behave the same here, but a naive
"replace spaces, then v, then w…" cascade does **not**, and neither does a
recursive substitution. `tools/vm_tables.py::xh_decode` implements the correct
version and reproduces the observed 199,880 byte output byte-for-byte.

Note `XH[4:]`: Luau strings are 1-based and `WH` uses `sub(XH, 5)`, so the four
characters `LPH+` are a discarded header.

## Why the payload had to be encoded at all

The encoded blob contains exactly the characters `!`…`u` — no quotes, no
backslashes, no newlines. It therefore needs no escaping inside the long-string
literal `[=[ … ]=]`, which is the sole reason for this layer: it is an
**escaping layer**, not a cryptographic one. The substring `!!!!E` at the very
end of `XH` is padding from the last 5-character expansion.

## Verified reproduction

```
$ python3 - <<'EOF'
import tools.vm_tables as vm
xh = open("work/original/n.txt").read()          # extract the [=[ ]=] literal
dec = vm.xh_decode(xh)
print(len(dec.encode("latin1")))                 # 199880
print(dec[:40])                                  # ]smoiX8jLZ!_K?a_SBaPZH-L`9/K&i-A?Q4'3]`W
EOF
```

compares equal to `work/dumps/xh_decoded.bin` over the **entire 199,880 bytes**
(verified: `full match: True`).
