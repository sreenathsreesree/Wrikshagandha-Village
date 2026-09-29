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
#  - unavailable interactables never capture a tap.
def func_body(src, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S)
    return m.group(0) if m else None
IM, PL = "scripts/autoload/input_manager.gd", "scripts/player/player.gd"
contracts = [
    (IM, "_handle_tap", lambda b: not re.search(r"is_tap_to_move|movement_mode", b),
     "tap routing must not depend on the movement mode"),
    (IM, "_handle_tap", lambda b: "_interactable_near(" in b and "move_target_requested.emit" in b,
     "tap routing must try small-object selection and emit ground movement"),
    (IM, "_find_interactable", lambda b: "is_interaction_available()" in b,
     "unavailable interactables must not capture taps"),
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

# ------------------------------------------------------------ interaction contract
# One generic interaction architecture (docs/ARCHITECTURE.md §6): the
# Interactable base holds only the contract; object behaviour lives in
# subclasses; Player and InputManager use only the contract, never a
# concrete type; interact() has exactly one call site.
BASE = "scripts/interactables/interactable.gd"
PROBE = "tools/fixtures/generic_interactable_probe.gd"
def code_only(src):
    return "\n".join(line.split("#")[0] if not line.lstrip().startswith("##") else "" for line in src.splitlines())
base_src = scripts.get(BASE, "")
base_code = code_only(base_src)
for fn in ("is_interaction_available", "interact", "get_interaction_metadata", "set_highlighted", "update_proximity"):
    if func_body(base_src, fn) is None:
        err(f"{BASE}: generic contract function {fn}() missing")
if BASE not in scripts or "remove_on_harvest" not in own_members(BASE):
    err(f"{BASE}: generic contract member remove_on_harvest missing")
avail = func_body(base_src, "is_interaction_available") or ""
if "return monitorable" not in avail:
    err(f"{BASE}: is_interaction_available() must be backed by monitorable (the InteractionZone and tap rays agree)")
OBJECT_SPECIFIC = re.compile(r"\bDiscovery(Manager|Database|Definition|Interactable)\b|\bdiscovery_id\b|\b_definition\b|"
                             r"\bFarm(Manager|Plot)\b|\bCrop\w*|\bCATEGORY_WINDUP\b|^signal\s", re.M)
for m in OBJECT_SPECIFIC.finditer(base_code):
    err(f"{BASE}: object-specific '{m.group(0).strip()}' in the generic Interactable base")
subclasses = sorted(f for f in scripts if f != BASE and BASE in chain(f))
sub_names = sorted(file_class[f] for f in subclasses if f in file_class)
for f in subclasses:
    body = func_body(scripts[f], "interact")
    if body is None or not re.match(r"func interact\(\)\s*->\s*bool:", body):
        err(f"{f}: an Interactable must implement interact() -> bool")
for f in (PL, IM):
    code = code_only(scripts.get(f, ""))
    for name in sub_names + ["discovery_id", "DiscoveryManager", "FarmManager", "harvested", "plot_state", "crop_definition"]:
        if re.search(rf"\b{name}\b", code):
            err(f"{f}: object-specific '{name}' — Player/InputManager must use only the Interactable contract")
calls = [(f, n) for f, s2 in scripts.items() if not f.startswith("tools/")
         for n in [len(re.findall(r"\.interact\(\)", code_only(s2)))] if n]
if calls != [(PL, 1)]:
    err(f"interact() must have exactly one call site (Player._interact_with); found {calls}")
iw = func_body(scripts.get(PL, ""), "_interact_with") or ""
spent = re.search(r"if _spent_interactables\.has\(target\) or not target\.is_interaction_available\(\):\s*return"
                  r".*if target\.remove_on_harvest:\s*_nearby_interactables\.erase\(target\)\s*_spent_interactables\.append\(target\)"
                  r".*_begin_interaction\(target\)", iw, re.S)
if not spent:
    err(f"{PL}: _interact_with() must keep one-shot protection (refuse spent objects; register one-shot objects before interacting)")
if "is_interaction_available()" not in iw or iw.find("is_interaction_available()") > iw.find("_begin_interaction("):
    err(f"{PL}: _interact_with() must refuse unavailable objects before interacting")
for f, s2 in scripts.items():
    if not f.startswith("tools/") and re.search(r"^class\s+\w+\s+extends\s+(Area3D|Interactable)", s2, re.M):
        err(f"{f}: a second interaction class hierarchy (inner class) — extend Interactable instead")
bare = [f for f in glob.glob("**/*.tscn", recursive=True) if f'path="res://{BASE}"' in open(f, encoding="utf-8").read()]
if bare:
    err(f"scenes use the bare Interactable base, which does nothing: {bare}")
if PROBE not in scripts or PROBE not in subclasses or re.search(r"^class_name", scripts[PROBE], re.M):
    err(f"{PROBE}: the generic probe must exist, extend Interactable and have no class_name (never game content)")
elif not os.path.exists("tools/.gdignore"):
    err("tools/.gdignore missing: the interaction probe would become game content")
refs = [f for f in glob.glob("**/*.tscn", recursive=True) + glob.glob("**/*.tres", recursive=True) + ["project.godot"]
        if "res://tools/" in open(f, encoding="utf-8").read()]
if refs:
    err(f"game content must not reference tools/: {refs}")
# M02.5 (A6): one way in. A tap names its target (interact_target_requested),
# Player walks/faces/interacts through _interact_with(); the old "interact
# with the nearest" path (interact_requested / request_interact) is gone.
im_code = code_only(scripts.get(IM, ""))
game_files = [f for f in list(scripts) + glob.glob("**/*.tscn", recursive=True) + ["project.godot"] if not f.startswith("tools/")]
for f in game_files:
    txt = code_only(scripts[f]) if f in scripts else open(f, encoding="utf-8").read()
    for m in re.finditer(r"\b(interact_requested|request_interact|_on_interact_requested)\b", txt):
        err(f"{f}: '{m.group(1)}' — the removed nearest-object interaction path (A6) must not return")
im_interact_signals = sorted(re.findall(r"^signal\s+(\w*interact\w*)", im_code, re.M))
if im_interact_signals != ["interact_target_requested"]:
    err(f"{IM}: exactly one interaction request signal, interact_target_requested (found {im_interact_signals})")
if "interact_target_requested.emit(" not in (func_body(scripts.get(IM, ""), "_handle_tap") or "") or \
   "InputManager.interact_target_requested.connect(_on_interact_target_requested)" not in (func_body(scripts.get(PL, ""), "_ready") or ""):
    err("the tap target-request path (InputManager._handle_tap -> Player._on_interact_target_requested) must stay wired")
pl_code_src = scripts.get(PL, "")
iw_callers = sorted(fn for fn in re.findall(r"^func (\w+)\(", pl_code_src, re.M)
                    if fn != "_interact_with" and "_interact_with(" in code_only(func_body(pl_code_src, fn) or ""))
if iw_callers != ["_on_interact_target_requested", "_on_interaction_zone_area_entered"]:
    err(f"{PL}: _interact_with() must be entered only from a tap (in range) or arrival at the tapped object (found {iw_callers})")
notes.append(f"interaction contract: {len(subclasses)} Interactable implementations {sub_names + ['(probe)']}")

# ------------------------------------------------------------ interaction verbs
# Verbs are data (decision D-09, M02.2): one enum, Interactable.Verb, whose
# names come from D-09; objects offer verbs for their current state through
# one guarded query; Player/InputManager never name a specific verb; verbs
# are never spelled as strings.
d09 = re.search(r"^\| D-09 \|[^|]*capabilities:\s*([^.]*)\.", open("docs/DESIGN_DECISIONS.md", encoding="utf-8").read(), re.M)
D09_VERBS = {v.strip().upper() for v in d09.group(1).split(",")} if d09 else set()
if not D09_VERBS:
    err("docs/DESIGN_DECISIONS.md: D-09 verb list not found")
verb_enums = [(f, m) for f, s2 in scripts.items() for m in re.finditer(r"^enum\s+(\w*Verb\w*)\s*\{([^}]*)\}", s2, re.M)]
if len(verb_enums) != 1 or verb_enums[0][0] != BASE or verb_enums[0][1].group(1) != "Verb":
    err(f"interaction verbs: expected exactly one 'enum Verb' in {BASE}, found {[(f, m.group(1)) for f, m in verb_enums]}")
    VERBS = {}
else:
    VERBS = {}
    for item in [x.strip() for x in verb_enums[0][1].group(2).split(",") if x.strip()]:
        m = re.fullmatch(r"([A-Z_]+)\s*=\s*(\d+)", item)
        if not m:
            err(f"{BASE}: Verb.{item} needs an explicit, stable value")
            continue
        VERBS[m.group(1)] = int(m.group(2))
    if len(set(VERBS.values())) != len(VERBS):
        err(f"{BASE}: Verb values must be unique {VERBS}")
    for name in sorted(set(VERBS) - D09_VERBS):
        err(f"{BASE}: Verb.{name} is not a decided verb (D-09: {sorted(D09_VERBS)})")
gav = func_body(base_src, "get_available_interaction_verbs") or ""
if not re.search(r"if is_interaction_available\(\):\s*verbs = _get_interaction_verbs\(\)", gav):
    err(f"{BASE}: get_available_interaction_verbs() must offer nothing while unavailable")
iwv = func_body(base_src, "interact_with_verb") or ""
if not re.search(r"if not get_available_interaction_verbs\(\)\.has\(verb\):\s*return false.*_perform_interaction_verb\(verb\)", iwv, re.S):
    err(f"{BASE}: interact_with_verb() must perform only a currently offered verb")
if "interact()" not in (func_body(base_src, "_perform_interaction_verb") or ""):
    err(f"{BASE}: _perform_interaction_verb() must default to interact() (existing behaviour)")
for f in subclasses:
    for fn in ("get_available_interaction_verbs", "interact_with_verb"):
        if func_body(scripts[f], fn) is not None:
            err(f"{f}: overrides {fn}() — override _get_interaction_verbs()/_perform_interaction_verb() instead")
FIXTURES = {"tools/fixtures/inspect_fixture.gd": {"INSPECT"},
            "tools/fixtures/open_fixture.gd": {"OPEN"},
            "tools/fixtures/read_fixture.gd": {"INSPECT", "READ"}}
EXPECTED_VERBS = {"scripts/interactables/discovery_interactable.gd": {"COLLECT"},
                  "scripts/farming/farm_plot.gd": {"PLANT", "WATER", "HARVEST"}, **FIXTURES}
for f, want in EXPECTED_VERBS.items():
    body = func_body(scripts.get(f, ""), "_get_interaction_verbs") or ""
    have = set(re.findall(r"\bVerb\.([A-Z_]+)", body))
    if have != want:
        err(f"{f}: _get_interaction_verbs() offers {sorted(have)}, expected {sorted(want)} (from its existing behaviour)")
for f in (PL, IM):
    m = re.search(r"\bVerb\.[A-Z_]+", code_only(scripts.get(f, "")))
    if m:
        err(f"{f}: names a specific verb '{m.group(0)}' — Player/InputManager stay verb-agnostic")
# (Lower-case words such as the "plant" discovery category are nouns, not
# verbs: a string counts as a verb when it's spelled in upper case, or on a
# line that is about verbs.)
for f, s2 in scripts.items():
    for line in code_only(s2).splitlines():
        for m in re.finditer(r"\"([A-Za-z_]+)\"", line):
            word = m.group(1)
            if word.upper() in D09_VERBS | set(VERBS) and (word.isupper() or re.search(r"verb", line, re.I)):
                err(f"{f}: verb spelled as a string \"{word}\" — use Interactable.Verb")
    if f != BASE:
        for m in re.finditer(r"\bVerb\.([A-Za-z_]+)", code_only(s2)):
            if m.group(1) not in VERBS:
                err(f"{f}: unknown verb Verb.{m.group(1)}")
offered = set()
for f in subclasses:
    offered |= set(re.findall(r"\bVerb\.([A-Z_]+)", func_body(scripts[f], "_get_interaction_verbs") or ""))
for name in sorted(set(VERBS) - offered):
    err(f"{BASE}: Verb.{name} is offered by no object or fixture — verbs arrive with the behaviour that needs them")

# M02.6: INSPECT / OPEN / READ verification fixtures — new object types on
# the generic contract with zero Player/InputManager knowledge of them.
for f, want in FIXTURES.items():
    src = scripts.get(f)
    if src is None or f not in subclasses or re.search(r"^class_name", src, re.M):
        err(f"{f}: a fixture must exist, extend Interactable and have no class_name (never game content)")
        continue
    fcode = code_only(src)
    if not re.search(r"func set_available\(value: bool\) -> void:\s*monitorable = value", src):
        err(f"{f}: a fixture switches availability only through the generic contract (monitorable)")
    if re.search(r"\bInputManager\b|\bPlayer\b|_interact_with|get_tree\(|get_first_node_in_group|(?<!func )\binteract\(\)", fcode):
        err(f"{f}: a fixture must not reach into Player/InputManager or call interact() itself (one path: Player)")
    for fn in ("get_available_interaction_verbs", "interact_with_verb", "is_interaction_available"):
        if func_body(src, fn) is not None:
            err(f"{f}: overrides {fn}() — fixtures use the guarded base contract")
rf = scripts.get("tools/fixtures/read_fixture.gd", "")
perf = func_body(rf, "_perform_interaction_verb") or ""
if len(FIXTURES["tools/fixtures/read_fixture.gd"]) < 2 or not re.search(r"if verb == Verb\.INSPECT:\s*return _inspect\(\)\s*return _read\(\)", perf) \
   or "return _read()" not in (func_body(rf, "interact") or ""):
    err("tools/fixtures/read_fixture.gd: the multi-verb fixture must offer INSPECT and READ and perform the selected one (READ by default)")
for f in (PL, IM):
    m = re.search(r"\b(INSPECT|OPEN|READ|[Ff]ixture\w*|probe\w*|res://tools)\b", code_only(scripts.get(f, "")))
    if m:
        err(f"{f}: knows about '{m.group(1)}' — Player/InputManager stay unaware of fixtures and specific verbs")
for f in (PL, IM):
    code = code_only(scripts.get(f, ""))
    objs = set(re.findall(r"\b(\w+)\s*:\s*(?:Interactable|Node|Node3D|Area3D)\b", code)) | \
           set(re.findall(r"\bvar\s+(\w+)\s*:?=\s*[^\n]*\bas (?:Interactable|Node)\b", code))
    m = re.search(r"\b(has_method|get_script|is_class|has_signal)\(|\.(call|callv|call_deferred)\(", code) or \
        (objs and re.search(rf"\b(?:{'|'.join(sorted(objs))})\.(get|get_meta|has_meta)\(", code))
    if m:
        err(f"{f}: reflection ('{m.group(0)}') — Player/InputManager must not tell objects apart by their methods or script")
for f, s2 in scripts.items():
    if not f.startswith("tools/") and re.search(r"res://tools/|_fixture\b|fixtures/", code_only(s2)):
        err(f"{f}: game code must not load or reference the verification fixtures")
notes.append(f"interaction verbs: {sorted(VERBS, key=VERBS.get)} (D-09 subset); fixtures: {len(FIXTURES)}")

# ------------------------------------------------------------ facing on arrival
# M02.3: the player turns toward an object once, at the generic interaction
# boundary (Player._interact_with), after it has been accepted and before
# INTERACT/interact() — never while walking, never for a cancelled target.
pl_src = scripts.get(PL, "")
iw = func_body(pl_src, "_interact_with") or ""
pos = {k: iw.find(k) for k in ("is_interaction_available()", "_face_target(target)", "_begin_interaction(target)", "target.interact()")}
if -1 in pos.values() or not (pos["is_interaction_available()"] < pos["_face_target(target)"] < pos["_begin_interaction(target)"] < pos["target.interact()"]):
    err(f"{PL}: _interact_with() must face the target after accepting it and before INTERACT/interact() {pos}")
ft = func_body(pl_src, "_face_target") or ""
if not ft:
    err(f"{PL}: _face_target() missing")
else:
    if "target.global_position - global_position" not in ft or not re.search(r"\.y = 0\.0", ft):
        err(f"{PL}: _face_target() must use the horizontal direction to the target's position")
    guard = re.search(r"if to_target\.length\(\) < FACE_TARGET_MIN_DISTANCE:\s*return", ft)
    if not guard or guard.start() > ft.find("_facing_angle ="):
        err(f"{PL}: _face_target() must keep the facing when there's no horizontal direction")
    if re.search(r"\bvelocity\b|\bdirection\b|nav_agent|\bis\s+[A-Z]|visual\.rotation|\bawait\b|\bVerb\.", ft):
        err(f"{PL}: _face_target() must use only the target position (no movement direction, type, verb, snap or waiting)")
    if "_facing_angle = atan2(to_target.x, -to_target.z)" not in ft:
        err(f"{PL}: _face_target() must set the existing facing (_facing_angle) that _update_facing() eases to")
face_calls = [(f, len(re.findall(r"_face_target\(", code_only(s2))) - (1 if f == PL else 0)) for f, s2 in scripts.items()]
face_calls = [c for c in face_calls if c[1]]
if face_calls != [(PL, 1)] or "_face_target(" not in iw:
    err(f"_face_target() must be called only from Player._interact_with (found {face_calls})")
writers = sorted({m for m in re.findall(r"^func (\w+)\(", pl_src, re.M) if "_facing_angle =" in (func_body(pl_src, m) or "")})
if writers != ["_face_target", "_ready", "_update_facing", "place_at"]:
    err(f"{PL}: _facing_angle may only be set in _ready/_update_facing/_face_target/place_at (found {writers})")
if re.search(r"_face_target|target\.global_position", func_body(pl_src, "_physics_process") or "") or \
   re.search(r"_approach_target|_interaction_target", func_body(pl_src, "_update_facing") or ""):
    err(f"{PL}: no continuous turning toward a target while walking")
for fn in ("_start_navigation", "_stop_navigation"):
    if "_approach_target = null" not in (func_body(pl_src, fn) or ""):
        err(f"{PL}: {fn}() must drop the approach target (no late facing/interaction for a cancelled or replaced target)")
if not re.search(r"if interactable == _approach_target:\s*_stop_navigation\(\)\s*_interact_with\(interactable\)",
                 func_body(pl_src, "_on_interaction_zone_area_entered") or ""):
    err(f"{PL}: arrival must interact (and face) only with the current approach target")
if re.search(r"^func _process\(", pl_src, re.M):
    err(f"{PL}: no _process() in Player — its one per-frame step is the existing _physics_process()")
notes.append("facing contracts checked: 12")

# ------------------------------------------------------------ tap feedback + selection
# M02.4: a recognised tap shows the object's own Indicator at once (with the
# existing pulse) until its interaction starts or the walk is cancelled or
# replaced; near-miss selection ranks available candidates by distance to
# their shape; exact hits win; tolerance and range are pinned to the docs.
im_src = scripts.get(IM, "")
arch = open("docs/ARCHITECTURE.md", encoding="utf-8").read()
def const_val(src, name):
    m = re.search(rf"^const {name} := ([0-9.]+)", src, re.M)
    return float(m.group(1)) if m else None
doc_tol = re.search(r"`TAP_SELECT_TOLERANCE` \(([0-9.]+) m\)", arch)
if not doc_tol or const_val(im_src, "TAP_SELECT_TOLERANCE") != float(doc_tol.group(1)):
    err(f"{IM}: TAP_SELECT_TOLERANCE {const_val(im_src, 'TAP_SELECT_TOLERANCE')} differs from docs/ARCHITECTURE.md — a tolerance change must be deliberate and documented")
doc_range = re.search(r"`InteractionZone` \(([0-9.]+) m Area3D\)", arch)
zone = re.search(r'SphereShape3D_interact"\]\s*radius = ([0-9.]+)', open("scenes/player/Player.tscn", encoding="utf-8").read())
if not doc_range or not zone or {float(zone.group(1)), const_val(pl_src, "INTERACTION_RADIUS")} != {float(doc_range.group(1))}:
    err("interaction range: Player.tscn InteractionZone radius, Player.INTERACTION_RADIUS and docs/ARCHITECTURE.md must agree (2.2 m)")
sts = func_body(base_src, "set_tap_selected") or ""
g = re.search(r"if active and not is_interaction_available\(\):\s*return", sts)
if not g or g.start() > sts.find("_tap_selected = active") or "indicator.pulse(" not in sts or "_refresh_indicator()" not in sts:
    err(f"{BASE}: set_tap_selected() must refuse unavailable objects, then show the Indicator with its pulse")
if "indicator.visible = _highlighted or _tap_selected" not in (func_body(base_src, "_refresh_indicator") or "") or \
   not re.search(r"_highlighted = active\s*_refresh_indicator\(\)", func_body(base_src, "set_highlighted") or ""):
    err(f"{BASE}: the Indicator shows while in range OR tap-selected (one visibility rule)")
for f in subclasses:
    for fn in ("set_tap_selected", "_refresh_indicator"):
        if func_body(scripts[f], fn) is not None:
            err(f"{f}: overrides {fn}() — tap feedback stays generic")
pulse_defs = [f for f, s2 in scripts.items() if re.search(r"^func pulse\(", s2, re.M)]
ind_classes = [f for f, s2 in scripts.items() if re.search(r"^class_name \w*(Indicator|Highlight|Feedback|Marker)\w*", s2, re.M)]
if pulse_defs != ["scripts/interactables/indicator_bob.gd"] or ind_classes != ["scripts/interactables/indicator_bob.gd"]:
    err(f"one indicator/feedback mechanism only (found pulse in {pulse_defs}, classes {ind_classes})")
sel_calls = [(f, len(re.findall(r"\.set_tap_selected\(", code_only(s2)))) for f, s2 in scripts.items()]
if [c for c in sel_calls if c[1]] != [(PL, 2)] or ".set_tap_selected(" in code_only(func_body(pl_src, "_on_interact_target_requested") or "x"):
    err(f"set_tap_selected() is driven only by Player._set_selected_target (found {[c for c in sel_calls if c[1]]})")
oitr = func_body(pl_src, "_on_interact_target_requested") or ""
near_branch = oitr[:oitr.find("_start_navigation(")]
far_branch = oitr[oitr.find("_start_navigation("):]
if not re.search(r"_stop_navigation\(\)\s*_set_selected_target\(target\)\s*_interact_with\(target\)", near_branch) or \
   not re.search(r"_approach_target = target\s*_set_selected_target\(target\)", far_branch) or "await" in oitr:
    err(f"{PL}: a tapped object must get its feedback immediately (in range: before interacting; far: when the walk starts)")
if "_set_selected_target(" in (func_body(pl_src, "_on_interaction_zone_area_entered") or ""):
    err(f"{PL}: tap feedback must not wait for arrival")
for fn in ("_start_navigation", "_stop_navigation"):
    if "_set_selected_target(null)" not in (func_body(pl_src, fn) or ""):
        err(f"{PL}: {fn}() must release the tap selection (no stale feedback after cancel/replace)")
iw = func_body(pl_src, "_interact_with") or ""
if not re.match(r"func _interact_with\([^)]*\) -> void:\s*_set_selected_target\(null\)", iw):
    err(f"{PL}: _interact_with() must release the tap selection as the interaction starts")
sst = func_body(pl_src, "_set_selected_target") or ""
if not re.search(r"_selected_target\.set_tap_selected\(false\).*_selected_target = target.*target\.set_tap_selected\(true\)", sst, re.S):
    err(f"{PL}: _set_selected_target() must release the old selection before acknowledging the new one")
ht = func_body(im_src, "_handle_tap") or ""
if not (0 <= ht.find("interact_target_requested.emit(target)") < ht.find("_interactable_near(") < ht.find("move_target_requested.emit")):
    err(f"{IM}: exact interactable hit, then near-miss selection, then ground movement")
near = code_only(func_body(im_src, "_interactable_near") or "")
if not all(k in near for k in ("_find_interactable(", "_tap_distance(candidate, point)", "distance < best_distance",
                               "get_instance_id() < best.get_instance_id()", "_tap_select_shape.radius = TAP_SELECT_TOLERANCE")):
    err(f"{IM}: near-miss selection must skip unavailable objects and pick the nearest (to its shape, deterministic ties) within TAP_SELECT_TOLERANCE")
td = code_only(func_body(im_src, "_tap_distance") or "")
if not td or re.search(r"\bis\s+(?!\w*Shape3D\b)\w+", td) or set(re.findall(r"candidate\.(\w+)", near + td)) - {"get_children", "global_position", "get_instance_id"}:
    err(f"{IM}: selection distance must be generic (shapes only, never the kind of object or its state)")
if "Vector2(offset.x, offset.z).length() - reach" not in td:
    err(f"{IM}: _tap_distance() must measure to the object's shape (minus its radius), not its centre")
# Per-frame loops: this is the whole set. A new one is a deliberate,
# reviewed change to this list (docs/ARCHITECTURE.md §17), never a side effect.
PER_FRAME = [('scripts/camera/follow_camera.gd', '_physics_process'), ('scripts/interactables/indicator_bob.gd', '_process'), ('scripts/player/player.gd', '_physics_process'), ('scripts/ui/virtual_joystick.gd', '_process'), ('scripts/world/butterfly.gd', '_process'), ('scripts/world/drifting_leaf.gd', '_process'), ('scripts/world/floating_motes.gd', '_process'), ('scripts/world_simulation/environmental_event_controller.gd', '_process'), ('scripts/world_simulation/exploration_landmark_controller.gd', '_process'), ('scripts/world_simulation/time_of_day.gd', '_process'), ('scripts/world_simulation/vegetation_controller.gd', '_process'), ('scripts/world_simulation/wildlife_actor.gd', '_process'), ('scripts/world_simulation/wildlife_butterfly.gd', '_process')]
found = sorted((f, m) for f, s2 in scripts.items() if not f.startswith("tools/") or f.startswith("tools/fixtures/")
               for m in re.findall(r"^func (_process|_physics_process)\(", s2, re.M))
if found != sorted(tuple(x) for x in PER_FRAME):
    err(f"per-frame callbacks changed: added {sorted(set(found) - set(map(tuple, PER_FRAME)))}, removed {sorted(set(map(tuple, PER_FRAME)) - set(found))}")
notes.append("tap feedback + selection contracts checked: 18; per-frame callbacks: %d" % len(PER_FRAME))

# ------------------------------------------------------------ persistent shell (M03.1)
# Main is the persistent runtime shell: it owns the Player, the FollowCamera
# and the HUD (one of each, as direct children); an area (the Meadow) is
# world content only and owns none of them.
import hashlib
MAIN_SCENE, MEADOW_SCENE = "scenes/Main.tscn", "scenes/world/Meadow.tscn"
SHELL = {"Player": "scenes/player/Player.tscn", "FollowCamera": "scenes/camera/FollowCamera.tscn", "HUD": "scenes/ui/HUD.tscn"}
def expand(scene, prefix="", depth=0):
    """Every node of a scene with instanced scenes expanded: (path, type, instanced scene or None)."""
    out = []
    if depth > 12 or not os.path.exists(scene): return out
    _, secs, ext, _ = load_scene_info(scene)
    for k, a, b in secs:
        if k != "node": continue
        name = a["name"].strip('"'); par = a.get("parent", None)
        par = par.strip('"') if par is not None else None
        rel = "." if par is None else (name if par == "." else par + "/" + name)
        full = prefix if rel == "." else (f"{prefix}/{rel}" if prefix else rel)
        inst = None
        if "instance" in a:
            inst = script_for_ext(ext, re.search(r'ExtResource\("([^"]+)"\)', a["instance"]).group(1))
            inner = expand(inst, full, depth + 1)
            root_type = inner[0][1] if inner else ""
            out.append((full or ".", root_type, inst)); out.extend(inner[1:])
        else:
            out.append((full or ".", a.get("type", "").strip('"'), None))
    return out
main_cfg = re.search(r'^run/main_scene="res://([^"]+)"', cfg, re.M)
if not main_cfg or main_cfg.group(1) != MAIN_SCENE:
    err(f"project.godot: the startup scene must be res://{MAIN_SCENE} (found {main_cfg.group(1) if main_cfg else None})")
if not os.path.exists(MAIN_SCENE):
    err(f"{MAIN_SCENE} missing")
else:
    main_tree = expand(MAIN_SCENE)
    for name, scene in SHELL.items():
        where = [pth for pth, _, inst in main_tree if inst == scene]
        if where != [name]:
            err(f"{MAIN_SCENE}: exactly one {name} ({scene}), owned directly by Main (found at {where})")
    cams = [pth for pth, t, _ in main_tree if t == "Camera3D"]
    if len(cams) != 1 or not cams[0].startswith("FollowCamera/"):
        err(f"{MAIN_SCENE}: exactly one Camera3D, inside the FollowCamera (found {cams})")
    if [pth for pth, t, _ in main_tree if t in ("SubViewport", "Viewport")]:
        err(f"{MAIN_SCENE}: no SubViewport — the player's navigation agent and the area's navigation mesh share one World3D")
    areas = [pth for pth, _, inst in main_tree if inst == MEADOW_SCENE]
    main_src = open(MAIN_SCENE, encoding="utf-8").read()
    if areas != ["Meadow"] or re.search(r'\[node name="Meadow"[^\n]*\]\n(position|transform|rotation|scale)', main_src):
        err(f"{MAIN_SCENE}: the Meadow is instanced once, directly under Main, at the origin (world coordinates unchanged)")
meadow_tree = expand(MEADOW_SCENE)
for pth, t, inst in meadow_tree:
    if inst in SHELL.values() or t == "Camera3D" or t == "CanvasLayer" or inst == "scenes/ui/VirtualJoystick.tscn":
        err(f"{MEADOW_SCENE}: {pth} — an area must not own the persistent Player/Camera/HUD")
MAIN_GD, MEADOW_GD = "scripts/main.gd", "scripts/world/meadow.gd"
mready = func_body(scripts.get(MAIN_GD, ""), "_ready") or ""
if not re.search(r"follow_camera\.target = player\s*_apply_camera_bounds\(\)\s*follow_camera\.snap_to_target\(\)\s*area\.attach_player\(player\)", mready):
    err(f"{MAIN_GD}: _ready() must point the camera at the player and hand the player to the area")
mcode = code_only(scripts.get(MEADOW_GD, ""))
if re.search(r"\$(Player|FollowCamera|HUD)\b|\bFollowCamera\b|\bHUD\b", mcode) or \
   "world_simulation.configure(player, directional_light, world_environment)" not in (func_body(scripts.get(MEADOW_GD, ""), "attach_player") or ""):
    err(f"{MEADOW_GD}: the area owns no shell node and gets the player only through attach_player()")
NAV_PINS = {"geometry_parsed_geometry_type": "1", "geometry_source_geometry_mode": "1", "geometry_source_group_name": '&"navigation_source"',
            "cell_size": "0.25", "cell_height": "0.25", "agent_height": "1.3", "agent_radius": "0.35", "agent_max_climb": "0.25", "agent_max_slope": "37.0"}
mead = open(MEADOW_SCENE, encoding="utf-8").read()
navm = re.search(r'\[sub_resource type="NavigationMesh"[^\]]*\]\n(.*?)\n\n', mead, re.S)
navsettings = dict(re.findall(r"^(\w+) = (.+)$", navm.group(1), re.M)) if navm else {}
if navsettings != NAV_PINS or not re.search(r'\[node name="Meadow" type="Node3D" groups=\["navigation_source"\]\]', mead) \
   or not re.search(r'\[node name="NavigationRegion3D" type="NavigationRegion3D" parent="\."\]', mead) \
   or "NavigationAgent3D" not in open(SHELL["Player"], encoding="utf-8").read() or "_bake_navigation()" not in (func_body(scripts.get(MEADOW_GD, ""), "_ready") or ""):
    err("navigation: the Meadow keeps its NavigationRegion3D (settings unchanged, baked at load from the navigation_source group); the Player keeps its NavigationAgent3D")
# M04.3 (O-14) added Inventory: after DiscoveryManager (it connects to it), before FarmManager and GameState.
# M05.1 (D-20) added Wallet (coins + ledger), before SaveManager and GameState (which loads the save).
AUTOLOADS = ["PointsManager", "DiscoveryDatabase", "DiscoveryManager", "JournalManager", "CollectionManager", "DailyDiscoveryManager",
             "Inventory", "Wallet", "FarmManager", "ExplorationManager", "AmbientAudioManager", "SaveManager", "GameState", "InputManager"]
found_al = re.findall(r'^(\w+)="\*?res://', re.search(r"\[autoload\]\n(.*?)(?:\n\[|\Z)", cfg, re.S).group(1), re.M)
if found_al != AUTOLOADS:
    err(f"project.godot: autoloads changed {found_al} — adding one is a documented decision, never a side effect")
# Deliberate-change pins: files a milestone promised not to touch. Changing
# one is allowed only on purpose — update its pin in the same commit and
# say why in the plan.
PINNED = {"scripts/player/player.gd": "8a99e3acb0095f27", "scripts/autoload/input_manager.gd": "23c5bb6ebab73164",
          "scripts/camera/follow_camera.gd": "b76efe265c7b2004", "scenes/camera/FollowCamera.tscn": "c6b25f3568d7b59a",
          "scenes/player/Player.tscn": "815b6bcf1df69d36", "scenes/ui/HUD.tscn": "e58d6f3099f3e9f4",
          # M03.2 must not pull M03.3 forward: farm, save and game-state code untouched.
          # (HUD.tscn re-pinned deliberately by M04.5: Inventory button + screen.)
          # (FarmManager and SaveManager re-pinned deliberately by M04.2: seeds/basket -> ItemStore, save v2;
          #  and by M04.3: the store moves to the Inventory autoload, save v3;
          #  SaveManager by M05.1: the wallet section, save v4; by M05.2: the exploration section, save v5.)
          "scripts/autoload/farm_manager.gd": "794080fbd0bfa2f1", "scripts/farming/farm_plot.gd": "f0204855a7da7b37",
          "scripts/autoload/save_manager.gd": "91db55e6a093d2ea", "scripts/autoload/game_state.gd": "e0f2dcfc7f642d83",
          # M03.3 persists farm plots only: discovery respawns, environmental events and time of day stay as they were.
          # (discovery_spawn_point.gd re-pinned deliberately by M05.3: a claimed once-ever discovery isn't spawned;
          #  farm_manager.gd by M05.3: milestone bonuses from reward data.)
          "scripts/interactables/discovery_spawn_point.gd": "1956d72184b1d590",
          "scripts/world_simulation/environmental_event.gd": "5945221474b886f2",
          "scripts/world_simulation/time_of_day.gd": "4faf06b101abc1ef"}
for f, h in PINNED.items():
    got = hashlib.sha256(open(f, "rb").read()).hexdigest()[:16] if os.path.exists(f) else None
    if got != h:
        err(f"{f}: changed (sha256 {got}, pinned {h}) — if deliberate, update the pin in tools/check_project.py and record why")
notes.append(f"persistent shell: Main owns {sorted(SHELL)}; startup {MAIN_SCENE}; {len(PINNED)} pinned files; {len(AUTOLOADS)} autoloads")

# ------------------------------------------------------------ area loader (M03.2)
# Infrastructure only: Main.load_area(scene, entry_id) swaps the area,
# deferred, freeing the old one before the new one registers, and places the
# player on a named AreaEntry. Nothing in the game calls it yet.
ENTRY_GD = "scripts/world/area_entry.gd"
es = scripts.get(ENTRY_GD, "")
if not re.search(r"^extends Marker3D\s*\nclass_name AreaEntry", es, re.M) or \
   not re.search(r"func _enter_tree\(\) -> void:\s*add_to_group\(GROUP\)", es) or 'const GROUP := &"area_entry"' not in es:
    err(f"{ENTRY_GD}: AreaEntry is a Marker3D that joins the area_entry group")
entry_scenes = {}
for path in glob.glob("**/*.tscn", recursive=True):
    if path.startswith((".godot", "tools/")): continue
    s2, secs, ext, _ = load_scene_info(path)
    for k, a, b in secs:
        m = re.search(r'^script = ExtResource\("([^"]+)"\)', b, re.M)
        if k == "node" and m and script_for_ext(ext, m.group(1)) == ENTRY_GD:
            eid = re.search(r'^entry_id = "([^"]*)"', b, re.M)
            pos = re.search(r"^position = Vector3\(([^)]*)\)", b, re.M)
            entry_scenes.setdefault(path, []).append((eid.group(1) if eid else "", pos.group(1).replace(" ", "") if pos else "0,0,0"))
for path, entries in entry_scenes.items():
    ids = [e for e, _ in entries]
    for e in ids:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", e):
            err(f"{path}: AreaEntry id '{e}' must be a non-empty lower_snake_case id")
    if len(set(ids)) != len(ids):
        err(f"{path}: duplicate AreaEntry ids {ids}")
if not entry_scenes.get(MEADOW_SCENE):
    err(f"{MEADOW_SCENE}: an area needs at least one AreaEntry")
boot_player = re.search(r'\[node name="Player" parent="\." [^\n]*\]\nposition = Vector3\(([^)]*)\)', open(MAIN_SCENE, encoding="utf-8").read())
if ("meadow_start", boot_player.group(1).replace(" ", "") if boot_player else None) not in entry_scenes.get(MEADOW_SCENE, []):
    err(f"{MEADOW_SCENE}: the 'meadow_start' entry must sit exactly where Main boots the player (boot unchanged)")
main_src = scripts.get(MAIN_GD, "")
la = func_body(main_src, "load_area") or ""
if not re.search(r"_swap_area\.call_deferred\(scene, entry_id\)", la) or re.search(r"remove_child|free\(|add_child|place_at", la):
    err(f"{MAIN_GD}: load_area() only defers the swap (never runs inside the unloading area's callback)")
sw = code_only(func_body(main_src, "_swap_area") or "")
order = ["FarmManager.cancel_seed_choice()", "FarmManager.release_plots_in(old)", "remove_child(old)", "old.free()", "add_child(area)", "move_child(area, 0)",
         "area.attach_player(player)", "_find_entry(area, entry_id)", "player.place_at(entry.global_transform)", "_apply_camera_bounds()", "follow_camera.snap_to_target()"]
idx = [sw.find(k) for k in order]
if -1 in idx or idx != sorted(idx) or re.search(r"queue_free|await|call_deferred", sw):
    err(f"{MAIN_GD}: _swap_area() must cancel the picker, capture the old area's plots, remove and free() it, then add (first), attach, place and snap — no queue_free/await")
fe = code_only(func_body(main_src, "_find_entry") or "")
if not all(k in fe for k in ("get_nodes_in_group(AreaEntry.GROUP)", "in_area.is_ancestor_of(entry)", "entry.entry_id == entry_id", "entry.entry_id < first.entry_id")):
    err(f"{MAIN_GD}: _find_entry() picks the named entry of this area, else the lowest id (deterministic)")
callers = [f for f, s2 in scripts.items() if f != MAIN_GD and re.search(r"\bload_area\(|_swap_area", code_only(s2))]
if callers or len(re.findall(r"\b_swap_area\b", code_only(main_src))) != 2:
    err(f"the area loader is infrastructure only — nothing in the game calls it yet (found {callers})")
for path in glob.glob("**/*.tscn", recursive=True):
    if "load_area" in open(path, encoding="utf-8").read():
        err(f"{path}: connects to load_area — no player-facing transition before M08.1")
actions = sorted(re.findall(r"^(\w+)=\{", re.search(r"\[input\]\n(.*?)(?:\n\[|\Z)", cfg, re.S).group(1), re.M)) if "[input]" in cfg else []
if actions != ["move_down", "move_left", "move_right", "move_up"]:
    err(f"project.godot: input actions changed {actions} — no new (debug) actions")
pa = code_only(func_body(pl_src, "place_at") or "")
if not re.search(r"func place_at\(spot: Transform3D\) -> void:\s*_stop_navigation\(\)\s*velocity = Vector3\.ZERO\s*global_position = spot\.origin", pa) \
   or not re.search(r"if forward\.length\(\) < FACE_TARGET_MIN_DISTANCE:\s*return.*_facing_angle = atan2\(forward\.x, -forward\.z\)", pa, re.S) \
   or re.search(r"\bAreaEntry\b|MeadowArea|\bMain\b|InputManager|_interact_with|interact\(|await|\bis\s+[A-Z]", pa):
    err(f"{PL}: place_at() stays minimal and generic: stop the walk, zero velocity, set position, face the spot's forward")
pa_callers = [f for f, s2 in scripts.items() if f not in (PL,) and re.search(r"\.place_at\(", code_only(s2))]
if pa_callers != [MAIN_GD]:
    err(f"Player.place_at() is called only by Main's area loader (found {pa_callers})")
used = set(re.findall(r"\bplayer\.(\w+)", code_only(main_src)))
if used - {"global_position", "global_transform", "place_at"}:
    err(f"{MAIN_GD}: Main uses only Player.place_at() and its transform — never Player internals (found {sorted(used)})")
for f, s2 in scripts.items():
    if f != PL and re.search(r"\bplayer\._\w+", code_only(s2)):
        err(f"{f}: reaches into Player's private members")
# ------------------------------------------------------------ camera bounds per area (M03.4)
# Each area owns one AreaCameraBounds (an X/Z rectangle); Main hands it to
# the persistent FollowCamera whenever an area loads (replacing or clearing
# the previous area's); the camera clamps the point it follows — no area
# knowledge, no hard-coded sizes, no per-frame lookups.
CB_GD, CAM_GD = "scripts/world/area_camera_bounds.gd", "scripts/camera/follow_camera.gd"
cbs, cam_src = scripts.get(CB_GD, ""), scripts.get(CAM_GD, "")
if not re.search(r"^extends Node3D\s*\nclass_name AreaCameraBounds", cbs, re.M) or 'const GROUP := &"area_camera_bounds"' not in cbs \
   or not re.search(r"func _enter_tree\(\) -> void:\s*add_to_group\(GROUP\)", cbs) or "@export var size: Vector2 = Vector2.ZERO" not in cbs \
   or "return Rect2(Vector2(global_position.x, global_position.z) - size * 0.5, size)" not in cbs:
    err(f"{CB_GD}: AreaCameraBounds is a Node3D in the area_camera_bounds group: an X/Z rectangle centred on it, no default size")
bounds_nodes = {}
for path in glob.glob("**/*.tscn", recursive=True):
    if path.startswith((".godot", "tools/")): continue
    _, secs, ext, _ = load_scene_info(path)
    for k, a, b in secs:
        m = re.search(r'^script = ExtResource\("([^"]+)"\)', b, re.M)
        if k == "node" and m and script_for_ext(ext, m.group(1)) == CB_GD:
            bounds_nodes.setdefault(path, []).append((a.get("parent", "").strip('"'), b))
if list(bounds_nodes) != [MEADOW_SCENE] or len(bounds_nodes[MEADOW_SCENE]) != 1:
    err(f"camera bounds: exactly one AreaCameraBounds, in the area (found {[(p, len(v)) for p, v in bounds_nodes.items()]}) — never in Main")
else:
    par, body = bounds_nodes[MEADOW_SCENE][0]
    size = re.search(r"^size = Vector2\(([^)]*)\)", body, re.M)
    ground = re.search(r'\[sub_resource type="PlaneMesh" id="PlaneMesh_ground"\]\nsize = Vector2\(([^)]*)\)', mead := open(MEADOW_SCENE, encoding="utf-8").read())
    if par != "." or re.search(r"^(position|transform|rotation|rotation_degrees|scale) = ", body, re.M) or not size or not ground \
       or size.group(1).replace(" ", "") != ground.group(1).replace(" ", "") \
       or re.search(r'\[node name="(Terrain|Ground)"[^\n]*\]\n(position|transform)', mead):
        err(f"{MEADOW_SCENE}: the Meadow's camera bounds are its ground plane — at the origin, unrotated, the PlaneMesh_ground size")
if re.search(r"\bMeadow|AreaCameraBounds|get_nodes_in_group|get_tree\(|\b(32|64)(\.0)?\b", code_only(cam_src)):
    err(f"{CAM_GD}: the camera knows no area — no Meadow sizes, no lookups; bounds come only from set_bounds()")
cpp = code_only(func_body(cam_src, "_physics_process") or "")
if "var desired_position := _clamp_to_bounds(target_position + look_ahead)" not in cpp or \
   re.search(r"get_node|get_nodes_in_group|find_|_bounds\s*=|_has_bounds\s*=", cpp):
    err(f"{CAM_GD}: _physics_process() clamps the followed point with the stored bounds and never looks them up")
CAM_BEHAVIOUR = ["var velocity_estimate := (target_position - _last_target_position) / maxf(delta, 0.0001)",
                 "var speed_ratio := clampf(horizontal_speed / look_ahead_speed_reference, 0.0, 1.0)",
                 "if horizontal_speed > 0.15:",
                 "look_ahead = Vector3(velocity_estimate.x, 0.0, velocity_estimate.z).normalized() * look_ahead_distance * speed_ratio",
                 "var smoothing := 1.0 - exp(-follow_speed * delta)",
                 "global_position = global_position.lerp(desired_position, smoothing)",
                 "_camera.fov = lerp(_camera.fov, base_fov + speed_ratio * fov_boost, fov_smoothing)"]
missing_cam = [ln for ln in CAM_BEHAVIOUR if ln not in cpp]
if missing_cam:
    err(f"{CAM_GD}: the camera's follow/look-ahead/smoothing/FOV behaviour must stay as it was (changed: {missing_cam})")
if not re.search(r"point\.x = clampf\(point\.x, _bounds\.position\.x, _bounds\.end\.x\)\s*point\.z = clampf\(point\.z, _bounds\.position\.y, _bounds\.end\.y\)",
                 func_body(cam_src, "_clamp_to_bounds") or "") or "if not _has_bounds:" not in (func_body(cam_src, "_clamp_to_bounds") or ""):
    err(f"{CAM_GD}: _clamp_to_bounds() keeps X in [min.x, max.x] and Z in [min.y, max.y]")
if not re.search(r"global_position = _clamp_to_bounds\(target\.global_position\)\s*_has_last_position = false", func_body(cam_src, "snap_to_target") or ""):
    err(f"{CAM_GD}: snap_to_target() jumps onto the target inside the bounds")
writers = sorted(fn for fn in re.findall(r"^func (\w+)\(", cam_src, re.M) if re.search(r"_has_bounds = |_bounds = ", func_body(cam_src, fn) or ""))
if writers != ["clear_bounds", "set_bounds"]:
    err(f"{CAM_GD}: bounds are set only by set_bounds()/clear_bounds() (found {writers})")
acb = code_only(func_body(main_src, "_apply_camera_bounds") or "")
if not re.search(r"var bounds := _find_camera_bounds\(area\)\s*if bounds != null:\s*follow_camera\.set_bounds\(bounds\.get_rect\(\)\)\s*else:\s*follow_camera\.clear_bounds\(\)", acb):
    err(f"{MAIN_GD}: _apply_camera_bounds() gives the camera the current area's bounds, or clears them")
fcb = code_only(func_body(main_src, "_find_camera_bounds") or "")
if not all(k in fcb for k in ("get_nodes_in_group(AreaCameraBounds.GROUP)", "in_area.is_ancestor_of(bounds)")):
    err(f"{MAIN_GD}: _find_camera_bounds() looks only inside the given area")
bcallers = sorted(fn for fn in re.findall(r"^func (\w+)\(", main_src, re.M)
                  if fn != "_apply_camera_bounds" and "_apply_camera_bounds()" in code_only(func_body(main_src, fn) or ""))
if bcallers != ["_ready", "_swap_area"] or [f for f, s2 in scripts.items() if f not in (MAIN_GD, CAM_GD) and re.search(r"\.(set_bounds|clear_bounds|snap_to_target)\(", code_only(s2))]:
    err(f"camera bounds are applied only by Main, at start and on every area swap (found {bcallers})")
notes.append("camera bounds: one AreaCameraBounds per area, applied by Main on load")

# ------------------------------------------------------------ pinch / wheel zoom (M03.5)
# One zoom path: InputManager turns a two-finger pinch or a mouse-wheel
# notch into zoom_requested(factor); Main connects it once to
# FollowCamera.zoom_by(); set_zoom_distance() is the only writer of the
# spring arm's length and clamps it. Two fingers on the world never tap.
def _hash_body(src, n):
    m = re.search(rf"^func {n}\(.*?(?=^func |^## |\Z)", src, re.M | re.S)
    return hashlib.sha256(m.group(0).strip().encode()).hexdigest()[:12] if m else None
TAP_ROUTING = {"_track_tap": "f5463beadc8c", "_handle_tap": "2250c9598daa", "_is_player_tap": "af8f36edd1df",
               "_interactable_near": "d7b7f30b456b", "_tap_distance": "92f36e7bb53a", "_walkable_point": "f4cb1a094bae",
               "_find_interactable": "25ab3beea88c"}
changed_routing = [n for n, h in TAP_ROUTING.items() if _hash_body(im_src, n) != h]
if changed_routing:
    err(f"{IM}: tap routing changed {changed_routing} — M03.5 may add zoom but never alter how taps are routed")
zmin, zmax = const_val(cam_src, "ZOOM_MIN_DISTANCE"), const_val(cam_src, "ZOOM_MAX_DISTANCE")
arm = re.search(r'\[node name="SpringArm3D"[^\]]*\][^\[]*?spring_length = ([0-9.]+)', open("scenes/camera/FollowCamera.tscn", encoding="utf-8").read())
if zmin is None or zmax is None or not (0 < zmin < zmax) or not arm or not (zmin <= float(arm.group(1)) <= zmax):
    err(f"{CAM_GD}: explicit zoom limits ZOOM_MIN_DISTANCE < ZOOM_MAX_DISTANCE around the scene's spring_length ({zmin}, {zmax}, {arm.group(1) if arm else None})")
if "_spring_arm.spring_length = clampf(distance, ZOOM_MIN_DISTANCE, ZOOM_MAX_DISTANCE)" not in (func_body(cam_src, "set_zoom_distance") or ""):
    err(f"{CAM_GD}: set_zoom_distance() clamps to [ZOOM_MIN_DISTANCE, ZOOM_MAX_DISTANCE]")
zb = code_only(func_body(cam_src, "zoom_by") or "")
if not re.search(r"if _spring_arm == null or not is_finite\(factor\) or factor <= 0\.0:\s*return\s*set_zoom_distance\(_spring_arm\.spring_length \* factor\)", zb):
    err(f"{CAM_GD}: zoom_by() scales the distance by a valid factor through set_zoom_distance()")
arm_writers = sorted({(f, fn) for f, s2 in scripts.items() for fn in re.findall(r"^func (\w+)\(", s2, re.M)
                      if re.search(r"spring_length\s*=[^=]|\.set_length\(|\bspring_length\s*[-+*/]=", code_only(func_body(s2, fn) or ""))})
if arm_writers != [(CAM_GD, "set_zoom_distance")]:
    err(f"the camera distance is written only by FollowCamera.set_zoom_distance() (found {arm_writers})")
if re.search(r"spring_length|zoom|ZOOM", code_only(func_body(cam_src, "_physics_process") or "")):
    err(f"{CAM_GD}: no zoom work per frame — zoom changes only on input")
zem = [(f, len(re.findall(r"zoom_requested\.emit\(", code_only(s2)))) for f, s2 in scripts.items()]
zem = [z for z in zem if z[1]]
if zem != [(IM, 2)]:
    err(f"zoom_requested is emitted only by InputManager's pinch and wheel paths (found {zem})")
zcalls = [(f, n) for f, s2 in scripts.items() for n in re.findall(r"\.(zoom_by|set_zoom_distance)\b", code_only(s2)) if f != CAM_GD]
if zcalls != [(MAIN_GD, "zoom_by")] or "InputManager.zoom_requested.connect(follow_camera.zoom_by)" not in (func_body(main_src, "_ready") or "") \
   or code_only(main_src).count("zoom_requested.connect") != 1:
    err(f"Main connects InputManager.zoom_requested to FollowCamera.zoom_by once, in _ready (found {zcalls})")
ui = code_only(func_body(im_src, "_unhandled_input") or "")
if not re.search(r"_track_touch\(touch\.index, touch\.pressed, touch\.position\)\s*if _world_touches\.size\(\) >= 2:\s*.*?_tap_starts\.clear\(\)\s*return\s*_track_tap\(touch\.index", ui, re.S):
    err(f"{IM}: with two fingers on the world no touch is a tap (tap candidates cleared before any tap tracking)")
wb = re.search(r"elif event is InputEventMouseButton and _is_wheel\(event as InputEventMouseButton\):(.*?)elif event is InputEventMouseButton and not _mouse_emulates_touch:", ui, re.S)
if not wb or not re.search(r"if wheel\.pressed:\s*zoom_requested\.emit\(1\.0 / WHEEL_ZOOM_STEP if wheel\.button_index == MOUSE_BUTTON_WHEEL_UP else WHEEL_ZOOM_STEP\)", wb.group(1)) \
   or "_track_tap" in wb.group(1) or not (const_val(im_src, "WHEEL_ZOOM_STEP") or 0) > 1.0:
    err(f"{IM}: the wheel (before clicks) zooms on press only: up = closer, down = farther, never a tap")
if not re.search(r"MOUSE_BUTTON_WHEEL_UP or event\.button_index == MOUSE_BUTTON_WHEEL_DOWN", func_body(im_src, "_is_wheel") or ""):
    err(f"{IM}: _is_wheel() recognises both wheel directions")
tp = code_only(func_body(im_src, "_track_pinch") or "")
if not re.search(r"if not _world_touches\.has\(index\):\s*return", tp) or "zoom_requested.emit(_pinch_distance / distance)" not in tp \
   or not re.search(r"if _pinch_distance > 0\.0 and distance > 0\.0:", tp) or not tp.rstrip().endswith("_pinch_distance = distance"):
    err(f"{IM}: a pinch emits old/new finger distance (apart = closer) from tracked world fingers only")
if "if _world_touches.size() != 2:" not in (func_body(im_src, "_two_finger_distance") or "") or \
   not re.search(r"_world_touches\.erase\(index\)\s*_pinch_distance = _two_finger_distance\(\)", func_body(im_src, "_track_touch") or ""):
    err(f"{IM}: only exactly two fingers pinch, and every finger change restarts the pinch (no jumps)")
if re.search(r"^func _(unhandled_)?input\(|^func _gui_input\(|InputEvent", cam_src, re.M):
    err(f"{CAM_GD}: the camera reads no input — zoom reaches it only through zoom_by()")
for f, s2 in scripts.items():
    if f != IM and re.search(r"InputEventMagnifyGesture|InputEventPanGesture|MOUSE_BUTTON_WHEEL", code_only(s2)):
        err(f"{f}: zoom gestures and the wheel are read only by InputManager (one zoom path)")
fov_writers = [(f, fn) for f, s2 in scripts.items() for fn in re.findall(r"^func (\w+)\(", s2, re.M)
               if re.search(r"\.fov\s*[-+*/]?=[^=]", code_only(func_body(s2, fn) or ""))]
if fov_writers != [(CAM_GD, "_physics_process")]:
    err(f"the camera's FOV is written only by its existing speed widening (found {fov_writers}) — zoom is the arm length")
notes.append(f"zoom: [{zmin}, {zmax}] m around {arm.group(1) if arm else '?'} m; one path (pinch + wheel -> zoom_requested -> zoom_by)")

# ------------------------------------------------------------ farm across area reload (M03.3)
# Plots are captured by stable id just before their area unloads and
# restored when their next instance registers — never recounted, never
# lost from a save made in between.
FM, FP = "scripts/autoload/farm_manager.gd", "scripts/farming/farm_plot.gd"
fm_src, fp_src = scripts.get(FM, ""), scripts.get(FP, "")
rel = code_only(func_body(fm_src, "release_plots_in") or "")
if not re.search(r"for plot_id: String in _plots\.keys\(\):\s*var plot := _get_plot\(plot_id\)\s*if plot == null:\s*_plots\.erase\(plot_id\)"
                 r"\s*elif area\.is_ancestor_of\(plot\):\s*_unloaded_plot_states\[plot_id\] = plot\.capture\(\)\s*_plots\.erase\(plot_id\)", rel):
    err(f"{FM}: release_plots_in() captures every plot of the area by id and forgets every old reference")
rp = code_only(func_body(fm_src, "register_plot") or "")
un = re.search(r"if _unloaded_plot_states\.has\(plot\.plot_id\):(.*?)\breturn\b", rp, re.S)
if not un or rp.find("_plots[plot.plot_id] = plot") > un.start() or un.start() > rp.find("if _saved_plot_states.has(") \
   or "_unloaded_plot_states.erase(plot.plot_id)" not in un.group(1) or "_ready_by_crop" in un.group(1) \
   or not re.search(r'var kept: Dictionary = _unloaded_plot_states\[plot\.plot_id\].*plot\.restore\(kept, _find_crop\(String\(kept\.get\("crop", ""\)\)\)\)', un.group(1), re.S):
    err(f"{FM}: register_plot() tracks the plot, then restores an unloaded state once (erased, not recounted) before the boot-save path")
gs = code_only(func_body(fm_src, "get_save_data") or "")
if not re.search(r"plots\.merge\(_unloaded_plot_states\.duplicate\(true\), true\)\s*for plot_id: String in _plots:", gs):
    err(f"{FM}: get_save_data() must include unloaded plot states (live captures win)")
if "_unloaded_plot_states.clear()" not in (func_body(fm_src, "apply_save_data") or ""):
    err(f"{FM}: apply_save_data() starts with no unloaded states")
users = sorted(fn for fn in re.findall(r"^func (\w+)\(", fm_src, re.M) if "_unloaded_plot_states" in code_only(func_body(fm_src, fn) or ""))
if users != ["apply_save_data", "get_save_data", "register_plot", "release_plots_in"]:
    err(f"{FM}: unloaded plot states are touched only by release/register/save/load (found {users})")
if re.search(r"FarmManager\.(apply_save_data|get_save_data)|\.restore\(|\.capture\(", code_only(main_src)):
    err(f"{MAIN_GD}: Main never restores farm state itself — plots restore when they register in the new area")
cap = func_body(fp_src, "capture") or ""
res = func_body(fp_src, "restore") or ""
cap_keys = set(re.findall(r'"(\w+)":', cap))
read_keys = set(re.findall(r'data\.get\("(\w+)"', res)) | set(re.findall(r'(?:kept|data)\.get\("(\w+)"', func_body(fm_src, "register_plot") or ""))
FARM_FIELDS = {"state", "soil_memory", "crop", "stage", "needs_water", "stage_time_left", "soil", "care", "quality",
               "longest_thirst", "thirsty_for"}
if FARM_FIELDS - cap_keys:
    err(f"{FP}: capture() dropped farm fields {sorted(FARM_FIELDS - cap_keys)} — every field the save supports survives a reload")
if not cap_keys or cap_keys - read_keys:
    err(f"{FP}: restore() must read back every field capture() saves (missing {sorted(cap_keys - read_keys)})")
notes.append(f"area loader: entries {entry_scenes}")

# ------------------------------------------------------------ place data (M03.6, A5)
# Places are PlaceDefinition resources in data/places/ (like discoveries and
# crops); ExplorationManager loads them; no place id, name or pairing lives
# in a script, and the data agrees with the areas' landmarks and the crops.
PLACE_GD, EXPLO = "scripts/world_simulation/place_definition.gd", "scripts/autoload/exploration_manager.gd"
pd = scripts.get(PLACE_GD, "")
PLACE_FIELDS = {"id": "String", "display_name": "String", "arrival_text": "String", "order": "int", "secret": "bool",
                "garden": "bool", "curiosity_discovery_id": "String"}
if not re.search(r"^extends Resource\s*\nclass_name PlaceDefinition", pd, re.M) or \
   dict(re.findall(r"^@export var (\w+): (\w+)", pd, re.M)) != PLACE_FIELDS:
    err(f"{PLACE_GD}: PlaceDefinition is a Resource with exactly {sorted(PLACE_FIELDS)}")
places = {}
for f in sorted(glob.glob("data/places/*.tres")):
    txt = open(f, encoding="utf-8").read()
    if 'path="res://scripts/world_simulation/place_definition.gd"' not in txt or 'script_class="PlaceDefinition"' not in txt:
        err(f"{f}: not a PlaceDefinition resource"); continue
    vals = dict(re.findall(r'^(\w+) = (.+)$', txt.split("[resource]", 1)[1], re.M))
    pid = vals.get("id", '""').strip('"')
    if not re.fullmatch(r"[a-z][a-z0-9_]*", pid) or os.path.basename(f) != pid + ".tres":
        err(f"{f}: place id '{pid}' must be lower_snake_case and match the file name")
    if pid in places:
        err(f"{f}: duplicate place id '{pid}'")
    places[pid] = {"name": vals.get("display_name", '""').strip('"'), "arrival": vals.get("arrival_text", '""').strip('"'),
                   "order": int(vals.get("order", "0")), "secret": vals.get("secret") == "true", "garden": vals.get("garden") == "true",
                   "curiosity": vals.get("curiosity_discovery_id", '""').strip('"')}
    if not places[pid]["name"]:
        err(f"{f}: a place needs a display_name")
if not places:
    err("data/places: no place definitions")
orders = [p["order"] for p in places.values()]
if len(set(orders)) != len(orders):
    err(f"data/places: order values must be unique ({sorted(orders)})")
if sum(p["garden"] for p in places.values()) != 1:
    err("data/places: exactly one place is the garden")
disc_ids = {re.search(r'^id = "([^"]+)"', open(f, encoding="utf-8").read(), re.M).group(1) for f in glob.glob("data/discoveries/*.tres")}
for pid, p in places.items():
    if p["curiosity"] and p["curiosity"] not in disc_ids:
        err(f"data/places/{pid}.tres: curiosity discovery '{p['curiosity']}' does not exist")
landmarks = {}
for path in glob.glob("scenes/**/*.tscn", recursive=True):
    for lid, kind in re.findall(r'location_id = "(\w+)"\nkind = (\d)', open(path, encoding="utf-8").read()):
        if lid in landmarks:
            err(f"{path}: two landmarks for place '{lid}'")
        landmarks[lid] = kind == "1"
if set(landmarks) != set(places):
    err(f"places and landmarks must match one to one (no landmark: {sorted(set(places) - set(landmarks))}, no place: {sorted(set(landmarks) - set(places))})")
for pid in set(landmarks) & set(places):
    if landmarks[pid] != places[pid]["secret"]:
        err(f"data/places/{pid}.tres: secret = {places[pid]['secret']} but its landmark kind says {landmarks[pid]}")
for f in glob.glob("data/crops/*.tres"):
    txt = open(f, encoding="utf-8").read()
    if 'found_seed_source = "place"' in txt:
        src = re.search(r'found_seed_source_id = "([^"]+)"', txt)
        if not src or src.group(1) not in places:
            err(f"{f}: found-seed place '{src.group(1) if src else ''}' is not a place in data/places")
ex = scripts.get(EXPLO, "")
lp = code_only(func_body(ex, "_load_places") or "")
if 'const PLACES_PATH := "res://data/places/"' not in ex or "ResourceDirectory.list_tres_paths(PLACES_PATH)" not in lp \
   or "return a.order < b.order" not in lp or "_load_places()" not in (func_body(ex, "_ready") or ""):
    err(f"{EXPLO}: places come from data/places/ (ResourceDirectory), ordered by PlaceDefinition.order, loaded at startup")
if not re.search(r"_secret_place_count > 0 and _found_secret_locations\.size\(\) >= _secret_place_count", ex):
    err(f"{EXPLO}: 'every secret found' counts the secret places in the data")
if "var paired_discovery_id := place.curiosity_discovery_id if place else \"\"" not in (func_body(ex, "_maybe_award_curiosity_bonus") or ""):
    err(f"{EXPLO}: the curiosity pairing comes from the place's data")
if not re.search(r'if place_id != "" and place_id == ExplorationManager\.get_garden_place_id\(\):', func_body(scripts.get(FM, ""), "notify_place_reached") or ""):
    err(f"{FM}: the garden is recognised by the place data's garden flag")
place_literals = {p for pid, v in places.items() for p in (pid, v["name"], v["arrival"]) if p}
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    code = code_only(s2)
    for lit in re.findall(r'"([^"]+)"', code):
        if lit in place_literals:
            err(f"{f}: place data '{lit}' hard-coded in a script — it belongs in data/places/")
    for m in re.finditer(r"\b(const PLACES\b|CURIOSITY_PAIRS|GARDEN_PLACE_ID)|_found_secret_locations\.size\(\) >= \d", code):
        err(f"{f}: '{m.group(0)}' — the old hard-coded place data must not return")
    for name in {v["name"] for v in places.values()}:
        if re.search(r'"[^"]*\b' + re.escape(name) + r'\b[^"]*"', code):
            err(f"{f}: place name '{name}' inside a script string — use ExplorationManager.get_place_display_name()")
notes.append(f"places: {len(places)} from data/places ({sum(p['secret'] for p in places.values())} secret, garden "
             f"{[k for k, v in places.items() if v['garden']]}), all matched to landmarks")

# ------------------------------------------------------------ items (M04.1, M04.2)
# Items are ItemDefinition resources in data/items/ (like crops, discoveries
# and places), loaded through ResourceDirectory. An ItemStore counts them by
# id, one count per quality level (quality is an attribute, D-18): only
# add()/remove()/apply_save_data() change counts; add/remove refuse unknown
# ids, levels and amounts below 1; remove() is all or nothing; loading drops
# malformed entries only with a warning. The player's store lives in the
# Inventory autoload (M04.3, O-14): the one source of truth for seeds, the
# basket and collectibles (one per discovery collected).
ITEM_GD, STORE = "scripts/items/item_definition.gd", "scripts/items/item_store.gd"
idf = scripts.get(ITEM_GD, "")
ITEM_FIELDS = {"id": "String", "display_name": "String", "category": "String", "crop_id": "String", "quality_levels": "int",
               "discovery_id": "String"}
ITEM_CATEGORIES = ["seed", "produce", "collectible"]
INV = "scripts/autoload/inventory.gd"
disc_names = {}
for f in glob.glob("data/discoveries/*.tres"):
    t = open(f, encoding="utf-8").read()
    disc_names[re.search(r'^id = "([^"]+)"', t, re.M).group(1)] = (re.search(r'^display_name = "([^"]*)"', t, re.M) or [None, ""])[1]
fm_src = scripts.get(FM, "")
qnames = re.search(r'^const QUALITY_NAMES := \[([^\]]*)\]', fm_src, re.M)
QUALITY_LEVELS = len(qnames.group(1).split(",")) if qnames else 0
item_fields = dict((m.group(1), m.group(2)) for m in re.finditer(r"^@export(?:_enum\([^)]*\))? var (\w+): (\w+)", idf, re.M))
cat_enum = re.search(r"^@export_enum\(([^)]*)\) var category: String = \"seed\"", idf, re.M)
if not re.search(r"^extends Resource\s*\nclass_name ItemDefinition", idf, re.M) or item_fields != ITEM_FIELDS \
   or not cat_enum or [c.strip().strip('"') for c in cat_enum.group(1).split(",")] != ITEM_CATEGORIES \
   or "@export var quality_levels: int = 1" not in idf or '@export var discovery_id: String = ""' not in idf:
    err(f"{ITEM_GD}: ItemDefinition is a Resource with exactly {sorted(ITEM_FIELDS)}, category one of {ITEM_CATEGORIES}, quality_levels default 1")
items = {}
for f in sorted(glob.glob("data/items/*.tres")):
    txt = open(f, encoding="utf-8").read()
    if f'path="res://{ITEM_GD}"' not in txt or 'script_class="ItemDefinition"' not in txt:
        err(f"{f}: not an ItemDefinition resource"); continue
    vals = dict(re.findall(r'^(\w+) = (.+)$', txt.split("[resource]", 1)[1], re.M))
    iid = vals.get("id", '""').strip('"')
    if not re.fullmatch(r"[a-z][a-z0-9_]*", iid) or os.path.basename(f) != iid + ".tres":
        err(f"{f}: item id '{iid}' must be lower_snake_case and match the file name")
    if iid in items:
        err(f"{f}: duplicate item id '{iid}'")
    items[iid] = {"name": vals.get("display_name", '""').strip('"'), "category": vals.get("category", '"seed"').strip('"'),
                  "crop": vals.get("crop_id", '""').strip('"'), "levels": int(vals.get("quality_levels", "1")),
                  "discovery": vals.get("discovery_id", '""').strip('"')}
    if not items[iid]["name"]:
        err(f"{f}: an item needs a display_name")
    if items[iid]["category"] not in ITEM_CATEGORIES:
        err(f"{f}: category '{items[iid]['category']}' is not one of {ITEM_CATEGORIES}")
    if items[iid]["category"] == "collectible":
        if items[iid]["crop"] or items[iid]["discovery"] not in disc_names:
            err(f"{f}: a collectible names an existing discovery (discovery_id '{items[iid]['discovery']}') and no crop")
        elif items[iid]["name"] != disc_names[items[iid]["discovery"]]:
            err(f"{f}: a collectible is called what its discovery is called ('{disc_names[items[iid]['discovery']]}')")
    elif items[iid]["crop"] not in crop_ids or items[iid]["discovery"]:
        err(f"{f}: crop_id '{items[iid]['crop']}' must be a crop in data/crops (and a seed/produce item names no discovery)")
    want_levels = QUALITY_LEVELS if items[iid]["category"] == "produce" else 1
    if items[iid]["levels"] != want_levels:
        err(f"{f}: quality_levels {items[iid]['levels']} — produce keeps FarmManager's {QUALITY_LEVELS} qualities, seeds none (1)")
if not items:
    err("data/items: no item definitions")
for did in sorted(disc_names):
    n = sum(1 for v in items.values() if v["category"] == "collectible" and v["discovery"] == did)
    if n > 1:
        err(f"data/items: discovery '{did}' has {n} collectible items — collecting it gives one item")
for cid in sorted(crop_ids):
    for cat in ("seed", "produce"):
        n = sum(1 for v in items.values() if v["crop"] == cid and v["category"] == cat)
        if n != 1:
            err(f"data/items: crop '{cid}' needs exactly one {cat} item (found {n})")
st = scripts.get(STORE, "")
st_funcs = {m.group(2): code_only(m.group(0)) for m in
            re.finditer(r"^(static )?func (\w+)\(.*?(?=^func |^static func |\Z)", st, re.M | re.S)}
ld = st_funcs.get("load_definitions", "")
if not re.search(r"^extends RefCounted\s*\nclass_name ItemStore", st, re.M) or 'const ITEMS_PATH := "res://data/items/"' not in st \
   or not st.count("static func load_definitions(") == 1 or "ResourceDirectory.list_tres_paths(ITEMS_PATH)" not in ld \
   or "as ItemDefinition" not in ld or 'definition == null or definition.id == "" or definition.quality_levels < 1' not in ld:
    err(f"{STORE}: ItemStore (a RefCounted) loads data/items/ through ResourceDirectory, skipping unusable files")
STORE_API = ["load_definitions", "crop_item_ids", "_init", "is_valid_item", "get_definition", "get_quantity", "has", "add", "remove",
             "get_save_data", "apply_save_data", "_accepts", "_counts_of", "_whole_counts"]
if list(st_funcs) != STORE_API:
    err(f"{STORE}: the store's API is exactly {STORE_API} (found {list(st_funcs)})")
QTY_WRITE = re.compile(r"\b_quantities\s*(\[[^\]]*\]\s*=[^=]|=[^=]|\.(erase|clear|merge|assign|make_read_only|sort)\b)")
DEF_WRITE = re.compile(r"\b_definitions\s*(\[[^\]]*\]\s*=[^=]|=[^=]|\.(erase|clear|merge|assign)\b)")
for fn, body in st_funcs.items():
    if QTY_WRITE.search(body) and fn not in ("add", "remove", "apply_save_data"):
        err(f"{STORE}: {fn}() changes a count — only add(), remove() and apply_save_data() may")
    if DEF_WRITE.search(body) and fn != "_init":
        err(f"{STORE}: {fn}() changes the known items — only _init() may")
fields_code = code_only(st.split("static func", 1)[0])
if re.findall(r"^var (\w+)", fields_code, re.M) != ["_definitions", "_quantities"]:
    err(f"{STORE}: the store's state is exactly _definitions and _quantities")
GUARD = r"if not _accepts\(item_id, quality\) or amount < 1:\s*push_warning\(.*?\)\n\s*return false\s*"
if not re.search(GUARD + r"var counts := _counts_of\(item_id\)\s*counts\[quality\] = int\(counts\[quality\]\) \+ amount\s*"
                 r"_quantities\[item_id\] = counts\s*return true\s*$", st_funcs.get("add", "")):
    err(f"{STORE}: add() refuses an unknown id or quality or an amount below 1, otherwise adds exactly that amount at that quality (no cap drops items)")
if not re.search(GUARD + r"if get_quantity\(item_id, quality\) < amount:\s*return false\s*var counts := _counts_of\(item_id\)\s*"
                 r"counts\[quality\] = int\(counts\[quality\]\) - amount\s*if counts\.max\(\) == 0:\s*_quantities\.erase\(item_id\)\s*"
                 r"else:\s*_quantities\[item_id\] = counts\s*return true\s*$", st_funcs.get("remove", "")):
    err(f"{STORE}: remove() refuses an unknown id or quality, an amount below 1 or more than is held (all or nothing), never going below 0")
if "return is_valid_item(item_id) and quality >= 0 and quality < get_definition(item_id).quality_levels" not in st_funcs.get("_accepts", ""):
    err(f"{STORE}: _accepts() = a known item and a quality level it has")
gq = st_funcs.get("get_quantity", "")
if "var counts: Array = _quantities.get(item_id, [])" not in gq or "total += count" not in gq \
   or "return int(counts[quality]) if quality < counts.size() else 0" not in gq \
   or "return amount >= 1 and get_quantity(item_id, quality) >= amount" not in st_funcs.get("has", "") \
   or "return _definitions.has(item_id)" not in st_funcs.get("is_valid_item", "") \
   or "return _quantities.duplicate(true)" not in st_funcs.get("get_save_data", "") \
   or "return (_quantities[item_id] as Array).duplicate()" not in st_funcs.get("_counts_of", ""):
    err(f"{STORE}: counts are read through get_quantity()/has() (all levels or one); is_valid_item() = a known definition; the save data and working counts are copies")
ap = st_funcs.get("apply_save_data", "")
if not re.search(r"var loaded := \{\}\s*for item_id: String in data:\s*var counts := _whole_counts\(item_id, data\[item_id\]\)\s*"
                 r"if counts\.is_empty\(\):\s*push_warning\(.*?\)\n\s*continue\s*if counts\.max\(\) > 0:\s*loaded\[item_id\] = counts\s*"
                 r"_quantities = loaded\s*$", ap):
    err(f"{STORE}: apply_save_data() replaces all counts, keeps only valid entries and drops the rest with a warning (never silently)")
wc = st_funcs.get("_whole_counts", "")
if not all(k in wc for k in ("if not is_valid_item(item_id) or typeof(value) != TYPE_ARRAY:", "if entry.size() != get_definition(item_id).quality_levels:",
                             "if typeof(count) != TYPE_INT and typeof(count) != TYPE_FLOAT:", "counts.append(maxi(int(count), 0))")):
    err(f"{STORE}: a saved entry is valid only for a known id with one number per quality level; counts never negative")
if not re.search(r"^var _definitions: Dictionary = \{\}\s*\nvar _quantities: Dictionary = \{\}", st, re.M) \
   or not re.search(r"if definition == null or definition.id == \"\" or _definitions\.has\(definition\.id\):", st_funcs.get("_init", "")):
    err(f"{STORE}: _init() ignores a duplicate item id")
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    code = code_only(s2)
    if f != STORE and re.search(r"\._quantities\b|\._definitions\b|\"_quantities\"|\"_definitions\"", code):
        err(f"{f}: reaches into an ItemStore's internals — use its methods")
    if f != STORE and "res://data/items" in code:
        err(f"{f}: loads item data directly — ItemStore.load_definitions() is the one loader")
    for lit in re.findall(r'"([^"]+)"', code):
        if lit in items or lit in {v["name"] for v in items.values()}:
            err(f"{f}: item data '{lit}' hard-coded in a script — it belongs in data/items/")
    if f not in (INV, STORE) and re.search(r"\bItemStore\.new\(", code):
        err(f"{f}: creates an ItemStore — the player's items have one store, the Inventory's (O-14)")
    if f != "scripts/autoload/save_manager.gd" and re.search(r"Inventory\.(get_save_data|apply_save_data)\(|FarmManager\.apply_save_data\(", code):
        err(f"{f}: saves or loads the player's items or farm — only SaveManager does")
    if f not in (FM, INV) and re.search(r"\bInventory\.(add|remove)\(", code):
        err(f"{f}: changes the player's items — only FarmManager's seed/basket rules and Inventory's discovery rewards do")

# One owner (M04.3, O-14): the Inventory autoload holds the player's store;
# FarmManager keeps no count of its own and changes the Inventory only where
# the seed/basket rules say; Inventory adds a collectible per discovery.
inv_src = scripts.get(INV, "")
inv_code = code_only(inv_src)
inv_funcs = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", inv_src, re.M | re.S)}
INV_API = ["_ready", "is_valid_item", "get_definition", "get_quantity", "has", "add", "remove", "get_view", "get_save_data",
           "apply_save_data", "_on_discovery_collected"]
if not inv_src.startswith("extends Node\n") or re.search(r"^class_name", inv_src, re.M) or list(inv_funcs) != INV_API \
   or re.findall(r"^var (\w+)", inv_code, re.M) != ["_store", "_collectible_item_ids", "_definitions"] or "var _store: ItemStore" not in inv_code:
    err(f"{INV}: the Inventory is a plain autoload Node holding one ItemStore (API {INV_API})")
if re.search(r"\b_store\b(?!\.|: ItemStore| = ItemStore\.new\()", inv_code) or inv_code.count("ItemStore.new(") != 1 \
   or "_store = ItemStore.new(definitions)" not in inv_funcs.get("_ready", ""):
    err(f"{INV}: the store is created once in _ready() and never handed out")
FORWARD = {"is_valid_item": "return _store.is_valid_item(item_id)", "get_definition": "return _store.get_definition(item_id)",
           "get_quantity": "return _store.get_quantity(item_id, quality)", "has": "return _store.has(item_id, amount, quality)",
           "get_save_data": "return _store.get_save_data()"}
# The three writers forward, then announce the change (M04.5) — only after it happened.
for fn in ("add", "remove"):
    if not re.search(rf"if not _store\.{fn}\(item_id, amount, quality\):\s*return false\s*items_changed\.emit\(\)\s*return true\s*$", inv_funcs.get(fn, "")):
        err(f"{INV}: {fn}() forwards to the store and emits items_changed only when something changed")
if not re.search(r"func apply_save_data\(data: Dictionary\) -> void:\s*_store\.apply_save_data\(data\)\s*items_changed\.emit\(\)\s*$", inv_funcs.get("apply_save_data", "")):
    err(f"{INV}: apply_save_data() forwards to the store, then emits items_changed")
if not re.search(r"^signal items_changed$", inv_src, re.M) or len(re.findall(r"items_changed\.emit\(\)", inv_code)) != 4 \
   or [f for f, s2 in scripts.items() if "items_changed.emit" in code_only(s2)] != [INV]:
    err(f"{INV}: items_changed is the Inventory's, emitted exactly after each change (add, remove, load, reward) and nowhere else")
for fn, line in FORWARD.items():
    body = inv_funcs.get(fn, "")
    if line not in body or len([l for l in body.splitlines()[1:] if l.strip()]) != 1:
        err(f"{INV}: {fn}() only forwards to the store ({line})")
inv_calls = {}
for fn, body in inv_funcs.items():
    for m in re.finditer(r"\b_store\.(add|remove|apply_save_data)\(", body):
        inv_calls[(m.group(1), fn)] = inv_calls.get((m.group(1), fn), 0) + 1
if inv_calls != {("add", "add"): 1, ("remove", "remove"): 1, ("apply_save_data", "apply_save_data"): 1, ("add", "_on_discovery_collected"): 1}:
    err(f"{INV}: the store changes only through the forwarding methods and the discovery reward (found {sorted(inv_calls.items())})")
ir = inv_funcs.get("_ready", "")
if not re.search(r'if definition\.category == "collectible" and definition\.discovery_id != "" \\\s*and not _collectible_item_ids\.has\(definition\.discovery_id\):\s*'
                 r"_collectible_item_ids\[definition\.discovery_id\] = definition\.id", ir) \
   or "DiscoveryManager.discovery_made.connect(_on_discovery_collected)" not in ir \
   or "DiscoveryManager.discovery_repeated.connect(_on_discovery_collected)" not in ir \
   or len(re.findall(r"\b_collectible_item_ids\s*(\[[^\]]*\]\s*=[^=]|=[^=])", inv_code)) != 1:
    err(f"{INV}: every collection of a discovery (first or repeat) is heard; the reward comes from the collectible items' discovery_id")
if not re.search(r'var item_id: String = _collectible_item_ids\.get\(definition\.id, ""\)\s*if item_id != "" and _store\.add\(item_id\):\s*items_changed\.emit\(\)\s*$',
                 inv_funcs.get("_on_discovery_collected", "")):
    err(f"{INV}: collecting a discovery gives exactly one of its collectible, or nothing if it has none")
if not (0 <= found_al.index("DiscoveryManager") < found_al.index("Inventory") < found_al.index("FarmManager") < found_al.index("GameState")
        if all(n in found_al for n in ("DiscoveryManager", "Inventory", "FarmManager", "GameState")) else False):
    err("project.godot: Inventory loads after DiscoveryManager and before FarmManager and GameState")
# Filtered views (M04.4): the screens read the Inventory by category through
# get_view(), a read-only view built fresh from the store; they keep no counts.
gv = inv_funcs.get("get_view", "")
if len(re.findall(r"\b_definitions\s*(\[[^\]]*\]\s*=[^=]|=[^=]|\.(append|erase|clear|sort|push_back|insert)\b)", inv_code)) != 1 \
   or "_definitions = definitions" not in ir \
   or not re.search(r"func get_view\(category: String\) -> Array:\s*var rows: Array = \[\]\s*for definition in _definitions:\s*"
                    r"if definition\.category != category:\s*continue\s*var total := _store\.get_quantity\(definition\.id\)\s*"
                    r"if total <= 0:\s*continue\s*var counts: Array = \[\]\s*for quality in definition\.quality_levels:\s*"
                    r"counts\.append\(_store\.get_quantity\(definition\.id, quality\)\)\s*"
                    r'rows\.append\(\{"item": definition, "total": total, "counts": counts\}\)\s*return rows\s*$', gv):
    err(f"{INV}: get_view() is a read-only view — one row per held item of the category, every quality level, built fresh from the store")
SP, BS = "scripts/ui/seed_picker.gd", "scripts/ui/basket_screen.gd"
for f in (SP, BS):
    code = code_only(scripts.get(f, ""))
    if re.search(r"^var ", code, re.M):
        err(f"{f}: a filtered view keeps no state of its own (member vars)")
    if re.search(r"FarmManager\.(get_seed_count|get_basket|get_produce_count|get_produce_total)\(|Inventory\.(get_quantity|has|get_save_data)\(", code):
        err(f"{f}: reads the player's items only through Inventory.get_view()")
sp_rb = code_only(func_body(scripts.get(SP, ""), "_rebuild") or "")
if not re.search(r'var held := \{\}\s*for row: Dictionary in Inventory\.get_view\("seed"\):\s*held\[\(row\.item as ItemDefinition\)\.crop_id\] = int\(row\.total\)', sp_rb) \
   or "var crops := FarmManager.get_known_crops()" not in sp_rb or "var count: int = held.get(crop.crop_id, 0)" not in sp_rb \
   or "FarmManager.seeds_changed.connect(_on_seeds_changed)" not in (func_body(scripts.get(SP, ""), "_ready") or ""):
    err(f"{SP}: one card per known crop, its count from the Inventory's seed view; refreshed on FarmManager.seeds_changed (after a planting, never mid-press)")
bs_src = scripts.get(BS, "")
br = code_only(func_body(bs_src, "_basket_rows") or "")
if not re.search(r'var held := \{\}\s*for row: Dictionary in Inventory\.get_view\("produce"\):\s*held\[\(row\.item as ItemDefinition\)\.crop_id\] = row\s*'
                 r"var rows: Array = \[\]\s*for crop in FarmManager\.get_crops\(\):\s*if held\.has\(crop\.crop_id\):\s*"
                 r'rows\.append\(\{"crop": crop, "total": held\[crop\.crop_id\]\.total, "counts": held\[crop\.crop_id\]\.counts\}\)\s*return rows\s*$', br) \
   or "var rows := _basket_rows()" not in code_only(func_body(bs_src, "_refresh") or "") \
   or "var count := int(row.counts[quality])" not in code_only(func_body(bs_src, "_quality_split") or "") \
   or "FarmManager.produce_changed.connect(_on_produce_changed)" not in (func_body(bs_src, "_ready") or ""):
    err(f"{BS}: the basket is the Inventory's produce view in crop order, split by quality; refreshed on FarmManager.produce_changed")
# Inventory screen (M04.5): one modal, read-only view of every held item —
# Seeds, Produce (quality split), Collectibles — through get_view() only;
# refreshed on open and on items_changed while open; opened from the HUD.
IS = "scripts/ui/inventory_screen.gd"
is_src = scripts.get(IS, "")
is_code = code_only(is_src)
is_funcs = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", is_src, re.M | re.S)}
if not re.search(r"^extends Control\s*\nclass_name InventoryScreen", is_src, re.M) or re.search(r"^var ", is_code, re.M) \
   or 'const SECTIONS := [["seed", "Seeds"], ["produce", "Produce"], ["collectible", "Collectibles"]]' not in is_code \
   or {c for c in ITEM_CATEGORIES} != set(re.findall(r'\["(\w+)", "\w+"\]', re.search(r"const SECTIONS := (.*)", is_code).group(1) if "const SECTIONS" in is_code else "")):
    err(f"{IS}: an InventoryScreen with no state of its own and one section per item category ({ITEM_CATEGORIES})")
if re.search(r"FarmManager\.(get_seed_count|get_basket|get_produce_count|get_produce_total|get_known_crops)\(|Inventory\.(?!get_view\(|items_changed\b)\w+", is_code) \
   or is_code.count("Inventory.get_view(") != 1:
    err(f"{IS}: reads the player's items only through Inventory.get_view() — never FarmManager's getters or other Inventory methods")
if not re.search(r"for section: Array in SECTIONS:\s*var rows := _section_rows\(section\[0\]\)\s*if rows\.is_empty\(\):\s*continue", is_funcs.get("_refresh", "")) \
   or "for child in list_container.get_children():" not in is_funcs.get("_refresh", ""):
    err(f"{IS}: rebuilt from scratch each time; a category with nothing held shows no section")
sr = is_funcs.get("_section_rows", "")
if not re.search(r"for row: Dictionary in Inventory\.get_view\(category\):\s*var crop_id := \(row\.item as ItemDefinition\)\.crop_id\s*"
                 r'if crop_id == "":\s*row\["crop"\] = null\s*others\.append\(row\)\s*else:\s*by_crop\[crop_id\] = row', sr) \
   or not re.search(r"for crop in FarmManager\.get_crops\(\):\s*if by_crop\.has\(crop\.crop_id\):", sr) or "return rows + others" not in sr:
    err(f"{IS}: crop items in FarmManager's crop order (as the picker and basket), others in data order")
br_ = is_funcs.get("_build_row", "")
if '"%s  ×%d" % [item.display_name, int(row.total)]' not in br_ or "if item.quality_levels > 1:" not in br_ or "_quality_split(row.counts)" not in br_:
    err(f"{IS}: each row shows the item's name and total, and a quality split for items with quality levels")
qs = is_funcs.get("_quality_split", "")
bqs = code_only(func_body(scripts.get(BS, ""), "_quality_split") or "")
for line in ("if count <= 0:", "var label := FarmManager.get_quality_name(quality)", "if quality == FarmManager.QUALITY_FINE:",
             'label = "✦ " + label', 'parts.append("%s %d" % [label, count])', 'return " · ".join(parts)'):
    if line not in qs or line not in bqs:
        err(f"{IS}: the quality split reads exactly as the basket's ({line})")
if "for quality in counts.size():" not in qs or "var count := int(counts[quality])" not in qs:
    err(f"{IS}: the quality split covers every quality level held")
if "Inventory.items_changed.connect(_on_items_changed)" not in is_funcs.get("_ready", "") \
   or not re.search(r"if visible:\s*_refresh\(\)", is_funcs.get("_on_items_changed", "")) \
   or not re.search(r"_refresh\(\)\s*visible = true", is_funcs.get("open", "")):
    err(f"{IS}: rebuilt on open and on Inventory.items_changed while open")
hud_src = scripts.get("scripts/ui/hud.gd", "")
hud_tscn = open("scenes/ui/HUD.tscn", encoding="utf-8").read()
if "inventory_button.pressed.connect(inventory_screen.open)" not in (func_body(hud_src, "_ready") or "") \
   or not re.search(r'\[node name="InventoryButton" type="Button" parent="ScreenButtons"\]', hud_tscn) \
   or not re.search(r'\[node name="InventoryScreen" parent="\." instance=ExtResource\("\w+"\)\]', hud_tscn) \
   or 'path="res://scenes/ui/InventoryScreen.tscn"' not in hud_tscn:
    err("HUD: an Inventory button opens the one InventoryScreen")
for f in scripts:
    if f not in (IS, INV) and "items_changed" in code_only(scripts[f]):
        err(f"{f}: listens to items_changed — only the Inventory screen does (the picker and basket keep FarmManager's post-planting signals)")
fm_code = code_only(fm_src)
fm_funcs = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", fm_src, re.M | re.S)}
HOLDING_VARS = {"_seed_item_ids", "_produce_item_ids", "_starter_seeds_given", "_found_seed_crop_ids", "_found_seed_origins"}
holding_like = {v for v in re.findall(r"^var (\w+)", fm_code, re.M) if re.search(r"seed|produce|basket|item|harvest_count|inventory|store", v)}
if holding_like != HOLDING_VARS or re.search(r"\bItemStore\b(?!\.(load_definitions|crop_item_ids)\()", fm_code):
    err(f"{FM}: seeds and the basket live only in the Inventory — no store or copy here (state {sorted(holding_like)}, expected {sorted(HOLDING_VARS)})")
for v in ("_seed_item_ids", "_produce_item_ids"):
    if len(re.findall(rf"\b{v} =[^=]", fm_code)) != 1 or f'{v} = ItemStore.crop_item_ids(item_definitions, "{"seed" if "seed" in v else "produce"}")' not in fm_funcs.get("_ready", ""):
        err(f"{FM}: {v} is built once in _ready() from the item data")
STORE_CALLS = {("add", "notify_crop_harvested"): 2, ("add", "_grant_found_seeds"): 1, ("add", "_give_starting_seeds"): 1,
               ("remove", "choose_seed"): 1, ("remove", "_start_fresh_seeds"): 1}
calls = {}
for fn, body in fm_funcs.items():
    for m in re.finditer(r"\bInventory\.(add|remove|apply_save_data|get_save_data)\(", body):
        calls[(m.group(1), fn)] = calls.get((m.group(1), fn), 0) + 1
if calls != STORE_CALLS:
    err(f"{FM}: the Inventory changes only where the seed/basket rules say (found {sorted(calls.items())}, expected {sorted(STORE_CALLS.items())})")
if 'return Inventory.get_quantity(_seed_item_ids.get(crop_id, ""))' not in fm_funcs.get("get_seed_count", "") \
   or not re.search(r'var item_id: String = _produce_item_ids\.get\(crop_id, ""\)\s*if quality < 0:\s*return Inventory\.get_quantity\(item_id\)\s*'
                    r'return Inventory\.get_quantity\(item_id, clampi\(quality, QUALITY_PLAIN, QUALITY_FINE\)\)', fm_funcs.get("get_produce_count", "")):
    err(f"{FM}: seed and produce counts are read from the Inventory (the same clamped quality as before)")
cs = fm_funcs.get("choose_seed", "")
if not re.search(r"if crop == null or get_seed_count\(crop\.crop_id\) <= 0:\s*return false", cs) \
   or not (0 <= cs.find("if not _pending_plot.plant(crop, soil):") < cs.find('Inventory.remove(_seed_item_ids.get(crop.crop_id, ""))')):
    err(f"{FM}: planting is refused without a seed, and the seed is taken only after the plot planted")
hv = fm_funcs.get("notify_crop_harvested", "")
if 'Inventory.add(_seed_item_ids.get(crop_definition.crop_id, ""))\n' not in hv \
   or 'Inventory.add(_produce_item_ids.get(crop_definition.crop_id, ""), 1, clampi(quality, QUALITY_PLAIN, QUALITY_FINE))' not in hv:
    err(f"{FM}: a harvest returns exactly one seed and puts one produce at the quality it grew")
gf = fm_funcs.get("_grant_found_seeds", "")
if not re.search(r'if _found_seed_crop_ids\.has\(crop\.crop_id\):\s*continue.*_found_seed_crop_ids\.append\(crop\.crop_id\).*'
                 r'Inventory\.add\(_seed_item_ids\.get\(crop\.crop_id, ""\)\)\n', gf, re.S):
    err(f"{FM}: a found seed is one seed, once ever per crop")
gs_ = fm_funcs.get("_give_starting_seeds", "")
if not re.search(r"for crop in _crops:\s*if _starter_seeds_given\.has\(crop\.crop_id\):\s*continue\s*_starter_seeds_given\.append\(crop\.crop_id\)\s*"
                 r'if crop\.starting_seeds > 0:\s*Inventory\.add\(_seed_item_ids\.get\(crop\.crop_id, ""\), crop\.starting_seeds\)\s*$', gs_) \
   or "_give_starting_seeds()" not in fm_funcs.get("_ready", ""):
    err(f"{FM}: each crop's starting seeds are given once ever (at a fresh start, or for a crop the save hasn't seen)")
if not re.search(r"for crop in _crops:\s*var held := get_seed_count\(crop\.crop_id\)\s*if held > 0:\s*"
                 r'Inventory\.remove\(_seed_item_ids\.get\(crop\.crop_id, ""\), held\)\s*_starter_seeds_given\.clear\(\)\s*_give_starting_seeds\(\)\s*$',
                 fm_funcs.get("_start_fresh_seeds", "")):
    err(f"{FM}: a fresh farm's seeds are exactly the starting seeds")
fa = fm_funcs.get("apply_save_data", "")
if not re.search(r"func apply_save_data\(data: Dictionary\) -> void:\s*if data\.is_empty\(\):\s*_start_fresh_seeds\(\)\s*return\s*"
                 r"_starter_seeds_given\.clear\(\)\s*for crop_id: Variant in data\.get\(\"starter_seeds\", \[\]\):"
                 r".*?_give_starting_seeds\(\)", fa, re.S):
    err(f"{FM}: apply_save_data() gives a fresh farm for an empty farm section; otherwise gives any starting seeds not yet given")
fsd = fm_funcs.get("get_save_data", "")
if re.search(r'"(seeds|basket)":', fsd) or '"starter_seeds": Array(_starter_seeds_given),' not in fsd:
    err(f"{FM}: the farm section no longer holds seeds or the basket (they are the items section); it records starter_seeds")
# The quality rules themselves are unchanged by M04.2.
QUALITY_RULES = {"rate_soil": "08687935b173", "rate_care": "f6fa6d2a3dc8", "combine_quality": "352aae2471d5",
                 "get_harvest_points": "b2554a355faf", "get_quality_name": "b06aa2985f01", "get_basket": "094c15abfe71",
                 "get_produce_total": "79b22fabce3d"}
changed_q = [n for n, h in QUALITY_RULES.items() if _hash_body(fm_src, n) != h]
if changed_q or not re.search(r"^const QUALITY_PLAIN := 0\nconst QUALITY_GOOD := 1\nconst QUALITY_FINE := 2\n"
                              r'const QUALITY_NAMES := \["Plain", "Good", "Fine"\]', fm_src, re.M) \
   or not all(c in fm_src for c in ("const NEGLECT_FACTOR := 3.0\n", "const QUALITY_POINT_SCALE := [0.75, 1.0, 1.5]\n",
                                    "const QUALITY_SIZE := [0.9, 1.0, 1.1]\n", "const SOIL_MEMORY := 2\n")):
    err(f"{FM}: produce quality rules changed {changed_q} — M04.2 moves where produce is held, never how quality is decided")
# Save 1 -> 2 (M04.2): seeds and basket move from the farm section to "items".
SMF = "scripts/autoload/save_manager.gd"
sm_src = scripts.get(SMF, "")
smf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |^static func |\Z)", sm_src, re.M | re.S)}
if not re.search(r"^\t\t\t1:\s*_move_holdings_to_items\(data\)", smf.get("_migrate", ""), re.M):
    err(f"{SMF}: _migrate() step 1 moves the farm's seeds and basket into items")
