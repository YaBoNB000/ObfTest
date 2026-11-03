#!/usr/bin/env python3
"""Format a machine-generated, single-line Luau chunk into something readable.

Not a real parser: a block-aware re-indenter that understands
function/if/while/for/repeat/do ... end/until, string literals, comments and
long brackets.  Good enough for analysing obfuscated output.
"""
import re
import sys

TOKEN_RE = re.compile(r"""
    (?P<lstring>\[(?P<eq>=*)\[.*?\](?P=eq)\])
  | (?P<string>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')
  | (?P<comment>--\[(?P<eq2>=*)\[.*?\](?P=eq2)\]|--[^\n]*)
  | (?P<number>0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>\.\.\.|\.\.|==|~=|<=|>=|//|::|\+=|-=|\*=|/=|%=|\^=|\.\.=|[-+*/%^#<>=(){}\[\];:,.|&~])
  | (?P<ws>[ \t\r\n]+)
""", re.VERBOSE | re.DOTALL)


def tokenize(src):
    pos, out = 0, []
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            out.append(("op", src[pos]))
            pos += 1
            continue
        kind = m.lastgroup
        text = m.group()
        if kind == "ws":
            pos = m.end()
            continue
        if kind == "comment":
            pos = m.end()
            continue
        if kind in ("lstring",):
            kind = "string"
        out.append((kind, text))
        pos = m.end()
    return out


OPEN_KW = {"function", "if", "while", "for", "repeat"}


def format_code(toks, indent_str="  "):
    lines = []
    cur = []          # current line fragments
    depth = 0
    stack = []        # block kinds
    paren = 0         # ()[]{} nesting

    def pad():
        return indent_str * depth

    def flush(force=False):
        nonlocal cur
        text = "".join(cur).rstrip()
        if text or force:
            lines.append(pad() + text if text else "")
        cur = []

    i, n = 0, len(toks)
    while i < n:
        kind, val = toks[i]
        prev_val = toks[i - 1][1] if i else ""
        nxt_val = toks[i + 1][1] if i + 1 < n else ""

        if kind == "name":
            if val == "function":
                # `function name(...)` or anonymous
                cur.append("function")
                i += 1
                continue
            if val == "if":
                if prev_val in ("elseif",):
                    pass
                flush()
                if prev_val in ("else", "elseif") or (stack and stack[-1] == "else-open"):
                    pass
                stack.append("if")
                depth += 1
                cur = ["if "]
                i += 1
                continue
            if val == "elseif":
                flush()
                depth = max(depth - 1, 0)
                cur = ["elseif "]
                i += 1
                continue
            if val == "else":
                flush()
                depth = max(depth - 1, 0)
                cur = ["else"]
                i += 1
                # if next token starts a statement, indent
                depth += 1
                stack.append("else")
                i += 1
                continue
            if val == "while":
                flush()
                stack.append("while")
                depth += 1
                cur = ["while "]
                i += 1
                continue
            if val == "for":
                flush()
                stack.append("for")
                depth += 1
                cur = ["for "]
                i += 1
                continue
            if val == "repeat":
                flush()
                stack.append("repeat")
                depth += 1
                cur = ["repeat"]
                i += 1
                continue
            if val == "do":
                if stack and stack[-1] in ("for", "while"):
                    cur.append(" do")
                    stack[-1] = stack[-1] + "-do"
                    i += 1
                    continue
                flush()
                cur = ["do"]
                stack.append("do")
                depth += 1
                i += 1
                continue
            if val == "until":
                flush()
                depth = max(depth - 1, 0)
                if stack and stack[-1] == "repeat":
                    stack.pop()
                cur = ["until "]
                i += 1
                continue
            if val == "end":
                flush()
                depth = max(depth - 1, 0)
                if stack:
                    stack.pop()
                cur = ["end"]
                i += 1
                continue
            if val == "then":
                cur.append(" then")
                i += 1
                continue
            if val == "return":
                flush()
                cur = ["return "]
                i += 1
                continue
            if val == "local":
                flush()
                cur = ["local "]
                i += 1
                continue
            cur.append(val)
            i += 1
            continue

        if kind == "op":
            if val in "([{":
                paren += 1
                cur.append(val)
                i += 1
                continue
            if val in ")]}":
                paren = max(paren - 1, 0)
                cur.append(val)
                i += 1
                continue
            if val == ";":
                flush()
                i += 1
                continue
            if val == ",":
                cur.append(", ")
                i += 1
                continue
            cur.append(val)
            i += 1
            continue

        cur.append(val)
        i += 1

    flush()
    return "\n".join(lines)


def main():
    src = open(sys.argv[1]).read()
    out = format_code(tokenize(src))
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
