#!/usr/bin/env python3
"""GDScript semantic checks that Godot 4's analyzer treats as errors by default,
driven by the Godot 4.7.2 API (generated TS bindings from @ringozz/godot).

- INFERENCE_ON_VARIANT: `var x := <expr>` where <expr> has type Variant
- NATIVE_METHOD_OVERRIDE: a script func shadowing a native (non-virtual) method
- class_name colliding with a native class / global
- GET_NODE_DEFAULT_WITHOUT_ONREADY, ONREADY_WITH_EXPORT
Unresolvable initialisers are listed as UNKNOWN for manual review.
"""
import os, re, sys, glob

API = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "godot-api", "package", "gen")
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if not os.path.isdir(API):
    print("Godot API data not found. Run tools/fetch_godot_api.sh first (see tools/README.md).")
    sys.exit(2)

def camel(snake):
    parts = snake.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])

def ts_type(t):
    t = t.strip()
    t = re.sub(r"\s*\|\s*null$", "", t)
    m = re.match(r"GodotArray<(\w+)>$", t)
    if m:
        inner = m.group(1)
        return "Array" if inner in ("T", "Variant") else f"Array[{inner}]"
    if t.startswith("GodotArray"): return "Array"
    if t.startswith("GodotDictionary"): return "Dictionary"
    return {"number": "num", "string": "String", "boolean": "bool", "void": "void",
            "T": "Variant", "V": "Variant", "K": "Variant"}.get(t, t)

native = {}  # name -> {"parent", "methods", "props"}
def load_ts(path, name_override=None):
    s = re.sub(r"/\*.*?\*/", "", open(path).read(), flags=re.S)
    m = re.search(r"export (?:abstract )?class (\w+)(?:<[^>]*>)?(?: extends (\w+))?", s)
    if not m: return
    name = name_override or m.group(1)
    methods, props = {}, {}
    for mm in re.finditer(r"^\s+(?:static )?(get |set )?(\w+)\(([^)]*)\): ([^{]+?)\s*\{", s, re.M):
        kind, n, args, ret = mm.groups()
        if kind == "get ": props[n] = ts_type(ret)
        elif kind is None: methods[n] = ts_type(ret)
    native[name] = {"parent": m.group(2), "methods": methods, "props": props}

for f in glob.glob(f"{API}/classes/*.ts"): load_ts(f)
for f in glob.glob(f"{API}/value-types/*.ts"):
    vs = open(f).read()
    vname = os.path.basename(f)[:-3]
    vm = {}
    for n, ret in re.findall(r"^export function (\w+)\(self: \w+[^)]*\): ([^{]+?)\s*\{", vs, re.M):
        vm[n] = ts_type(ret)
    native[vname] = {"parent": None, "methods": vm, "props": {}}
load_ts(f"{API}/heap-types/GodotArray.ts", "Array")
load_ts(f"{API}/heap-types/GodotDictionary.ts", "Dictionary")
for f in glob.glob(f"{API}/heap-types/Packed*.ts"): load_ts(f)
utility = {}
for n, ret in re.findall(r"^export function (\w+)\([^)]*\): ([^{]+?)\s*\{", open(f"{API}/utility-functions.ts").read(), re.M):
    utility[n] = ts_type(ret)
VALUE_TYPES = {"int", "float", "bool", "String", "StringName", "NodePath", "Vector2", "Vector2i", "Vector3", "Vector3i",
               "Vector4", "Vector4i", "Color", "Rect2", "Rect2i", "Transform2D", "Transform3D", "Basis", "Quaternion",
               "AABB", "Plane", "Projection", "RID", "Callable", "Signal", "Dictionary", "Array", "PackedStringArray",
               "PackedFloat32Array", "PackedInt32Array", "PackedVector3Array", "PackedVector2Array", "PackedColorArray",
               "PackedByteArray", "PackedInt64Array", "PackedFloat64Array"}
