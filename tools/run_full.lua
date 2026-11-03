-- Full run of the obfuscated chunk against the permissive Roblox stub.
-- Every API access performed by the payload is written to the log file.
local t0 = os.clock()
assert(loadstring(readfile("/home/user/ObfTest/tools/sandbox_shim.lua"), "shim"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/roblox_stub.lua"), "stub"))()

-- progress ticker
local n = 0
local orig = buffer.writeu8
buffer.writeu8 = function(b, o, v)
	n = n + 1
	if n % 500000 == 0 then
		log(string.format("[progress] buffer.writeu8=%d elapsed=%.1fs", n, os.clock() - t0))
		logflush()
	end
	return orig(b, o, v)
end

log("[run] loading chunk")
logflush()
local fn = assert(loadstring(readfile("/home/user/ObfTest/work/original/n.txt"), "=obf"))
log("[run] chunk compiled, executing")
logflush()
local ok, err = xpcall(fn, function(e) return tostring(e) end)
log(string.format("[run] finished ok=%s err=%s writes=%d elapsed=%.1fs", tostring(ok), tostring(err), n, os.clock() - t0))
logflush()
