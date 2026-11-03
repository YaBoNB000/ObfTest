-- Permissive Roblox environment stub.
--
-- Every unknown global, every field access and every call returns a fresh
-- "proxy" object.  All accesses are appended to a log so we can see what the
-- obfuscated payload tries to touch (its API surface).

local LOG = {}
local function emit(s)
	LOG[#LOG + 1] = s
	if #LOG % 1 == 0 then
		log(s)
	end
end

local proxyMT = {}

local function describe(v)
	local t = type(v)
	if t == "string" then
		if #v > 60 then return string.format("%q", string.sub(v, 1, 60) .. "...") end
		return string.format("%q", v)
	end
	if t == "proxy" then return v.__path end
	return tostring(v)
end

local function newproxy(path, kind)
	local p = setmetatable({ __path = path, __kind = kind or "object" }, proxyMT)
	return p
end

proxyMT.__index = function(self, k)
	local path = self.__path .. "." .. tostring(k)
	emit("GET " .. path)
	local p = newproxy(path)
	rawset(self, k, p)
	return p
end

proxyMT.__newindex = function(self, k, v)
	emit("SET " .. self.__path .. "." .. tostring(k) .. " = " .. describe(v))
	rawset(self, k, v)
end

proxyMT.__call = function(self, ...)
	local args = {}
	for i = 1, select("#", ...) do
		args[i] = describe((select(i, ...)))
	end
	emit("CALL " .. self.__path .. "(" .. table.concat(args, ", ") .. ")")
	return newproxy(self.__path .. "()")
end

proxyMT.__tostring = function(self) return self.__path end
proxyMT.__concat = function(a, b) return describe(a) .. describe(b) end
proxyMT.__len = function(self) return 1 end
proxyMT.__eq = function(a, b) return rawequal(a, b) end
proxyMT.__lt = function() return false end
proxyMT.__le = function() return false end
proxyMT.__add = function() return newproxy("<sum>") end
proxyMT.__sub = function() return newproxy("<diff>") end
proxyMT.__mul = function() return newproxy("<prod>") end
proxyMT.__div = function() return newproxy("<quot>") end
proxyMT.__mod = function() return newproxy("<mod>") end
proxyMT.__pow = function() return newproxy("<pow>") end
proxyMT.__unm = function() return newproxy("<neg>") end
proxyMT.__idiv = function() return newproxy("<idiv>") end

-- typeof() must not be confused by proxies --------------------------------
local rawtype = type
_ENV_TYPEOF = function(v)
	if rawtype(v) == "table" and getmetatable(v) == proxyMT then return "Instance" end
	return typeof(v)
end
typeof = _ENV_TYPEOF

-- Roblox globals ------------------------------------------------------------
local function roboglobal(name)
	return function(...)
		local args = {}
		for i = 1, select("#", ...) do args[i] = describe((select(i, ...))) end
		emit("GLOBAL " .. name .. "(" .. table.concat(args, ", ") .. ")")
		return newproxy(name .. "()")
	end
end

game = newproxy("game")
workspace = newproxy("workspace")
Workspace = workspace
script = newproxy("script")
Instance = { new = roboglobal("Instance.new") }
Enum = newproxy("Enum")
task = {
	wait = function(t)
		emit("task.wait(" .. tostring(t) .. ")")
		return 0
	end,
	spawn = function(f, ...)
		emit("task.spawn")
		local ok, err = pcall(f, ...)
		emit("task.spawn result: " .. tostring(ok) .. " " .. tostring(err))
	end,
	defer = function(f, ...)
		emit("task.defer")
		return nil
	end,
	delay = function(t, f)
		emit("task.delay")
		return nil
	end,
	cancel = function(th)
		emit("task.cancel(" .. describe(th) .. ")")
	end,
	synchronize = function() end,
	desynchronize = function() end,
}
function wait(t)
	emit("wait(" .. tostring(t) .. ")")
	return 0, 0
end
function spawn(f) return task.spawn(f) end
function delay(t, f) return task.delay(t, f) end
tick = function() return os.clock() end
time = function() return os.clock() end
warn = function(...)
	local parts = {}
	for i = 1, select("#", ...) do parts[i] = describe((select(i, ...))) end
	emit("WARN " .. table.concat(parts, " "))
end
print = function(...)
	local parts = {}
	for i = 1, select("#", ...) do parts[i] = describe((select(i, ...))) end
	emit("PRINT " .. table.concat(parts, " "))
end
require = function(v)
	emit("require(" .. describe(v) .. ")")
	return newproxy("require()")
end
getgenv = function() return _G end
getrenv = function() return _G end
hookfunction = function(a, b) emit("hookfunction") return a end
setreadonly = function() end
isfile = function() return false end
readfile = readfile
writefile = writefile
identifyexecutor = function() return "ArenaSandbox", "1.0" end
getidentity = function() return 8 end
checkcaller = function() return true end
loadstring = loadstring
newcclosure = function(f) return f end
cloneref = function(v) return v end
gethui = function() return newproxy("gethui()") end
getconnections = function() return {} end
firesignal = function() end
firetouchinterest = function() end
setclipboard = function() end
is_synapse_function = function() return false end
syn = newproxy("syn")


-- Roblox datatype constructors --------------------------------------------
local dtNames = {
	"Vector3","Vector2","Color3","UDim","UDim2","Rect","CFrame","NumberRange",
	"NumberSequence","NumberSequenceKeypoint","ColorSequence","ColorSequenceKeypoint",
	"Ray","Region3","Region3int16","Vector3int16","Vector2int16","BrickColor",
	"TweenInfo","PhysicalProperties","Random","Faces","Axes","PathWaypoint",
	"DateTime","Font","OverlapParams","RaycastParams","CatalogSearchParams",
	"DockWidgetPluginGuiInfo","FloatCurveKey","RotationCurveKey","Content",
	"SharedTable","Secret","SecurityCapabilities","Path2DControlPoint","Tags",
	"Instance","Enum","EnumItem","Enumeration","TextChatMessageProperties",
}
for _, n in ipairs(dtNames) do
	if rawget(_G, n) == nil then
		local holder = newproxy(n)
		holder.new = roboglobal(n .. ".new")
		_G[n] = holder
	end
end

emit("=== stub environment ready ===")
