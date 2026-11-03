-- Minimal Roblox-ish sandbox shims so the obfuscated chunk can be loaded
-- outside of Roblox.  Only what the chunk actually touches is implemented.

local G = _G

-- Vector / UDim / Color3 style userdata stand-ins --------------------------------
local function vec(...)
	return { __vec = true, components = { ... } }
end

G.Vector3 = { new = function(x, y, z) return vec(x or 0, y or 0, z or 0) end }
G.Vector2 = { new = function(x, y) return vec(x or 0, y or 0) end }
G.Color3 = { new = function(r, g, b) return vec(r or 0, g or 0, b or 0) end }
G.UDim = { new = function(s, o) return { scale = s or 0, offset = o or 0 } end }
G.UDim2 = { new = function(a, b, c, d) return { a or 0, b or 0, c or 0, d or 0 } end }
G.Rect = { new = function(...) return { ... } end }

-- typeof: Roblox flavoured type() -----------------------------------------------
local rawtype = type
G.typeof = function(v)
	local t = rawtype(v)
	if t == "table" then
		if v.__vec then return "Vector3" end
		if v.scale ~= nil and v.offset ~= nil then return "UDim" end
	end
	return t
end

-- getfenv / setfenv are gone from modern Luau; provide inert versions -----------
if not G.getfenv then
	G.getfenv = function() return G end
	G.setfenv = function(_, _) return true end
end

return true
