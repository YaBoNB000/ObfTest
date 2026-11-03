-- Dump every buffer reachable from the handler table / VM world.
--
-- The payload VM keeps its decrypted bytecode in buffers hanging off its
-- "world" table (uv13 of the rH closure).  After a bounded run we walk the
-- reachable object graph and write out every buffer we find, so the decrypted
-- instruction stream can be studied offline.

local DIR = _G.DUMP_DIR or "/tmp/vmdump"
local MAXW = tonumber(_G.DUMP_MAX_WRITES) or 300000

local writes = 0
local seen = {}
local bufs = {}
local nbuf = 0

local realWriteu8 = buffer.writeu8
local realWriteu32 = buffer.writeu32
local realWritei32 = buffer.writei32
local realWriteu16 = buffer.writeu16
local realWritef64 = buffer.writef64
local realTostring = buffer.tostring
local realCopy = buffer.copy
local realFill = buffer.fill

local function bump()
	writes = writes + 1
	if writes % 100000 == 0 then
		log(string.format("[dump] writes=%d buffers=%d", writes, nbuf))
		logflush()
	end
	if writes >= MAXW then
		log("[dump] budget reached")
		logflush()
		error("DUMP_DONE", 0)
	end
end

buffer.writeu8 = function(b, o, v) bump(); return realWriteu8(b, o, v) end
buffer.writeu32 = function(b, o, v) bump(); return realWriteu32(b, o, v) end
buffer.writei32 = function(b, o, v) bump(); return realWritei32(b, o, v) end
buffer.writeu16 = function(b, o, v) bump(); return realWriteu16(b, o, v) end
buffer.writef64 = function(b, o, v) bump(); return realWritef64(b, o, v) end
buffer.copy = function(...) bump(); return realCopy(...) end
buffer.fill = function(...) bump(); return realFill(...) end

local function isbuffer(v)
	return type(v) == "buffer"
end

local function walk(v, path, depth)
	if depth > 6 then return end
	local t = type(v)
	if t == "buffer" then
		local key = path
		if not seen[v] then
			seen[v] = true
			nbuf = nbuf + 1
			local ok, s = pcall(realTostring, v)
			if ok then
				bufs[#bufs + 1] = {path = key, data = s, id = nbuf}
			end
		end
		return
	end
	if t ~= "table" then return end
	if seen[v] then return end
	seen[v] = true
	for k, x in pairs(v) do
		walk(x, path .. "." .. tostring(k), depth + 1)
	end
end

function walk_upvalue(v, path, depth)
	walk(v, path, depth)
end

function flush_buffers(tag)
	local out = {}
	for _, b in ipairs(bufs) do
		local name = string.format("%s/buf%03d_%d.bin", DIR, b.id, #b.data)
		writefile(name, b.data)
		out[#out + 1] = string.format("%s  %d bytes  path=%s", name, #b.data, b.path)
	end
	writefile(DIR .. "/index_" .. tostring(tag) .. ".txt", table.concat(out, "\n"))
	log("[dump] wrote " .. #bufs .. " buffers")
	logflush()
end

function __dump_vm(tab)
	walk(tab, "tab", 0)
	flush_buffers("tab")
end

log("[dump] installed dir=" .. DIR .. " max_writes=" .. MAXW)
