// Small Luau host used for analysing the obfuscated chunk.
//
// It exposes a handful of host functions that the analysis harness needs:
//   readfile(path)          -> string
//   writefile(path, data)   -> ()
//   log(str)                -> appends str + "\n" to the log file given on cmdline
//   exit(code)
// plus the normal Luau standard library (string/table/math/bit32/buffer/...).
//
// usage: luau-host <script.lua> [logfile]

#include "lua.h"
#include "Luau/Compiler.h"
#include "Luau/CodeGen.h"
#include <string>
#include "lualib.h"
#include "lualib.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>

static std::string g_logpath;

static int host_getupvalue(lua_State* L)
{
    int n = (int)luaL_checknumber(L, 2);
    const char* name = lua_getupvalue(L, 1, n);
    if (!name)
        return 0;
    lua_pushstring(L, name);
    lua_insert(L, -2);
    return 2;
}

static int host_setupvalue(lua_State* L)
{
    int n = (int)luaL_checknumber(L, 2);
    lua_pushvalue(L, 3);
    const char* name = lua_setupvalue(L, 1, n);
    lua_pushstring(L, name ? name : "");
    return 1;
}

static int host_getinfo(lua_State* L)
{
    lua_Debug ar;
    int level = (int)luaL_checknumber(L, 1);
    if (!lua_getinfo(L, level, "nSlua", &ar))
        return 0;
    lua_newtable(L);
    lua_pushstring(L, ar.name ? ar.name : "");
    lua_setfield(L, -2, "name");
    lua_pushstring(L, ar.short_src ? ar.short_src : "");
    lua_setfield(L, -2, "short_src");
    lua_pushstring(L, ar.source ? ar.source : "");
    lua_setfield(L, -2, "source");
    lua_pushnumber(L, ar.currentline);
    lua_setfield(L, -2, "currentline");
    lua_pushnumber(L, ar.linedefined);
    lua_setfield(L, -2, "linedefined");
    lua_pushnumber(L, ar.nparams);
    lua_setfield(L, -2, "nparams");
    lua_pushboolean(L, ar.isvararg);
    lua_setfield(L, -2, "isvararg");
    return 1;
}

static int host_loadstring(lua_State* L)
{
    size_t l = 0;
    const char* s = luaL_checklstring(L, 1, &l);
    const char* chunkname = luaL_optstring(L, 2, s);

    Luau::CompileOptions opts = {};
    opts.optimizationLevel = 1;
    opts.debugLevel = 1;
    opts.typeInfoLevel = 0;
    std::string bytecode = Luau::compile(std::string(s, l), opts);
    if (luau_load(L, chunkname, bytecode.data(), bytecode.size(), 0) == 0)
        return 1;
    lua_pushnil(L);
    lua_insert(L, -2);
    return 2;
}

static void host_flush();

static int host_logflush(lua_State* L)
{
    host_flush();
    return 0;
}

