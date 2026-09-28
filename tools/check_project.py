#!/usr/bin/env python3
"""Static verification suite for the Wrikshagandha Godot project (no engine)."""
import os, re, sys, glob, configparser

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)
errors, notes = [], []
def err(m): errors.append(m)

def res_path(p):
    return p.replace("res://", "")

# ---------------------------------------------------------------- scripts
scripts = {}
for f in glob.glob("**/*.gd", recursive=True):
    if f.startswith(".godot") or f.startswith("addons"):
        continue
    scripts[f] = open(f, encoding="utf-8").read()

class_of = {}    # class_name -> file
file_class = {}  # file -> class_name
extends_of = {}  # file -> extends token
for f, s in scripts.items():
    m = re.search(r"^class_name\s+(\w+)", s, re.M)
    if m:
        if m.group(1) in class_of:
            err(f"duplicate class_name {m.group(1)}: {f} & {class_of[m.group(1)]}")
        class_of[m.group(1)] = f
        file_class[f] = m.group(1)
    m = re.search(r"^extends\s+(\S+)", s, re.M)
    extends_of[f] = m.group(1).strip('"') if m else "RefCounted"

def parent_file(f):
    e = extends_of.get(f, "")
    if e.startswith("res://"):
        return res_path(e)
    return class_of.get(e)

MEMBER_RE = re.compile(r"^(?:@export[^\n]*?\s)?(?:@onready\s+)?(?:static\s+)?var\s+(\w+)", re.M)
EXPORT_RE = re.compile(r"^@export[^\n]*?\bvar\s+(\w+)", re.M)
FUNC_RE = re.compile(r"^(?:static\s+)?func\s+(\w+)\s*\(([^)]*)\)", re.M)
SIG_RE = re.compile(r"^signal\s+(\w+)(?:\(([^)]*)\))?", re.M)
CONST_RE = re.compile(r"^(?:const|enum)\s+(\w+)", re.M)

def own_members(f):
    s = scripts[f]
    return set(MEMBER_RE.findall(s))

def chain(f):
    out = []
    while f and f in scripts:
        out.append(f)
        f = parent_file(f)
    return out

def all_members(f):
    m = set()
    for c in chain(f):
        m |= own_members(c)
    return m

def all_exports(f):
    m = set()
    for c in chain(f):
        m |= set(EXPORT_RE.findall(scripts[c]))
    return m

def all_funcs(f):
    d = {}
    for c in reversed(chain(f)):
        for name, args in FUNC_RE.findall(scripts[c]):
            a = [x for x in args.split(",") if x.strip()]
            req = [x for x in a if "=" not in x]
            d[name] = (len(req), len(a))
    return d

def all_signals(f):
    d = {}
    for c in chain(f):
        for name, args in SIG_RE.findall(scripts[c]):
            d[name] = len([x for x in (args or "").split(",") if x.strip()])
    return d

def all_consts(f):
    m = set()
    for c in chain(f):
        m |= set(CONST_RE.findall(scripts[c]))
        # enum values
        for body in re.findall(r"^enum\s+\w+\s*\{([^}]*)\}", scripts[c], re.M):
            m |= {x.split("=")[0].strip() for x in body.split(",") if x.strip()}
    return m

# parent-member redeclaration
for f in scripts:
    p = parent_file(f)
    if p:
        inherited = all_members(p)
        for v in own_members(f):
            if v in inherited:
                err(f"{f}: redeclares parent member '{v}'")

# autoloads
cfg = open("project.godot", encoding="utf-8").read()
auto_sec = re.search(r"\[autoload\]\n(.*?)(?:\n\[|\Z)", cfg, re.S).group(1)
autoloads = {}
for line in auto_sec.strip().splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        autoloads[k.strip()] = res_path(v.strip().strip('"').lstrip("*"))
for k, v in autoloads.items():
    if not os.path.exists(v):
        err(f"autoload {k} missing file {v}")