mv = smf.get("_move_holdings_to_items", "")
mv_ok = all(k in mv for k in ('var seed_items := ItemStore.crop_item_ids(definitions, "seed")',
                              'var produce_items := ItemStore.crop_item_ids(definitions, "produce")',
                              'var seeds: Variant = farm.get("seeds", {})', 'var basket: Variant = farm.get("basket", {})',
                              'farm["starter_seeds"] = (seeds as Dictionary).keys()', "items[seed_items[crop_id]] = [seeds[crop_id]]",
                              "items[produce_items[crop_id]] = basket[crop_id]", 'farm.erase("seeds")', 'farm.erase("basket")',
                              'data["items"] = items'))
if not mv_ok or set(re.findall(r'\bdata\["(\w+)"\]\s*=', mv)) != {"items"} or re.search(r"\bdata\.(erase|clear|merge)\b", mv) \
   or len(re.findall(r"else:\s*push_warning\([^)]*\)", mv)) != 2 or re.search(r'farm\.erase\("(?!seeds|basket)', mv) \
   or set(re.findall(r'farm\["(\w+)"\]\s*=', mv)) != {"starter_seeds"}:
    err(f"{SMF}: the 1 -> 2 step moves every seed count and basket row (counts as they are, a dropped crop warned about) into items, "
        "records starter_seeds, and touches nothing else")