GD_BUILTINS = {"len": "int", "range": "Array", "str": "String", "load": "Resource", "preload": "Resource",
               "typeof": "int", "is_instance_valid": "bool", "print": "void", "push_warning": "void",
               "push_error": "void", "assert": "void", "char": "String", "convert": "Variant", "type_exists": "bool",
               "Color8": "Color", "print_debug": "void", "inst_to_dict": "Dictionary", "dict_to_inst": "Object",
               "get_stack": "Array", "print_stack": "void", "instance_from_id": "Object", "ord": "int"}

# ------------------------------------------------------------------ scripts
scripts = {}
for f in glob.glob(f"{ROOT}/**/*.gd", recursive=True):
    if "/.godot/" in f or "/addons/" in f: continue
    scripts[os.path.relpath(f, ROOT)] = open(f, encoding="utf-8").read()
cfg = open(f"{ROOT}/project.godot").read()
autoloads = {}
for k, v in re.findall(r'^(\w+)="\*?res://([^"]+)"', re.search(r"\[autoload\]\n(.*?)(?:\n\[|\Z)", cfg, re.S).group(1), re.M):
    autoloads[k] = v
classes = {}
info = {}
for f, s in scripts.items():
    m = re.search(r"^class_name\s+(\w+)", s, re.M)
    cn = m.group(1) if m else None
    if cn: classes[cn] = f
    ext = (re.search(r"^extends\s+(\S+)", s, re.M) or [None, "RefCounted"])[1].strip('"')
    info[f] = {"class_name": cn, "extends": ext, "members": {}, "consts": {}, "funcs": {}, "signals": set(),
               "enums": set(), "src": s}

errors, unknowns, notes = [], [], []

def script_of_type(t):
    if t in classes: return classes[t]
    return None

def parent_script(f):
    e = info[f]["extends"]
    if e.startswith("res://"): return e[6:]
    return classes.get(e)

def native_base(f):
    seen = 0
    while f and seen < 20:
        e = info[f]["extends"]
        p = parent_script(f)
        if p is None: return e
        f = p; seen += 1
    return "Object"

def native_chain(n):
    out = []
    while n and n in native:
        out.append(n); n = native[n]["parent"]
    return out

def native_method(tname, meth):
    for c in native_chain(tname):
        r = native[c]["methods"].get(camel(meth))
        if r is not None: return r
    return None

def native_prop(tname, prop):
    for c in native_chain(tname):
        r = native[c]["props"].get(camel(prop))
        if r is not None: return r
    return None

# --------------------------------------------------------------- tokenizer
TOK = re.compile(r"""
 (?P<ws>[ \t]+)|
 (?P<num>0x[0-9a-fA-F_]+|\d[\d_]*\.\d*(?:e[-+]?\d+)?|\d[\d_]*(?:e[-+]?\d+)?|\.\d+)|
 (?P<str>[&^]?"(?:[^"\\]|\\.)*"|[&^]?'(?:[^'\\]|\\.)*')|
 (?P<node>[$%](?:"[^"]*"|[\w/]+))|
 (?P<id>[A-Za-z_]\w*)|
 (?P<op>\*\*|==|!=|<=|>=|&&|\|\||<<|>>|->|[-+*/%<>!&|^~.,()\[\]{}:=@])
""", re.X)

def tokenize(src):
    out, i = [], 0
    while i < len(src):
        m = TOK.match(src, i)
        if not m: raise SyntaxError(f"bad char {src[i]!r} in {src!r}")
        i = m.end()
        k = m.lastgroup
        if k == "ws": continue
        out.append((k, m.group()))
    return out

