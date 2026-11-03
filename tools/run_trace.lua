-- Trace the *start-up* phase of the obfuscated chunk, then abort.
-- task.wait is allowed to return twice; afterwards it raises so we can see the
-- API surface the payload touches before it settles into its polling loop.
CAPTURE_DIR = "/home/user/ObfTest/work/capture"
assert(loadstring(readfile("/home/user/ObfTest/tools/sandbox_shim.lua"), "shim"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/roblox_stub.lua"), "stub"))()
local waits = 0
local realWait = task.wait
task.wait = function(t)
	waits = waits + 1
	log("[trace] task.wait #" .. waits .. " t=" .. tostring(t))
	logflush()
	if waits > 2 then
		error("TRACE_ABORT", 0)
	end
	return 0
end
assert(loadstring(readfile("/home/user/ObfTest/tools/capture_payload.lua"), "capture"))()
local fn = assert(loadstring_internal(readfile("/home/user/ObfTest/work/original/n.txt"), "=obf"))
local ok, err = xpcall(fn, function(e) return tostring(e) end)
log("[run] ok="..tostring(ok).." err="..tostring(err))
logflush()
