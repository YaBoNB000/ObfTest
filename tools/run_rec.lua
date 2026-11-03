REC_DIR = "/home/user/ObfTest/work/rec"
REC_MAX_WRITES = 100000
assert(loadstring(readfile("/home/user/ObfTest/tools/sandbox_shim.lua"), "shim"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/roblox_stub.lua"), "stub"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/record_buffers.lua"), "rec"))()
local fn = assert(loadstring(readfile("/home/user/ObfTest/work/original/n.txt"), "=obf"))
local ok, err = xpcall(fn, function(e) return tostring(e) end)
log("[run] ok="..tostring(ok).." err="..tostring(err))
logflush()