class P:
    def __init__(s, toks, env): s.t, s.i, s.env = toks, 0, env
    def peek(s, o=0): return s.t[s.i + o] if s.i + o < len(s.t) else (None, None)
    def next(s): tok = s.t[s.i]; s.i += 1; return tok
    def accept(s, v):
        if s.peek()[1] == v: s.i += 1; return True
        return False
    def expect(s, v):
        if not s.accept(v): raise SyntaxError(f"expected {v} got {s.peek()}")

    # precedence climbing (types flow upward)
    def expr(s):
        t = s.ternary()
        return t
    def ternary(s):
        a = s.bin(0)
        if s.peek() == ("id", "if"):
            s.next(); s.bin(0); s.expect("else"); b = s.ternary()
            if a == b: return a
            if {a, b} <= {"int", "float", "num"}: return "UNCERTAIN"
            return "Variant" if "Variant" in (a, b) else "UNCERTAIN"
        return a
    LEVELS = [["or", "||"], ["and", "&&"], ["not_placeholder"], ["in", "==", "!=", "<", ">", "<=", ">=", "is"],
              ["|"], ["^"], ["&"], ["<<", ">>"], ["+", "-"], ["*", "/", "%"], ["**"]]
    def bin(s, lvl):
        if lvl == 2:  # 'not' prefix
            if s.peek() in (("id", "not"), ("op", "!")):
                s.next(); s.bin(2); return "bool"
            return s.bin(3)
        if lvl >= len(s.LEVELS): return s.unary()
        left = s.bin(lvl + 1)
        while True:
            k, v = s.peek()
            if v in s.LEVELS[lvl] and (k == "op" or v in ("or", "and", "in", "is")):
                s.next()
                if v == "is":
                    s.next(); left = "bool"; continue
                if v == "not": s.next()
                right = s.bin(lvl + 1)
                left = combine(v, left, right)
            elif lvl == 3 and (k, v) == ("id", "not") and s.peek(1)[1] == "in":
                s.next(); s.next(); s.bin(lvl + 1); left = "bool"
            else:
                return left
    def unary(s):
        if s.peek()[1] in ("-", "+", "~"):
            s.next(); t = s.unary(); return t
        if s.peek()[1] == "await":
            s.next(); s.unary(); return "Variant"
        t = s.postfix()
        while s.peek() == ("id", "as"):
            s.next(); k, name = s.next()
            if s.peek()[1] == "[":  # Array[T]
                s.next(); inner = s.next()[1]; s.expect("]"); name = f"Array[{inner}]"
            t = name
        return t
    def args(s):
        n = 0
        if s.accept(")"): return 0
        while True:
            s.expr(); n += 1
            if s.accept(")"): return n
            s.expect(",")
    def postfix(s):
        t, ctx = s.primary()
        while True:
            v = s.peek()[1]
            if v == "(":
                s.next(); s.args()
                t = call_type(ctx, s.env); ctx = ("value", t)
            elif v == ".":
                s.next(); name = s.next()[1]
                if s.peek()[1] == "(":
                    ctx = ("method", t, name)
                else:
                    t = attr_type(ctx, t, name); ctx = ("value", t)
            elif v == "[":
                s.next(); s.expr(); s.expect("]")
                t = index_type(t); ctx = ("value", t)
            else:
                return t
    def primary(s):
        k, v = s.next()
        if k == "num": return ("float" if ("." in v or "e" in v.lower()) and not v.startswith("0x") else "int"), None
        if k == "str":
            return ("StringName" if v.startswith("&") else "NodePath" if v.startswith("^") else "String"), None
        if k == "node": return "Node", None
        if v == "(":
            t = s.expr(); s.expect(")"); return t, ("value", t)
        if v == "[":
            if not s.accept("]"):
                while True:
                    s.expr()
                    if s.accept("]"): break
                    s.expect(",")
                    if s.accept("]"): break
            return "Array", ("value", "Array")
        if v == "{":
            if not s.accept("}"):
                while True:
                    s.expr()
                    if not (s.accept(":") or s.accept("=")): raise SyntaxError("dict")
                    s.expr()
                    if s.accept("}"): break
                    s.expect(",")
                    if s.accept("}"): break
            return "Dictionary", ("value", "Dictionary")
        if k == "id":
            if v in ("true", "false"): return "bool", None
            if v == "null": return "Variant", None
            if v in ("PI", "TAU", "INF", "NAN"): return "float", None
            if v == "self": return s.env["self_type"], ("value", s.env["self_type"])
            if v == "super": return s.env["self_type"], ("super",)
            if v == "func": raise SyntaxError("lambda")
            if s.peek()[1] == "(":
                return None, ("func", v)
            t = ident_type(v, s.env)
            return t, ("ident", v, t)
        raise SyntaxError(f"unexpected {v}")

