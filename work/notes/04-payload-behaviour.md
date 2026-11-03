# 04 — What the payload actually does

The payload is executed by the custom VM, so none of this is visible in the
obfuscated source. Everything below was observed by running the chunk inside a
purpose-built host and a permissive Roblox stub that logs every API access.

## 4.1 The ASCII-art banner

The first materialised artefact is a 2,311 byte string
(`work/capture/001_buffer_2311.bin`). It is a hand-drawn logo:

```
                                 .@%(/*,.......      ...,,*/(#%&@@.
                                (*   ,/(#%%&&@@@@&%((////(((##%###((/**,,.     ,//(&.
                           /* .%@@@@@@@@%,  .(&@@@&&&&&&@@@@@@&#(*,........*%@@@(.  ,#.
                         */ .&@@@@@@@*  (%,   *(&&@@@@@&%(*,.             .,*(#%(*@@&*  *,
                        #, /@@@@@@* *&( ,&&/.,/#%&&@@@&(&@@@@@@@@@@@@#*,.....,/&@@@@@@@@( .%
                    #  #@@@@@*/@% .#%./(,.,/*,//*,.,/(*@@@@@@@@@@@@%@@@@@@@@@#.#@@@@@@&. %
                   /  &@@@@@@@@(%@# *&&*&@@@@#/&@@@@/%%.,%@@@@@@@%/@@&(,  ,,,...  *%@@@# *
                 #  .&@@@@@@@@@@@,((%@@@@@#.    ,&@@#@@&* .&@@@@@&,.#@@@@/&@@%(@@@&(/,(&, /,
              (/   (@&&&%&@@@&/, ,@#(@@@@,        #@@/,&@& /@@@@@,%#%@@@@@(     *@@@@@&,%%. .
             /  #/,#@@@&#(//#@@@/ %@@@&@@@(.    ,&@@(.*/*  %@@*   %@@@@@@%       (@@&(*...%&.
            ///@@&,  (&@@#,   /@/ ,*&@@@@#&@@%#%((%@&* /@@@@@@&. #@@@#&@@@&%%@@@@@@&,/(*@/#
            %%.&@# .&@@@# /@@@@%&@@@&/.   ,/((/*,  ./&@@@@@@@@@@,*&(./%@@#*&@@@(#(....,&#*@/
            @%.&& .&@@@&*    /&@@@@@@@@@@@@@@@@&@@#/(%@@@@@@@@@@&,  (@@@@@@@@@@@@/,@@@@@#.&*
            &&,%% .&*    /@@@(.  ,(@@@@@&/(////#( /&@@@@@@@@@@@@@@@(  ,&@@@@@@@@&, (@@&*/@(/
            .%*#@( /@@@@( *@@@@@@/     *%@@@@@@@&.,@& ,#, .&@@@@@@# .#*%&/,#@@@@*   *@@&/*&*
             .&/.#@@@@@@@,   *&@@%.,&@@&(,    ,(%@%&@@@@@@@@@(.*,  /@@@@@@@@@&,      %@@@@..
            @* .%@@@@@@@@(       .   (@@@@@@@@(       .*(%&@@@@@@@@@@@@&(,  ./.*@%   /@@% ./
              @* .&@@@@@@&.             ./&@@@*.&@@@@@@@&, ,**,.    .,*(&(.%@@# %@*  ,@@% ,#
                &, /@@@@@@*                    .#@@@@@@@@*.%@@@@@(,@@@@@@& ,%(.      .&@% ,#
                  / *@@@@@#                                                           %@&.,#
                  (( .&@@@@*                                                          #@&.,#
                   .&. ,&@@@,                                                         (@&.,#
                      #. .%@@* /@@/                                                   /@&.,(
                        ./  #@%. %@&,,#,                                              /@@,./
                          *(  #@%. . (@@@@@%/,                                        /@@,.*
                            //  %@&, *@@@@@@@@( (@%/.                                 #@@, (
                              #* .&@@#. (@@@@&.*@@@@@@@@%. */.                  *..%*.&@@, /
                                @* .%@@@%, ,/ .@@@@@@@@@@,.%@@@@@% .&@@@* #@&..&@*,* %@@&. *
                                   /  *&@@@@%,   *(&@@@@&. #@@@@@* #@@@% (@@* ,.   /@@@@* (
                                     @#. .#@@@@@@&(,.                      .,*(%&@@@@@&..(
                                       &(.   ./%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@(. ((
                                          ,#/*.       ..,,,,,,,,....          ,/#
```