lg_ = code_only(func_body(sm_src, "load_game") or "")
if '"items": Inventory.get_save_data(),' not in code_only(func_body(sm_src, "save_game") or "") \
   or not (0 <= lg_.find('Inventory.apply_save_data(data.get("items", {}))') < lg_.find('FarmManager.apply_save_data(data.get("farm", {}))')):
    err(f"{SMF}: the items section is the Inventory's, loaded before the farm (which gives any missing starting seeds)")
if not re.search(r"^\t\t\t2:\s*pass\b", smf.get("_migrate", ""), re.M):
    err(f"{SMF}: step 2 -> 3 (M04.3) rewrites nothing — only collectibles may now appear in items")
notes.append(f"items: {len(items)} from data/items ({sum(v['category'] == 'seed' for v in items.values())} seed, "
             f"{sum(v['category'] == 'produce' for v in items.values())} produce x{QUALITY_LEVELS} qualities); ItemStore API {len(STORE_API)} "
             f"functions; Inventory autoload owns the store; {sum(v['category'] == 'collectible' for v in items.values())} collectibles "
             f"from discoveries; save steps 1 -> 2 (holdings) and 2 -> 3 (no rewrite)")

# ------------------------------------------------------------ wallet + ledger (M05.1, D-20)
# Coins live in the Wallet autoload, apart from Wriksha Points (the score).
# The append-only ledger is the truth: the balance is its sum and never
# below 0; only credit()/debit() append (amount >= 1, a reason, debit within
# the balance); a load replays the saved ledger and keeps its valid prefix.
# Nothing credits or debits coins yet (earn rules M05.3, selling M06.2).
WL = "scripts/autoload/wallet.gd"
wl_src = scripts.get(WL, "")
wl_code = code_only(wl_src)
wlf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", wl_src, re.M | re.S)}
WL_API = ["get_balance", "can_afford", "get_ledger", "credit", "debit", "get_save_data", "apply_save_data", "_record", "_parse_entry"]
if not wl_src.startswith("extends Node\n") or re.search(r"^class_name", wl_src, re.M) or list(wlf) != WL_API \
   or re.findall(r"^var (\w+)", wl_code, re.M) != ["_balance", "_ledger"] or "var _balance: int = 0" not in wl_code \
   or "var _ledger: Array[Dictionary] = []" not in wl_code or not re.search(r"^signal balance_changed\(balance: int\)$", wl_src, re.M):
    err(f"{WL}: the Wallet is a plain autoload Node with a balance, a ledger and the API {WL_API}")