notes.append("autoloads: " + ", ".join(autoloads))

# Autoload.x / ClassName.x references
for f, s in scripts.items():
    code = re.sub(r"#.*", "", s)
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)
    for name, attr in re.findall(r"\b([A-Z]\w+)\.([A-Za-z_]\w*)", code):
        target = autoloads.get(name) or class_of.get(name)
        if not target or target not in scripts:
            continue
        known = all_members(target) | set(all_funcs(target)) | set(all_signals(target)) | all_consts(target)
        builtin = {"new", "connect", "emit", "disconnect", "is_connected", "get_tree", "name",
                   "get_node", "has_method", "call", "call_deferred", "set", "get", "queue_free",
                   "add_child", "get_children", "is_inside_tree"}
        if attr not in known and attr not in builtin:
            err(f"{f}: {name}.{attr} not found in {target}")
    # Autoload.method(args) arity
    for name, meth, args in re.findall(r"\b([A-Z]\w+)\.(\w+)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", code):
        target = autoloads.get(name) or class_of.get(name)
        if not target or target not in scripts:
            continue
        fn = all_funcs(target).get(meth)
        if fn is None:
            continue
        depth, n, cur = 0, 0, ""
        for ch in args:
            if ch in "([{": depth += 1
            if ch in ")]}": depth -= 1
            if ch == "," and depth == 0: n += 1
        n = n + 1 if args.strip() else 0
        if not (fn[0] <= n <= fn[1]):
            err(f"{f}: {name}.{meth} called with {n} args, expects {fn}")

# emit arity (same-file signals and Autoload.signal.emit)
for f, s in scripts.items():
    sigs = all_signals(f)
    for sig, args in re.findall(r"(?<![\w.])(\w+)\.emit\(([^()]*(?:\([^()]*\)[^()]*)*)\)", s):
        if sig in sigs:
            depth, n = 0, 0
            for ch in args:
                if ch in "([{": depth += 1
                if ch in ")]}": depth -= 1
                if ch == "," and depth == 0: n += 1
            n = n + 1 if args.strip() else 0
            if n != sigs[sig]:
                err(f"{f}: {sig}.emit with {n} args, declared {sigs[sig]}")

# connect handler arity: X.sig.connect(_handler) where X autoload/self/class member
for f, s in scripts.items():
    funcs = all_funcs(f)
    for src, sig, handler in re.findall(r"(\w+)\.(\w+)\.connect\(([\w.]+)", s):
        target = autoloads.get(src)
        if target is None:
            # member typed var: look up "var src: Type"
            m = re.search(rf"var\s+{src}\s*:\s*(\w+)", s)
            if m and m.group(1) in class_of:
                target = class_of[m.group(1)]
        if target is None or target not in scripts:
            continue
        sigs = all_signals(target)
        if sig not in sigs:
            err(f"{f}: {src}.{sig} is not a signal of {target}")
            continue
        if handler.endswith(".unbind"):
            handler = handler[:-len(".unbind")]
        um = re.search(rf"{re.escape(src)}\.{re.escape(sig)}\.connect\({re.escape(handler)}\.unbind\((\d+)\)", s)
        if um:
            hf = funcs.get(handler)
            if hf is None: err(f"{f}: handler {handler} not found"); continue
            if not (hf[0] <= sigs[sig] - int(um.group(1)) <= hf[1]):
                err(f"{f}: {handler}.unbind({um.group(1)}) arity {hf} vs signal {src}.{sig} ({sigs[sig]})")
            continue
        if "." in handler:
            obj, meth = handler.split(".", 1)
            m = re.search(rf"var\s+{obj}\s*:\s*(\w+)", s)
            if not (m and m.group(1) in class_of):
                continue
            hf = all_funcs(class_of[m.group(1)]).get(meth)
        else:
            hf = funcs.get(handler)
        if hf is None:
            err(f"{f}: handler {handler} not found for {src}.{sig}")
        elif not (hf[0] <= sigs[sig] <= hf[1]):
            err(f"{f}: handler {handler} arity {hf} vs signal {src}.{sig} ({sigs[sig]})")

