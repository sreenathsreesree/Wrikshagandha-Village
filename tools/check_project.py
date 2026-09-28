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
if writers != ["_face_target", "_ready", "_update_facing"]:
    err(f"{PL}: _facing_angle may only be set in _ready/_update_facing/_face_target (found {writers})")
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
if not re.search(r"follow_camera\.target = player\s*follow_camera\.global_position = player\.global_position\s*area\.attach_player\(player\)", mready):
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
AUTOLOADS = ["PointsManager", "DiscoveryDatabase", "DiscoveryManager", "JournalManager", "CollectionManager", "DailyDiscoveryManager",
             "FarmManager", "ExplorationManager", "AmbientAudioManager", "SaveManager", "GameState", "InputManager"]
found_al = re.findall(r'^(\w+)="\*?res://', re.search(r"\[autoload\]\n(.*?)(?:\n\[|\Z)", cfg, re.S).group(1), re.M)
if found_al != AUTOLOADS:
    err(f"project.godot: autoloads changed {found_al} — adding one is a documented decision, never a side effect")
# Deliberate-change pins: files a milestone promised not to touch. Changing
# one is allowed only on purpose — update its pin in the same commit and
# say why in the plan.
PINNED = {"scripts/player/player.gd": "17c051f39f44d2e1", "scripts/autoload/input_manager.gd": "bd56f4c597de8b35",
          "scripts/camera/follow_camera.gd": "defdcc07193979c4", "scenes/camera/FollowCamera.tscn": "c6b25f3568d7b59a",
          "scenes/player/Player.tscn": "815b6bcf1df69d36", "scenes/ui/HUD.tscn": "bdeb7885881ba053"}
for f, h in PINNED.items():
    got = hashlib.sha256(open(f, "rb").read()).hexdigest()[:16] if os.path.exists(f) else None
    if got != h:
        err(f"{f}: changed (sha256 {got}, pinned {h}) — if deliberate, update the pin in tools/check_project.py and record why")
notes.append(f"persistent shell: Main owns {sorted(SHELL)}; startup {MAIN_SCENE}; {len(PINNED)} pinned files; {len(AUTOLOADS)} autoloads")

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