BAL_W = re.compile(r"\b_balance\s*(=[^=]|\+=|-=|\*=|/=)")
LED_W = re.compile(r"\b_ledger\s*(=[^=]|\.(append|push_back|insert|erase|remove_at|clear|pop_back|pop_front|resize|sort|reverse|fill|assign)\b|\[[^\]]*\]\s*=[^=])")
writes = {fn: (len(BAL_W.findall(b)), sorted(set(m.group(0).split(".")[-1].split("(")[0] for m in LED_W.finditer(b)))) for fn, b in wlf.items()}
if {fn: w for fn, w in writes.items() if w != (0, [])} != {"_record": (1, ["append"]), "apply_save_data": (2, ["append", "clear"])}:
    err(f"{WL}: only _record() (for credit/debit) and a load write the balance and the ledger, and the ledger is only appended to ({writes})")
if not re.search(r'func credit\(amount: int, reason: String\) -> bool:\s*if amount < 1 or reason == "":\s*push_warning\(.*?\)\n\s*return false\s*'
                 r"_record\(amount, reason\)\s*return true\s*$", wlf.get("credit", "")):
    err(f"{WL}: credit() refuses an amount below 1 or an empty reason, otherwise records exactly +amount")
if not re.search(r'func debit\(amount: int, reason: String\) -> bool:\s*if amount < 1 or reason == "":\s*push_warning\(.*?\)\n\s*return false\s*'
                 r"if amount > _balance:\s*return false\s*_record\(-amount, reason\)\s*return true\s*$", wlf.get("debit", "")):
    err(f"{WL}: debit() refuses an amount below 1, an empty reason or more than the balance, otherwise records exactly -amount")