# typed-variable method calls: var x: Class / var x := ... as Class / for x: Class
def count_args(args):
    depth, n = 0, 0
    for ch in args:
        if ch in "([{": depth += 1
        if ch in ")]}": depth -= 1
        if ch == "," and depth == 0: n += 1
    return n + 1 if args.strip() else 0
GODOT_BASE = {"connect", "emit", "get_node", "get_node_or_null", "has_method", "call", "queue_free",
              "add_child", "get_children", "is_inside_tree", "get_tree", "set", "get", "duplicate",
              "distance_to", "is_connected", "disconnect", "get_parent", "look_at", "create_tween",
              "set_process", "show", "hide", "add_to_group", "is_in_group", "remove_child", "to_global",
              "to_local", "get_global_position", "set_surface_override_material", "get_surface_override_material",
              "get_active_material", "grab_focus", "set_deferred", "call_deferred", "has_node", "is_queued_for_deletion"}
typed_calls = 0
for f, s2 in scripts.items():
    code = re.sub(r"#.*", "", s2)
    types = {}
    for v, t in re.findall(r"\b(?:var|for)\s+(\w+)\s*:\s*(\w+)", code): types[v] = t
    for v, t in re.findall(r"var\s+(\w+)\s*:?=\s*[^\n]*\bas\s+(\w+)\s*$", code, re.M): types[v] = t
    for v, t in list(types.items()):
        if t not in class_of: del types[v]
    for v, meth, args in re.findall(r"(?<![\w.])(\w+)\.(\w+)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", code):
        if v not in types: continue
        target = class_of[types[v]]
        fn = all_funcs(target).get(meth)
        if fn is None:
            if meth not in GODOT_BASE and meth not in all_signals(target):
                notes.append(f"unresolved typed call {f}: {v}.{meth} ({types[v]}) — builtin?")
            continue
        typed_calls += 1
        n = count_args(args)
        if not (fn[0] <= n <= fn[1]):
            err(f"{f}: {v}.{meth} ({types[v]}) called with {n} args, expects {fn}")
notes.append(f"typed calls checked: {typed_calls}")

# ------------------------------------------------------------- scenes/res
HDR_RE = re.compile(r"^\[(\w+)([^\]]*)\]", re.M)
def attrs(h):
    return dict(re.findall(r'(\w+)=("[^"]*"|\[[^\]]*\]|\S+)', h))

scene_root_script = {}
EXPORT_NAMES = set()
for _f in scripts: EXPORT_NAMES |= set(EXPORT_RE.findall(scripts[_f]))
def parse_scene(path):
    s = open(path, encoding="utf-8").read()
    sections = []
    for m in HDR_RE.finditer(s):
        sections.append((m.group(1), attrs(m.group(2)), m.start(), m.end()))
    out = []
    for i, (kind, a, st, en) in enumerate(sections):
        body_end = sections[i + 1][2] if i + 1 < len(sections) else len(s)
        out.append((kind, a, s[en:body_end]))
    return s, out

def load_scene_info(path):
    s, secs = parse_scene(path)
    ext = {a.get("id", "").strip('"'): a for k, a, b in secs if k == "ext_resource"}
    subs = {a.get("id", "").strip('"'): (a, b) for k, a, b in secs if k == "sub_resource"}
    return s, secs, ext, subs

all_res = [f for f in glob.glob("**/*.tscn", recursive=True) + glob.glob("**/*.tres", recursive=True)
           if not f.startswith(".godot")]

def script_for_ext(ext, sid):
    a = ext.get(sid)
    if a:
        return res_path(a["path"].strip('"'))

