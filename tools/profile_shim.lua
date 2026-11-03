-- Profiling shim: counts calls into every standard-library function that the
-- obfuscated chunk touches, plus a wall-clock watchdog that aborts the run
-- after N seconds so we can see where the time goes.

local counts = {}
local originals = {}
local order = {}
local t0 = os.clock()
local LIMIT = tonumber(_G.PROFILE_SECONDS) or 10
_G.__profile_timeout = false

local function wrap(tbl, name)
	for k, v in pairs(tbl) do
		if type(v) == "function" then
			local key = name .. "." .. tostring(k)
			originals[key] = {tbl = tbl, k = k, fn = v}
			tbl[k] = function(...)
				local c = counts[key]
				if not c then
					counts[key] = 1
					order[#order + 1] = key
				else
					counts[key] = c + 1
				end
				if #order > 0 and os.clock() - t0 > LIMIT then
					_G.__profile_timeout = true
					log("=== PROFILE TIMEOUT in " .. key)
					error("PROFILE_TIMEOUT", 0)
				end
				return v(...)
			end
		end
	end
end

wrap(string, "string")
wrap(table, "table")
wrap(buffer, "buffer")
wrap(bit32, "bit32")
wrap(coroutine, "coroutine")
wrap(math, "math")

function __dump_profile()
	LIMIT = math.huge
	for key, o in pairs(originals) do o.tbl[o.k] = o.fn end
	local out = {}
	for _, k in ipairs(order) do
		out[#out + 1] = string.format("%-28s %d", k, counts[k])
	end
	writefile("/tmp/profile.txt", table.concat(out, "\n"))
	log("profile dumped: " .. #out .. " entries")
end