NUMERIC = {"int", "float", "num"}
def combine(op, a, b):
    if op in ("==", "!=", "<", ">", "<=", ">=", "in", "and", "or", "&&", "||"):
        if "Variant" in (a, b) and op not in ("and", "or", "&&", "||"): return "UNCERTAIN_CMP"
        return "bool"
    if a == "Variant" or b == "Variant": return "Variant"
    if a is None or b is None or a.startswith("UNCERTAIN") or b.startswith("UNCERTAIN"): return None
    if a in NUMERIC and b in NUMERIC:
        if op in ("<<", ">>", "&", "|", "^"): return "int"
        if "float" in (a, b): return "float"
        if a == b == "int": return "int"
        return "num"
    if a == "String" and op == "%": return "String"
    if a in NUMERIC: return b
    return a

def ident_type(v, env):
    if v in env["locals"]: return env["locals"][v]
    f = env["file"]
    while f:
        i = info[f]
        if v in i["members"]: return i["members"][v]
        if v in i["consts"]: return i["consts"][v]
        if v in i["enums"]: return "Dictionary"
        f = parent_script(f)
    if v in autoloads: return "AUTOLOAD:" + v
    if v in classes or v in native or v in VALUE_TYPES: return "TYPE:" + v
    p = native_prop(native_base(env["file"]), v)
    if p: return p
    return None

def resolve_script(t):
    if t is None: return None
    if t.startswith("AUTOLOAD:"): return autoloads[t[9:]]
    if t.startswith("TYPE:") and t[5:] in classes: return classes[t[5:]]
    return classes.get(t)

def script_member(f, name, kind):
    while f:
        i = info[f]
        if kind == "func" and name in i["funcs"]: return i["funcs"][name]
        if kind == "attr":
            if name in i["members"]: return i["members"][name]
            if name in i["consts"]: return i["consts"][name]
            if name in i["signals"]: return "Signal"
            if name in i["enums"]: return "Dictionary"
        f = parent_script(f)
    return "MISSING"

def call_type(ctx, env):
    if ctx is None: return None
    if ctx[0] == "func":
        n = ctx[1]
        r = script_member(env["file"], n, "func")
        if r != "MISSING": return r
        r = native_method(native_base(env["file"]), n)
        if r is not None: return r
        if n in GD_BUILTINS: return GD_BUILTINS[n]
        if camel(n) in utility: return utility[camel(n)]
        if n in VALUE_TYPES: return n
        if n in classes or n in native: return n
        return None
    if ctx[0] == "method":
        _, recv, name = ctx
        if recv is None: return None
        if recv.startswith("TYPE:"):
            tn = recv[5:]
            if name == "new": return tn
            sf = classes.get(tn)
            if sf:
                r = script_member(sf, name, "func")
                return None if r == "MISSING" else r
            r = native_method(tn, name)
            return r
        sf = resolve_script(recv)
        if sf:
            r = script_member(sf, name, "func")
            if r != "MISSING": return r
            recv = native_base(sf)
        if recv == "Variant": return "Variant"
        m = re.match(r"Array\[(\w+)\]$", recv)
        if m:
            r = native_method("Array", name)
            if r == "Variant" and name in ("back", "front", "pop_back", "pop_front", "pick_random", "get", "max", "min", "pop_at"):
                return "UNCERTAIN_TYPED_ARRAY"
            return recv if r == "Array" else r
        if recv in ("String", "StringName"):
            return {"length": "int", "find": "int", "hash": "int", "to_int": "int", "to_float": "float",
                    "split": "PackedStringArray", "begins_with": "bool", "ends_with": "bool", "is_empty": "bool",
                    "contains": "bool"}.get(name, "String")
        if recv in ("int", "float", "num", "bool"): return None
        if recv == "Node":  # $Path
            r = native_method("Node", name); return r
        return native_method(recv, name)
    if ctx[0] == "super":
        return None
    return None