if not re.search(r'func _record\(amount: int, reason: String\) -> void:\s*_ledger\.append\(\{"amount": amount, "reason": reason\}\)\s*'
                 r"_balance \+= amount\s*balance_changed\.emit\(_balance\)\s*$", wlf.get("_record", "")):
    err(f"{WL}: every change is one appended ledger entry, the balance moves by exactly that amount, then balance_changed")
ap_ = wlf.get("apply_save_data", "")
if not re.search(r"_ledger\.clear\(\)\s*_balance = 0\s*var entries: Variant = data\.get\(\"ledger\", \[\]\)", ap_) \
   or not re.search(r"for entry: Variant in entries:\s*var parsed := _parse_entry\(entry\)\s*if parsed\.is_empty\(\) or _balance \+ int\(parsed\.amount\) < 0:\s*"
                    r"push_warning\(.*?\)\n\s*break\s*_ledger\.append\(parsed\)\s*_balance \+= int\(parsed\.amount\)", ap_) \
   or "balance_changed.emit(_balance)" not in ap_:
    err(f"{WL}: a load replays the saved ledger from zero and keeps only its valid prefix (never negative), with a warning")
pe = wlf.get("_parse_entry", "")
if not all(k in pe for k in ("if typeof(entry) != TYPE_DICTIONARY:", "typeof(reason) != TYPE_STRING",
                             'if float(amount) != floorf(float(amount)) or int(amount) == 0 or reason == "":',
                             'return {"amount": int(amount), "reason": String(reason)}')):
    err(f"{WL}: a saved entry is a whole, non-zero amount with a reason")
