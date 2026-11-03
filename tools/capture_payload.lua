-- Capture shim: intercept anything that looks like final payload execution.
--
--   loadstring / load          -> save the source text, then refuse to run it
--   buffer.tostring            -> save every buffer that is converted to a string
--   setfenv / getfenv          -> pass through, but log
--
-- A watchdog aborts the run after CAPTURE_SECONDS so partial progress is kept.

local DIR = _G.CAPTURE_DIR or "/tmp/capture"
local LIMIT = tonumber(_G.CAPTURE_SECONDS) or 30
local t0 = os.clock()
local seq = 0

local function stamp(name)
	seq = seq + 1
	return string.format("%s/%03d_%s", DIR, seq, name)
end

local realLoadstring = loadstring
loadstring_internal = realLoadstring
local realBufferTostring = buffer.tostring

local function recordLoad(src, chunkname, where)
	local path = stamp("loadstring.luau")
	writefile(path, tostring(src))
	log(string.format("[capture] loadstring(%s bytes) from %s -> %s", tostring(#tostring(src)), tostring(where), path))
	logflush()
end

loadstring = function(src, chunkname)
	recordLoad(src, chunkname, "loadstring")
	return nil, "captured"
end
load = loadstring

buffer.tostring = function(b)
	local s = realBufferTostring(b)
	if #s > 200 then
		local ok, path = pcall(function() return stamp("buffer_" .. #s .. ".bin") end)
		if ok then writefile(path, s) end
	end
	return s
end

-- watchdog: hook the byte writer since it runs constantly
local realWriteu8 = buffer.writeu8
local n = 0
buffer.writeu8 = function(b, o, v)
	n = n + 1
	if n % 1000000 == 0 then
		local el = os.clock() - t0
		log(string.format("[capture] writes=%d elapsed=%.0fs", n, el))
		logflush()
		if el > LIMIT then
			log("[capture] watchdog stopping run")
			logflush()
			error("CAPTURE_TIMEOUT", 0)
		end
	end
	return realWriteu8(b, o, v)
end

log("[capture] installed, dir=" .. DIR .. " limit=" .. LIMIT .. "s")
