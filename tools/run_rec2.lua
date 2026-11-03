-- Run the payload further into the block-decryption phase, then dump every
-- buffer that was ever created.  The proto buffers (02 <idx> 1f ...) become
-- progressively more decrypted as the budget grows.
REC_DIR = os.getenv and "/tmp/rec2" or "/tmp/rec2"
REC_MAX_WRITES = 8000000
assert(loadstring(readfile("/home/user/ObfTest/tools/sandbox_shim.lua"), "shim"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/roblox_stub.lua"), "stub"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/record_buffers.lua"), "rec"))()
local fn = assert(loadstring(readfile("/home/user/ObfTest/work/original/n.txt"), "=obf"))
local ok, err = xpcall(fn, function(e) return tostring(e) end)
log("[run] ok="..tostring(ok).." err="..tostring(err))
logflush()