if "return _balance" not in wlf.get("get_balance", "") or "return amount >= 1 and amount <= _balance" not in wlf.get("can_afford", "") \
   or "return _ledger.duplicate(true)" not in wlf.get("get_ledger", "") \
   or 'return {"ledger": _ledger.duplicate(true)}' not in wlf.get("get_save_data", ""):
    err(f"{WL}: reads return the balance and copies of the ledger; the save is the ledger only")
for f, s2 in scripts.items():
    if f.startswith("tools/") or f == WL: continue
    code = code_only(s2)
    if re.search(r"\bWallet\.(credit|debit)\(", code):
        err(f"{f}: changes coins — nothing earns or spends coins before M05.3/M06.2 (a later milestone lists its callers here)")
    if re.search(r"\bWallet\.(_\w+)|\bWallet\.(get_save_data|apply_save_data)\(", code) and f != "scripts/autoload/save_manager.gd":
        err(f"{f}: reaches into the Wallet — only SaveManager saves/loads it; others read get_balance()/can_afford()/get_ledger()")
    if f != WL and "balance_changed.emit" in code:
        err(f"{f}: only the Wallet announces balance changes")
sm_w = scripts.get("scripts/autoload/save_manager.gd", "")
if '"wallet": Wallet.get_save_data(),' not in code_only(func_body(sm_w, "save_game") or "") \
   or 'Wallet.apply_save_data(data.get("wallet", {}))' not in code_only(func_body(sm_w, "load_game") or "") \
   or not re.search(r"^\t\t\t3:\s*pass\b", code_only(func_body(sm_w, "_migrate") or ""), re.M):
    err("scripts/autoload/save_manager.gd: the wallet section is saved and loaded; step 3 -> 4 (M05.1) rewrites nothing (absent = an empty wallet)")