def attr_type(ctx, t, name):
    if t is None: return None
    if t.startswith("TYPE:"):
        tn = t[5:]
        sf = classes.get(tn)
        if sf:
            r = script_member(sf, name, "attr"); return None if r == "MISSING" else r
        if name.isupper() or name[:1].isupper(): return tn if tn in VALUE_TYPES else "int"
        return None
    sf = resolve_script(t)
    if sf:
        r = script_member(sf, name, "attr")
        if r != "MISSING": return r
        t = native_base(sf)
    if t == "Dictionary": return "Variant"
    if t == "Variant": return "Variant"
    r = native_prop(t, name)
    if r is not None: return r
    if t in ("Vector2", "Vector3", "Vector4"): return "float" if name in "xyzw" else None
    if t in ("Vector2i", "Vector3i"): return "int"
    if t == "Color": return "float"
    return None

def index_type(t):
    if t is None: return None
    m = re.match(r"Array\[(\w+)\]$", t)
    if m: return m.group(1)
    if t in ("Array", "Dictionary", "Variant"): return "Variant"
    if t == "PackedStringArray" or t == "String": return "String"
    if t.startswith("Packed"): return None
    return None

def infer(expr, env):
    toks = tokenize(expr)
    p = P(toks, env)
    t = p.expr()
    if p.i != len(toks): raise SyntaxError(f"trailing tokens {toks[p.i:]}")
    return t

def norm_type(t):
    t = t.strip()
    return t

# ------------------------------------------------------------ collect decls
DECL = re.compile(r"^(?:@\w+(?:\([^)]*\))?\s+)*(?:static\s+)?var\s+(\w+)\s*(?::\s*([\w\[\]]+))?\s*(:?=)?\s*(.*?)\s*(?::\s*$)?$")
def strip_comment(line):
    out, q = "", None
    for i, ch in enumerate(line):
        if q:
            out += ch
            if ch == q and line[i - 1] != "\\": q = None
        elif ch in "\"'":
            q = ch; out += ch
        elif ch == "#":
            break
        else:
            out += ch
    return out.rstrip()

def logical_lines(src):
    """Join bracket/backslash continuations. Yields (lineno, indent, text)."""
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        start = i
        raw = strip_comment(lines[i])
        text = raw
        depth = sum(text.count(c) for c in "([{") - sum(text.count(c) for c in ")]}")
        while (depth > 0 or text.endswith("\\")) and i + 1 < len(lines):
            i += 1
            nxt = strip_comment(lines[i]).strip()
            text = text[:-1] if text.endswith("\\") else text
            text += " " + nxt
            depth = sum(text.count(c) for c in "([{") - sum(text.count(c) for c in ")]}")
        indent = len(raw) - len(raw.lstrip("\t"))
        yield start + 1, indent, text.strip()
        i += 1

pending = []  # (file, lineno, name, expr, env) to infer after all members known
for f, i in info.items():
    s = i["src"]
    for ln, ind, text in logical_lines(s):
        if ind != 0 or not text: continue
        m = re.match(r"^signal\s+(\w+)", text)
        if m: i["signals"].add(m.group(1)); continue
        m = re.match(r"^enum\s+(\w+)", text)
        if m: i["enums"].add(m.group(1))
        m = re.match(r"^enum\s*\w*\s*\{(.*)\}", text)
        if m:
            for part in m.group(1).split(","):
                if part.strip(): i["consts"][part.split("=")[0].strip()] = "int"
            continue
        m = re.match(r"^(?:static\s+)?func\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([\w\[\]]+))?", text)
        if m:
            i["funcs"][m.group(1)] = m.group(3) or "Variant"
            continue
        m = re.match(r"^const\s+(\w+)\s*(?::\s*([\w\[\]]+))?\s*:?=\s*(.*)$", text)
        if m:
            i["consts"][m.group(1)] = m.group(2) or ("PENDING", m.group(3))
            continue
        m = DECL.match(text)
        if m:
            name, typ, op, expr = m.groups()
            if typ: i["members"][name] = typ
            elif op == ":=": i["members"][name] = ("PENDING", expr); pending.append((f, ln, name, expr, None, text))
            else: i["members"][name] = "Variant"
            if "@onready" in text and "@export" in text:
                errors.append(f"{f}:{ln}: ONREADY_WITH_EXPORT")
            if "@onready" not in text and re.search(r"(^|[^\w])(\$|%)\w|get_node\(", expr or ""):
                errors.append(f"{f}:{ln}: GET_NODE_DEFAULT_WITHOUT_ONREADY: {text}")