(rendered with `@` as the dark tone; the original uses a density ramp
` .@%(/*,...` in the first line, i.e. it is shaded ASCII art).

## 4.2 The long compute phase

After the banner the payload enters a loop that performs, per second, roughly

| operation | rate |
| --- | --- |
| `buffer.writeu8` | ~85,000 |
| `bit32.band` | ~400,000 |
| `bit32.bxor` | ~250,000 |
| `table.pack` | ~200,000 |
| `table.move` | ~200,000 |

and runs for many millions of byte writes without ever calling `task.wait`,
`task.spawn`, `coroutine.yield` or any Roblox API. That signature — heavy
`bit32` mixing plus byte-wise buffer writes, no scheduling — is the payload VM
**decrypting its own bytecode blocks** (see `03-vm-internals.md` §3.2). In other
words, the "compute phase" is not application logic; it is the loader finishing
its job.

Budget: ≈20 M byte writes were observed in ~240 s in this sandbox, i.e. roughly
20 MB of block decryption. Extrapolating from the 53,749 byte proto buffer and
the ~200 KB payload the total work is on the order of several hundred MB of
byte-level mixing, so a full run takes hours at this speed (Luau's interpreter
is the bottleneck: the hot path is a `while true` in Luau, and native codegen
does not help because the inner loop is dominated by table/buffer builtins).

## 4.3 Roblox API surface

The payload resolves these globals (detected by running with a stubbed
environment that raises on missing globals):

* datatypes constructed with `.new`: `Vector3`, `Vector2`, `Color3`, `UDim`,
  `UDim2`, `Rect`, `CFrame`, `NumberRange`, `NumberSequence`,
  `NumberSequenceKeypoint`, `ColorSequence`, `ColorSequenceKeypoint`, `Ray`,
  `Region3`, `Region3int16`, `Vector3int16`, `Vector2int16`, `BrickColor`,
  `TweenInfo`, `PhysicalProperties`, `Random`, `Faces`, `Axes`, `PathWaypoint`,
  `DateTime`, `Font`, `OverlapParams`, `RaycastParams`, `CatalogSearchParams`;
* `game`, `workspace`, `script`, `Instance.new`, `Enum`;
* `task.*` (`wait`, `spawn`, `defer`, `delay`, `cancel`, `synchronize`);
* `bit32`, `buffer`, `coroutine`, `string`, `table`, `math`, `typeof`,
  `getfenv`, `setfenv`, `newproxy`, `unpack`, `pcall`, `xpcall`.

That is a **Roblox-executor** style surface (the chunk is designed to run in a
Roblox exploit environment as much as in Studio), and it is why the chunk fails
immediately under a plain Luau interpreter with
`attempt to index nil with 'new'`.

## 4.4 Failure modes observed

| environment | result |
| --- | --- |
| plain `luau` CLI | `attempt to index nil with 'new'` (no Roblox datatypes, no `io`) |
| host + Roblox stubs, missing `buffer` | `attempt to index nil with 'cancel'` — the word `cancel` never appears in the source, so this is the *decoded* payload asking for `task.cancel` |
| host + full stubs | banner produced, then the long block-decryption phase |
| host + `loadstring` intercepted | never called — the payload does **not** re-`loadstring` its final code; it runs it in its own VM |

The `task.cancel` observation is worth keeping: it proves the payload's first
decoded instructions query the executor environment before doing anything else,
which is consistent with an anti-tamper preamble.