pm = code_only(scripts.get("scripts/autoload/points_manager.gd", ""))
if re.search(r"Wallet|coin", pm, re.I) or re.search(r"\bWallet\b", code_only(scripts.get("scripts/autoload/farm_manager.gd", ""))):
    err("Wriksha Points and coins stay separate until O-02 (M05.5)")
notes.append(f"wallet: ledger-derived balance, API {len(WL_API)} functions, no coin sources yet")

# ------------------------------------------------------------ repeat-reward protection (M05.2, P-02, D-21)
# Exploration progress is saved: places reached, secrets found and the two
# once-ever bonuses. Every exploration reward is paid only behind its
# "already?" check; loading restores that state and pays nothing; malformed
# saved state can only make a bonus count as paid. Repeatable discovery
# collection (points, collectibles, daily) is unchanged.
EXF = "scripts/autoload/exploration_manager.gd"
ex_src = scripts.get(EXF, "")
exf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", ex_src, re.M | re.S)}
ex_code = code_only(ex_src)
pays = {}
for fn, body in exf.items():
    n = len(re.findall(r"PointsManager\.add_points\(", body))
    if n: pays[fn] = n
if pays != {"_on_discovery_made": 1, "mark_landmark_reached": 1, "mark_secret_location_found": 2, "_maybe_award_curiosity_bonus": 1}:
    err(f"{EXF}: exploration pays points only in its known reward sites ({pays})")
ml, ms, mc = exf.get("mark_landmark_reached", ""), exf.get("mark_secret_location_found", ""), exf.get("_maybe_award_curiosity_bonus", "")
if not (0 <= ml.find("if _reached_landmarks.has(landmark_id):\n\t\treturn") < ml.find("_reached_landmarks.append(landmark_id)") < ml.find('var bonus := _rewards.points("landmark")') < ml.find("PointsManager.add_points(bonus)")):
    err(f"{EXF}: a landmark pays once ever — checked, recorded, then paid")
if not (0 <= ms.find("if _found_secret_locations.has(location_id):\n\t\treturn") < ms.find("_found_secret_locations.append(location_id)") < ms.find('var bonus := _rewards.points("secret_location")') < ms.find("PointsManager.add_points(bonus)")) \
   or not re.search(r'and not _all_secrets_bonus_awarded:\s*_all_secrets_bonus_awarded = true\s*var all_bonus := _rewards\.points\("all_secret_locations"\)\s*PointsManager\.add_points\(all_bonus\)', ms):
    err(f"{EXF}: a secret place and 'every secret found' each pay once ever — checked, recorded, then paid")
if not (0 <= mc.find("if _curiosity_bonus_given:\n\t\treturn") < mc.find("_curiosity_bonus_given = true") < mc.find('var bonus := _rewards.points("curiosity")') < mc.find("PointsManager.add_points(bonus)")):
    err(f"{EXF}: the curiosity bonus pays once ever — checked, recorded, then paid")
ONCE = {"_reached_landmarks": {"mark_landmark_reached", "apply_save_data"}, "_found_secret_locations": {"mark_secret_location_found", "apply_save_data"},
        "_all_secrets_bonus_awarded": {"mark_secret_location_found", "apply_save_data"}, "_curiosity_bonus_given": {"_maybe_award_curiosity_bonus", "apply_save_data"}}
for var, allowed in ONCE.items():
    writers = {fn for fn, b in exf.items() if re.search(rf"\b{var}\s*(=[^=]|\.(append|clear|erase|remove_at|assign)\b)", b)}
    if writers != allowed:
        err(f"{EXF}: {var} is written only when its reward is paid and on load (found {sorted(writers)})")
if not re.search(r'return \{\s*"landmarks": Array\(_reached_landmarks\),\s*"secrets": Array\(_found_secret_locations\),\s*'
                 r'"all_secrets_bonus": _all_secrets_bonus_awarded,\s*"curiosity_bonus": _curiosity_bonus_given,\s*\}', exf.get("get_save_data", "")):
    err(f"{EXF}: the save holds exactly the places reached, secrets found and the two once-ever bonus flags")
apx = exf.get("apply_save_data", "")
if not re.search(r"_reached_landmarks\.clear\(\)\s*_found_secret_locations\.clear\(\)\s*"
                 r'_restore_places\(data\.get\("landmarks", \[\]\), false, _reached_landmarks\)\s*'
                 r'_restore_places\(data\.get\("secrets", \[\]\), true, _found_secret_locations\)\s*'
                 r'_curiosity_bonus_given = _was_paid\(data, "curiosity_bonus"\)\s*'
                 r'_all_secrets_bonus_awarded = _was_paid\(data, "all_secrets_bonus"\)\s*$', apx):
    err(f"{EXF}: a load restores places of the right kind and the two once-ever flags")
for fn in ("apply_save_data", "_restore_places", "_was_paid"):
    if re.search(r"PointsManager|FarmManager|\.emit\(|mark_\w+\(|_maybe_award", exf.get(fn, "")):
        err(f"{EXF}: {fn}() pays or announces something — loading restores state only")
rp = exf.get("_restore_places", "")
if not re.search(r"if typeof\(saved\) != TYPE_ARRAY:\s*push_warning\(.*?\)\n\s*return", rp) \
   or not re.search(r"var place: PlaceDefinition = null\s*if typeof\(place_id\) == TYPE_STRING:\s*place = _find_place\(place_id\)", rp) \
   or not re.search(r"if place == null or place\.secret != secret or into\.has\(place\.id\):\s*push_warning\(.*?\)\n\s*continue\s*into\.append\(place\.id\)", rp):
    err(f"{EXF}: only known places of the right kind are restored, once each; the rest is dropped with a warning")
if not re.search(r"if not data\.has\(key\):\s*return false\s*var value: Variant = data\[key\]\s*return value if typeof\(value\) == TYPE_BOOL else true", exf.get("_was_paid", "")):
    err(f"{EXF}: a once-ever bonus is unpaid only if absent (pre-M05.2) or saved as false — anything malformed counts as paid")
SESSION_ONLY = ("_session_discovery_count", "_session_rare_discovery_count", "_awarded_thresholds", "_first_discovery_announced",
                "_rare_discovery_announced", "_summary_shown")
if any(v in exf.get("get_save_data", "") + apx for v in SESSION_ONLY):
    err(f"{EXF}: session beats and thresholds stay session-only (thresholds count first-ever discoveries, already saved)")
dm = code_only(func_body(scripts.get("scripts/autoload/discovery_manager.gd", ""), "discover") or "")
if not re.search(r"^\tPointsManager\.add_points\(definition\.points_value\)$", dm, re.M) or len(re.findall(r"add_points\(", dm)) != 1 \
   or "discovery_repeated.emit(definition)" not in dm \
   or "if is_first_time:\n\t\tdiscovered_ids.append(id)" not in dm:
    err("scripts/autoload/discovery_manager.gd: collecting a discovery stays repeatable (points every time; first-ever vs repeat by saved ids)")
sm5 = scripts.get("scripts/autoload/save_manager.gd", "")
if '"exploration": ExplorationManager.get_save_data(),' not in code_only(func_body(sm5, "save_game") or "") \
   or 'ExplorationManager.apply_save_data(data.get("exploration", {}))' not in code_only(func_body(sm5, "load_game") or "") \
   or not re.search(r"^\t\t\t4:\s*pass\b", code_only(func_body(sm5, "_migrate") or ""), re.M):
    err("scripts/autoload/save_manager.gd: the exploration section is saved and loaded; step 4 -> 5 (M05.2) rewrites nothing (absent = nothing reached)")
for f, s2 in scripts.items():
    if f.startswith("tools/") or f in (EXF, "scripts/autoload/save_manager.gd"): continue
    if re.search(r"ExplorationManager\.(get_save_data|apply_save_data)\(|ExplorationManager\._", code_only(s2)):
        err(f"{f}: reaches into exploration progress — only SaveManager saves/loads it")
notes.append("repeat-reward protection: exploration progress saved; once-ever bonuses guarded; loading pays nothing")

# ------------------------------------------------------------ reward rules as data (M05.3, D-22)
# Flat Wriksha Points rewards are RewardRule data (data/rewards/), read
# through RewardRules (a plain class); per-definition amounts stay on their
# definitions (discovery / crop points_value; the harvest quality scale is
# FarmManager's rule). Points only. A never-respawning discovery is a
# once-ever claim, recorded by the saved discovered_ids.
RR_GD, RRS = "scripts/rewards/reward_rule.gd", "scripts/rewards/reward_rules.gd"
rr_src = scripts.get(RR_GD, "")
if not re.search(r"^extends Resource\s*\nclass_name RewardRule", rr_src, re.M) or \
   dict(re.findall(r"^@export var (\w+): (\w+)", rr_src, re.M)) != {"id": "String", "points": "int", "threshold": "int"}:
    err(f"{RR_GD}: RewardRule is a Resource with exactly id, points, threshold")
rules = {}
for f in sorted(glob.glob("data/rewards/*.tres")):
    txt = open(f, encoding="utf-8").read()
    if f'path="res://{RR_GD}"' not in txt or 'script_class="RewardRule"' not in txt:
        err(f"{f}: not a RewardRule resource"); continue
    vals = dict(re.findall(r'^(\w+) = (.+)$', txt.split("[resource]", 1)[1], re.M))
    rid = vals.get("id", '""').strip('"')
    if not re.fullmatch(r"[a-z][a-z0-9_]*", rid) or os.path.basename(f) != rid + ".tres":
        err(f"{f}: reward id '{rid}' must be lower_snake_case and match the file name")
    pts, thr = vals.get("points", "0"), vals.get("threshold", "0")
    if not re.fullmatch(r"\d+", pts) or not re.fullmatch(r"\d+", thr):
        err(f"{f}: points and threshold are whole numbers >= 0")
        continue
    rules[rid] = (int(pts), int(thr))
thr_values = [t for _, t in rules.values() if t]
if not rules or len(set(thr_values)) != len(thr_values):
    err(f"data/rewards: reward rules exist and no two share a threshold")
rs_src = scripts.get(RRS, "")
rsf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", rs_src, re.M | re.S)}
if not re.search(r"^extends RefCounted\s*\nclass_name RewardRules", rs_src, re.M) or list(rsf) != ["_init", "points", "thresholds"] \
   or 'const REWARDS_PATH := "res://data/rewards/"' not in rs_src or "ResourceDirectory.list_tres_paths(REWARDS_PATH)" not in rsf.get("_init", "") \
   or 'rule == null or rule.id == "" or rule.points < 0 or rule.threshold < 0 or _rules.has(rule.id)' not in rsf.get("_init", "") \
   or re.findall(r"^var (\w+)", code_only(rs_src), re.M) != ["_rules"] \
   or any(re.search(r"\b_rules\s*(\[[^\]]*\]\s*=[^=]|=[^=]|\.(erase|clear|merge)\b)", b) for fn, b in rsf.items() if fn != "_init") \
   or not re.search(r"if rule == null:\s*push_warning\(.*?\)\n\s*return 0\s*return rule\.points", rsf.get("points", "")) \
   or not re.search(r"if rule\.threshold > 0:\s*result\[rule\.threshold\] = rule\.points", rsf.get("thresholds", "")):
    err(f"{RRS}: RewardRules (a RefCounted) loads data/rewards/ via ResourceDirectory, read-only, points(id) (0 + warning if unknown), thresholds()")