def base_env(f):
    return {"file": f, "locals": {}, "self_type": info[f]["class_name"] or f}

# resolve pending member/const types (iterate to fixpoint)
for _ in range(4):
    for f, i in info.items():
        for d in ("members", "consts"):
            for k, v in list(i[d].items()):
                if isinstance(v, tuple):
                    try:
                        t = infer(v[1], base_env(f))
                    except SyntaxError:
                        t = None
                    if t is not None and not (isinstance(t, str) and t.startswith("UNCERTAIN")):
                        i[d][k] = t
for f, i in info.items():
    for d in ("members", "consts"):
        for k, v in list(i[d].items()):
            if isinstance(v, tuple): i[d][k] = None

# class-level: members declared with := that are Variant
checked = 0
def check_inference(f, ln, name, expr, env, text):
    global checked
    checked += 1
    try:
        t = infer(expr, env)
    except SyntaxError as e:
        unknowns.append(f"{f}:{ln}: PARSE? {e} :: {text}"); return None
    if t == "Variant":
        errors.append(f"{f}:{ln}: INFERENCE_ON_VARIANT `{name}` :: {text.strip()}")
    elif t is None or t.startswith("UNCERTAIN"):
        unknowns.append(f"{f}:{ln}: {t or 'unknown'} :: {text.strip()}")
    return t

for f, ln, name, expr, _, text in pending:
    check_inference(f, ln, name, expr, base_env(f), text)
for f, i in info.items():
    for ln, ind, text in logical_lines(i["src"]):
        m = re.match(r"^const\s+(\w+)\s*:=\s*(.*)$", text)
        if m and ind == 0:
            check_inference(f, ln, m.group(1), m.group(2), base_env(f), text)

# function bodies
for f, i in info.items():
    env = None
    for ln, ind, text in logical_lines(i["src"]):
        if not text: continue
        m = re.match(r"^(?:static\s+)?func\s+(\w+)\s*\((.*)\)\s*(?:->\s*[\w\[\]]+)?\s*:", text)
        if m and ind == 0:
            env = base_env(f)
            for a in m.group(2).split(","):
                a = a.strip()
                if not a: continue
                am = re.match(r"(\w+)\s*(?::\s*([\w\[\]]+))?\s*(:?=\s*(.*))?", a)
                if am:
                    pn, pt, _, dflt = am.groups()
                    if pt: env["locals"][pn] = pt
                    elif dflt and a.find(":=") >= 0:
                        try: env["locals"][pn] = infer(dflt, env)
                        except SyntaxError: env["locals"][pn] = None
                    else: env["locals"][pn] = "Variant"
            continue
        if ind == 0:
            env = None; continue
        if env is None: continue
        m = re.match(r"^var\s+(\w+)\s*(?::\s*([\w\[\]]+))?\s*(:?=)?\s*(.*)$", text)
        if m:
            name, typ, op, expr = m.groups()
            if typ: env["locals"][name] = typ
            elif op == ":=":
                t = check_inference(f, ln, name, expr, env, text)
                env["locals"][name] = t
            else: env["locals"][name] = "Variant"
            continue
        m = re.match(r"^for\s+(\w+)\s*(?::\s*([\w\[\]]+))?\s+in\s+(.*):$", text)
        if m:
            name, typ, it = m.groups()
            if typ: env["locals"][name] = typ
            else:
                try: itt = infer(it, env)
                except SyntaxError: itt = None
                if itt in ("int",) or re.match(r"^range\(", it): env["locals"][name] = "int"
                elif itt and itt.startswith("Array["): env["locals"][name] = itt[6:-1]
                elif itt == "PackedStringArray": env["locals"][name] = "String"
                elif itt in ("Array", "Dictionary", "Variant"): env["locals"][name] = "Variant"
                else: env["locals"][name] = None

