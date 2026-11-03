# Plaintext strings recovered from the payload's bytecode buffers

Extracted by scanning the run-time buffers in `work/rec/` for printable
runs.  Most buffers are still ciphertext, but the payload materialises a
few strings verbatim before the block cipher touches them.

| buffer | offset | text |
| --- | --- | --- |
| `b019_16_budget.bin` | 0 | `identifyexecutor` |
| `b032_78_budget.bin` | 0 | `The debug library is required on Luau platforms. Please open a support ticket.` |

## Interpretation

* `The debug library is required on Luau platforms. Please open a support
  ticket.` is the payload's own error message when `debug` is missing.
  It is evidence that the payload probes `debug.getupvalue`-style APIs,
  which only exist in *executor* environments, not in plain Roblox.
* `identifyexecutor` is the standard executor fingerprinting global.
  Together with the message above it pins the target environment down
  to a Roblox script executor (Synapse/Delta/Wave style).
