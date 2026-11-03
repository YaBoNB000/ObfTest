CAPTURE_SECONDS = 900
CAPTURE_DIR = "/home/user/ObfTest/work/capture"
assert(loadstring(readfile("/home/user/ObfTest/tools/sandbox_shim.lua"), "shim"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/roblox_stub.lua"), "stub"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/capture_payload.lua"), "capture"))()
local fn = assert(loadstring_internal(readfile("/home/user/ObfTest/work/original/n.txt"), "=obf"))
local ok, err = xpcall(fn, function(e) return tostring(e) end)
log("[run] finished ok="..tostring(ok).." err="..tostring(err))
logflush()
