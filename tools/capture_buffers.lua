-- Buffer capture shim.
--
-- The obfuscated chunk materialises the payload bytecode inside Luau buffers
-- (buffer.create + buffer.copy + byte-wise writes).  This shim records every
-- buffer it hands out so the contents can be dumped afterwards, either when
-- the run finishes or when the watchdog fires.
--
-- Configure through globals:
--   CAPTURE_SECONDS  watchdog limit (default 30)
--   CAPTURE_DIR      output directory (default /tmp/buffers)

local DIR = _G.CAPTURE_DIR or "/tmp/buffers"
local LIMIT = tonumber(_G.CAPTURE_SECONDS) or 30
local t0 = os.clock()

local created = {}   -- ordered list of buffers
local kept = setmetatable({}, { __mode = "k" })

local realCreate = buffer.create
local realCopy = buffer.copy
local realTostring = buffer.tostring

local function save(tag)
	local n = 0
	for i, b in ipairs(created) do
		local ok, s = pcall(realTostring, b)
		if ok then
			n = n + 1
			writefile(string.format("%s/buf_%04d.bin", DIR, i), s)
		end
	end
	log("[capture] saved " .. n .. " buffers to " .. DIR)
end

function __capture_save()
	save("manual")
end

buffer.create = function(size)
	local b = realCreate(size)
	created[#created + 1] = b
	kept[b] = true
	return b
end

buffer.copy = function(dst, dstoff, src, srcoff, count)
	local r = realCopy(dst, dstoff, src, srcoff, count)
	if os.clock() - t0 > LIMIT then
		log("[capture] watchdog fired inside buffer.copy")
		save("watchdog")
		error("CAPTURE_TIMEOUT", 0)
	end
	return r
end

buffer.tostring = function(b)
	local s = realTostring(b)
	if os.clock() - t0 > LIMIT then
		log("[capture] watchdog fired inside buffer.tostring")
		save("watchdog")
		error("CAPTURE_TIMEOUT", 0)
	end
	return s
end

log("[capture] shim installed, dir=" .. DIR .. " limit=" .. LIMIT .. "s")