static int host_readfile(lua_State* L)
{
    const char* path = luaL_checkstring(L, 1);
    FILE* f = fopen(path, "rb");
    if (!f)
    {
        lua_pushnil(L);
        lua_pushstring(L, "cannot open file");
        return 2;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    std::string data;
    data.resize(sz > 0 ? (size_t)sz : 0);
    if (sz > 0)
        fread(&data[0], 1, (size_t)sz, f);
    fclose(f);
    lua_pushlstring(L, data.data(), data.size());
    return 1;
}

static int host_writefile(lua_State* L)
{
    const char* path = luaL_checkstring(L, 1);
    size_t len = 0;
    const char* data = luaL_checklstring(L, 2, &len);
    FILE* f = fopen(path, "wb");
    if (!f)
    {
        lua_pushboolean(L, 0);
        return 1;
    }
    fwrite(data, 1, len, f);
    fclose(f);
    lua_pushboolean(L, 1);
    return 1;
}

static std::string g_buf;

static void host_flush()
{
    if (g_buf.empty())
        return;
    FILE* f = g_logpath.empty() ? NULL : fopen(g_logpath.c_str(), "ab");
    if (f)
    {
        fwrite(g_buf.data(), 1, g_buf.size(), f);
        fclose(f);
    }
    else
    {
        fwrite(g_buf.data(), 1, g_buf.size(), stdout);
        fflush(stdout);
    }
    g_buf.clear();
}


static int host_log(lua_State* L)
{
    size_t len = 0;
    const char* s = luaL_checklstring(L, 1, &len);
    g_buf.append(s, len);
    g_buf.push_back('\n');
    if (g_buf.size() > (1u << 16))
        host_flush();
    return 0;
}

static int host_exit(lua_State* L)
{
    int code = (int)luaL_optnumber(L, 1, 0);
    lua_close(L);
    exit(code);
    return 0;
}

int main(int argc, char** argv)
{
    if (argc < 2)
    {
        fprintf(stderr, "usage: %s <script.lua> [logfile] [args...]\n", argv[0]);
        return 2;
    }
    if (argc >= 3)
        g_logpath = argv[2];

    bool codegen = getenv("LUAU_CODEGEN") != nullptr;
    bool codegenCold = getenv("LUAU_CODEGEN_COLD") != nullptr;
    bool codegenLazy = getenv("LUAU_CODEGEN_LAZY") != nullptr;

    lua_State* L = luaL_newstate();
    if (codegen)
        Luau::CodeGen::create(L);
    luaL_openlibs(L);

    // CLI style helpers
    lua_pushcfunction(L, host_readfile, "readfile");
    lua_setglobal(L, "readfile");
    lua_pushcfunction(L, host_writefile, "writefile");
    lua_setglobal(L, "writefile");
    lua_pushcfunction(L, host_log, "log");
    lua_setglobal(L, "log");
    lua_pushcfunction(L, host_logflush, "logflush");
    lua_setglobal(L, "logflush");
    lua_pushcfunction(L, host_exit, "exit");
    lua_setglobal(L, "exit");
    lua_pushcfunction(L, host_readfile, "loadfile_data");
    lua_setglobal(L, "loadfile_data");
    lua_pushcfunction(L, host_loadstring, "loadstring");
    lua_setglobal(L, "loadstring");
    lua_pushcfunction(L, host_loadstring, "load");
    lua_setglobal(L, "load");
    lua_pushcfunction(L, host_getupvalue, "getupvalue");
    lua_setglobal(L, "getupvalue");
    lua_pushcfunction(L, host_setupvalue, "setupvalue");
    lua_setglobal(L, "setupvalue");
    lua_pushcfunction(L, host_getinfo, "getinfo");
    lua_setglobal(L, "getinfo");

    // arg table
    lua_newtable(L);
    for (int i = 0; i < argc - 3; ++i)
    {
        lua_pushstring(L, argv[i + 3]);
        lua_rawseti(L, -2, i + 1);
    }
    lua_setglobal(L, "arg");

    FILE* f = fopen(argv[1], "rb");
    if (!f)
    {
        fprintf(stderr, "cannot open %s\n", argv[1]);
        return 2;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    std::string src;
    src.resize((size_t)sz);
    if (sz)
        fread(&src[0], 1, (size_t)sz, f);
    fclose(f);

    std::string chunkname = std::string("@") + argv[1];
    Luau::CompileOptions copts = {};
    copts.optimizationLevel = 1;
    copts.debugLevel = 1;
    copts.typeInfoLevel = 0;
    std::string bytecode = Luau::compile(src, copts);
    int st = luau_load(L, chunkname.c_str(), bytecode.data(), bytecode.size(), 0);
    if (st != 0)
    {
        const char* err = lua_tostring(L, -1);
        fprintf(stderr, "load error: %s\n", err ? err : "?");
        return 1;
    }

    if (codegen)
    {
        Luau::CodeGen::CompilationOptions nativeOptions;
        if (codegenCold)
            nativeOptions.flags = Luau::CodeGen::CodeGen_ColdFunctions;
        nativeOptions.runtimeFeedback = true;
        Luau::CodeGen::enableRuntimeCompilation(L, nativeOptions, codegenLazy);
        if (!codegenLazy)
            Luau::CodeGen::compile(L, -1, nativeOptions);
        fprintf(stderr, "[host] native codegen enabled (cold=%d lazy=%d)\n", int(codegenCold), int(codegenLazy));
    }

    int rc = lua_pcall(L, 0, 0, 0);
    if (rc != 0)
    {
        const char* err = lua_tostring(L, -1);
        fprintf(stderr, "runtime error: %s\n", err ? err : "?");
    }
    host_flush();
    lua_close(L);
    return rc != 0 ? 1 : 0;
}