for path in all_res:
    s, secs, ext, subs = load_scene_info(path)
    head = secs[0]
    ls = head[1].get("load_steps")
    if ls is not None and int(ls) != len(ext) + len(subs) + 1:
        err(f"{path}: load_steps {ls} != {len(ext) + len(subs) + 1}")
    for sid, a in ext.items():
        p = res_path(a["path"].strip('"'))
        if not os.path.exists(p):
            err(f"{path}: missing ext path {p}")
        if not re.search(rf'ExtResource\("{re.escape(sid)}"\)', s):
            err(f"{path}: unused ext_resource {sid}")
    for sid in subs:
        if not re.search(rf'SubResource\("{re.escape(sid)}"\)', s):
            err(f"{path}: unused sub_resource {sid}")
    for ref in re.findall(r'ExtResource\("([^"]+)"\)', s):
        if ref not in ext: err(f"{path}: undefined ExtResource {ref}")
    for ref in re.findall(r'SubResource\("([^"]+)"\)', s):
        if ref not in subs: err(f"{path}: undefined SubResource {ref}")
    # collision shapes
    for k, a, b in secs:
        if k == "node" and a.get("type", "").strip('"') == "CollisionShape3D":
            m = re.search(r'shape = SubResource\("([^"]+)"\)', b)
            if m and "Mesh" in subs[m.group(1)][0].get("type", ""):
                err(f"{path}: mesh used as collision shape")
    # .tres resource fields
    if path.endswith(".tres"):
        for k, a, b in secs:
            if k == "resource":
                m = re.search(r'script = ExtResource\("([^"]+)"\)', b)
                if m:
                    sf = script_for_ext(ext, m.group(1))
                    members = all_members(sf)
                    for field in re.findall(r"^(\w+) = ", b, re.M):
                        if field not in members and field not in ("script", "resource_name"):
                            err(f"{path}: field {field} not on {sf}")

def scene_root_script_of(path):
    if path in scene_root_script:
        return scene_root_script[path]
    s, secs, ext, subs = load_scene_info(path)
    res = None
    for k, a, b in secs:
        if k == "node" and "parent" not in a:
            m = re.search(r'script = ExtResource\("([^"]+)"\)', b)
            if m:
                res = script_for_ext(ext, m.group(1))
            elif "instance" in a:
                iid = re.search(r'ExtResource\("([^"]+)"\)', a["instance"]).group(1)
                res = scene_root_script_of(script_for_ext(ext, iid))
            break
    scene_root_script[path] = res
    return res

# Builtin property vocabulary: anything the project sets on script-less nodes.
BUILTIN_PROPS = set()
for _p in glob.glob("**/*.tscn", recursive=True):
    if _p.startswith(".godot"): continue
    for _k, _a, _b in parse_scene(_p)[1]:
        if _k == "node" and not re.search(r'^script = ', _b, re.M) and "instance" not in _a:
            BUILTIN_PROPS |= set(re.findall(r"^([\w/]+) = ", _b, re.M))
BUILTIN_PROPS |= {"floor_snap_length", "floor_max_angle", "custom_minimum_size"}
def instance_node_paths(scene_path):
    out = set()
    for k, a, b in parse_scene(scene_path)[1]:
        if k == "node" and "parent" in a:
            par = a["parent"].strip('"'); nm = a["name"].strip('"')
            out.add(nm if par == "." else f"{par}/{nm}")
    return out
NODE_TYPES_ALLOWED_PROPS = {"position", "rotation", "rotation_degrees", "scale", "transform", "visible",
                            "script", "metadata/_edit_group_", "metadata/_edit_lock_"}
