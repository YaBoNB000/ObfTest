-- Run the payload for a bounded number of writes, then dump every buffer that
-- is reachable from the handler table (which includes the VM's own world).
DUMP_DIR = "/home/user/ObfTest/work/vmdump"
DUMP_MAX_WRITES = 300000
assert(loadstring(readfile("/home/user/ObfTest/tools/sandbox_shim.lua"), "shim"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/roblox_stub.lua"), "stub"))()
assert(loadstring(readfile("/home/user/ObfTest/tools/dump_vm.lua"), "dump"))()
-- helper that walks a closure's upvalues
function __dump_vm_entry(fn)
	local i = 1
	while true do
		local name, v = getupvalue(fn, i)
		if not name then break end
		walk_upvalue(v, "uv" .. i, 0)
		i = i + 1
	end
	flush_buffers("entry")
end

local tab = nil
-- grab the handler table by wrapping rH
local realRH
do
  -- the chunk returns the VM's entry; we need the table itself, so we load the
  -- truncated form which returns the table directly
  local src = readfile("/home/user/ObfTest/work/original/n.txt")
  local k = src:find("I={}}", 1, true)
  assert(k, "marker not found")
  local body = src:sub(1, k + 3)          -- up to and including  I={}
  tab = assert(loadstring(body .. "}, {})", "=partial"))()
end
log("[run] handler table loaded, entries=" .. tostring(#tab))

-- rH() returns the VM entry; the VM world (uv13) is shared with it, so we walk
-- the entry closure's upvalues as well as the handler table itself.
local entry = tab:rH()
local ok, err = xpcall(function() return entry("run") end, function(e) return tostring(e) end)
log("[run] ok=" .. tostring(ok) .. " err=" .. tostring(err))
__dump_vm(tab)
if type(entry) == "function" then
	log("[run] walking entry closure upvalues")
	__dump_vm_entry(entry)
end
