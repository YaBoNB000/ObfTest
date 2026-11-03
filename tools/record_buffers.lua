-- Reconstruct the bytecode buffers the payload builds at run time.
--
-- The virtual machine decrypts its own bytecode inside Luau buffers using
-- buffer.writeu8 / writeu32 / copy.  We tag every buffer with an id, record the
-- write pattern, and dump each buffer when it is first converted to a string or
-- when the write budget is exhausted.

local DIR = _G.REC_DIR or "/tmp/rec"
local MAXW = tonumber(_G.REC_MAX_WRITES) or 400000

local ids = {}
local nextid = 0
local counts = {}
local writes = 0

local realCreate = buffer.create
local realCopy = buffer.copy
local realFromString = buffer.fromstring
local realTostring = buffer.tostring
local wu8, wu32, wi32, wu16, wf64 = buffer.writeu8, buffer.writeu32, buffer.writei32, buffer.writeu16, buffer.writef64

local function idof(b)
	local id = ids[b]
	if not id then
		nextid = nextid + 1
		id = nextid
		ids[b] = id
	end
	return id
end

local function dump(b, why)
	local id = idof(b)
	local ok, s = pcall(realTostring, b)
	if ok then
		writefile(string.format("%s/b%03d_%d_%s.bin", DIR, id, #s, why), s)
		log(string.format("[rec] dumped buffer #%d (%d bytes) reason=%s writes=%d", id, #s, why, counts[id] or 0))
	end
end

function __rec_dump_all(why)
	for b in pairs(ids) do
		if type(b) == "buffer" then dump(b, why or "manual") end
	end
end

buffer.create = function(size)
	local b = realCreate(size)
	idof(b)
	return b
end

buffer.fromstring = function(s)
	local b = realFromString(s)
	idof(b)
	return b
end

local function bump(b)
	local id = idof(b)
	counts[id] = (counts[id] or 0) + 1
	writes = writes + 1
	if writes % 50000 == 0 then
		log(string.format("[rec] writes=%d", writes))
		logflush()
	end
	if writes == MAXW then
		log("[rec] write budget reached, dumping")
		__rec_dump_all("budget")
		error("REC_DONE", 0)
	end
end

buffer.writeu8 = function(b, o, v) bump(b); return wu8(b, o, v) end
buffer.writeu32 = function(b, o, v) bump(b); return wu32(b, o, v) end
buffer.writei32 = function(b, o, v) bump(b); return wi32(b, o, v) end
buffer.writeu16 = function(b, o, v) bump(b); return wu16(b, o, v) end
buffer.writef64 = function(b, o, v) bump(b); return wf64(b, o, v) end

buffer.tostring = function(b)
	local s = realTostring(b)
	local id = idof(b)
	if #s > 512 then
		writefile(string.format("%s/b%03d_%d_tostring.bin", DIR, id, #s), s)
		log(string.format("[rec] tostring on buffer #%d -> %d bytes", id, #s))
		logflush()
	end
	return s
end

log("[rec] installed dir=" .. DIR .. " max_writes=" .. MAXW)