for path in glob.glob("**/*.tscn", recursive=True):
    if path.startswith(".godot"): continue
    s, secs, ext, subs = load_scene_info(path)
    nodes = {}  # path -> (script, props-body)
    seen = set()
    for k, a, b in secs:
        if k != "node": continue
        name = a["name"].strip('"')
        parent = a.get("parent", None)
        parent = parent.strip('"') if parent else None
        if parent is None:
            npath = "."
        else:
            if parent != "." and parent not in seen:
                err(f"{path}: node {name} parent {parent} not declared before")
            npath = name if parent == "." else f"{parent}/{name}"
        if npath in seen:
            err(f"{path}: duplicate node {npath}")
        seen.add(npath)
        script = None
        m = re.search(r'^script = ExtResource\("([^"]+)"\)', b, re.M)
        if m:
            script = script_for_ext(ext, m.group(1))
        elif "instance" in a:
            iid = re.search(r'ExtResource\("([^"]+)"\)', a["instance"]).group(1)
            script = scene_root_script_of(script_for_ext(ext, iid))
        nodes[npath] = (script, b, a)
        if a.get("type", "").strip('"') == "CollisionShape3D":
            pn = parent if parent else None
            ptype = None
            for k2, a2, b2 in secs:
                if k2 == "node":
                    n2 = a2["name"].strip('"'); p2 = a2.get("parent", "").strip('"')
                    full = "." if "parent" not in a2 else (n2 if p2 == "." else f"{p2}/{n2}")
                    if full == pn:
                        ptype = a2.get("type", "").strip('"'); inst = "instance" in a2
            if ptype and ptype not in ("Area3D", "StaticBody3D", "CharacterBody3D", "RigidBody3D", "AnimatableBody3D"):
                err(f"{path}: CollisionShape3D under {ptype}")
    # exported props exist
    for npath, (script, b, a) in nodes.items():
        if not script: continue
        members = all_members(script)
        for prop in re.findall(r"^([\w/]+) = ", b, re.M):
            if prop in NODE_TYPES_ALLOWED_PROPS or prop.startswith("metadata/"): continue
            if prop in BUILTIN_PROPS and prop not in EXPORT_NAMES: continue
            if "type" in a:  # builtin node with a script: may set builtin props
                if prop not in members and prop in ("mesh", "shape", "text", "collision_layer", "collision_mask",
                                                    "monitoring", "monitorable", "light_energy", "omni_range"):
                    continue
            if prop not in members:
                # builtin Node3D props on instanced nodes are fine only if well known
                err(f"{path}: {npath} sets '{prop}' not on {script}")
    # NodePaths
    for npath, (script, b, a) in nodes.items():
        for np_ in re.findall(r'NodePath\("([^"]*)"\)', b):
            if not np_: continue
            base = [] if npath == "." else npath.split("/")
            parts = base[:]
            for seg in np_.split("/"):
                if seg == "..":
                    if not parts:
                        err(f"{path}: {npath} NodePath {np_} escapes root"); break
                    parts.pop()
                elif seg != ".":
                    parts.append(seg)
            target = "/".join(parts) if parts else "."
            if target not in nodes:
                # may point inside an instanced scene; accept if prefix is an instance
                prefix_ok = False
                for n in nodes:
                    if n == "." or not target.startswith(n + "/") or "instance" not in nodes[n][2]:
                        continue
                    iid = re.search(r'ExtResource\("([^"]+)"\)', nodes[n][2]["instance"]).group(1)
                    inner = instance_node_paths(script_for_ext(ext, iid))
                    if target[len(n) + 1:] in inner:
                        prefix_ok = True
                if not prefix_ok:
                    err(f"{path}: {npath} NodePath {np_} -> {target} unresolved")
    # $Node paths for the root script
    root_script = nodes.get(".", (None,))[0]
    root_direct = re.search(r'^script = ', nodes.get(".", (None, "", {}))[1], re.M) if "." in nodes else None
    if root_script and root_direct:
        for ref in re.findall(r"\$([\w/]+)", scripts.get(root_script, "")):
            if ref not in nodes and not any(ref.startswith(n + "/") and "instance" in nodes[n][2] for n in nodes if n != "."):
                err(f"{path}: {root_script} uses ${ref} which is not in scene")