# native override / class_name collisions
for f, i in info.items():
    cn = i["class_name"]
    if cn and (cn in native or cn in VALUE_TYPES or camel(cn) in utility):
        errors.append(f"{f}: class_name {cn} collides with a Godot 4.7.2 class/global")
    base = native_base(f)
    if base not in native:
        notes.append(f"{f}: native base {base!r} not in API")
        continue
    for fn in i["funcs"]:
        if fn.startswith("_"): continue
        for c in native_chain(base):
            if camel(fn) in native[c]["methods"]:
                errors.append(f"{f}: NATIVE_METHOD_OVERRIDE {fn}() shadows {c}.{fn}")
                break

print(f"API: {len(native)} native types, {len(utility)} utility functions")
print(f"checked {checked} inferred declarations across {len(scripts)} scripts")
for n in notes: print("NOTE", n)
print(f"\nUNKNOWN / needs review ({len(unknowns)}):")
for u in unknowns: print("  " + u)
print(f"\nERRORS ({len(errors)}):")
for e in errors: print("  " + e)
if errors: sys.exit(1)

# ---- bare call resolution: name(...) must be a script/native method, builtin, utility or type
unresolved = []
KEYWORDS = {"if", "elif", "while", "for", "match", "return", "and", "or", "not", "in", "await", "func", "assert",
            "super", "print", "preload", "load", "is", "as", "var", "signal", "Array", "Dictionary"}
for f, i in info.items():
    for ln, ind, text in logical_lines(i["src"]):
        if re.match(r"^(static\s+)?func\s|^signal\s|^class_name|^extends|^@", text): continue
        code = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', '""', text)
        for m in re.finditer(r"(?<![\w.$%])([A-Za-z_]\w*)\s*\(", code):
            n = m.group(1)
            if n in KEYWORDS: continue
            if script_member(f, n, "func") != "MISSING": continue
            if native_method(native_base(f), n) is not None: continue
            if n in GD_BUILTINS or camel(n) in utility or n in VALUE_TYPES or n in classes or n in native: continue
            unresolved.append(f"{f}:{ln}: {n}(")
print(f"\nUNRESOLVED BARE CALLS ({len(unresolved)}):")
for u in unresolved: print("  " + u)
if unresolved: sys.exit(1)

# ---- methods called on native-typed members/locals must exist on that class
bad_native = []; native_calls = 0
for f, i in info.items():
    local_types = {}
    for ln, ind, text in logical_lines(i["src"]):
        for v, t in re.findall(r"\bvar\s+(\w+)\s*:\s*(\w+)\s*=", text): local_types[v] = t
        for v, t in re.findall(r"\bvar\s+(\w+)\s*:=\s*[^\n]*\bas\s+(\w+)\s*$", text): local_types[v] = t
        code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
        for recv, meth in re.findall(r"(?<![\w.])(\w+)\.(\w+)\(", code):
            t = i["members"].get(recv) if isinstance(i["members"].get(recv), str) else None
            t = local_types.get(recv, t)
            if t is None or t not in native or t in VALUE_TYPES: continue
            native_calls += 1
            if native_method(t, meth) is None and meth not in ("emit", "connect", "call_deferred"):
                bad_native.append(f"{f}:{ln}: {recv}.{meth}() not on {t}")
print(f"\nNATIVE METHOD CALLS checked {native_calls}, missing ({len(bad_native)}):")
for b in bad_native: print("  " + b)
if bad_native: sys.exit(1)
