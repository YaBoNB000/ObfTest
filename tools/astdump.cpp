// astdump: parse a Luau chunk and emit every control-flow node with its
// source position, so that external tools can rebuild the dispatch tree by
// containment instead of hand-rolled block counting (which desyncs on empty
// branches and on `repeat ... until`).
//
// Build (inside a Luau checkout):
//   g++ -std=c++17 -O2 -I Ast/include -I Common/include astdump.cpp \
//       Ast/src/*.cpp Common/src/*.cpp -o astdump
//
// Usage: astdump <file.luau>
// One record per line, tab separated:
//   IF      condL condC condEL condEC thenL thenC thenEL thenEC elseL elseC elseEL elseEC
//   WHILE   condL condC condEL condEC bodyL bodyC bodyEL bodyEC
//   REPEAT  bodyL bodyC bodyEL bodyEC condL condC condEL condEC
//   FORNUM  varL varC varEL varEC fromL fromC fromEL fromEC bodyL bodyC bodyEL bodyEC
//   FORIN   bodyL bodyC bodyEL bodyEC
//   FUNC    bodyL bodyC bodyEL bodyEC
//   END
// For IF, the else span is `-1 -1 -1 -1` when there is no else branch.
// Positions are 1-based line/column, as Luau reports them.
#include "Luau/Ast.h"
#include "Luau/Allocator.h"
#include "Luau/Lexer.h"
#include "Luau/Parser.h"

#include <cstdio>
#include <string>

static std::string g_src;

static void pos(const Luau::Location& l, const char* which)
{
    if (which[0] == 'b')
        printf("%u\t%u", l.begin.line, l.begin.column);
    else
        printf("%u\t%u", l.end.line, l.end.column);
}

static void span(const Luau::Location& l)
{
    printf("%u\t%u\t%u\t%u", l.begin.line, l.begin.column, l.end.line, l.end.column);
}

static void none()
{
    printf("-1\t-1\t-1\t-1");
}

static void walkStat(Luau::AstStat* s);

static void walkBlock(Luau::AstStatBlock* b)
{
    if (!b)
        return;
    for (Luau::AstStat* s : b->body)
        walkStat(s);
}

static void walkExpr(Luau::AstExpr* e)
{
    if (!e)
        return;
    if (auto* f = e->as<Luau::AstExprFunction>())
        walkBlock(f->body);
}

static void walkStat(Luau::AstStat* s)
{
    if (!s)
        return;
    if (auto* n = s->as<Luau::AstStatIf>())
    {
        printf("IF\t");
        span(n->condition->location);
        printf("\t");
        span(n->thenbody->location);
        printf("\t");
        if (n->elsebody)
        {
            if (auto* eb = n->elsebody->as<Luau::AstStatBlock>())
                span(eb->location);
            else
                span(n->elsebody->location);
        }
        else
            none();
        printf("\n");
        walkExpr(n->condition);
        walkBlock(n->thenbody);
        if (n->elsebody)
        {
            if (auto* eb = n->elsebody->as<Luau::AstStatBlock>())
                walkBlock(eb);
            else
                walkStat(n->elsebody);
        }
        return;
    }
    if (auto* n = s->as<Luau::AstStatWhile>())
    {
        printf("WHILE\t");
        span(n->condition->location);
        printf("\t");
        span(n->body->location);
        printf("\n");
        walkExpr(n->condition);
        walkBlock(n->body);
        return;
    }
    if (auto* n = s->as<Luau::AstStatRepeat>())
    {
        printf("REPEAT\t");
        span(n->body->location);
        printf("\t");
        span(n->condition->location);
        printf("\n");
        walkBlock(n->body);
        walkExpr(n->condition);
        return;
    }
    if (auto* n = s->as<Luau::AstStatFor>())
    {
        printf("FORNUM\t");
        span(n->var->location);
        printf("\t");
        span(n->from->location);
        printf("\t");
        span(n->body->location);
        printf("\n");
        walkExpr(n->from);
        walkExpr(n->to);
        walkExpr(n->step);
        walkBlock(n->body);
        return;
    }
    if (auto* n = s->as<Luau::AstStatForIn>())
    {
        printf("FORIN\t");
        span(n->body->location);
        printf("\n");
        walkBlock(n->body);
        return;
    }
    if (auto* n = s->as<Luau::AstStatLocalFunction>())
    {
        if (n->func && n->func->body)
        {
            printf("FUNC\t");
            span(n->func->body->location);
            printf("\n");
            walkBlock(n->func->body);
        }
        return;
    }
    if (auto* n = s->as<Luau::AstStatFunction>())
    {
        if (n->func && n->func->body)
        {
            printf("FUNC\t");
            span(n->func->body->location);
            printf("\n");
            walkBlock(n->func->body);
        }
        return;
    }
    if (auto* n = s->as<Luau::AstStatLocal>())
    {
        for (Luau::AstExpr* v : n->values)
            walkExpr(v);
        return;
    }
    if (auto* n = s->as<Luau::AstStatAssign>())
    {
        for (Luau::AstExpr* v : n->values)
            walkExpr(v);
        return;
    }
    if (auto* n = s->as<Luau::AstStatReturn>())
    {
        for (Luau::AstExpr* v : n->list)
            walkExpr(v);
        return;
    }
    if (auto* n = s->as<Luau::AstStatExpr>())
    {
        walkExpr(n->expr);
        return;
    }
}

int main(int argc, char** argv)
{
    if (argc < 2)
    {
        fprintf(stderr, "usage: %s <file.luau>\n", argv[0]);
        return 2;
    }
    FILE* f = fopen(argv[1], "rb");
    if (!f)
    {
        perror("open");
        return 1;
    }
    char buf[65536];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0)
        g_src.append(buf, n);
    fclose(f);

    Luau::Allocator alloc;
    Luau::AstNameTable names(alloc);
    Luau::ParseOptions opts;
    Luau::ParseResult res = Luau::Parser::parse(g_src.c_str(), g_src.size(), names, alloc, opts);
    if (!res.errors.empty())
    {
        for (auto& e : res.errors)
        {
            Luau::Location loc = e.getLocation();
            fprintf(stderr, "%u:%u: %s\n", loc.begin.line, loc.begin.column, e.getMessage().c_str());
        }
        return 1;
    }
    if (!res.root)
    {
        fprintf(stderr, "no root\n");
        return 1;
    }
    walkBlock(res.root);
    printf("END\n");
    return 0;
}