# ------------------------------------------------------------ greps
crop_ids = set()
for f in glob.glob("data/crops/*.tres"):
    m = re.search(r'crop_id = "([^"]+)"', open(f).read())
    if m: crop_ids.add(m.group(1))
for f, s in scripts.items():
    for cid in crop_ids:
        if re.search(rf'"{cid}"', s):
            err(f"{f}: hard-coded crop id {cid}")
    if re.search(r"(sunflower|carrot|herb)\"", s, re.I):
        err(f"{f}: crop-name literal")
    if re.search(r"HTTPRequest|StreamPeerTCP|PacketPeerUDP|WebSocket|HTTPClient|ENetMultiplayer", s):
        err(f"{f}: network API")

# ------------------------------------------------------------ physics layers
# PhysicsLayers (scripts/data/physics_layers.gd) is the only place layer
# numbers may appear in code, and each *_LAYER must match its name in
# project.godot's [layer_names].
LAYERS_SCRIPT = "scripts/data/physics_layers.gd"
layer_names = dict(re.findall(r'^3d_physics/layer_(\d+)="([^"]*)"', cfg, re.M))
if LAYERS_SCRIPT in scripts:
    declared = re.findall(r"^const\s+(\w+)_LAYER\s*:=\s*(\d+)", scripts[LAYERS_SCRIPT], re.M)
    if not declared:
        err(f"{LAYERS_SCRIPT}: no *_LAYER constants found")
    for prefix, num in declared:
        name = layer_names.get(num)
        if name is None:
            err(f"{LAYERS_SCRIPT}: {prefix}_LAYER = {num} but project.godot has no name for 3D physics layer {num}")
        elif name.lower() != prefix.lower():
            err(f"{LAYERS_SCRIPT}: {prefix}_LAYER = {num} but project.godot names layer {num} '{name}'")
    notes.append(f"physics layers: {', '.join(f'{p}={n}' for p, n in declared)}")
else:
    err(f"{LAYERS_SCRIPT} missing")
MAGIC_MASK = re.compile(
    r"(collision_(layer|mask)\s*=\s*\d)|((_MASK|_LAYER)\s*:?=\s*\d)|"
    r"(set_collision_(layer|mask)(_value)?\(\s*\d)|(PhysicsRayQueryParameters3D\.create\([^)]*,\s*\d+\s*[,)])")
for f, s2 in scripts.items():
    if f == LAYERS_SCRIPT:
        continue
    for ln, line in enumerate(s2.split("\n"), 1):
        code = line.split("#", 1)[0]
        if MAGIC_MASK.search(code):
            err(f"{f}:{ln}: numeric physics layer/mask; use PhysicsLayers ({code.strip()})")

# ------------------------------------------------------------ input map
# Movement must come from InputMap actions (never raw key polling), the
# desktop movement keys must stay mapped, and every action a script uses
# must be defined in project.godot (or be a built-in ui_* action).
REQUIRED_MOVE_KEYS = {  # action -> physical keycodes that must stay mapped
    "move_up": {87: "W", 4194320: "Up"},
    "move_down": {83: "S", 4194322: "Down"},
    "move_left": {65: "A", 4194319: "Left"},
    "move_right": {68: "D", 4194321: "Right"},
}
input_sec = re.search(r"^\[input\]\n(.*?)(?=^\[|\Z)", cfg, re.M | re.S)
defined_actions = {}
if input_sec:
    for m in re.finditer(r'^(\w+)=\{(.*?)^\}', input_sec.group(1), re.M | re.S):
        defined_actions[m.group(1)] = {int(k) for k in re.findall(r'"physical_keycode":(\d+)', m.group(2))} | \
                                      {int(k) for k in re.findall(r'"keycode":(\d+)', m.group(2)) if k != "0"}