used = set()
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    code = code_only(s2)
    for rid in re.findall(r'_rewards\.points\("(\w+)"\)|RewardRules\.new\(\)\.points\("(\w+)"\)', code):
        used.update(x for x in rid if x)
    for const_name in re.findall(r"_rewards\.points\(([A-Z_]+)\)", code):
        m = re.search(rf'^const {const_name} := "(\w+)"', s2, re.M)
        if m: used.add(m.group(1))
        else: err(f"{f}: reward id constant {const_name} not found")
    if re.search(r"^const \w*(BONUS|THRESHOLDS)\w* := [\d{\[]", code, re.M):
        err(f"{f}: a reward amount as a constant — it belongs in data/rewards/")
    if re.search(r"PointsManager\.add_points\(\s*-?\d", code):
        err(f"{f}: a literal points amount — rewards come from data")
    if re.search(r"\.BONUS_POINTS\b", code):
        err(f"{f}: reads a reward constant — use the owner's getter")
for rid in sorted(used - set(rules)):
    err(f"a reward '{rid}' is paid in code but has no data/rewards/{rid}.tres")
unused = {r for r, (_, t) in rules.items() if not t} - used
if unused:
    err(f"data/rewards: rules no code pays {sorted(unused)}")
PAY_SITES = {("scripts/autoload/discovery_manager.gd", "discover"): 1, ("scripts/farming/farm_plot.gd", "_run_harvest_sequence"): 1,
             ("scripts/autoload/farm_manager.gd", "_reach"): 1, ("scripts/autoload/daily_discovery_manager.gd", "_on_discovery_made"): 1,
             (EXF, "_on_discovery_made"): 1, (EXF, "mark_landmark_reached"): 1, (EXF, "mark_secret_location_found"): 2,
             (EXF, "_maybe_award_curiosity_bonus"): 1}
sites = {}
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", s2, re.M | re.S):
        n = len(re.findall(r"PointsManager\.add_points\(", code_only(m.group(0))))
        if n: sites[(f, m.group(1))] = n
if sites != PAY_SITES:
    err(f"Wriksha Points are paid only at the known reward sites (found {sorted(sites.items())})")
exr = exf.get("_ready", "")
if "_rewards = RewardRules.new()" not in exr or "_thresholds = _rewards.thresholds()" not in exr \
   or "_summary_threshold = _thresholds.keys().max() if not _thresholds.is_empty() else 0" not in exr \
   or "if _thresholds.has(_session_discovery_count) and not _awarded_thresholds.has(_session_discovery_count):" not in exf.get("_on_discovery_made", "") \
   or "var bonus: int = _thresholds[_session_discovery_count]" not in exf.get("_on_discovery_made", "") \
   or "if _session_discovery_count == _summary_threshold:" not in exf.get("_on_discovery_made", ""):
    err(f"{EXF}: discovery-count thresholds and their points come from reward data; the summary shows at the highest threshold")
for sig, var in (("landmark_reached.emit(landmark_id, bonus)", "mark_landmark_reached"), ("secret_location_found.emit(location_id, bonus)", "mark_secret_location_found"),
                 ("all_secret_locations_found.emit(all_bonus)", "mark_secret_location_found"), ("curiosity_bonus_awarded.emit(location_id, bonus)", "_maybe_award_curiosity_bonus")):
    if sig not in exf.get(var, ""):
        err(f"{EXF}: {var}() announces exactly the points it paid ({sig})")
ddm = scripts.get("scripts/autoload/daily_discovery_manager.gd", "")
ddf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", ddm, re.M | re.S)}
if '_bonus_points = RewardRules.new().points("daily_discovery")' not in ddf.get("_ready", "") or "return _bonus_points" not in ddf.get("get_bonus_points", "") \
   or not re.search(r"PointsManager\.add_points\(_bonus_points\)\s*daily_completed\.emit\(definition, _bonus_points\)", ddf.get("_on_discovery_made", "")) \
   or "DailyDiscoveryManager.get_bonus_points()" not in scripts.get("scripts/ui/daily_discovery_screen.gd", ""):
    err("daily discovery: its bonus comes from reward data; the screen reads it through get_bonus_points()")
# Once-ever discoveries (D-22): claimed by the first collection (saved discovered_ids).
dmf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", scripts.get("scripts/autoload/discovery_manager.gd", ""), re.M | re.S)}
if not re.search(r"var definition := DiscoveryDatabase\.get_definition\(id\)\s*return definition != null and definition\.respawn_seconds <= 0\.0 and discovered_ids\.has\(id\)", dmf.get("is_claimed", "")):
    err("scripts/autoload/discovery_manager.gd: is_claimed() = a never-respawning discovery already collected (in the saved discovered_ids)")
if re.findall(r"^var (\w+)", code_only(scripts.get("scripts/autoload/discovery_manager.gd", "")), re.M) != ["discovered_ids"]:
    err("scripts/autoload/discovery_manager.gd: its only state is the saved discovered_ids — the once-ever claim derives from it, no second record")
dd = dmf.get("discover", "")
if not (0 <= dd.find("if is_claimed(id):\n\t\treturn false") < dd.find("var is_first_time") < dd.find("PointsManager.add_points(")):
    err("scripts/autoload/discovery_manager.gd: a claimed once-ever discovery can't be collected — refused before anything is recorded or paid")
spf = code_only(func_body(scripts.get("scripts/interactables/discovery_spawn_point.gd", ""), "_spawn") or "")
if not re.search(r"var instance: DiscoveryInteractable = discovery_scene\.instantiate\(\)\s*if DiscoveryManager\.is_claimed\(instance\.discovery_id\):\s*instance\.free\(\)\s*return\s*instance\.harvested\.connect", spf):
    err("scripts/interactables/discovery_spawn_point.gd: a claimed once-ever discovery is never spawned (launch, reload, area reload)")
et = ddf.get("_ensure_today_target", "")
if 'if target_date == today and target_id != "" and not DiscoveryManager.is_claimed(target_id):' not in et \
   or not re.search(r"for step in definitions\.size\(\):\s*var candidate: DiscoveryDefinition = definitions\[\(index \+ step\) % definitions\.size\(\)\]\s*if not DiscoveryManager\.is_claimed\(candidate\.id\):", et):
    err("daily discovery: a claimed once-ever discovery is never today's target — the next one in order is taken")
notes.append(f"rewards: {len(rules)} rules in data/rewards ({len(thr_values)} thresholds); {sum(PAY_SITES.values())} pay sites; once-ever discoveries by respawn_seconds <= 0")

# ------------------------------------------------------------ economy configuration (M05.4, D-23)
# EconomyConfig holds D-10's redemption reference (1000 coins = ₹10) as
# configuration only: no gameplay script, scene or UI reads it; it isn't
# the Wallet's and isn't a points ↔ coins rate. No economy rate lives in
# gameplay code, except FarmManager's frozen QUALITY_POINT_SCALE (a farm-
# quality rule, pinned by the M04.2 quality contract). RewardRules stay in
# data/rewards/, separate.
EC_GD, EC_TRES = "scripts/economy/economy_config.gd", "data/economy/economy_config.tres"
ec_src = scripts.get(EC_GD, "")
EC_FIELDS = [("redemption_reference_coins", "int", "1000"), ("redemption_reference_amount", "int", "10"),
             ("redemption_reference_currency", "String", '"INR"')]
if not re.search(r"^extends Resource\s*\nclass_name EconomyConfig", ec_src, re.M) \
   or re.findall(r"^@export var (\w+): (\w+) = (.+)$", ec_src, re.M) != EC_FIELDS \
   or re.search(r"^(func|var|const|signal) ", code_only(ec_src), re.M):
    err(f"{EC_GD}: EconomyConfig is a Resource with exactly the three redemption-reference fields (1000 coins = 10 INR) and nothing else")
ec_files = sorted(glob.glob("data/economy/*.tres"))
if ec_files != [EC_TRES]:
    err(f"data/economy: exactly one economy config ({EC_TRES}) (found {ec_files})")
else:
    txt = open(EC_TRES, encoding="utf-8").read()
    vals = dict(re.findall(r'^(\w+) = (.+)$', txt.split("[resource]", 1)[1], re.M))
    if f'path="res://{EC_GD}"' not in txt or 'script_class="EconomyConfig"' not in txt or \
       vals != {"script": 'ExtResource("1")', "redemption_reference_coins": "1000", "redemption_reference_amount": "10",
                "redemption_reference_currency": '"INR"'}:
        err(f"{EC_TRES}: the redemption reference is exactly 1000 coins = 10 INR (D-10) — {vals}")
ECON_REF = re.compile(r"\bEconomyConfig\b|economy_config|res://data/economy|redemption_reference|\bredemption\b|₹|\bINR\b", re.I)
for f, s2 in scripts.items():
    if f.startswith("tools/") or f == EC_GD: continue
    if ECON_REF.search(code_only(s2)):
        err(f"{f}: reads or shows the redemption reference — it is configuration for a future backend only (D-10, D-23)")
for path in glob.glob("scenes/**/*.tscn", recursive=True) + glob.glob("data/**/*.tres", recursive=True):
    if path == EC_TRES: continue
    if ECON_REF.search(open(path, encoding="utf-8").read()):
        err(f"{path}: references or shows the redemption reference")
if re.search(r"^[^#\n]*(economy|redemption)", open("project.godot", encoding="utf-8").read(), re.M | re.I):
    err("project.godot: no economy autoload or setting — EconomyConfig is plain data")
for f in glob.glob("data/rewards/*.tres"):
    if re.search(r"economy_config|EconomyConfig|redemption", open(f, encoding="utf-8").read()):
        err(f"{f}: reward rules and the economy configuration stay separate")
# No economy rate in gameplay code: the only rate-named constant is the frozen farm-quality multiplier.
ECON_CONST = re.compile(r"^const (\w*(POINT|COIN|REWARD|BONUS|PRICE|COST|RATE|REDEMPTION|EXCHANGE)\w*) :=", re.M)
rate_consts = sorted((f, m.group(1)) for f, s2 in scripts.items() if not f.startswith("tools/")
                     for m in ECON_CONST.finditer(code_only(s2)) if not m.group(1).endswith("_PATH"))
if rate_consts != [(FM, "QUALITY_POINT_SCALE")] or "const QUALITY_POINT_SCALE := [0.75, 1.0, 1.5]\n" not in scripts.get(FM, ""):
    err(f"no economy rate in gameplay code — only FarmManager's frozen QUALITY_POINT_SCALE [0.75, 1.0, 1.5] (found {rate_consts})")
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    code = code_only(s2)
    if re.search(r"points_value\s*[*/]\s*[\d.]|[\d.]\s*\*\s*\w*\.points_value", code):
        err(f"{f}: scales points_value by a literal — a rate belongs in data")
    if f != FM and "QUALITY_POINT_SCALE" in code:
        err(f"{f}: uses the farm-quality multiplier outside FarmManager's harvest rule")
if [fn for fn in re.findall(r"^func (\w+)\(", fm_src, re.M) if "QUALITY_POINT_SCALE" in (func_body(fm_src, fn) or "")] != ["get_harvest_points"]:
    err(f"{FM}: QUALITY_POINT_SCALE is used only by get_harvest_points()")
notes.append("economy config: redemption reference 1000 coins = 10 INR, read by nothing; one frozen farm-quality multiplier")

# ------------------------------------------------------------ save versioning (M04.0, P-01)
# One versioned save file, written and read only by SaveManager: every save
# carries save_version; a load validates it (absent = 0, malformed rejected,
# newer refused and never overwritten), migrates step by step, and passes
# only correctly typed sections to their systems.
SM = "scripts/autoload/save_manager.gd"
sm = scripts.get(SM, "")
sv = const_val(sm, "SAVE_VERSION")
if sv is None or sv != int(sv) or sv < 1 or 'const VERSION_KEY := "save_version"' not in sm:
    err(f"{SM}: an explicit integer SAVE_VERSION >= 1 and VERSION_KEY \"save_version\"")
sg = code_only(func_body(sm, "save_game") or "")
if not re.match(r"func save_game\(\) -> void:\s*if _saving_blocked:\s*push_warning\([^)]*\)\s*return", sg) or "VERSION_KEY: SAVE_VERSION," not in sg:
    err(f"{SM}: save_game() refuses while saving is blocked and always writes save_version")
lg = code_only(func_body(sm, "load_game") or "")
order = ["JSON.parse_string(text)", "if typeof(parsed) != TYPE_DICTIONARY:", "var version := read_version(parsed)",
         "if version < 0:", "if version > SAVE_VERSION:", "_saving_blocked = true", "var data := _migrate(parsed, version)",
         "if data.is_empty():", "data = _valid_sections(data)", "PointsManager.set_points("]
idx = [lg.find(k) for k in order]
if -1 in idx or idx != sorted(idx):
    err(f"{SM}: load_game() must parse, check the dictionary, read the version, reject malformed/newer (blocking saves), migrate, validate sections — before applying anything")
fut = re.search(r"if version > SAVE_VERSION:(.*?)return false", lg, re.S)
if not fut or "_saving_blocked = true" not in fut.group(1) or "apply" in fut.group(1):
    err(f"{SM}: a newer save is neither loaded nor overwritten")
applied = lg[lg.find("data = _valid_sections(data)"):]
if re.search(r"\bparsed\b", applied):
    err(f"{SM}: sections are applied only from the migrated, validated data")
_rvm = re.search(r"^static func read_version\(.*?(?=^func |^static func |\Z)", sm, re.M | re.S)
rv = code_only(_rvm.group(0) if _rvm else "")
if not all(k in rv for k in ("if not save.has(VERSION_KEY):\n\t\treturn 0", "typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT",
                             "if number < 0.0 or number != floorf(number):\n\t\treturn -1")):
    err(f"{SM}: read_version(): absent = 0; a non-number, negative or fractional version = -1 (malformed)")
mg = code_only(func_body(sm, "_migrate") or "")
steps = sorted(int(x) for x in re.findall(r"^\t\t\t(\d+):", mg, re.M))
if sv is not None and steps != list(range(int(sv))):
    err(f"{SM}: _migrate() needs exactly one step for each version 0..{int(sv) - 1 if sv else '?'} (found {steps})")
if not re.search(r"^\t\t\t0:\s*pass\b", mg, re.M):
    err(f"{SM}: _migrate() step 0 (a save from before M04.0) keeps every section as it is — only save_version was missing")
if not re.search(r"_:\s*push_warning\([^)]*\)\s*return \{\}", mg) or "version += 1" not in mg or "data[VERSION_KEY] = version" not in mg \
   or "save.duplicate(true)" not in mg:
    err(f"{SM}: _migrate() steps one version at a time on a copy, stamps the version, rejects an unknown step")
written = set(re.findall(r'^\t\t"(\w+)": ', sg, re.M))
typed = set(re.findall(r'^\t"(\w+)": \[', sm, re.M))
read = set(re.findall(r'data\.get\("(\w+)"', lg))
PRE_M04_SECTIONS = {"points": "TYPE_INT, TYPE_FLOAT", "discovered_ids": "TYPE_ARRAY", "journal_entries": "TYPE_DICTIONARY",
                    "daily_discovery": "TYPE_DICTIONARY", "farm": "TYPE_DICTIONARY", "settings": "TYPE_DICTIONARY"}
section_types = dict(re.findall(r'^\t"(\w+)": \[([^\]]*)\],', sm, re.M))
if any(section_types.get(k) != v for k, v in PRE_M04_SECTIONS.items()):
    err(f"{SM}: every section saved before M04.0 is still read with the type it was written with "
        f"(expected {PRE_M04_SECTIONS}) — old saves, incl. M03.3 farm plots, must keep loading")
vs = code_only(func_body(sm, "_valid_sections") or "")
if not re.search(r"for key: String in SECTION_TYPES:.*if allowed\.has\(typeof\(data\[key\]\)\):\s*valid\[key\] = data\[key\]\s*else:", vs, re.S) \
   or len(re.findall(r"\bvalid\b", vs)) != 3 or not re.search(r"return valid\s*$", vs):
    err(f"{SM}: _valid_sections() passes on only sections whose type is listed in SECTION_TYPES")
if not written or written != typed or typed != read:
    err(f"{SM}: every section written is type-checked and read back (written {sorted(written)}, typed {sorted(typed)}, read {sorted(read)})")
for f, s2 in scripts.items():
    if f.startswith("tools/") or f == SM: continue
    if re.search(r"FileAccess|DirAccess\.remove|\"user://|JSON\.(parse|stringify)|ConfigFile", code_only(s2)):
        err(f"{f}: file/JSON persistence outside SaveManager — the save is written and read only by SaveManager")
    if re.search(r"SaveManager\.(_\w+|SAVE_PATH)", code_only(s2)):
        err(f"{f}: reaches into SaveManager internals")
notes.append(f"save: save_version {int(sv) if sv is not None else sv} ({SM}); migration steps {steps}; sections {sorted(typed)}")

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