for action, keys in REQUIRED_MOVE_KEYS.items():
    if action not in defined_actions:
        err(f"project.godot: input action '{action}' missing")
        continue
    for code, label in keys.items():
        if code not in defined_actions[action]:
            err(f"project.godot: input action '{action}' lost its {label} key")
notes.append(f"input actions: {', '.join(sorted(defined_actions))}")
ACTION_CALL = re.compile(r"(?:is_action\w*|get_vector|get_axis|get_action_\w+|action_press|action_release)\(([^)]*)\)")
RAW_KEYS = re.compile(r"\bis_(physical_)?key_pressed\(|\bKEY_[A-Z0-9_]+\b|\.(physical_)?keycode\b")
for f, s2 in scripts.items():
    consts = dict(re.findall(r'^const\s+(\w+)\s*:?=\s*&?"(\w+)"', s2, re.M))
    for ln, line in enumerate(s2.split("\n"), 1):
        code = re.sub(r"#.*", "", line)
        if RAW_KEYS.search(code):
            err(f"{f}:{ln}: raw key handling; use an InputMap action ({code.strip()})")
        for args in ACTION_CALL.findall(code):
            for tok in [t.strip() for t in args.split(",")]:
                name = None
                lit = re.fullmatch(r'&?"(\w+)"', tok)
                if lit: name = lit.group(1)
                elif tok in consts: name = consts[tok]
                if name and not name.startswith("ui_") and name not in defined_actions:
                    err(f"{f}:{ln}: input action '{name}' is not defined in project.godot")

# ------------------------------------------------------------ tap contracts
# Guards the touch-control rules (docs/ARCHITECTURE.md §6-7) in the real
# scripts, not just in the simulation's port of them:
#  - taps resolve the same in every movement mode;
#  - a tapped Interactable is walked to and interacted with on entering the
#    player's InteractionZone, never by a separate distance rule;
#  - joystick/keyboard input cancels a tap-started walk;
#  - inactive (non-monitorable) interactables never capture a tap.
def func_body(src, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S)
    return m.group(0) if m else None
IM, PL = "scripts/autoload/input_manager.gd", "scripts/player/player.gd"
contracts = [
    (IM, "_handle_tap", lambda b: not re.search(r"is_tap_to_move|movement_mode", b),
     "tap routing must not depend on the movement mode"),
    (IM, "_handle_tap", lambda b: "_interactable_near(" in b and "move_target_requested.emit" in b,
     "tap routing must try small-object selection and emit ground movement"),
    (IM, "_find_interactable", lambda b: "monitorable" in b,
     "inactive (non-monitorable) interactables must not capture taps"),
    (PL, "_on_interact_target_requested", lambda b: "_nearby_interactables.has(target)" in b and "_approach_target = target" in b,
     "a tapped interactable is interacted with in InteractionZone range, otherwise walked to"),
    (PL, "_on_interact_target_requested", lambda b: not re.search(r"distance_to|REACH", b),
     "no separate distance/reach rule for tapped interactables"),
    (PL, "_on_interaction_zone_area_entered", lambda b: "_approach_target" in b and "_interact_with(" in b,
     "reaching the tapped object's range must trigger its interaction"),
    (PL, "_physics_process", lambda b: re.search(r"if direction != Vector3\.ZERO:\s*_stop_navigation\(\)", b) is not None,
     "joystick/keyboard input must cancel a tap-started walk"),
    (IM, "_handle_tap", lambda b: "_is_player_tap(" in b and "stop_requested.emit()" in b
         and b.find("stop_requested.emit()") < b.find("move_target_requested.emit"),
     "tapping the player must request a stop, before any ground movement"),
    (PL, "_ready", lambda b: "stop_requested.connect(_on_stop_requested)" in b and "PLAYER_GROUP" in b,
     "the player must join PLAYER_GROUP and listen for stop requests"),
    (PL, "_on_stop_requested", lambda b: "_stop_navigation()" in b,
     "a stop request must cancel the walk and any pending interaction"),
]
for f, fn, ok, why in contracts:
    body = func_body(scripts.get(f, ""), fn)
    if body is None:
        err(f"{f}: {fn}() missing (tap contract: {why})")
    elif not ok(body):
        err(f"{f}: {fn}() breaks tap contract: {why}")
notes.append(f"tap contracts checked: {len(contracts)}")

# ------------------------------------------------------------ animation hook
# One gameplay animation state (IDLE/WALK/INTERACT) in Player, derived from
# real movement/interaction and never driving them (docs/ARCHITECTURE.md §4).
anim_enums = [(f, m.group(1), m.group(2)) for f, s2 in scripts.items()
              for m in re.finditer(r"^enum\s+(\w*Anim\w*)\s*\{([^}]*)\}", s2, re.M)]
if len(anim_enums) != 1 or anim_enums[0][0] != PL or anim_enums[0][1] != "AnimState":
    err(f"animation state: expected exactly one 'enum AnimState' in {PL}, found {[(f, n) for f, n, _ in anim_enums]}")
else:
    states = {x.strip() for x in anim_enums[0][2].split(",") if x.strip()}
    if states != {"IDLE", "WALK", "INTERACT"}:
        err(f"{PL}: AnimState must be exactly IDLE, WALK, INTERACT (found {sorted(states)})")
emitters = [f for f, s2 in scripts.items() if "animation_state_changed.emit" in s2]
if emitters != [PL] or scripts[PL].count("animation_state_changed.emit") != 1:
    err(f"animation_state_changed must be emitted in exactly one place in {PL} (found in {emitters})")
MOVEMENT_LOGIC = re.compile(r"\bvelocity\s*=|move_and_slide|nav_agent|_stop_navigation|_start_navigation|"
                            r"_interact_with|InputManager|\.interact\(|global_position\s*=")
anim_contracts = [
    ("_set_animation_state", lambda b: "if state == _animation_state:" in b and "animation_state_changed.emit" in b
         and not MOVEMENT_LOGIC.search(b), "single emitter, only on change, no movement/interaction logic"),
    ("_update_movement_animation_state", lambda b: "WALK_START_SPEED" in b and "WALK_STOP_SPEED" in b
         and "AnimState.INTERACT" in b and not MOVEMENT_LOGIC.search(b),
     "IDLE/WALK from speed with hysteresis, INTERACT untouched, no movement logic"),
    ("_physics_process", lambda b: "_update_movement_animation_state(" in b, "state evaluated in the existing physics step"),
    ("_interact_with", lambda b: re.search(r"_begin_interaction\(target\).*await target\.interact\(\).*_end_interaction\(serial\)", b, re.S) is not None,
     "INTERACT begins before and ends after the real interact() call"),
    ("_begin_interaction", lambda b: "tree_exiting.connect" in b and "AnimState.INTERACT" in b,
     "INTERACT ends if the object disappears"),
    ("_end_interaction", lambda b: "serial != _interaction_serial" in b and "AnimState.IDLE" in b and not MOVEMENT_LOGIC.search(b),
     "only the current interaction ends INTERACT; returns to IDLE/WALK; no movement logic"),
]
for fn, ok, why in anim_contracts:
    body = func_body(scripts.get(PL, ""), fn)
    if body is None:
        err(f"{PL}: {fn}() missing (animation contract: {why})")
    elif not ok(body):
        err(f"{PL}: {fn}() breaks animation contract: {why}")
if re.search(r"\bTimer\b|create_timer", scripts.get(PL, "")):
    err(f"{PL}: no timers in Player (animation state is event/state-change driven)")
notes.append(f"animation contracts checked: {len(anim_contracts) + 3}")

print("NOTES:"); [print("  " + n) for n in notes]
print(f"{len(scripts)} scripts, {len(all_res)} resources checked")
if errors:
    print("ERRORS:"); [print("  " + e) for e in errors]; sys.exit(1)
print("ALL CHECKS PASSED")
