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
if not re.search(r"_spent_interactables\.assign\(_spent_interactables\.filter\(\s*func\(spent: Variant\) -> bool: return is_instance_valid\(spent\)\s*\)\)", func_body(scripts.get(PL, ""), "_interact_with") or "") \
   or re.search(r"_spent_interactables\s*=\s*_spent_interactables\.filter", scripts.get(PL, "")):
    err(f"{PL}: _interact_with() prunes freed objects from the typed spent list with assign() (a plain = filter() aborts every interaction after a collection)")
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
                  "scripts/farming/farm_plot.gd": {"PLANT", "WATER", "HARVEST"},
                  # M08.1: a door offers its own verb, ENTER (a way in) or EXIT (a way out).
                  "scripts/world/area_door.gd": {"ENTER", "EXIT"},
                  # M08.3: an NPC offers TALK.
                  "scripts/npc/npc_talk.gd": {"TALK"}, **FIXTURES}
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
# (M09.2, D-42: WorldSimulation._process — the one driver of WorldClock.)
PER_FRAME = [('scripts/camera/follow_camera.gd', '_physics_process'), ('scripts/interactables/indicator_bob.gd', '_process'), ('scripts/npc/npc.gd', '_physics_process'), ('scripts/player/player.gd', '_physics_process'), ('scripts/ui/virtual_joystick.gd', '_process'), ('scripts/world/butterfly.gd', '_process'), ('scripts/world/drifting_leaf.gd', '_process'), ('scripts/world/floating_motes.gd', '_process'), ('scripts/world_simulation/environmental_event_controller.gd', '_process'), ('scripts/world_simulation/exploration_landmark_controller.gd', '_process'), ('scripts/world_simulation/time_of_day.gd', '_process'), ('scripts/world_simulation/vegetation_controller.gd', '_process'), ('scripts/world_simulation/wildlife_actor.gd', '_process'), ('scripts/world_simulation/wildlife_butterfly.gd', '_process'), ('scripts/world_simulation/world_simulation.gd', '_process')]
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
MAIN_GD, MEADOW_GD, GAME_AREA_GD = "scripts/main.gd", "scripts/world/meadow.gd", "scripts/world/game_area.gd"
mready = func_body(scripts.get(MAIN_GD, ""), "_ready") or ""
if not re.search(r"follow_camera\.target = player\s*_apply_camera_bounds\(\)\s*follow_camera\.snap_to_target\(\)\s*area\.attach_player\(player\)", mready):
    err(f"{MAIN_GD}: _ready() must point the camera at the player and hand the player to the area")
mcode = code_only(scripts.get(MEADOW_GD, ""))
if re.search(r"\$(Player|FollowCamera|HUD)\b|\bFollowCamera\b|\bHUD\b", mcode) or \
   "world_simulation.configure(player, directional_light, world_environment)" not in (func_body(scripts.get(MEADOW_GD, ""), "attach_player") or ""):
    err(f"{MEADOW_GD}: the area owns no shell node and gets the player only through attach_player()")
# M08.2a re-pinned deliberately: cell_height 0.25 -> 0.1 (the map's default cell height with it) and detail sampling
# 1 m / 0.05 m — the baked mesh had floated up to 0.62 m above the ground, beyond the agent's 0.4 m path reach, and
# tap-walks stalled near (-6, 1.4); agent_max_climb 0.25 -> 0.0 — the mesh had planned over the mounds' 0.15 m tiers,
# which the player's capsule cannot step (~0.065 m), stalling every walk across a mound (a 0.1 m climb still let the
# voxel-quantised tier through); every walkable surface here is flat. sim_nav_height checks both.
NAV_PINS = {"geometry_parsed_geometry_type": "1", "geometry_source_geometry_mode": "1", "geometry_source_group_name": '&"navigation_source"',
            "cell_size": "0.25", "cell_height": "0.1", "agent_height": "1.3", "agent_radius": "0.35", "agent_max_climb": "0.0", "agent_max_slope": "37.0",
            "detail_sample_distance": "1.0", "detail_sample_max_error": "0.05"}
if not re.search(r"^\[navigation\]\n\n3d/default_cell_height=0\.1$", cfg, re.M) or re.search(r"^3d/default_cell_size=", cfg, re.M):
    err("project.godot: the navigation map's default cell height is the mesh's 0.1 m (cell size stays the 0.25 m default) — sim_nav_height checks the height budget")
mead = open(MEADOW_SCENE, encoding="utf-8").read()
navm = re.search(r'\[sub_resource type="NavigationMesh"[^\]]*\]\n(.*?)\n\n', mead, re.S)
navsettings = dict(re.findall(r"^(\w+) = (.+)$", navm.group(1), re.M)) if navm else {}
if navsettings != NAV_PINS or not re.search(r'\[node name="Meadow" type="Node3D" groups=\["navigation_source"\]\]', mead) \
   or not re.search(r'\[node name="NavigationRegion3D" type="NavigationRegion3D" parent="\."\]', mead) \
   or "NavigationAgent3D" not in open(SHELL["Player"], encoding="utf-8").read() or "_bake_navigation()" not in (func_body(scripts.get(GAME_AREA_GD, ""), "_ready") or "") \
   or not re.search(r"^extends GameArea\s*\nclass_name MeadowArea", scripts.get(MEADOW_GD, ""), re.M) or func_body(scripts.get(MEADOW_GD, ""), "_ready") is not None:
    err("navigation: the Meadow keeps its NavigationRegion3D (settings unchanged, baked at load by GameArea from the navigation_source group); the Player keeps its NavigationAgent3D")
# M04.3 (O-14) added Inventory: after DiscoveryManager (it connects to it), before FarmManager and GameState.
# M05.1 (D-20) added Wallet (coins + ledger), before SaveManager and GameState (which loads the save).
# M06.2 (D-25) added Market (selling produce), after Inventory and Wallet, before GameState (which saves on a sale).
# M08.1 (D-34) added AreaRouter (travel requests between areas, the current area id; never saved), last.
# M09.2 (D-42) added WorldClock (the one game clock: day + fraction, saved), before SaveManager and GameState (which loads the save).
AUTOLOADS = ["PointsManager", "DiscoveryDatabase", "DiscoveryManager", "JournalManager", "CollectionManager", "DailyDiscoveryManager",
             "Inventory", "Wallet", "Market", "FarmManager", "ExplorationManager", "Relationships", "Requests", "Services", "AmbientAudioManager", "WorldClock", "SaveManager", "GameState", "InputManager",
             "AreaRouter"]
found_al = re.findall(r'^(\w+)="\*?res://', re.search(r"\[autoload\]\n(.*?)(?:\n\[|\Z)", cfg, re.S).group(1), re.M)
if found_al != AUTOLOADS:
    err(f"project.godot: autoloads changed {found_al} — adding one is a documented decision, never a side effect")
# Deliberate-change pins: files a milestone promised not to touch. Changing
# one is allowed only on purpose — update its pin in the same commit and
# say why in the plan.
PINNED = {"scripts/player/player.gd": "b609b46679af2a19", "scripts/autoload/input_manager.gd": "23c5bb6ebab73164",
          "scripts/camera/follow_camera.gd": "b76efe265c7b2004", "scenes/camera/FollowCamera.tscn": "c2887e1f37ed6277",
          "scenes/player/Player.tscn": "815b6bcf1df69d36", "scenes/ui/HUD.tscn": "c567a3c097843e8f",
          # M03.2 must not pull M03.3 forward: farm, save and game-state code untouched.
          # (HUD.tscn re-pinned deliberately by M04.5: Inventory button + screen;
          #  and by M06.3: the top-anchored top bar, bottom-right thumb buttons, the shared theme.)
          # (player.gd re-pinned deliberately by M08.1: _interact_with() keeps its spent list typed with assign() —
          #  the old "= filter()" raised a script error and aborted every interaction after a one-shot collection.)
          # (HUD.tscn re-pinned deliberately by M08.3: the SpeechPanel instance, docked by _apply_safe_area().)
          # (FollowCamera.tscn re-pinned deliberately by M07.3 (D-29): the SpringArm3D ignores geometry,
          #  collision_mask = 0 — the camera no longer collapses against the house or the monolith.)
          # (FarmManager and SaveManager re-pinned deliberately by M04.2: seeds/basket -> ItemStore, save v2;
          #  and by M04.3: the store moves to the Inventory autoload, save v3;
          #  SaveManager by M05.1: the wallet section, save v4; by M05.2: the exploration section, save v5.)
          # (GameState re-pinned deliberately by M06.2: it also saves after a sale, Market.produce_sold;
          #  by M08.5: it also saves when an NPC's friendship rises, Relationships.friendship_changed;
          #  by M08.6: it also saves when a request is accepted or completed;
          #  and by M08.7: it also saves after an NPC trade, Market.items_traded.)
          # (SaveManager re-pinned deliberately by M08.5: the relationships section, save v6 — D-17, D-38;
          #  and by M08.6: the requests section, save v7 — D-17, D-39;
          #  and by M09.2: the world_time section (WorldClock's day and fraction), save v8 — D-17, D-42.)
          # (farm_plot.gd re-pinned deliberately by M08.1: restore() replaces a crop visual the plot already shows,
          #  so a parked area's live plots are restored in place, never doubled — D-31, D-33.)
          "scripts/autoload/farm_manager.gd": "21c7e9be70c17230", "scripts/farming/farm_plot.gd": "ed0ea77b157b7d08",
          "scripts/autoload/save_manager.gd": "81d49237bccad2dd", "scripts/autoload/game_state.gd": "6c25394b3d7a4368",
          # M03.3 persists farm plots only: discovery respawns, environmental events and time of day stay as they were.
          # (discovery_spawn_point.gd re-pinned deliberately by M05.3: a claimed once-ever discovery isn't spawned;
          #  farm_manager.gd by M05.3: milestone bonuses from reward data;
          #  and by M06.4: every milestone reward looked up by id in _reach(), one reward path.)
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
# M08.1: the game's one way to swap is AreaRouter.travel_requested -> Main._on_travel_requested ->
# _swap_area (after the fade covers); load_area() stays the debugger's plain swap, called by nothing.
callers = [f for f, s2 in scripts.items() if f != MAIN_GD and re.search(r"\bload_area\(|_swap_area", code_only(s2))]
swap_sites = re.findall(r"^func (\w+)\(", main_src, re.M)
swap_sites = sorted(fn for fn in swap_sites if re.search(r"\b_swap_area\b", code_only(func_body(main_src, fn) or "")) and fn != "_swap_area")
if callers or swap_sites != ["_on_travel_requested", "load_area"] or len(re.findall(r"\b_swap_area\b", code_only(main_src))) != 3:
    err(f"the area swap is reached only from load_area() (debugger) and Main._on_travel_requested() (found {callers}, {swap_sites})")
for path in glob.glob("**/*.tscn", recursive=True):
    if "load_area" in open(path, encoding="utf-8").read():
        err(f"{path}: connects to load_area — travel goes through AreaRouter (M08.1)")
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
AREA_SCENES = [MEADOW_SCENE, "scenes/world/HomeInterior.tscn"]  # M08.1: one AreaCameraBounds per area scene
if sorted(bounds_nodes) != sorted(AREA_SCENES) or any(len(v) != 1 for v in bounds_nodes.values()):
    err(f"camera bounds: exactly one AreaCameraBounds in each area {AREA_SCENES} (found {[(p, len(v)) for p, v in bounds_nodes.items()]}) — never in Main")
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
# M08.1 (D-32): besides the zoom input, Main sets an area's fixed camera distance (and gives the player's
# own zoom back) — only in _apply_camera_distance(), which reads it from the area's data.
acd = code_only(func_body(main_src, "_apply_camera_distance") or "")
zcalls_outside = [(f, n) for f, n in zcalls if not (f == MAIN_GD and n == "set_zoom_distance")]
if len(re.findall(r"set_zoom_distance", code_only(main_src))) != len(re.findall(r"set_zoom_distance", acd)) or acd.count("set_zoom_distance") != 2 \
   or "definition.camera_distance" not in acd:
    err(f"{MAIN_GD}: an area's camera distance is set only by _apply_camera_distance(), from its AreaDefinition")
if zcalls_outside != [(MAIN_GD, "zoom_by")] or "InputManager.zoom_requested.connect(follow_camera.zoom_by)" not in (func_body(main_src, "_ready") or "") \
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
               "discovery_id": "String", "sell_value": "int"}
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
   or "@export var quality_levels: int = 1" not in idf or '@export var discovery_id: String = ""' not in idf \
   or "@export var sell_value: int = 0" not in idf:
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
                  "discovery": vals.get("discovery_id", '""').strip('"'), "sell_value": vals.get("sell_value", "0")}
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
    # M06.2 (D-25): only produce sells; every produce item has a whole price >= 1; seeds and collectibles never sell.
    sv = items[iid]["sell_value"]
    if not re.fullmatch(r"\d+", sv) or (items[iid]["category"] == "produce") != (int(sv) >= 1):
        err(f"{f}: sell_value {sv} — only produce sells (a whole sell_value >= 1); seeds and collectibles stay unsellable (0)")
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
    if f not in (FM, INV, "scripts/autoload/market.gd", "scripts/autoload/requests.gd") and re.search(r"\bInventory\.(add|remove)\(", code):
        err(f"{f}: changes the player's items — only FarmManager's seed/basket rules, Inventory's discovery rewards, the Market's sale and a completed request (M08.6) do")

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
    # M06.2: the basket may hold the one sale being chosen (not counts) — nothing else.
    if re.findall(r"^var (\w+)", code, re.M) != ([] if f == SP else ["_pending"]):
        err(f"{f}: a filtered view keeps no state of its own (member vars; the basket only its pending sale)")
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
                 r'rows\.append\(\{"crop": crop, "item": held\[crop\.crop_id\]\.item, "total": held\[crop\.crop_id\]\.total, "counts": held\[crop\.crop_id\]\.counts\}\)\s*return rows\s*$', br) \
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
# M06.2: a sale changes items without any farm signal, so the basket (its view)
# and the HUD's basket button (its visibility) also refresh on items_changed.
ITEMS_CHANGED_LISTENERS = {IS: "Inventory.items_changed.connect(_on_items_changed)", BS: "Inventory.items_changed.connect(_on_produce_changed)",
                           "scripts/ui/hud.gd": "Inventory.items_changed.connect(_update_basket_button)"}
for f in scripts:
    code = code_only(scripts[f])
    if f == INV or "items_changed" not in code:
        continue
    if f not in ITEMS_CHANGED_LISTENERS or code.count("items_changed.connect(") != 1 or ITEMS_CHANGED_LISTENERS[f] not in (func_body(scripts[f], "_ready") or ""):
        err(f"{f}: listens to items_changed — only the Inventory screen, the basket and the HUD's basket button do (the picker keeps FarmManager's post-planting signal)")
for f, line in ITEMS_CHANGED_LISTENERS.items():
    if line not in (func_body(scripts.get(f, ""), "_ready") or ""):
        err(f"{f}: refreshes on Inventory.items_changed ({line})")
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
    if re.search(r"\bWallet\.debit\(", code):
        err(f"{f}: spends coins — M06.2 is earn-only (D-25): no coin sink exists")
    credits = [fn for fn in re.findall(r"^func (\w+)\(", s2, re.M) if re.search(r"\bWallet\.credit\(", code_only(func_body(s2, fn) or ""))]
    if re.search(r"\bWallet\.credit\(", code) and (f != "scripts/autoload/market.gd" or credits != ["sell", "trade"] or code.count("Wallet.credit(") != 2):
        err(f"{f}: credits coins — the coin sources are selling produce and NPC trades, both in the Market: Market.sell() and Market.trade() are the only callers of Wallet.credit(), once each (D-25 as amended by D-40; points and coins independent, D-24)")
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
    err("Wriksha Points and coins are permanently independent (O-02 closed, D-24)")
if not any("Wallet.credit(" in code_only(s2) for s2 in scripts.values()):
    err("Market.sell() credits the Wallet — selling produce is the one coin source (D-25)")
notes.append(f"wallet: ledger-derived balance, API {len(WL_API)} functions; one credit caller (Market.sell), no debit")

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
if not re.search(r"^extends RefCounted\s*\nclass_name RewardRules", rs_src, re.M) or list(rsf) != ["_init", "has", "points", "thresholds"] \
   or not re.search(r"func has\(rule_id: String\) -> bool:\s*return _rules\.has\(rule_id\)\s*$", rsf.get("has", "")) \
   or 'const REWARDS_PATH := "res://data/rewards/"' not in rs_src or "ResourceDirectory.list_tres_paths(REWARDS_PATH)" not in rsf.get("_init", "") \
   or 'rule == null or rule.id == "" or rule.points < 0 or rule.threshold < 0 or _rules.has(rule.id)' not in rsf.get("_init", "") \
   or re.findall(r"^var (\w+)", code_only(rs_src), re.M) != ["_rules"] \
   or any(re.search(r"\b_rules\s*(\[[^\]]*\]\s*=[^=]|=[^=]|\.(erase|clear|merge)\b)", b) for fn, b in rsf.items() if fn != "_init") \
   or not re.search(r"if rule == null:\s*push_warning\(.*?\)\n\s*return 0\s*return rule\.points", rsf.get("points", "")) \
   or not re.search(r"if rule\.threshold > 0:\s*result\[rule\.threshold\] = rule\.points", rsf.get("thresholds", "")):
    err(f"{RRS}: RewardRules (a RefCounted) loads data/rewards/ via ResourceDirectory, read-only, has(id), points(id) (0 + warning if unknown), thresholds()")
# Farm milestones (M06.4, D-27): the registered milestone ids — FarmManager.get_milestones()'s rows: its
# constants, plus "grown:<crop>" for every starter crop (starting_seeds > 0) — are the progression hooks.
fm_src_m = scripts.get("scripts/autoload/farm_manager.gd", "")
starter_crops = set()
for f in glob.glob("data/crops/*.tres"):
    t = open(f, encoding="utf-8").read()
    cid, st = re.search(r'crop_id = "([^"]+)"', t), re.search(r"^starting_seeds = (\d+)", t, re.M)
    if cid and int(st.group(1) if st else 1) > 0:
        starter_crops.add(cid.group(1))
def fm_const(name):
    m = re.search(rf'^const {name} := "([^"]*)"', fm_src_m, re.M)
    return m.group(1) if m else None
gm = code_only(func_body(fm_src_m, "get_milestones") or "")
MILESTONE_CONSTS = re.findall(r"_milestone_row\(([A-Z_]+),", gm)
FARM_MILESTONES = {fm_const(c) for c in MILESTONE_CONSTS} | ({fm_const("CROP_GROWN_PREFIX") + c for c in starter_crops}
                                                              if "_milestone_row(CROP_GROWN_PREFIX + crop.crop_id," in gm else set())
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
used |= FARM_MILESTONES & set(rules)            # a farm milestone pays its rule through _reach() (M06.4)
for rid in sorted(used - set(rules)):
    err(f"a reward '{rid}' is paid in code but has no data/rewards/{rid}.tres")
unused = {r for r, (_, t) in rules.items() if not t} - used
if unused:
    err(f"data/rewards: rules no code pays {sorted(unused)}")
PAY_SITES = {("scripts/autoload/discovery_manager.gd", "discover"): 1, ("scripts/farming/farm_plot.gd", "_run_harvest_sequence"): 1,
             ("scripts/autoload/farm_manager.gd", "_reach"): 1, ("scripts/autoload/daily_discovery_manager.gd", "_on_discovery_made"): 1,
             (EXF, "_on_discovery_made"): 1, (EXF, "mark_landmark_reached"): 1, (EXF, "mark_secret_location_found"): 2,
             (EXF, "_maybe_award_curiosity_bonus"): 1, ("scripts/autoload/requests.gd", "complete"): 1}  # M08.6 (D-39): a completed request, once
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

# ------------------------------------------------------------ points and coins independent (M05.5, D-24)
# O-02 closed: Wriksha Points (PointsManager, the score) and coins (Wallet)
# are permanently independent — no conversion, no mirroring, no bridge in
# either direction; no current coin sources or sinks; EconomyConfig is no
# rate. The point reward paths are exactly the audited ones.
PMF, WLF = "scripts/autoload/points_manager.gd", "scripts/autoload/wallet.gd"
pm_src = scripts.get(PMF, "")
if re.search(r"\bWallet\b|\bcoins?\b|balance|ledger|credit|debit|Economy", code_only(pm_src), re.I):
    err(f"{PMF}: PointsManager never references the Wallet, coins or the economy configuration")
if re.search(r"\bPointsManager\b|\bpoints_changed\b|add_points|set_points|get_points|\bEconomyConfig\b|economy_config", code_only(scripts.get(WLF, ""))):
    err(f"{WLF}: the Wallet never references PointsManager, points or the economy configuration")
PM_FUNCS = {"add_points": "dec5bed36182", "set_points": "0257bfe4b241", "get_points": "f81f6d9b791c"}
pm_now = {n: _hash_body(pm_src, n) for n in re.findall(r"^func (\w+)\(", pm_src, re.M)}
if pm_now != PM_FUNCS or re.findall(r"^var (\w+)", code_only(pm_src), re.M) != ["points"] or not re.search(r"^signal points_changed\(total: int\)$", pm_src, re.M):
    err(f"{PMF}: the points API and behaviour are unchanged by M05.5 (found {pm_now})")
BRIDGE = re.compile(r"(?i)\w*(points?_?to_?coins?|coins?_?to_?points?|convert\w*|conversion|exchange_rate|mirror\w*)\b")
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    code = code_only(s2)
    if f != PMF and re.search(r"PointsManager\.points\s*(=[^=]|\+=|-=)", code):
        err(f"{f}: writes PointsManager.points directly — points change only through PointsManager's methods")
    if re.search(r"\bWallet\.", code) and re.search(r"\bPointsManager\.", code) and f != "scripts/autoload/save_manager.gd":
        err(f"{f}: touches both PointsManager and the Wallet — nothing bridges points and coins")
    if re.search(r"balance_changed\.connect\(", code) and (f != BS or code.count("balance_changed.connect(") != 1
                                                           or "Wallet.balance_changed.connect(_on_balance_changed)" not in code):
        err(f"{f}: listens to the coin balance — only the basket's coin label does (and never a points bridge)")
    if f != "scripts/ui/hud.gd" and re.search(r"points_changed\.connect\(", code):
        err(f"{f}: listens to the points total — only the HUD shows it; nothing mirrors it")
    m = BRIDGE.search(code)
    if m:
        err(f"{f}: '{m.group(0)}' — no points <-> coins conversion or mirroring exists (D-24)")
for line in code_only(func_body(scripts.get("scripts/autoload/save_manager.gd", ""), "save_game") or "").splitlines() + \
            code_only(func_body(scripts.get("scripts/autoload/save_manager.gd", ""), "load_game") or "").splitlines():
    if "Wallet" in line and "Points" in line:
        err(f"scripts/autoload/save_manager.gd: '{line.strip()}' — points and coins are saved and loaded independently")
for f in glob.glob("data/rewards/*.tres"):
    keys = set(re.findall(r'^(\w+) = ', open(f, encoding="utf-8").read().split("[resource]", 1)[-1], re.M))
    if not keys <= {"script", "id", "points", "threshold"}:
        err(f"{f}: a reward rule pays Wriksha Points only (found {sorted(keys)})")
notes.append("points and coins: independent (D-24) — no bridge, no conversion; coins only from selling produce, no sinks")

# ------------------------------------------------------------ selling produce (M06.2, O-01 closed -> D-25)
# The one coin source: the Market autoload sells produce the player holds.
# Only produce with a sell_value sells; one unit's price is its sell_value x
# the quality's percent (data/market/sell_rules.tres) / 100, rounded half up
# in whole numbers, then x the quantity. A sale validates everything, then
# removes the items, credits the Wallet once ("sell:<item_id>:<quality>"),
# puts the items back if the credit is refused, and announces produce_sold,
# on which GameState saves (items and wallet together). The Market knows no
# points, no farm points scale and no redemption reference; no sink exists.
MK, SR_GD, SR_TRES = "scripts/autoload/market.gd", "scripts/economy/sell_rules.gd", "data/market/sell_rules.tres"
mk_src = scripts.get(MK, "")
mk_code = code_only(mk_src)
mkf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", mk_src, re.M | re.S)}
def body_lines(fn): return [l.strip() for l in mkf.get(fn, "").splitlines()[1:] if l.strip()]
if not mk_src.startswith("extends Node\n") or re.search(r"^class_name", mk_src, re.M) \
   or list(mkf) != ["_ready", "get_unit_price", "sell", "_unit_coins", "trade"] or re.findall(r"^var (\w+)", mk_code, re.M) != ["_quality_percents"] \
   or re.findall(r"^signal .*$", mk_src, re.M) != ["signal produce_sold(item_id: String, quality: int, quantity: int, coins: int)",
                                                   "signal items_traded(item_id: String, quantity: int, coins: int)"] \
   or re.findall(r"^const (\w+) := (.+)$", mk_code, re.M) != [("SELL_RULES_PATH", '"res://data/market/sell_rules.tres"')]:
    err(f"{MK}: the Market is a plain autoload Node — _ready/get_unit_price/sell/_unit_coins and (M08.7) trade, the rules' percents, the produce_sold and items_traded signals")
if re.search(r"\bPointsManager\b|\bpoints?\b|points_value|QUALITY_POINT_SCALE|add_points|EconomyConfig|economy_config|SaveManager|save_game"
             r"|FarmManager|DiscoveryManager|ExplorationManager|DailyDiscoveryManager|RewardRules?|_process|Timer|create_timer", mk_code):
    err(f"{MK}: the Market prices from item data and the sell rules only — never points, the farm's points scale, the redemption reference, saving or other systems")
if body_lines("_ready") != ["var rules := load(SELL_RULES_PATH) as SellRules", "if rules == null:",
                            'push_warning("Market: %s is not a SellRules resource; nothing can be sold" % SELL_RULES_PATH)', "return",
                            "_quality_percents = rules.quality_percents.duplicate()"]:
    err(f"{MK}: _ready() takes the quality percents from the one SellRules file, and sells nothing without it")
if body_lines("_unit_coins") != ["if quality >= _quality_percents.size():", "return 0", '@warning_ignore("integer_division")',
                                 "return (item.sell_value * _quality_percents[quality] + 50) / 100"]:
    err(f"{MK}: one unit = sell_value x the quality's percent / 100, rounded half up in whole numbers")
if body_lines("get_unit_price") != ["var item := Inventory.get_definition(item_id)",
                                    'if item == null or item.category != "produce" or item.sell_value < 1:', "return 0",
                                    "if quality < 0 or quality >= item.quality_levels:", "return 0", "return _unit_coins(item, quality)"]:
    err(f"{MK}: get_unit_price() is 0 for anything unsellable, else one unit's coins")
SELL_BODY = ["var item := Inventory.get_definition(item_id)",
             "if item == null:", "return 0",
             'if item.category != "produce":', "return 0",
             "if item.sell_value < 1:", "return 0",
             "if quality < 0 or quality >= item.quality_levels:", "return 0",
             "if quantity < 1:", "return 0",
             "if not Inventory.has(item_id, quantity, quality):", "return 0",
             "var coins := _unit_coins(item, quality) * quantity",
             "if coins < 1:", "return 0",
             "if not Inventory.remove(item_id, quantity, quality):", "return 0",
             'if not Wallet.credit(coins, "sell:%s:%d" % [item_id, quality]):',
             "Inventory.add(item_id, quantity, quality)", "return 0",
             "produce_sold.emit(item_id, quality, quantity, coins)",
             "return coins"]
if body_lines("sell") != SELL_BODY or not mkf.get("sell", "").startswith("func sell(item_id: String, quality: int, quantity: int) -> int:"):
    err(f"{MK}: sell() validates (item, produce, sell_value, quality, quantity, held), prices, removes, credits once as "
        f"\"sell:<item_id>:<quality>\", restores the exact items if the credit is refused, then announces — in that order")
TRADE_BODY = ["var item := Inventory.get_definition(item_id)", "if item == null:", "return 0", 'if item.category != "collectible":', "return 0",
              "if item.quality_levels != 1:", "return 0", "if quantity < 1 or coins < 1:", "return 0",
              "if not Inventory.has(item_id, quantity, 0):", "return 0", "if not Inventory.remove(item_id, quantity, 0):", "return 0",
              'if not Wallet.credit(coins, "trade:%s" % service_id):', "Inventory.add(item_id, quantity, 0)", "return 0",
              "items_traded.emit(item_id, quantity, coins)", "return coins"]
if body_lines("trade") != TRADE_BODY or not mkf.get("trade", "").startswith("func trade(item_id: String, quantity: int, coins: int, service_id: String) -> int:"):
    err(f"{MK}: trade() (M08.7, D-40) validates (item, collectible, single quality, quantity, coins, held), removes, credits once as "
        f"\"trade:<service_id>\", restores the exact items if the credit is refused, then announces — in that order, never points")
if [len(re.findall(r"\bInventory\.(add|remove)\(", mkf.get(fn, ""))) for fn in ("sell", "trade")] != [2, 2] or len(re.findall(r"\bInventory\.(add|remove)\(", mk_code)) != 4 \
   or mk_code.count("produce_sold.emit(") != 1 or mk_code.count("items_traded.emit(") != 1 or "items_traded" in mkf.get("sell", "") or "produce_sold" in mkf.get("trade", ""):
    err(f"{MK}: the Market changes items only in sell() and trade() (one removal, one restore each) and announces each sale and each trade once")
sr_src = scripts.get(SR_GD, "")
if not re.search(r"^extends Resource\s*\nclass_name SellRules", sr_src, re.M) \
   or re.findall(r"^@export var (\w+): (.+?) = (.+)$", sr_src, re.M) != [("quality_percents", "Array[int]", "[]")] \
   or re.search(r"^(func|var|const|signal|static) ", code_only(sr_src), re.M):
    err(f"{SR_GD}: SellRules is a Resource with exactly quality_percents (Array[int]) and no logic")
sr_files = sorted(glob.glob("data/market/*.tres"))
QUALITY_GOOD = int(const_val(fm_src, "QUALITY_GOOD") or -1)
if sr_files != [SR_TRES]:
    err(f"data/market: exactly one sell rules file ({SR_TRES}) (found {sr_files})")
else:
    txt = open(SR_TRES, encoding="utf-8").read()
    pm_ = re.search(r"^quality_percents = Array\[int\]\(\[([^\]]*)\]\)$", txt, re.M)
    pct = [int(x) for x in pm_.group(1).split(",")] if pm_ and re.fullmatch(r"\s*\d+(\s*,\s*\d+)*\s*", pm_.group(1)) else []
    if f'path="res://{SR_GD}"' not in txt or 'script_class="SellRules"' not in txt or len(pct) != QUALITY_LEVELS \
       or min(pct or [0]) < 1 or pct != sorted(pct) or not (0 <= QUALITY_GOOD < len(pct) and pct[QUALITY_GOOD] == 100):
        err(f"{SR_TRES}: one whole percent >= 1 per quality level ({QUALITY_LEVELS}), rising with quality, Good = 100 (sell_value is the Good price) — {pct}")
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    code = code_only(s2)
    if f not in (MK, ITEM_GD) and re.search(r"\bsell_value\b", code):
        err(f"{f}: reads sell_value — prices come only from the Market (get_unit_price)")
    if f != MK and re.search(r"res://data/market|\bSellRules\b", code) and f != SR_GD:
        err(f"{f}: reads the sell rules — only the Market does")
    if f != BS and re.search(r"\bMarket\.sell\(", code):
        err(f"{f}: sells — only the basket's Confirm asks the Market to sell")
    if f not in ("scripts/autoload/game_state.gd", "scripts/ui/hud.gd") and "produce_sold.connect(" in code:
        err(f"{f}: listens to sales — only GameState (to save) and the HUD (to show the coins) do")
gs_src = scripts.get("scripts/autoload/game_state.gd", "")
if "Market.produce_sold.connect(_save.unbind(4))" not in (func_body(gs_src, "_ready") or ""):
    err("scripts/autoload/game_state.gd: GameState saves after every sale (Market.produce_sold) — items and wallet in one save")
if not (0 <= found_al.index("Inventory") < found_al.index("Market") and found_al.index("Wallet") < found_al.index("Market") < found_al.index("GameState")
        if all(n in found_al for n in ("Inventory", "Wallet", "Market", "GameState")) else False) or found_al.count("Market") != 1:
    err("project.godot: exactly one Market autoload, after Inventory and Wallet and before GameState")
hud_ps = code_only(func_body(hud_src, "_on_produce_sold") or "")
if "Market.produce_sold.connect(_on_produce_sold)" not in (func_body(hud_src, "_ready") or "") \
   or '"+%d Coins" % coins' not in hud_ps or re.search(r"Points|✿|PointsManager", hud_ps):
    err("scripts/ui/hud.gd: a sale shows \"+N Coins\" on the shared card — coins, never points")
bs_code = code_only(bs_src)
bsf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", bs_src, re.M | re.S)}
if re.search(r"\bPointsManager\b|points_changed|✿|Wallet\.(credit|debit|get_ledger|can_afford)\(", bs_code) \
   or re.findall(r"\bWallet\.\w+", bs_code) != ["Wallet.balance_changed", "Wallet.get_balance"] \
   or '"Coins %d" % balance' not in bsf.get("_on_balance_changed", ""):
    err(f"{BS}: the basket shows the coin balance (\"Coins N\") from the Wallet's balance — never points, never spending")
if bs_code.count("Market.sell(") != 1 or "Market.sell(" not in bsf.get("_on_confirm_pressed", "") \
   or not re.search(r'var quantity := clampi\(int\(_pending\["quantity"\]\), 1, maxi\(held, 1\)\)', bsf.get("_update_sell_panel", "")) \
   or "confirm_button.disabled = held < quantity or coins < 1" not in bsf.get("_update_sell_panel", "") \
   or "var coins := Market.get_unit_price(item.id, quality) * quantity" not in bsf.get("_update_sell_panel", "") \
   or "Inventory.get_view(\"produce\")" not in bsf.get("_held", "") \
   or "_pending = {}" not in bsf.get("_close_sell_panel", "") or "_close_sell_panel()" not in bsf.get("open", ""):
    err(f"{BS}: selling is confirm-first — a quantity stepper within 1..held, the Market's price x quantity shown, one Market.sell() on Confirm")
notes.append(f"selling: Market.sell() the one coin source (produce only, {sum(1 for v in items.values() if v['category'] == 'produce')} items); "
             f"quality percents from {SR_TRES}; round half up per unit; GameState saves on produce_sold")

# ------------------------------------------------------------ farm milestones through progression hooks (M06.4, D-27)
# One reward path: every farm milestone goes through FarmManager._reach(id, message), which records it
# once ever, pays the reward the reward data names for that id (no rule = nothing), opens the plots
# waiting on it and announces it — in that order. No caller chooses an amount. The ids are the hooks:
# plots' unlock_on_milestone, MilestoneReveals' milestone_id, farm reward rules and the Journal's
# get_milestones() all name registered milestones. Milestones are reached only from game events.
fmm = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", fm_src_m, re.M | re.S)}
REACH_BODY = ["if _milestones_reached.has(milestone_id):", "return false", "_milestones_reached.append(milestone_id)",
              "var bonus_points := _rewards.points(milestone_id) if _rewards.has(milestone_id) else 0",
              "if bonus_points > 0:", "PointsManager.add_points(bonus_points)",
              "if _unlock_plots_for(milestone_id) > 0:", 'message += " There\'s room to grow a little more."',
              "milestone_reached.emit(milestone_id, message, bonus_points)", "return true"]
reach_lines = [l.strip() for l in fmm.get("_reach", "").splitlines()[1:] if l.strip()]
if reach_lines != REACH_BODY or not fmm.get("_reach", "").startswith("func _reach(milestone_id: String, message: String) -> bool:"):
    err(f"{FM}: _reach(id, message) is the one milestone path — once ever, the id's reward from reward data, unlocks, then the announcement")
fm_code_m = code_only(fm_src_m)
if fm_code_m.count("milestone_reached.emit(") != 1 or re.findall(r"\b_rewards\.\w+", fm_code_m) != ["_rewards.points", "_rewards.has"] \
   or "_rewards = RewardRules.new()" not in fmm.get("_ready", "") or "PointsManager" in fm_code_m.replace(fmm.get("_reach", ""), ""):
    err(f"{FM}: milestone rewards are read only in _reach(); nothing else in FarmManager pays or announces a milestone")
reach_calls = re.findall(r"\b_reach\((.*)\)", fm_code_m.replace(fmm.get("_reach", ""), ""))
callers = sorted(fn for fn, body in fmm.items() if fn != "_reach" and "_reach(" in body)
if callers != ["choose_seed", "notify_crop_harvested", "notify_crop_ready"]:
    err(f"{FM}: milestones are reached only from game events — planting, ripening, harvesting (found in {callers})")
for call in reach_calls:
    first = call.split(",")[0].strip()
    depth = 0; commas = 0
    for ch in call:
        depth += ch in "([{"; depth -= ch in ")]}"
        commas += ch == "," and depth == 0
    if commas != 1:
        err(f"{FM}: _reach({call}) — a milestone call names the id and the message only; the reward comes from data")
    if not (first == "CROP_GROWN_PREFIX + crop_definition.crop_id" or (re.fullmatch(r"[A-Z_]+", first) and first in MILESTONE_CONSTS)):
        err(f"{FM}: _reach({first}, …) — every milestone reached is registered in get_milestones()")
reached_consts = {c.split(",")[0].strip() for c in reach_calls}
if set(MILESTONE_CONSTS) - reached_consts or "CROP_GROWN_PREFIX + crop_definition.crop_id" not in reached_consts:
    err(f"{FM}: every registered milestone can be reached (unreached: {sorted(set(MILESTONE_CONSTS) - reached_consts)})")
if len(FARM_MILESTONES) != len(MILESTONE_CONSTS) + len(starter_crops) or None in FARM_MILESTONES:
    err(f"{FM}: get_milestones() lists each milestone once, with its id constant")
for scene in glob.glob("scenes/**/*.tscn", recursive=True):
    for hook in re.findall(r'^(?:unlock_on_milestone|milestone_id) = "([^"]*)"$', open(scene, encoding="utf-8").read(), re.M):
        if hook not in FARM_MILESTONES:
            err(f"{scene}: a milestone hook names '{hook}', which is not a registered farm milestone {sorted(FARM_MILESTONES)}")
rule_like = {r for r in rules if r.startswith(("first_", "garden_", "all_starter", "grown"))}
if rule_like - FARM_MILESTONES:
    err(f"data/rewards: farm-milestone rules {sorted(rule_like - FARM_MILESTONES)} name no registered milestone")
notes.append(f"farm milestones: {len(FARM_MILESTONES)} registered, {len(FARM_MILESTONES & set(rules))} rewarded by data; one path (_reach); hooks checked")

# ------------------------------------------------------------ farming frozen (M06.5, D-11)
# Phase 06 leaves FarmManager with farm rules, plots, crops, milestones and the farm save; seeds and
# produce are the Inventory's, coins the Market's, reward amounts data. The boundary is frozen: the
# public API (signals with their exact signatures, functions, the constants others read), FarmPlot's
# calls into it and the farm save keys are pinned here; behaviour stays pinned by the whole-file
# pins of farm_manager.gd / farm_plot.gd. A deliberate change updates these lists and ARCHITECTURE §8.
FM_SIGNALS = ["crop_planted(crop_definition: CropDefinition, announced_by_milestone: bool, soil: int)",
              "crop_harvested(crop_definition: CropDefinition, points_awarded: int, quality: int, care: int)",
              "seeds_changed", "produce_changed", "seed_choice_requested", "seed_choice_closed",
              "seed_found(crop_definition: CropDefinition, new_crop: bool)",
              "milestone_reached(milestone_id: String, message: String, bonus_points: int)", "garden_interest_changed(level: float)"]
FM_PUBLIC = ["get_crops", "get_seed_count", "get_known_crops", "rate_soil", "get_soil_rating", "rate_care", "combine_quality",
             "get_care_note", "get_quality_name", "get_soil_note", "get_quality_size", "get_harvest_points", "get_produce_count",
             "get_produce_total", "get_basket", "get_found_seed_origins", "has_ready_crops", "get_last_ripened_msec",
             "get_garden_interest", "is_garden_found", "register_plot", "release_plots_in", "unlock_plot", "get_plot_counts",
             "is_choosing_seed", "request_seed_choice", "cancel_seed_choice", "choose_seed", "notify_crop_ready",
             "notify_crop_harvested", "notify_place_reached", "get_milestones", "is_milestone_reached", "get_grown_crop_names",
             "get_activity_counts", "get_save_data", "apply_save_data"]
FM_SHARED_CONSTS = {"QUALITY_PLAIN", "QUALITY_GOOD", "QUALITY_FINE", "CARE_CAREFUL", "SOIL_MEMORY", "GARDEN_IN_BLOOM", "WILDLIFE_ATTRACTION_KEY"}
FP_USES = {"register_plot", "request_seed_choice", "cancel_seed_choice", "notify_crop_ready", "notify_crop_harvested", "rate_care",
           "combine_quality", "get_harvest_points", "get_quality_size", "QUALITY_GOOD", "CARE_CAREFUL", "SOIL_MEMORY"}
FARM_SAVE_KEYS = ["version", "starter_seeds", "found_seeds", "grown", "milestones", "counts", "harvested_plots", "garden_found", "plots"]
fm_f = scripts.get(FM, "")
if re.findall(r"^signal (.+)$", fm_f, re.M) != FM_SIGNALS:
    err(f"{FM}: farming is frozen (M06.5) — FarmManager's signals and their signatures are {FM_SIGNALS}")
fm_public_now = re.findall(r"^func ([a-z]\w*)\(", fm_f, re.M)
if fm_public_now != FM_PUBLIC:
    err(f"{FM}: farming is frozen (M06.5) — FarmManager's public functions are exactly {FM_PUBLIC} (found {fm_public_now})")
fm_api = set(FM_PUBLIC) | {re.match(r"\w+", x).group(0) for x in FM_SIGNALS} | FM_SHARED_CONSTS
for f, s2 in scripts.items():
    if f.startswith("tools/") or f == FM: continue
    for name in set(re.findall(r"\bFarmManager\.(\w+)", code_only(s2))):
        if name.startswith("_") or name not in fm_api:
            err(f"{f}: uses FarmManager.{name} — outside FarmManager only its frozen public API is used (ARCHITECTURE §8)")
fp_uses = set(re.findall(r"\bFarmManager\.(\w+)", code_only(scripts.get(FP, ""))))
if fp_uses != FP_USES:
    err(f"{FP}: FarmPlot talks to FarmManager only through {sorted(FP_USES)} (found {sorted(fp_uses)})")
for c in FM_SHARED_CONSTS:
    if not re.search(rf"^const {c} := ", fm_f, re.M):
        err(f"{FM}: the shared constant {c} stays")
fsd_m = re.search(r"return \{(.*?)\n\t\}", code_only(func_body(fm_f, "get_save_data") or ""), re.S)
if not fsd_m or re.findall(r'^\s*"(\w+)":', fsd_m.group(1), re.M) != FARM_SAVE_KEYS \
   or '"version": SAVE_VERSION,' not in fsd_m.group(1) or not re.search(r"^const SAVE_VERSION := 1$", fm_f, re.M):
    err(f"{FM}: the farm save section keeps exactly {FARM_SAVE_KEYS} with its own version 1 (save_version 5 compatibility)")
if "scripts/autoload/farm_manager.gd" not in PINNED or "scripts/farming/farm_plot.gd" not in PINNED:
    err("farming is frozen: farm_manager.gd and farm_plot.gd stay pinned by content")
notes.append(f"farming frozen: FarmManager {len(FM_SIGNALS)} signals, {len(FM_PUBLIC)} public functions, {len(FM_SHARED_CONSTS)} shared constants; "
             f"FarmPlot {len(FP_USES)} calls; farm save keys {len(FARM_SAVE_KEYS)}")

# ------------------------------------------------------------ vertical slice placement (M07.2)
# The approved M07.1 layout (docs/VERTICAL_SLICE_LAYOUT.md) is placed in the Meadow under one
# VerticalSlice node: placeholders only, and "placement needs no code" — no script on any of its
# nodes, none in the two new prop scenes, and no script that names them. The house is a plain
# StaticBody3D (the navigation bake from the navigation_source group avoids it); the NPC spot is a
# marker without a collider; the door is a plain marker — the Meadow's only AreaEntry stays
# meadow_start until M08.1 adds the door's (so Main._find_entry's fallback is unchanged). Geometry
# against the plan (footprint, door, zones, paths, the existing-world digest) is sim_slice_layout's.
SLICE_PROPS = {"scenes/world/props/HousePlaceholder.tscn", "scenes/world/props/NpcSpotPlaceholder.tscn"}
SLICE_INSTANCES = SLICE_PROPS | {"scenes/world/props/TreeRound.tscn", "scenes/world/props/TreeTall.tscn", "scenes/world/props/TreeWide.tscn"}
_, msecs, mext, _ = load_scene_info(MEADOW_SCENE)
slice_nodes = [(a["name"].strip('"'), a.get("parent", "").strip('"'), a, b) for k, a, b in msecs
               if k == "node" and (a.get("parent", "").strip('"') == "VerticalSlice" or a.get("parent", "").strip('"').startswith("VerticalSlice/")
                                   or (a["name"].strip('"') == "VerticalSlice" and a.get("parent", "").strip('"') == "."))]
roots = [n for n in slice_nodes if n[0] == "VerticalSlice"]
if len(roots) != 1 or roots[0][2].get("type", "").strip('"') != "Node3D" or re.search(r"^(position|rotation|rotation_degrees|scale|transform) = ", roots[0][3], re.M):
    err(f"{MEADOW_SCENE}: one VerticalSlice Node3D directly under the Meadow, at the origin, unrotated")
for name, par, a, b in slice_nodes:
    inst = script_for_ext(mext, re.search(r'ExtResource\("([^"]+)"\)', a["instance"]).group(1)) if "instance" in a else None
    sm = re.search(r'^script = ExtResource\("([^"]+)"\)', b, re.M)
    if name == "HouseDoorEntry" and par == "VerticalSlice" and sm and script_for_ext(mext, sm.group(1)) == ENTRY_GD:
        continue  # M08.1: the house door's AreaEntry (house_door) — data, the one script allowed here
    if name == "Villager" and par == "VerticalSlice/NpcSpot" and inst == "scenes/npc/Npc.tscn":
        continue  # M08.3: the NPC stands at the NPC spot (checked in "NPC framework (M08.3)")
    if re.search(r"^script = ", b, re.M) or (inst and scene_root_script_of(inst)):
        err(f"{MEADOW_SCENE}: VerticalSlice/{name} carries a script — M07.2 placement needs no code")
    if inst and inst not in SLICE_INSTANCES:
        err(f"{MEADOW_SCENE}: VerticalSlice/{name} instances {inst} — only the house, NPC spot and tree placeholders")
    if par == "VerticalSlice/Path" and (a.get("type", "").strip('"') != "MeshInstance3D" or 'mesh = SubResource("CylinderMesh_path")' not in b
                                         or 'surface_material_override/0 = SubResource("Material_path")' not in b):
        err(f"{MEADOW_SCENE}: VerticalSlice/Path/{name} is a path patch (the existing path mesh and material)")
for prop in sorted(SLICE_PROPS):
    ptxt = open(prop, encoding="utf-8").read() if os.path.exists(prop) else ""
    if not ptxt or 'type="Script"' in ptxt or re.search(r"^script = ", ptxt, re.M):
        err(f"{prop}: a placeholder scene with no script (M07.2; the house's door is an instanced AreaDoor, M08.1)")
hp = open("scenes/world/props/HousePlaceholder.tscn", encoding="utf-8").read() if os.path.exists("scenes/world/props/HousePlaceholder.tscn") else ""
if not re.search(r'^\[node name="HousePlaceholder" type="StaticBody3D"\]', hp, re.M) or hp.count('type="CollisionShape3D"') != 1 \
   or not re.search(r'^\[node name="DoorMarker" type="Marker3D" parent="\."\]', hp, re.M) \
   or re.findall(r'^\[ext_resource type="(\w+)" path="([^"]+)"', hp, re.M) != [("PackedScene", "res://scenes/world/props/AreaDoor.tscn")]:
    err("scenes/world/props/HousePlaceholder.tscn: a StaticBody3D with one collision box, a plain DoorMarker and one instanced AreaDoor (M08.1)")
npt = open("scenes/world/props/NpcSpotPlaceholder.tscn", encoding="utf-8").read() if os.path.exists("scenes/world/props/NpcSpotPlaceholder.tscn") else ""
if not re.search(r'^\[node name="NpcSpotPlaceholder" type="Marker3D"\]', npt, re.M) or re.search(r"Body3D|CollisionShape3D|Area3D", npt):
    err("scenes/world/props/NpcSpotPlaceholder.tscn: a marker only — no collider (the NPC is M08.3's)")
if sorted(e for e, _ in entry_scenes.get(MEADOW_SCENE, [])) != ["house_door", "meadow_start"]:
    err(f"{MEADOW_SCENE}: the Meadow's entries are meadow_start and the house door's house_door (M08.1) (found {entry_scenes.get(MEADOW_SCENE)})")
for f, s2 in scripts.items():
    if not f.startswith("tools/") and re.search(r"VerticalSlice|HousePlaceholder|NpcSpotPlaceholder|DoorMarker|\bNpcSpot\b", code_only(s2)):
        err(f"{f}: names the vertical slice placeholders — M07.2 placement needs no code")
notes.append(f"vertical slice (M07.2): {len(slice_nodes)} VerticalSlice nodes, no scripts; house StaticBody3D + DoorMarker, NPC marker without collider; "
             f"Meadow entries {sorted(e for e, _ in entry_scenes.get(MEADOW_SCENE, []))}")

# ------------------------------------------------------------ slice navigation and bounds (M07.3, D-28, D-29)
# Runtime-audit fixes, each isolated: the camera's SpringArm3D ignores geometry (D-29); the house carves
# its footprint (and its top) out of the navigation mesh baked at load, so a tap on the house is never a
# walk onto its roof; the Meadow has four invisible rim walls just outside its 64 x 64 ground (inner faces
# on the camera bounds' edges), so the player can't walk off the world; the pond has a blocked inner core
# (collider + matching carve) inside its water, leaving a walkable shallow edge (O-07 -> D-28). Geometry
# (the core keeps both in-pond discoveries in interaction reach) is sim_slice_layout's.
fc = open("scenes/camera/FollowCamera.tscn", encoding="utf-8").read()
if not re.search(r'\[node name="SpringArm3D" type="SpringArm3D" parent="\."\]\n(?:[^\[]*\n)?collision_mask = 0\n', fc):
    err("scenes/camera/FollowCamera.tscn: the SpringArm3D ignores geometry (collision_mask = 0, D-29) — the camera never collapses onto the player")
def obstacle_ok(txt, name="NavigationObstacle3D"):
    m = re.search(rf'\[node name="{name}" type="NavigationObstacle3D" parent="\."\]\n(.*?)(?=\n\[|\Z)', txt, re.S)
    return bool(m) and all(k in m.group(1) for k in ("affect_navigation_mesh = true", "carve_navigation_mesh = true", "avoidance_enabled = false"))
if not obstacle_ok(hp):
    err("scenes/world/props/HousePlaceholder.tscn: a NavigationObstacle3D carves the house out of the navigation mesh (affect + carve, no avoidance)")
pw = open("scenes/world/props/PondWater.tscn", encoding="utf-8").read()
if not obstacle_ok(pw) or not re.search(r'^\[node name="Core" type="StaticBody3D" parent="\."\]', pw, re.M) or pw.count('type="CollisionShape3D"') != 1:
    err("scenes/world/props/PondWater.tscn: the pond has one blocked inner core (a StaticBody3D Core + a carving NavigationObstacle3D) — O-07B, never a solid pond")
rim = [(a["name"].strip('"'), b) for k, a, b in msecs if k == "node" and a.get("parent", "").strip('"') == "WorldRim"]
rim_root = [b for k, a, b in msecs if k == "node" and a["name"].strip('"') == "WorldRim" and a.get("parent", "").strip('"') == "." and a.get("type", "").strip('"') == "StaticBody3D"]
if len(rim_root) != 1 or sorted(n for n, _ in rim) != ["East", "North", "South", "West"] or re.search(r"^script = ", "".join(b for _, b in rim) + (rim_root[0] if rim_root else ""), re.M):
    err(f"{MEADOW_SCENE}: one WorldRim StaticBody3D with four collision walls (North/South/West/East), no script")
notes.append(f"slice navigation and bounds (M07.3): camera arm ignores geometry; house + pond core carve the navigation mesh; WorldRim walls {sorted(n for n, _ in rim)}")

# ------------------------------------------------------------ landscape orientation (M07.4, D-30)
# Wrikshagandha is a mobile-first landscape game: a 1920×1080 canvas (short side 1080, so every D-26
# size keeps its physical size), canvas_items / expand stretching, sensor landscape on the phone (either
# way up; never portrait). The HUD keeps the joystick in the bottom-left thumb zone clear of side
# cut-outs and the gesture bar through the display's safe area, as it does the top bar and thumb buttons.
LANDSCAPE = {"window/size/viewport_width": "1920", "window/size/viewport_height": "1080", "window/handheld/orientation": "4",
             "window/stretch/mode": '"canvas_items"', "window/stretch/aspect": '"expand"'}
display = dict(re.findall(r"^(window/[\w/]+)=(.+)$", cfg, re.M))
if any(display.get(k) != v for k, v in LANDSCAPE.items()):
    err(f"project.godot: the game is landscape (D-30) — {LANDSCAPE} (found { {k: display.get(k) for k in LANDSCAPE} })")
sa = code_only(func_body(scripts.get("scripts/ui/hud.gd", ""), "_apply_safe_area") or "")
if not all(k in sa for k in ("joystick.offset_left = insets[0]", "joystick.offset_right = insets[0] + joystick_size.x",
                             "joystick.offset_bottom = -insets[3]", "joystick.offset_top = -insets[3] - joystick_size.y")):
    err("scripts/ui/hud.gd: _apply_safe_area() keeps the joystick (its size unchanged) clear of the left and bottom safe-area insets")
notes.append("landscape (M07.4): canvas 1920x1080, sensor landscape; joystick, top bar and thumb buttons follow the safe area")

# ------------------------------------------------------------ UI surfaces and HUD (M06.3, D-26)
# One shared theme (scenes/ui/wriksha_theme.tres) for the HUD, the Basket,
# the Inventory and the notification card. The HUD's top bar is anchored to
# the top edge and sizes to its content — never stretched by a full-screen
# container (the pre-M06.3 tall-column bug); the Basket and Inventory buttons
# sit bottom-right; HUD containers never catch world taps. Every touch
# control on these surfaces is at least 120 canvas px (short side 1080; the canvas is 1920×1080 landscape since M07.4, D-30).
# Points (✿ pill) and coins (Coins chip) never share a label. The harvest
# and sale cards have fixed structures; the Inventory has no sell path.
THEME_TRES = "scenes/ui/wriksha_theme.tres"
TOUCH_MIN = 120
def scene_nodes(path):
    """{node path: (attrs text, body text)} for a .tscn, paths relative to the root ('.' = root)."""
    txt = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^\[node ([^\]]*)\]\n(.*?)(?=^\[|\Z)", txt, re.M | re.S):
        name = re.search(r'name="([^"]+)"', m.group(1)).group(1)
        par = re.search(r'parent="([^"]*)"', m.group(1))
        key = "." if par is None else (name if par.group(1) == "." else par.group(1) + "/" + name)
        out[key] = (m.group(1), m.group(2))
    return out, txt
def prop(body, key):
    m = re.search(rf"^{re.escape(key)} = (.+)$", body, re.M)
    return m.group(1).strip() if m else None
def theme_id(txt):
    m = re.search(rf'\[ext_resource type="Theme" path="res://{re.escape(THEME_TRES)}" id="([^"]+)"\]', txt)
    return m.group(1) if m else None
theme_txt = open(THEME_TRES, encoding="utf-8").read() if os.path.exists(THEME_TRES) else ""
variations = dict(re.findall(r'^(\w+)/base_type = &"(\w+)"$', theme_txt, re.M))
WANT_VARIATIONS = {"HudPill": "PanelContainer", "CoinChip": "PanelContainer", "PrimaryButton": "Button", "SecondaryButton": "Button",
                   "HudButton": "Button", "RowCard": "PanelContainer", "Caption": "Label", "Header": "Label"}
if not theme_txt.startswith('[gd_resource type="Theme"') or any(variations.get(k) != v for k, v in WANT_VARIATIONS.items()):
    err(f"{THEME_TRES}: the shared UI theme defines {sorted(WANT_VARIATIONS)} on their base types (found {variations})")
UI_SCENES = {"scenes/ui/HUD.tscn": ["TopArea", "ScreenButtons"], "scenes/ui/BasketScreen.tscn": ["."],
             "scenes/ui/InventoryScreen.tscn": ["."], "scenes/ui/DiscoveryNotification.tscn": ["."],
             # M07.4a: the Collection, Journal and Daily screens joined the shared theme (landscape pass).
             "scenes/ui/CollectionScreen.tscn": ["."], "scenes/ui/JournalScreen.tscn": ["."], "scenes/ui/DailyDiscoveryScreen.tscn": ["."],
             # M07.4b: the SeedPicker, the last screen on the old parchment theme, joined it too.
             "scenes/ui/SeedPicker.tscn": ["."],
             # M08.3: the speech panel (an NPC's greeting) in the shared theme.
             "scenes/ui/SpeechPanel.tscn": ["."]}
ui_nodes = {}
for scene, roots in UI_SCENES.items():
    nodes, txt = scene_nodes(scene)
    ui_nodes[scene] = nodes
    tid = theme_id(txt)
    for r in roots:
        if tid is None or r not in nodes or prop(nodes[r][1], "theme") != f'ExtResource("{tid}")':
            err(f"{scene}: '{r}' uses the shared theme {THEME_TRES}")
    for key, (node_attrs, body) in nodes.items():
        used = re.search(r'theme_type_variation = &"(\w+)"', body)
        if used and used.group(1) not in variations:
            err(f"{scene}: {key} uses theme variation '{used.group(1)}', which {THEME_TRES} doesn't define")
    if scene == "scenes/ui/DiscoveryNotification.tscn":
        continue
    for key, (node_attrs, body) in nodes.items():
        if 'type="Button"' not in node_attrs:
            continue
        size = re.match(r"Vector2\(([\d.]+), ([\d.]+)\)", prop(body, "custom_minimum_size") or "")
        if not size or min(float(size.group(1)), float(size.group(2))) < TOUCH_MIN:
            err(f"{scene}: button {key} is smaller than the {TOUCH_MIN} px touch target ({prop(body, 'custom_minimum_size')})")
hud_nodes = ui_nodes["scenes/ui/HUD.tscn"]
ta = hud_nodes.get("TopArea", ("", ""))
if 'type="MarginContainer"' not in ta[0] or prop(ta[1], "anchor_right") != "1.0" or prop(ta[1], "anchor_bottom") not in (None, "0.0") \
   or prop(ta[1], "anchor_top") not in (None, "0.0") or prop(ta[1], "grow_vertical") != "1" \
   or any(prop(hud_nodes.get(k, ("", ""))[1], "size_flags_vertical") != "0" for k in ("TopArea/TopColumn", "TopArea/TopColumn/TopBar")):
    err("scenes/ui/HUD.tscn: the top bar is anchored to the top edge (TopArea: top-wide, growing down) and never stretched vertically (TopColumn/TopBar shrink)")
if set(k for k in hud_nodes if k.startswith("TopArea/TopColumn/TopBar/MenuButtons/")) != \
   {f"TopArea/TopColumn/TopBar/MenuButtons/{b}" for b in ("CollectionButton", "JournalButton", "DailyButton", "MovementButton")} \
   or {k for k in hud_nodes if k.startswith("ScreenButtons/")} != {"ScreenButtons/BasketButton", "ScreenButtons/InventoryButton"} \
   or prop(hud_nodes.get("ScreenButtons", ("", ""))[1], "anchor_left") != "1.0" or prop(hud_nodes.get("ScreenButtons", ("", ""))[1], "anchor_top") != "1.0" \
   or prop(hud_nodes.get("ScreenButtons/BasketButton", ("", ""))[1], "visible") != "false":
    err("scenes/ui/HUD.tscn: 📚 📖 ⭐ 🕹 in the top bar; 🧺 (hidden until produce) and 🎒 anchored bottom-right")
for k in ("TopArea", "TopArea/TopColumn", "TopArea/TopColumn/TopBar", "TopArea/TopColumn/TopBar/PointsPill",
          "TopArea/TopColumn/TopBar/MenuButtons", "TopArea/TopColumn/NotificationRoot", "ScreenButtons"):
    if prop(hud_nodes.get(k, ("", ""))[1], "mouse_filter") != "2":
        err(f"scenes/ui/HUD.tscn: {k} ignores the mouse, so HUD layout never swallows world taps")
if prop(hud_nodes.get("TopArea/TopColumn/TopBar/PointsPill", ("", ""))[1], "theme_type_variation") != '&"HudPill"' \
   or "TopArea/TopColumn/TopBar/PointsPill/PointsLabel" not in hud_nodes \
   or "$TopArea/TopColumn/TopBar/PointsPill/PointsLabel" not in hud_src:
    err("scenes/ui/HUD.tscn: the ✿ points value lives in its own HudPill")
bs_nodes = ui_nodes["scenes/ui/BasketScreen.tscn"]
if prop(bs_nodes.get("Panel/VBoxContainer/Header/CoinChip", ("", ""))[1], "theme_type_variation") != '&"CoinChip"' \
   or "Panel/VBoxContainer/Header/CoinChip/CoinsLabel" not in bs_nodes \
   or prop(bs_nodes.get("Panel/VBoxContainer/Header/TitleLabel", ("", ""))[1], "text") != '"BASKET"':
    err("scenes/ui/BasketScreen.tscn: \"BASKET\" with the coin balance in its own CoinChip")
for key, (node_attrs, body) in ui_nodes["scenes/ui/BasketScreen.tscn"].items():
    if 'type="Panel' in node_attrs and key == "Panel" and (prop(body, "offset_left") or prop(body, "anchor_left") != "0.05"):
        err("scenes/ui/BasketScreen.tscn: the sheet is anchored to the screen's proportions, not fixed offsets")
bsu = code_only(scripts.get(BS, ""))
bsu_funcs = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", scripts.get(BS, ""), re.M | re.S)}
if "const TOUCH_TARGET := 120.0" not in bsu or bsu.count("Button.new()") != 1 \
   or "button.custom_minimum_size = Vector2(TOUCH_TARGET, TOUCH_TARGET)" not in bsu_funcs.get("_build_sell_buttons", "") \
   or "var price := Market.get_unit_price(item.id, quality)" not in bsu_funcs.get("_build_sell_buttons", ""):
    err(f"{BS}: every Sell button is a {TOUCH_MIN} px touch target priced by Market.get_unit_price()")
if '"Nothing harvested yet."' not in bsu_funcs.get("_build_empty_state", "") or "_build_empty_state()" not in bsu_funcs.get("_refresh", ""):
    err(f"{BS}: an empty basket shows the \"Nothing harvested yet.\" state")
hud_fn = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", hud_src, re.M | re.S)}
if 'notification.show_message("✦ HARVESTED ✦", name_line, "+%d Wriksha Points" % points_awarded, "+1 Seed", FarmManager.get_care_note(care))' not in hud_fn.get("_on_crop_harvested", "") \
   or 'var name_line := "%s · %s" % [crop_definition.display_name, FarmManager.get_quality_name(quality)]' not in hud_fn.get("_on_crop_harvested", ""):
    err("scripts/ui/hud.gd: the harvest card — ✦ HARVESTED ✦ / crop · quality / the care note / +N Wriksha Points / +1 Seed")
if 'notification.show_message(item_name.to_upper(), "%s ×%d" % [FarmManager.get_quality_name(quality), quantity], "+%d Coins" % coins)' not in hud_fn.get("_on_produce_sold", ""):
    err("scripts/ui/hud.gd: the sale card — CROP / quality ×quantity / +N Coins, from the Market's reported values")
if "get_viewport().size_changed.connect(_apply_safe_area)" not in hud_fn.get("_ready", "") or "DisplayServer.get_display_safe_area()" not in hud_fn.get("_apply_safe_area", ""):
    err("scripts/ui/hud.gd: the top bar and thumb buttons follow the display's safe area")
if re.search(r"\bWallet\b|\bMarket\.(sell|get_unit_price)\(", code_only(hud_src)):
    err("scripts/ui/hud.gd: the HUD shows points and sale feedback only — it never reads coins or prices")
DN = "scripts/ui/discovery_notification.gd"
dn = scripts.get(DN, "")
dn_nodes = ui_nodes["scenes/ui/DiscoveryNotification.tscn"]
if not re.search(r'^func show_message\(title: String, name_text: String, points_text: String, detail_text: String = "", note_text: String = ""\) -> void:', dn, re.M) \
   or any(f"Panel/VBoxContainer/{n}" not in dn_nodes for n in ("TitleLabel", "NameLabel", "NoteLabel", "PointsLabel", "DetailLabel")) \
   or "label.visible = pair[1] != \"\"" not in code_only(dn):
    err(f"{DN}: one card — title, name, optional note, amount, optional detail (empty lines hidden); existing callers unchanged")
for f in ("scripts/ui/hud.gd", BS, IS, DN):
    for lit in re.findall(r'"([^"\n]*)"', code_only(scripts.get(f, ""))):
        if re.search(r"✿|Points", lit) and re.search(r"Coin", lit):
            err(f"{f}: '{lit}' — points and coins never share a label")
for scene, nodes in ui_nodes.items():
    for key, (node_attrs, body) in nodes.items():
        t = prop(body, "text") or ""
        if re.search(r"✿|Points", t) and "Coin" in t:
            err(f"{scene}: {key} shows points and coins together")
isu = code_only(scripts.get(IS, ""))
if re.search(r"\bMarket\b|\bWallet\b|Button\.new\(|\"Sell|sell_value|get_unit_price", isu) \
   or [k for k, (a, b) in ui_nodes["scenes/ui/InventoryScreen.tscn"].items() if 'type="Button"' in a] != ["Panel/VBoxContainer/Header/CloseButton"]:
    err(f"{IS}: the Inventory stays read-only — its only button closes it; no Market, Wallet, price or Sell")
notes.append(f"ui: shared theme {len(variations)} variations; top bar anchored top; touch targets >= {TOUCH_MIN} px; harvest/sale cards fixed; inventory read-only")

# ------------------------------------------------------------ landscape UI pass: Collection, Journal, Daily (M07.4a, D-26/D-30)
# The three older screens use the shared theme's sheet (checked above with the other UI scenes: theme,
# variations, 120 px buttons). They only display: no reward, discovery, item, coin, seed or save call;
# nothing undiscovered is named (Collection and Journal show "???", the Daily teaser names a rarity until
# it is found); their cards let a drag through to the scrolling column; the Daily card's "Keep exploring"
# closes it like the ✕. Every modal sheet keeps clear of the safe area's insets.
LAND_UI = {"scripts/ui/collection_screen.gd": "Collection", "scripts/ui/journal_screen.gd": "Journal", "scripts/ui/daily_discovery_screen.gd": "Daily"}
WRITES = re.compile(r"\b(PointsManager\.add_points|mark_\w+\(|\.discover\(|Inventory\.(add|remove|apply_save_data)|Wallet|Market|choose_seed|request_seed_choice|notify_\w+\(|SaveManager|apply_save_data|_reach\()")
for f in LAND_UI:
    if WRITES.search(code_only(scripts.get(f, ""))):
        err(f"{f}: a display screen — it never pays, discovers, changes items/coins/seeds or saves")
cs_src, js_src, ds_src = (code_only(scripts.get(f, "")) for f in LAND_UI)
if 'entry.text = definition.display_name if discovered else "???"' not in cs_src or "var discovered := DiscoveryManager.is_discovered(definition.id)" not in cs_src:
    err("scripts/ui/collection_screen.gd: an undiscovered entry is \"???\" — the Collection never spoils a find")
if 'row.text = "✓ %s" % place.display_name if visited else "???"' not in js_src:
    err("scripts/ui/journal_screen.gd: an unvisited place stays \"???\" (secret places stay secret)")
drf = code_only(func_body(scripts.get("scripts/ui/daily_discovery_screen.gd", ""), "_refresh") or "")
done_branch, _, teaser_branch = drf.partition("\n\telse:")
if "if DailyDiscoveryManager.is_completed_today():" not in done_branch or "display_name" not in done_branch or "display_name" in teaser_branch \
   or "var bonus := DailyDiscoveryManager.get_bonus_points()" not in drf:
    err("scripts/ui/daily_discovery_screen.gd: the find's name only once it is found (the teaser names a rarity); the reward from get_bonus_points()")
if "explore_button.pressed.connect(_on_close_pressed)" not in (func_body(scripts.get("scripts/ui/daily_discovery_screen.gd", ""), "_ready") or ""):
    err("scripts/ui/daily_discovery_screen.gd: \"Keep exploring\" closes the card")
for f in ("scripts/ui/collection_screen.gd", "scripts/ui/journal_screen.gd"):
    if "card.mouse_filter = Control.MOUSE_FILTER_PASS" not in scripts.get(f, ""):
        err(f"{f}: its cards pass drags through to the scrolling column (MOUSE_FILTER_PASS)")
sa2 = code_only(func_body(scripts.get("scripts/ui/hud.gd", ""), "_apply_safe_area") or "")
if "for screen: Control in [collection_screen, journal_screen, daily_screen, basket_screen, inventory_screen]:" not in sa2 \
   or not all(f"sheet.offset_{side} = " in sa2 for side in ("left", "top", "right", "bottom")):
    err("scripts/ui/hud.gd: every modal sheet (Collection, Journal, Daily, Basket, Inventory) keeps clear of the safe area's insets")
notes.append("landscape UI pass (M07.4a): Collection/Journal/Daily on the shared theme, display-only, spoiler-free, scroll-friendly; sheets in the safe area")

# ------------------------------------------------------------ landscape seed picker (M07.4b, D-26/D-30)
# The SeedPicker stays a non-modal choice (no dim, the root ignores the mouse so the world stays playable),
# now docked at the bottom centre in the shared theme (checked above with the other UI scenes: theme,
# variations, a 120 px ✕). Its behaviour is unchanged: it opens and closes only on FarmManager's
# seed_choice_requested / seed_choice_closed, a card calls FarmManager.choose_seed(crop) and nothing else,
# the ✕ calls cancel_seed_choice(), a crop with no seeds is a disabled card; its code-built cards are at
# least the 120 px touch target and never take focus; the HUD keeps it above the gesture bar.
SPN, _ = scene_nodes("scenes/ui/SeedPicker.tscn")
spr = SPN.get(".", ("", ""))[1]; spp = SPN.get("Panel", ("", ""))[1]
if prop(spr, "mouse_filter") != "2" or "Dim" in SPN or prop(spp, "anchor_top") != "1.0" or prop(spp, "anchor_bottom") != "1.0" \
   or prop(spp, "anchor_left") != "0.5" or prop(spp, "anchor_right") != "0.5" or prop(spp, "grow_vertical") != "0":
    err("scenes/ui/SeedPicker.tscn: a non-modal picker (root ignores the mouse, no dim) docked at the bottom centre, growing upward")
sp_src = scripts.get(SP, "")
spc = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", sp_src, re.M | re.S)}
csz = re.search(r"^const CHOICE_SIZE := Vector2\(([\d.]+), ([\d.]+)\)", sp_src, re.M)
cmin = re.search(r"^const CHOICE_MIN_WIDTH := ([\d.]+)", sp_src, re.M)
if not csz or not cmin or min(float(csz.group(1)), float(csz.group(2)), float(cmin.group(1))) < TOUCH_MIN \
   or "button.custom_minimum_size = Vector2(width, CHOICE_SIZE.y)" not in spc.get("_build_choice", "") \
   or "return clampf(fitted, CHOICE_MIN_WIDTH, CHOICE_SIZE.x)" not in spc.get("_choice_width", "") \
   or "button.focus_mode = Control.FOCUS_NONE" not in spc.get("_build_choice", ""):
    err(f"{SP}: every seed card is at least the {TOUCH_MIN} px touch target (CHOICE_SIZE, CHOICE_MIN_WIDTH) and never takes focus")
if not re.search(r"FarmManager\.seed_choice_requested\.connect\(open\)\s*FarmManager\.seed_choice_closed\.connect\(close\)", spc.get("_ready", "")) \
   or not re.search(r"func _on_choice_pressed\(crop: CropDefinition\) -> void:\s*AmbientAudioManager\.play_ui_feedback\(\)\s*FarmManager\.choose_seed\(crop\)\s*$", spc.get("_on_choice_pressed", "")) \
   or not re.search(r"func _on_close_pressed\(\) -> void:\s*AmbientAudioManager\.play_ui_feedback\(\)\s*FarmManager\.cancel_seed_choice\(\)\s*$", spc.get("_on_close_pressed", "")) \
   or "button.disabled = count <= 0" not in spc.get("_build_choice", "") or "button.pressed.connect(_on_choice_pressed.bind(crop))" not in spc.get("_build_choice", ""):
    err(f"{SP}: the seed choice is unchanged — opens/closes on FarmManager's signals, a card plants through choose_seed(crop), the ✕ cancels, no seeds = a disabled card")
sa3 = code_only(func_body(scripts.get("scripts/ui/hud.gd", ""), "_apply_safe_area") or "")
if 'var picker_panel: Control = seed_picker.get_node("Panel")' not in sa3 or "picker_panel.offset_bottom = -(EDGE_MARGIN + insets[3])" not in sa3:
    err("scripts/ui/hud.gd: the seed picker keeps clear of the gesture bar (safe area)")
notes.append("landscape seed picker (M07.4b): shared theme, non-modal, bottom-centre dock, 120 px cards and ✕, behaviour pinned, safe area")

# ------------------------------------------------------------ area transitions (M08.1, D-31..D-35)
# The first real area change. Areas are data (one AreaDefinition per data/areas/*.tres, D-34); a door is
# an ordinary Interactable (AreaDoor) whose one action asks AreaRouter.travel() — tapped, never walked
# into (D-35); AreaRouter is the request layer and the source of the current area id, never saved
# (relaunch = the Meadow's meadow_start, save_version stays 5); Main alone fades, swaps, parks or frees,
# restores and places. The Meadow is kept alive (parked, out of the tree, the same instance — D-33): its
# time of day, discoveries, events and wildlife neither reset nor advance, and its farm plots are
# captured on leaving and given back on return (no farm time indoors, D-31). Interiors frame the
# player with small focus bounds and a fixed camera distance from their data (D-32).
AREA_DEF_GD, ROUTER_GD, DOOR_GD = "scripts/world/area_definition.gd", "scripts/autoload/area_router.gd", "scripts/world/area_door.gd"
FADE_GD, FADE_SCENE, DOOR_SCENE = "scripts/ui/transition_fade.gd", "scenes/ui/TransitionFade.tscn", "scenes/world/props/AreaDoor.tscn"
HOME_SCENE = "scenes/world/HomeInterior.tscn"
AREA_DEF_FIELDS = [("id", "String"), ("display_name", "String"), ("scene_path", "String"), ("keep_alive_when_left", "bool"), ("camera_distance", "float")]
ga_src, ad_src, ro_src, dr_src, fd_src = (scripts.get(f, "") for f in (GAME_AREA_GD, AREA_DEF_GD, ROUTER_GD, DOOR_GD, FADE_GD))
# GameArea: the one base of every area; areas say who they are, nothing else.
if not re.search(r"^extends Node3D\s*\nclass_name GameArea", ga_src, re.M) or '@export var area_id: String = ""' not in ga_src \
   or not re.search(r"func attach_player\(_player: Node3D\) -> void:\s*pass", ga_src) \
   or re.search(r"\bAreaRouter\b|\bFarmManager\b|\bMain\b|get_parent\(|remove_child|add_child|\bfree\(|queue_free", code_only(ga_src)):
    err(f"{GAME_AREA_GD}: GameArea is a Node3D with an area_id, an empty attach_player() and the navigation bake — no travel, farm or tree work")
area_scripts = sorted(f for f, s2 in scripts.items() if re.search(r"^extends GameArea\b", s2, re.M))
if area_scripts != [MEADOW_GD]:
    err(f"only the Meadow needs its own area script — other areas use GameArea itself (found {area_scripts})")
# AreaDefinition: exact fields, data only.
adf = re.findall(r"^@export(?:_file\([^)]*\))? var (\w+): (\w+)", ad_src, re.M)
if not re.search(r"^extends Resource\s*\nclass_name AreaDefinition", ad_src, re.M) or adf != AREA_DEF_FIELDS \
   or '@export_file("*.tscn") var scene_path' not in ad_src or re.search(r"^func ", ad_src, re.M):
    err(f"{AREA_DEF_GD}: AreaDefinition has exactly {AREA_DEF_FIELDS} (scene_path an exported .tscn file) and no logic")
area_defs = {}
for path in sorted(glob.glob("data/areas/*.tres")):
    txt = open(path, encoding="utf-8").read()
    fields = dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', txt.split("[resource]", 1)[-1], re.M))
    aid = fields.get("id", "")
    if 'path="res://scripts/world/area_definition.gd"' not in txt or aid != os.path.basename(path)[:-5] or not re.fullmatch(r"[a-z][a-z0-9_]*", aid) \
       or not fields.get("display_name") or not fields.get("scene_path", "").startswith("res://scenes/world/"):
        err(f"{path}: an AreaDefinition with a lower_snake id equal to its file name, a display name and an area scene")
        continue
    area_defs[aid] = fields
if sorted(area_defs) != ["home", "meadow"]:
    err(f"data/areas: the M08.1 areas are the Meadow and the home interior (found {sorted(area_defs)})")
zlo, zhi = const_val(cam_src, "ZOOM_MIN_DISTANCE") or 0, const_val(cam_src, "ZOOM_MAX_DISTANCE") or 0
area_entries = {}
for aid, fields in area_defs.items():
    scene = res_path(fields["scene_path"])
    if not os.path.exists(scene):
        err(f"data/areas/{aid}.tres: scene {scene} missing"); continue
    st = open(scene, encoding="utf-8").read()
    root_script = scene_root_script_of(scene)
    root_id = re.search(r'^\[node name="[^"]+" type="Node3D"[^\n]*\]\n(?:[^\[]*\n)?area_id = "([^"]*)"', st, re.M)
    if root_script not in (GAME_AREA_GD, MEADOW_GD) or not root_id or root_id.group(1) != aid:
        err(f"{scene}: the root is a GameArea whose area_id is '{aid}' (its AreaDefinition)")
    if not re.search(r'^\[node name="[^"]+" type="Node3D" groups=\["navigation_source"\]\]', st, re.M) \
       or not re.search(r'\[node name="NavigationRegion3D" type="NavigationRegion3D" parent="\."\]', st) \
       or dict(re.findall(r"^(\w+) = (.+)$", (re.search(r'\[sub_resource type="NavigationMesh"[^\]]*\]\n(.*?)\n\n', st, re.S) or re.search("()", "")).group(1), re.M)) != NAV_PINS:
        err(f"{scene}: an area bakes its own navigation from the navigation_source group with the shared settings")
    if not re.search(r'type="WorldEnvironment"', st) or not re.search(r'type="DirectionalLight3D"', st):
        err(f"{scene}: an area brings its own WorldEnvironment and light (the parked Meadow's leave with it)")
    area_entries[aid] = [e for e, _ in entry_scenes.get(scene, [])]
    cd = float(fields.get("camera_distance", "0") or 0)
    if fields.get("keep_alive_when_left", "false") not in ("true", "false") or not (cd == 0.0 or zlo <= cd <= zhi):
        err(f"data/areas/{aid}.tres: keep_alive_when_left is a bool and camera_distance 0 (free zoom) or within [{zlo}, {zhi}]")
if area_defs.get("meadow", {}).get("keep_alive_when_left") != "true" or area_defs.get("home", {}).get("keep_alive_when_left", "false") != "false":
    err("data/areas: the Meadow is kept alive while left (D-33); the home interior is freed and rebuilt")
if area_defs.get("meadow", {}).get("camera_distance", "0") not in ("0", "0.0") or float(area_defs.get("home", {}).get("camera_distance", "0")) != 7.5:
    err("data/areas: the Meadow keeps the player's own zoom; the home interior frames at 7.5 m (D-32)")
if area_entries.get("home") != ["home_door"]:
    err(f"{HOME_SCENE}: the home interior has one entry, home_door (found {area_entries.get('home')})")
hb = bounds_nodes.get(HOME_SCENE, [])
hbs = re.search(r"^size = Vector2\(([^)]*)\)", hb[0][1], re.M) if hb else None
if not hbs or any(float(x) <= 0 or float(x) > 4.0 for x in hbs.group(1).split(",")):
    err(f"{HOME_SCENE}: the interior's camera bounds are small (each side > 0 and <= 4 m) — they limit the focus only (D-32)")
# No area named in code: ids, scene paths and keep-alive live only in data.
for f, s2 in scripts.items():
    if f.startswith("tools/"): continue
    code = code_only(s2)
    if re.search(r'"(meadow|home|house_door|home_door|meadow_start)"|Meadow\.tscn|HomeInterior|res://scenes/world/', code):
        err(f"{f}: names an area, entry or area scene — areas are data (data/areas/, D-34)")
# AreaRouter: the request layer; never saves, never swaps.
if re.findall(r"^signal (.+)$", ro_src, re.M) != ["travel_requested(area_id: String, entry_id: String)", "area_changed(area_id: String)"] \
   or 'const AREAS_PATH := "res://data/areas/"' not in ro_src or "ResourceDirectory.list_tres_paths(AREAS_PATH)" not in ro_src:
    err(f"{ROUTER_GD}: AreaRouter declares travel_requested(area_id, entry_id) and area_changed(area_id) and loads data/areas via ResourceDirectory")
tr = code_only(func_body(ro_src, "travel") or "")
tpos = [tr.find(k) for k in ("if _travelling:", "return false", "if not _definitions.has(area_id):", "_travelling = true", "travel_requested.emit(area_id, entry_id)", "return true")]
if -1 in tpos or tpos != sorted(tpos) or tr.count("travel_requested.emit") != 1:
    err(f"{ROUTER_GD}: travel() refuses while a trip is under way and unknown areas, then marks the trip and asks once")
na = code_only(func_body(ro_src, "notify_arrived") or "")
if not re.search(r"_travelling = false\s*if area_id == _current_area_id:\s*return\s*_current_area_id = area_id\s*area_changed\.emit\(area_id\)", na):
    err(f"{ROUTER_GD}: notify_arrived() ends the trip and announces only a change of area")
if "_travelling = false" not in code_only(func_body(ro_src, "notify_travel_failed") or ""):
    err(f"{ROUTER_GD}: notify_travel_failed() ends the trip")
if re.search(r"SaveManager|save|FileAccess|user://|remove_child|add_child|instantiate|change_scene|get_tree\(\)", code_only(ro_src)):
    err(f"{ROUTER_GD}: AreaRouter never saves, loads scenes or touches the tree — Main carries trips out (D-34)")
writes = sorted({fn for fn in re.findall(r"^func (\w+)\(", ro_src, re.M) if re.search(r"_current_area_id\s*=[^=]", code_only(func_body(ro_src, fn) or ""))})
if writes != ["notify_arrived"]:
    err(f"{ROUTER_GD}: only notify_arrived() sets the current area (found {writes})")
use = {}
for f, s2 in scripts.items():
    for name in re.findall(r"\bAreaRouter\.(\w+)", code_only(s2)):
        use.setdefault(name, set()).add(f)
if use.get("travel") != {DOOR_GD} or use.get("notify_arrived") != {MAIN_GD} or use.get("notify_travel_failed") != {MAIN_GD} \
   or use.get("travel_requested") != {MAIN_GD}:
    err(f"AreaRouter: only AreaDoor asks for travel; only Main hears travel_requested and reports arrivals/failures (found {dict((k, sorted(v)) for k, v in use.items())})")
if re.search(r"AreaRouter|area_id|current_area", code_only(scripts.get("scripts/autoload/save_manager.gd", ""))):
    err("scripts/autoload/save_manager.gd: the current area is never saved — a relaunch starts at meadow_start (D-34, save_version 5)")
# AreaDoor: an Interactable with one action; never triggered by walking into it.
if not re.search(r"^extends Interactable\s*\nclass_name AreaDoor", dr_src, re.M) \
   or re.findall(r"^@export var (\w+)", dr_src, re.M) != ["target_area_id", "target_entry_id", "verb"] \
   or not re.search(r"func _ready\(\) -> void:\s*remove_on_harvest = false", dr_src):
    err(f"{DOOR_GD}: AreaDoor extends Interactable, exports target_area_id, target_entry_id and its verb, and is persistent")
gv = code_only(func_body(dr_src, "_get_interaction_verbs") or "")
if not re.search(r"if \(verb == Verb\.ENTER or verb == Verb\.EXIT\) and not AreaRouter\.is_travelling\(\):\s*verbs\.append\(verb\)", gv):
    err(f"{DOOR_GD}: a door offers only its own ENTER/EXIT verb, and nothing while a trip is under way")
di = code_only(func_body(dr_src, "interact") or "")
if not re.search(r"if _get_interaction_verbs\(\)\.is_empty\(\):\s*return false\s*return AreaRouter\.travel\(target_area_id, target_entry_id\)\s*$", di.strip() + "\n"):
    err(f"{DOOR_GD}: interact() only asks AreaRouter.travel() for its target (and only while it offers its verb)")
if re.search(r"body_entered|area_entered|body_exited|area_exited|_process|_physics_process|get_overlapping|\bawait\b|\bMain\b|load_area|place_at", code_only(dr_src)):
    err(f"{DOOR_GD}: a door never reacts to being walked into, never polls, waits or swaps — only a tap reaches interact() (D-35)")
dsc = open(DOOR_SCENE, encoding="utf-8").read() if os.path.exists(DOOR_SCENE) else ""
if not re.search(r'^\[node name="AreaDoor" type="Area3D"\]\ncollision_layer = 4\ncollision_mask = 0\n', dsc, re.M) or scene_root_script_of(DOOR_SCENE) != DOOR_GD \
   or dsc.count('type="CollisionShape3D"') != 1 or "DiscoveryIndicator.tscn" not in dsc:
    err(f"{DOOR_SCENE}: an Area3D on the interactables layer that detects nothing (mask 0), one shape, the shared Indicator")
doors = []
for path in glob.glob("scenes/**/*.tscn", recursive=True):
    _, secs, ext, _ = load_scene_info(path)
    for k, a, b in secs:
        if k == "node" and "instance" in a and script_for_ext(ext, re.search(r'ExtResource\("([^"]+)"\)', a["instance"]).group(1)) == DOOR_SCENE:
            f2 = dict(re.findall(r'^(target_area_id|target_entry_id|verb) = "?([^"\n]*)"?$', b, re.M))
            doors.append((path, f2.get("target_area_id"), f2.get("target_entry_id"), f2.get("verb")))
want_doors = sorted([("scenes/world/props/HousePlaceholder.tscn", "home", "home_door", str(VERBS.get("ENTER"))),
                     (HOME_SCENE, "meadow", "house_door", str(VERBS.get("EXIT")))])
if sorted(doors) != want_doors:
    err(f"doors: the house door enters home/home_door and the interior's door exits to meadow/house_door (found {sorted(doors)}, expected {want_doors})")
for path, aid, eid, _ in doors:
    if aid not in area_entries or eid not in area_entries.get(aid, []):
        err(f"{path}: a door leads to {aid}/{eid}, which is not an area entry")
# Main: the one place a trip is carried out.
if "AreaRouter.travel_requested.connect(_on_travel_requested)" not in mready or not code_only(mready).rstrip().endswith("AreaRouter.notify_arrived(area.area_id)"):
    err(f"{MAIN_GD}: _ready() connects travel_requested once and reports the boot area")
otr = code_only(func_body(main_src, "_on_travel_requested") or "")
opos = [otr.find(k) for k in ("AreaRouter.get_definition(area_id)", "load(definition.scene_path) as PackedScene", "await transition_fade.cover()",
                               "_swap_area(scene, entry_id)", "await transition_fade.reveal()")]
if -1 in opos or opos != sorted(opos) or otr.count("AreaRouter.notify_travel_failed()") != 2 or otr.count("await") != 2:
    err(f"{MAIN_GD}: _on_travel_requested() loads the area's scene from its data, covers, swaps, then reveals (a failed trip is reported)")
park = ["FarmManager.release_plots_in(old)", "remove_child(old)", "if _keeps_alive(old):", "_parked_areas[old.scene_file_path] = old", "else:", "old.free()",
        "_parked_areas.erase(scene.resource_path)", "add_child(area)", "move_child(area, 0)", "if restored:", "_reregister_plots(area)", "else:",
        "area.attach_player(player)", "_apply_camera_bounds()", "_apply_camera_distance()", "follow_camera.snap_to_target()", "AreaRouter.notify_arrived(area.area_id)"]
pi, cursor = [], 0
for k in park:
    j = sw.find(k, cursor); pi.append(j); cursor = j + 1 if j >= 0 else cursor
if -1 in pi or "var next: GameArea = _parked_areas.get(scene.resource_path)" not in sw or "var restored: bool = next != null" not in sw:
    err(f"{MAIN_GD}: _swap_area() reuses a parked area, captures the old area's plots, parks it if its data keeps it alive (else frees it), "
        f"adds the next, re-registers a restored area's plots (attaches only a fresh one), applies bounds and distance, snaps, reports")
ka = code_only(func_body(main_src, "_keeps_alive") or "")
if not re.search(r"var definition := AreaRouter\.get_definition\(left\.area_id\)\s*return definition != null and definition\.keep_alive_when_left", ka):
    err(f"{MAIN_GD}: whether a left area is parked comes only from its AreaDefinition (keep_alive_when_left)")
rr = code_only(func_body(main_src, "_reregister_plots") or "")
if not re.search(r'for node in restored_area\.find_children\("\*", "Area3D", true, false\):\s*var plot := node as FarmPlot\s*if plot != null:\s*FarmManager\.register_plot\(plot\)', rr):
    err(f"{MAIN_GD}: a restored area's plots are re-registered through FarmManager.register_plot() (the M03.3 restore path), never restored by Main")
parked_writers = sorted({fn for fn in re.findall(r"^func (\w+)\(", main_src, re.M) if re.search(r"_parked_areas(\[|\.erase|\.clear)", code_only(func_body(main_src, fn) or ""))})
if parked_writers != ["_exit_tree", "_swap_area"] or "parked.free()" not in code_only(func_body(main_src, "_exit_tree") or ""):
    err(f"{MAIN_GD}: parked areas are written only by _swap_area() and freed on exit (found {parked_writers})")
for f, s2 in scripts.items():
    if f != MAIN_GD and re.search(r"\b(remove_child|add_child)\((old|area|next|meadow)\b|_parked_areas", code_only(s2)):
        err(f"{f}: parks, restores or swaps an area — only Main does (D-33)")
# FarmPlot.restore() works in place on a live (parked) plot: the old crop visual is replaced, never doubled.
rst = code_only(func_body(scripts.get(FP, ""), "restore") or "")
if not re.search(r"func restore\(data: Dictionary, crop: CropDefinition\) -> CropDefinition:\s*if is_instance_valid\(_crop_visual\):\s*crop_root\.remove_child\(_crop_visual\)\s*_crop_visual\.queue_free\(\)\s*_crop_visual = null\s*_recent_crop_ids\.clear\(\)", rst):
    err(f"{FP}: restore() first drops a crop visual the plot already shows (a parked plot restored in place, M08.1)")
# The fade: a CanvasLayer under Main, above the HUD, taking touches only while it covers.
main_children = [a["name"].strip('"') for k, a, b in load_scene_info(MAIN_SCENE)[1] if k == "node" and a.get("parent", "").strip('"') == "."]
if main_children != ["Meadow", "Player", "FollowCamera", "HUD", "TransitionFade"] or scene_root_script_of(FADE_SCENE) != FADE_GD:
    err(f"{MAIN_SCENE}: Main's children are the area, Player, FollowCamera, HUD and TransitionFade, in that order (found {main_children})")
if not re.search(r"^extends CanvasLayer\s*\nclass_name TransitionFade", fd_src, re.M) or (const_val(fd_src, "LAYER") or 0) <= 1 or "layer = LAYER" not in fd_src \
   or not re.search(r"func cover\(\) -> void:\s*_veil\.visible = true\s*_veil\.mouse_filter = Control\.MOUSE_FILTER_STOP\s*await _fade_to\(1\.0, COVER_SECONDS\)", fd_src) \
   or not re.search(r"func reveal\(\) -> void:\s*_veil\.mouse_filter = Control\.MOUSE_FILTER_IGNORE\s*await _fade_to\(0\.0, REVEAL_SECONDS\)\s*_veil\.visible = false", fd_src) \
   or "_veil.mouse_filter = Control.MOUSE_FILTER_IGNORE" not in (func_body(fd_src, "_ready") or ""):
    err(f"{FADE_GD}: the fade sits above the HUD, takes every touch from the start of cover() until reveal() and none while clear")
fsc = open(FADE_SCENE, encoding="utf-8").read() if os.path.exists(FADE_SCENE) else ""
if not re.search(r'\[node name="Veil" type="ColorRect" parent="\."\]\nvisible = false\n(?:[^\[]*\n)?anchor_right = 1\.0\nanchor_bottom = 1\.0\n(?:[^\[]*\n)?mouse_filter = 2\n', fsc):
    err(f"{FADE_SCENE}: one full-screen Veil ColorRect, hidden and ignoring the mouse until a trip")
notes.append(f"area transitions (M08.1): areas {sorted(area_defs)} from data/areas; doors {len(doors)} (ENTER/EXIT, tap only); "
             f"entries {area_entries}; Meadow parked while left; AreaRouter never saved")

# ------------------------------------------------------------ home interior (M08.2)
# The real home on the M08.1 base: a furnished 8 x 6 m room, every piece a placeholder prop scene
# in scenes/world/props/home/ with no script and nothing to interact with (the exit door stays the
# room's only Interactable); solid pieces are StaticBody3D props with one box collider and one carving
# NavigationObstacle3D (the M07.3 pattern: no furniture top bakes as a walkable island); flat pieces
# (the rug, the window light) have no collider. HomeSlot markers reserve where later systems will
# stand the player (bed, chest, desk, hearth, shelves) — data only, read by nothing yet; no rest,
# storage, crafting, cooking or NPC system exists. Warm light from a few lamps, no omni shadows.
# Geometry (inside the room, no overlaps, carve = collider, reachability, slots facing their
# furniture, camera framing, tap reachability over the low wall) is sim_home_layout's.
SLOT_GD, HOME_PROPS = "scripts/world/home_slot.gd", "scenes/world/props/home/"
SLOT_IDS = ["bed", "chest", "desk", "hearth", "shelves"]
FURNITURE_SOLID = ["Bed", "Chest", "Desk", "Hearth", "Shelves", "Stool"]
FURNITURE_FLAT = ["Rug", "WindowLight"]
sl_src = scripts.get(SLOT_GD, "")
if not re.search(r"^extends Marker3D\s*\nclass_name HomeSlot", sl_src, re.M) or 'const GROUP := &"home_slot"' not in sl_src \
   or '@export var slot_id: String = ""' not in sl_src or not re.search(r"func _enter_tree\(\) -> void:\s*add_to_group\(GROUP\)", sl_src) \
   or re.findall(r"^func (\w+)\(", sl_src, re.M) != ["_enter_tree"]:
    err(f"{SLOT_GD}: HomeSlot is a Marker3D with a slot_id that joins the home_slot group — data only")
for f, s2 in scripts.items():
    if f != SLOT_GD and not f.startswith("tools/") and re.search(r"\bHomeSlot\b|home_slot|slot_id", code_only(s2)):
        err(f"{f}: reads the home slots — nothing uses them until a milestone adds rest, storage or crafting")
_, hsecs, hext, _ = load_scene_info(HOME_SCENE)
home_scripts = sorted({script_for_ext(hext, i) for k, a, b in hsecs for i in re.findall(r'script = ExtResource\("([^"]+)"\)', b)})
if home_scripts != sorted([GAME_AREA_GD, ENTRY_GD, CB_GD, SLOT_GD]):
    err(f"{HOME_SCENE}: the home uses only GameArea, AreaEntry, AreaCameraBounds and HomeSlot scripts (found {home_scripts})")
furniture, slot_ids, home_instances = [], [], []
for k, a, b in hsecs:
    if k != "node": continue
    par = a.get("parent", "").strip('"')
    if "instance" in a:
        inst = script_for_ext(hext, re.search(r'ExtResource\("([^"]+)"\)', a["instance"]).group(1))
        home_instances.append(inst)
        if par == "Furniture":
            furniture.append((a["name"].strip('"'), inst))
    if par == "HomeSlots":
        sid = re.search(r'^slot_id = "([^"]*)"', b, re.M)
        slot_ids.append(sid.group(1) if sid else "")
if sorted(n for n, _ in furniture) != sorted(FURNITURE_SOLID + FURNITURE_FLAT) or any(not i.startswith(HOME_PROPS) for _, i in furniture) \
   or sorted(set(home_instances) - {i for _, i in furniture}) != [DOOR_SCENE] or home_instances.count(DOOR_SCENE) != 1:
    err(f"{HOME_SCENE}: the furniture is {sorted(FURNITURE_SOLID + FURNITURE_FLAT)} from {HOME_PROPS}, and the exit door the only other instance (found {furniture})")
if sorted(slot_ids) != SLOT_IDS:
    err(f"{HOME_SCENE}: HomeSlots are exactly {SLOT_IDS} (found {sorted(slot_ids)})")
for name, inst in furniture:
    if not os.path.exists(inst): continue
    ptxt = open(inst, encoding="utf-8").read()
    if 'type="Script"' in ptxt or re.search(r"^script = ", ptxt, re.M) or re.search(r'type="Area3D"|instance=', ptxt):
        err(f"{inst}: furniture is a placeholder with no script, no Area3D and no instanced scene — nothing to interact with yet")
    root = re.search(r'^\[node name="[^"]+" type="(\w+)"\]', ptxt, re.M)
    obstacles = re.findall(r'\[node name="[^"]+" type="NavigationObstacle3D"[^\]]*\]\n(.*?)(?=\n\[|\Z)', ptxt, re.S)
    if name in FURNITURE_SOLID:
        if not root or root.group(1) != "StaticBody3D" or ptxt.count('type="CollisionShape3D"') != 1 or len(obstacles) != 1 \
           or not all(k in obstacles[0] for k in ("affect_navigation_mesh = true", "carve_navigation_mesh = true", "avoidance_enabled = false")):
            err(f"{inst}: a solid piece is a StaticBody3D with one collider and one carving NavigationObstacle3D (affect + carve, no avoidance)")
    elif re.search(r"Body3D|CollisionShape3D|NavigationObstacle3D", ptxt):
        err(f"{inst}: a flat piece has no collider or obstacle — it is walked over")
hs = open(HOME_SCENE, encoding="utf-8").read()
if not re.search(r'\[node name="SouthShape" type="CollisionShape3D" parent="Room"\]\n[^\[]*shape = SubResource\("BoxShape3D_wall_south"\)', hs) \
   or not re.search(r'\[node name="(SouthWallWest|SouthWallEast)" type="MeshInstance3D" parent="Room"\]\n[^\[]*mesh = SubResource\("BoxMesh_wall_low"\)', hs):
    err(f"{HOME_SCENE}: the camera-side wall is a low mesh with its own low collider (sim_home_layout checks its height against the capsule and the tap snap)")
lights = []
for path in [HOME_SCENE] + [i for _, i in furniture if os.path.exists(i)]:
    for kind, body in re.findall(r'\[node name="[^"]+" type="(OmniLight3D|SpotLight3D|DirectionalLight3D)"[^\]]*\]\n(.*?)(?=\n\[|\Z)', open(path, encoding="utf-8").read(), re.S):
        col = re.search(r"light_color = Color\(([^)]*)\)", body)
        rgb = [float(v) for v in col.group(1).split(",")[:3]] if col else [1.0, 1.0, 1.0]
        lights.append((path, kind, rgb, "shadow_enabled = true" in body))
omni = [l for l in lights if l[1] != "DirectionalLight3D"]
if len(omni) > 3 or [l for l in omni if l[3]] or [l for l in lights if not (l[2][0] >= l[2][1] >= l[2][2] and l[2][0] > l[2][2])]:
    err(f"{HOME_SCENE}: the home is lit warm (every light's colour red >= green >= blue), by at most 3 lamps without shadows (found {[(os.path.basename(p), k, c, sh) for p, k, c, sh in lights]})")
notes.append(f"home interior (M08.2): furniture {sorted(n for n, _ in furniture)} (no scripts, nothing interactive; {len(FURNITURE_SOLID)} carving solids); "
             f"slots {sorted(slot_ids)} read by nothing; {len(lights)} warm lights")

# ------------------------------------------------------------ NPC framework (M08.3)
# One neutral placeholder villager — not a Rishi (R-01..R-07 stay open), no relationship, schedule,
# request, service or saved state. NPCs are data (one NpcDefinition per data/npcs/*.tres: id, name,
# greeting, wander radius); the Npc scene consumes its definition and stands where it is placed (the
# Meadow's NpcSpot marker). It wanders a little on the area's own navigation map through its own
# NavigationAgent3D (no other navigation), stops and faces the player within NOTICE_DISTANCE (wider
# than the player's interaction reach, so it is still before the player arrives), steps aside only
# when a moving player is about to bump into it, and keeps its targets clear of area entries. Its body
# is solid (the player collides with it; not in the static bake). Talking is an ordinary Interactable
# (NpcTalk, verb TALK = 10) — Player/InputManager stay unaware — whose interact() shows the greeting
# in the HUD's SpeechPanel; the panel holds the conversation (its speaker) and closes on the ✕, when
# the player walks out of range (set_highlighted(false)) or when the speaker leaves the tree (its area
# parked). No autoload: nothing global is needed for one greeting (sim_npc models the approach).
NPC_DEF_GD, NPC_GD, NPC_TALK_GD, NPC_SCENE = "scripts/npc/npc_definition.gd", "scripts/npc/npc.gd", "scripts/npc/npc_talk.gd", "scenes/npc/Npc.tscn"
SPEECH_GD, SPEECH_SCENE = "scripts/ui/speech_panel.gd", "scenes/ui/SpeechPanel.tscn"
# (M08.4 deliberately replaced the single greeting with a DialogueDefinition — a short sequence of lines.)
# (M09.1 deliberately added the routine — phase -> routine spot id; checked in "NPC routine (M09.1)".)
NPC_DEF_FIELDS = [("id", "String"), ("display_name", "String"), ("dialogue", "DialogueDefinition"), ("wander_radius", "float"), ("routine", "Dictionary")]
nd_src, np_src, nt_src, sp2_src = (scripts.get(f, "") for f in (NPC_DEF_GD, NPC_GD, NPC_TALK_GD, SPEECH_GD))
if not re.search(r"^extends Resource\s*\nclass_name NpcDefinition", nd_src, re.M) or re.search(r"^func ", nd_src, re.M) \
   or re.findall(r"^@export(?:_multiline)? var (\w+): (\w+)", nd_src, re.M) != NPC_DEF_FIELDS:
    err(f"{NPC_DEF_GD}: NpcDefinition has exactly {NPC_DEF_FIELDS} and no logic")
npc_defs = {}
for path in sorted(glob.glob("data/npcs/*.tres")):
    txt = open(path, encoding="utf-8").read()
    fields = dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', txt.split("[resource]", 1)[-1], re.M))
    nid = fields.get("id", "")
    if 'path="res://scripts/npc/npc_definition.gd"' not in txt or nid != os.path.basename(path)[:-5] or not re.fullmatch(r"[a-z][a-z0-9_]*", nid) \
       or not fields.get("display_name") or not re.search(r'^dialogue = ExtResource\("[^"]+"\)$', txt, re.M) or not (0.0 < float(fields.get("wander_radius", "0") or 0) <= 3.0):
        err(f"{path}: an NpcDefinition with a lower_snake id equal to its file name, a name, a dialogue and a wander radius in (0, 3] m")
    if re.search(r"rishi", txt, re.I):
        err(f"{path}: an NPC is never a Rishi until R-01..R-07 are decided")
    npc_defs[nid] = fields
if sorted(npc_defs) != ["villager"]:
    err(f"data/npcs: M08.3 has one placeholder villager (found {sorted(npc_defs)})")
# The Npc: data in, a small wander on the existing navigation, notice, step aside, no state.
if not re.search(r"^extends CharacterBody3D\s*\nclass_name Npc", np_src, re.M) or "@export var definition: NpcDefinition" not in np_src \
   or re.findall(r"^@export var (\w+)", np_src, re.M) != ["definition"]:
    err(f"{NPC_GD}: Npc is a CharacterBody3D whose only export is its NpcDefinition")
consts = {k: const_val(np_src, k) for k in ("NOTICE_DISTANCE", "WALK_SPEED", "YIELD_DISTANCE", "YIELD_LEASH", "DOOR_CLEARANCE")}
reach = const_val(scripts.get(PL, ""), "INTERACTION_RADIUS") or 0.0
talk_r = re.search(r'\[sub_resource type="SphereShape3D" id="SphereShape3D_talk"\]\nradius = ([0-9.]+)', open(NPC_SCENE, encoding="utf-8").read()) if os.path.exists(NPC_SCENE) else None
talk_r = float(talk_r.group(1)) if talk_r else 0.0
if None in consts.values() or not (reach + talk_r < consts["NOTICE_DISTANCE"] <= 4.5) or not (0.0 < consts["YIELD_DISTANCE"] <= 1.2 < consts["NOTICE_DISTANCE"]) \
   or not (0.0 < consts["WALK_SPEED"] <= 1.5) or not (0.0 <= consts["YIELD_LEASH"] <= 1.0) or (consts["DOOR_CLEARANCE"] or 0) < 1.0:
    err(f"{NPC_GD}: it notices the player beyond the interaction reach ({reach} + {talk_r} m) and within 4.5 m, steps aside only at contact range (<= 1.2 m), walks slowly, stays leashed and clear of doors ({consts})")
npc_fn = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", np_src, re.M | re.S)}
ppn = npc_fn.get("_physics_process", "")
if not re.search(r"if player != null and \(talk\.is_tap_selected\(\) or _flat_distance\(player\.global_position\) <= NOTICE_DISTANCE\):\s*_wandering = false\s*_turn_toward\(player\.global_position - global_position, delta\)\s*direction = _yield_direction\(player\)", ppn):
    err(f"{NPC_GD}: from the tap that chooses it, and while the player is within NOTICE_DISTANCE, it stops wandering and faces the player (moving only to step aside)")
if not re.search(r"func is_tap_selected\(\) -> bool:\s*return _tap_selected\s*$", code_only(func_body(base_src, "is_tap_selected") or "").strip() + "\n") \
   or any(func_body(scripts[f], "is_tap_selected") is not None for f in subclasses) \
   or [f for f, s2 in scripts.items() if re.search(r"\._tap_selected\b|_tap_selected\s*=", code_only(s2)) and f != BASE]:
    err(f"{BASE}: is_tap_selected() only reads the tap selection (Player alone sets it) and is never overridden")
sw2 = npc_fn.get("_start_wander", "")
if "var radius := definition.wander_radius if definition else 0.0" not in sw2 or "NavigationServer3D.map_get_closest_point(map, candidate)" not in sw2 \
   or "nav_agent.target_position = point" not in sw2 or "<= radius and _clear_of_doors(point)" not in sw2 or "get_world_3d().navigation_map" not in sw2:
    err(f"{NPC_GD}: wander targets are points of the area's own navigation map within the definition's radius of home, clear of doors, walked by its NavigationAgent3D")
if re.search(r"NavigationRegion3D|bake_navigation|AStar|map_create|region_create|navigation_mesh|set_navigation_map", code_only(np_src)):
    err(f"{NPC_GD}: an NPC uses the existing navigation map only — no regions, bakes or path-finding of its own")
yd = npc_fn.get("_yield_direction", "")
if "var touching := to_me.length() <= YIELD_CONTACT" not in yd \
   or "var heading_at_me := motion.length() >= YIELD_MIN_PLAYER_SPEED and to_me.length() <= YIELD_DISTANCE and motion.dot(to_me) > 0.0" not in yd \
   or not re.search(r"if not touching and not heading_at_me:\s*_yield_side = Vector3\.ZERO\s*return Vector3\.ZERO", yd) \
   or not re.search(r"if _yield_side == Vector3\.ZERO:", yd) or "for candidate in [_yield_side, -_yield_side]:" not in yd \
   or "<= leash and _clear_of_doors(step)" not in npc_fn.get("_step_allowed", "") \
   or not (0.0 < (const_val(np_src, "YIELD_CONTACT") or 0) <= consts["YIELD_DISTANCE"]):
    err(f"{NPC_GD}: it steps aside only when touched or about to be walked into, to one committed side (the other if blocked), within its leash and clear of doors")
if re.search(r"SaveManager|save|user://|FileAccess|FarmManager|Inventory|Wallet|PointsManager|DiscoveryManager|AreaRouter|\bMain\b|\.place_at\(|_interact_with", code_only(np_src + nt_src + sp2_src)):
    err("scripts/npc/*, scripts/ui/speech_panel.gd: an NPC and its greeting save nothing and touch no game system, travel or Player internals")
if re.search(r"\b(villager|Villager)\b|calm day in the meadow", "\n".join(code_only(s2) for f, s2 in scripts.items() if not f.startswith("tools/"))):
    err("an NPC's identity and words live only in data/npcs — no script names them")
# The Npc scene: a solid body, its own agent, the TALK Interactable with the shared Indicator.
ns_txt = open(NPC_SCENE, encoding="utf-8").read() if os.path.exists(NPC_SCENE) else ""
ns_root = re.search(r'^\[node name="Npc" type="CharacterBody3D"\]\n(.*?)\n\n', ns_txt, re.M | re.S)
if not ns_root or "collision_layer" in ns_root.group(1) or "collision_mask" in ns_root.group(1) or scene_root_script_of(NPC_SCENE) != NPC_GD \
   or not re.search(r'\[node name="CollisionShape3D" type="CollisionShape3D" parent="\."\]\n[^\[]*shape = SubResource\("CapsuleShape3D_body"\)', ns_txt) \
   or ns_txt.count('type="NavigationAgent3D"') != 1 or "avoidance_enabled = true" in ns_txt \
   or not re.search(r'\[node name="NpcTalk" type="Area3D" parent="\."\]\ncollision_layer = 4\ncollision_mask = 0\nscript = ExtResource\("2"\)', ns_txt) \
   or "DiscoveryIndicator.tscn" not in ns_txt or 'type="StaticBody3D"' in ns_txt or "NavigationObstacle3D" in ns_txt:
    err(f"{NPC_SCENE}: a solid CharacterBody3D on the world layer (not a static collider, so never baked) with a capsule, one NavigationAgent3D, and the NpcTalk Interactable (interactables layer, detecting nothing) with the shared Indicator")
# NpcTalk: TALK through the normal contract; greeting from data into the SpeechPanel; walking away closes.
nt_fn = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", nt_src, re.M | re.S)}
if not re.search(r"^extends Interactable\s*\nclass_name NpcTalk", nt_src, re.M) or "remove_on_harvest = false" not in nt_fn.get("_ready", "") \
   or not re.search(r'_panel = get_tree\(\)\.get_first_node_in_group\(SpeechPanel\.GROUP\) as SpeechPanel.*return _panel\.open\(self, npc\.definition\.display_name, npc\.definition\.dialogue\.lines\)', nt_fn.get("interact", ""), re.S) \
   or not re.search(r"super\(active\)\s*if not active and _panel != null:\s*_panel\.close_for\(self\)", nt_fn.get("set_highlighted", "")) \
   or "return npc.definition.dialogue.lines" not in nt_fn.get("_lines", "") or "if not _lines().is_empty():" not in nt_fn.get("_get_interaction_verbs", ""):
    err(f"{NPC_TALK_GD}: TALK starts the definition's dialogue in the SpeechPanel (offered only while it has lines), and leaving interaction range closes it")
if VERBS.get("TALK") != 10 or {k: v for k, v in VERBS.items() if k != "TALK"} != {"COLLECT": 1, "PLANT": 2, "WATER": 3, "HARVEST": 4, "INSPECT": 5, "OPEN": 6, "READ": 7, "ENTER": 8, "EXIT": 9}:
    err(f"{BASE}: TALK is appended as 10 and every earlier verb keeps its value (found {VERBS})")
# Placement: exactly one NPC, standing at the NpcSpot marker, with a definition from data/npcs.
npcs_placed = []
for path in glob.glob("scenes/**/*.tscn", recursive=True):
    _, secs3, ext3, _ = load_scene_info(path)
    for k, a, b in secs3:
        if k == "node" and "instance" in a and script_for_ext(ext3, re.search(r'ExtResource\("([^"]+)"\)', a["instance"]).group(1)) == NPC_SCENE:
            dref = re.search(r'^definition = ExtResource\("([^"]+)"\)', b, re.M)
            npcs_placed.append((path, a.get("parent", "").strip('"'), script_for_ext(ext3, dref.group(1)) if dref else None,
                                bool(re.search(r"^(position|transform|rotation|rotation_degrees) = ", b, re.M))))
if npcs_placed != [(MEADOW_SCENE, "VerticalSlice/NpcSpot", "data/npcs/villager.tres", False)]:
    err(f"the one NPC stands exactly at the Meadow's NpcSpot marker (its authored position) with its data/npcs definition (found {npcs_placed})")
# The speech panel: non-modal, bottom-centre, the ✕ closes; its own state; docked by the HUD's safe area.
SPN2, _ = scene_nodes(SPEECH_SCENE)
spr2 = SPN2.get(".", ("", ""))[1]; spp2 = SPN2.get("Panel", ("", ""))[1]
if prop(spr2, "mouse_filter") != "2" or "Dim" in SPN2 or prop(spp2, "anchor_top") != "1.0" or prop(spp2, "anchor_bottom") != "1.0" \
   or prop(spp2, "anchor_left") != "0.5" or prop(spp2, "anchor_right") != "0.5" or prop(spp2, "grow_vertical") != "0" \
   or prop(SPN2.get("Panel/VBoxContainer/Row/CloseButton", ("", ""))[1], "custom_minimum_size") != "Vector2(120, 120)":
    err(f"{SPEECH_SCENE}: a non-modal panel (root ignores the mouse, no dim) docked at the bottom centre growing upward, with a 120 px ✕")
sp2_fn = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", sp2_src, re.M | re.S)}
if not re.search(r"^extends Control\s*\nclass_name SpeechPanel", sp2_src, re.M) or 'const GROUP := &"speech_panel"' not in sp2_src \
   or "add_to_group(GROUP)" not in sp2_fn.get("_ready", "") or "_speaker.tree_exiting.connect(close)" not in sp2_fn.get("open", "") \
   or not re.search(r"if speaker == _speaker and visible:\s*return true", sp2_fn.get("open", "")) \
   or not re.search(r"if speaker == _speaker:\s*close\(\)", sp2_fn.get("close_for", "")) \
   or not re.search(r"AmbientAudioManager\.play_ui_feedback\(\)\s*close\(\)\s*$", sp2_fn.get("_on_close_pressed", "")):
    err(f"{SPEECH_GD}: the panel keeps its speaker, opens once per speaker, closes on the ✕, for its own speaker only, and when the speaker leaves the tree")
sa4 = code_only(func_body(scripts.get("scripts/ui/hud.gd", ""), "_apply_safe_area") or "")
if 'var speech: Control = speech_panel.get_node("Panel")' not in sa4 or "speech.offset_bottom = -(EDGE_MARGIN + insets[3])" not in sa4 \
   or "speech.offset_left = (insets[0] - insets[2]) / 2.0" not in sa4:
    err("scripts/ui/hud.gd: the speech panel keeps clear of the gesture bar and centres between the side insets (safe area)")
if "ConversationManager" in cfg or any(re.search(r"\bConversation\w*\b", code_only(s2)) for f, s2 in scripts.items() if not f.startswith("tools/")):
    err("M08.3 keeps the conversation in the SpeechPanel — no global conversation state")
notes.append(f"NPC framework (M08.3): npcs {sorted(npc_defs)} from data/npcs; one placed at NpcSpot; notice {consts['NOTICE_DISTANCE']} m > reach {reach + talk_r:.1f} m; "
             f"TALK = {VERBS.get('TALK')}; speech panel in the HUD (shared theme, safe area, 120 px ✕); no autoload, no saved state")

# ------------------------------------------------------------ dialogue (M08.4, D-37)
# A short, linear conversation as data: one DialogueDefinition per data/dialogues/*.tres (id, ordered lines;
# no branches, conditions or outcomes), referred to from an NpcDefinition. The M08.3 SpeechPanel was extended,
# not replaced: it keeps the conversation (speaker, lines, index); only its Next button moves on — "Goodbye" on
# the last line ends it complete; the ✕, walking out of range (close_for) and the speaker leaving the tree end
# it early; every conversation ends exactly once with conversation_ended(speaker, completed), which nothing
# listens to yet (M08.5's hook). Re-tapping the NPC never restarts or skips. No save state, no global manager.
DLG_GD = "scripts/npc/dialogue_definition.gd"
dl_src = scripts.get(DLG_GD, "")
if not re.search(r"^extends Resource\s*\nclass_name DialogueDefinition", dl_src, re.M) or re.search(r"^func ", dl_src, re.M) \
   or re.findall(r"^@export(?:_multiline)? var (\w+): (\w+)", dl_src, re.M) != [("id", "String"), ("lines", "PackedStringArray")]:
    err(f"{DLG_GD}: DialogueDefinition is exactly an id and ordered lines — no branches, conditions or outcomes yet, no logic")
dialogues = {}
for path in sorted(glob.glob("data/dialogues/*.tres")):
    txt = open(path, encoding="utf-8").read()
    did = re.search(r'^id = "([^"]*)"$', txt, re.M)
    lines_m = re.search(r'^lines = PackedStringArray\((.*)\)$', txt, re.M)
    lines = re.findall(r'"((?:[^"\\]|\\.)*)"', lines_m.group(1)) if lines_m else []
    if 'path="res://scripts/npc/dialogue_definition.gd"' not in txt or not did or did.group(1) != os.path.basename(path)[:-5] \
       or not re.fullmatch(r"[a-z][a-z0-9_]*", did.group(1)) or not (2 <= len(lines) <= 8) or any(not l.strip() or len(l) > 120 for l in lines):
        err(f"{path}: a DialogueDefinition with a lower_snake id equal to its file name and 2-8 non-empty lines of at most 120 characters (they fit the panel)")
    if re.search(r"rishi", txt, re.I):
        err(f"{path}: dialogue never names a Rishi until R-01..R-07 are decided")
    dialogues[did.group(1) if did else path] = lines
for path in sorted(glob.glob("data/npcs/*.tres")):
    txt = open(path, encoding="utf-8").read()
    ref = re.search(r'^dialogue = ExtResource\("([^"]+)"\)$', txt, re.M)
    ext_d = dict((m.group(2), m.group(1)) for m in re.finditer(r'\[ext_resource type="Resource" path="res://([^"]+)" id="([^"]+)"\]', txt))
    if not ref or not ext_d.get(ref.group(1), "").startswith("data/dialogues/") or not os.path.exists(ext_d.get(ref.group(1), "")):
        err(f"{path}: an NPC's dialogue is a data/dialogues/ resource")
sp4 = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", sp2_src, re.M | re.S)}
if re.findall(r"^signal (.+)$", sp2_src, re.M) != ["conversation_ended(speaker: Node, completed: bool)"]:
    err(f"{SPEECH_GD}: the panel announces only conversation_ended(speaker, completed)")
if not re.search(r"func open\(speaker: Node, speaker_name: String, lines: PackedStringArray, end_text: String = END_TEXT\) -> bool:\s*if speaker == null or lines\.is_empty\(\):\s*return false\s*if speaker == _speaker and visible:\s*return true\s*_end\(false\)", sp4.get("open", "")) \
   or "_index = 0" not in sp4.get("open", "") or "_lines = lines" not in sp4.get("open", "") \
   or not re.search(r"_end\(false\)(.|\n)*_end_text = end_text", sp4.get("open", "")) or "_end_text = END_TEXT" not in sp4.get("_end", "") \
   or [fn for fn, b in sp4.items() if re.search(r"\b_end_text\s*=[^=]", b) and fn not in ("open", "_end")] \
   or not re.search(r"^var _end_text: String = END_TEXT$", sp2_src, re.M):
    err(f"{SPEECH_GD}: open() starts a conversation at its first line, ends any other first, and is a no-op for the speaker already shown (no restart, no skip)")
if not re.search(r"if _speaker == null:\s*return\s*if _index >= _lines\.size\(\) - 1:\s*_end\(true\)\s*return\s*_index \+= 1\s*_show_line\(\)", sp4.get("advance", "")):
    err(f"{SPEECH_GD}: advance() shows the next line, and past the last ends the conversation complete")
if not re.search(r"func _on_next_pressed\(\) -> void:\s*AmbientAudioManager\.play_ui_feedback\(\)\s*advance\(\)\s*$", sp4.get("_on_next_pressed", "")) \
   or "next_button.pressed.connect(_on_next_pressed)" not in sp4.get("_ready", "") \
   or [f for f, s2 in scripts.items() if f != SPEECH_GD and re.search(r"\.advance\(\)", code_only(s2))] \
   or re.search(r"_gui_input|_unhandled_input|_input\(|gui_input", code_only(sp2_src)):
    err(f"{SPEECH_GD}: only the Next button advances a conversation — no other touch, input handler or script moves it on")
if not re.search(r"if _speaker == null:\s*visible = false\s*return", sp4.get("_end", "")) or sp4.get("_end", "").count("conversation_ended.emit(") != 1 \
   or "_speaker = null" not in sp4.get("_end", "") or code_only(sp2_src).count("conversation_ended.emit(") != 1 \
   or not re.search(r"func close\(\) -> void:\s*_end\(false\)", sp4.get("close", "")) \
   or [fn for fn in ("open", "advance", "close") if "visible = false" in sp4.get(fn, "")]:
    err(f"{SPEECH_GD}: every conversation ends through _end() exactly once — complete only past the last line, early on the ✕, walking away or the speaker leaving")
if 'next_button.text = _end_text if _index >= _lines.size() - 1 else NEXT_TEXT' not in sp4.get("_show_line", "") \
   or 'const END_TEXT := "Goodbye"' not in sp2_src or 'const NEXT_TEXT := "Next ▸"' not in sp2_src or '"%d / %d" % [_index + 1, _lines.size()]' not in sp4.get("_show_line", ""):
    err(f"{SPEECH_GD}: the Next button reads Goodbye on the last line, and the progress shows the line out of the total")
# M08.5 (D-38): exactly one listener — the speaking NpcTalk, connected once from interact(), acting only
# on its own completed conversations (relationships section below).
listeners = [f for f, s2 in scripts.items() if re.search(r"conversation_ended\.connect", code_only(s2))]
if listeners != ["scripts/npc/npc_talk.gd"]:
    err(f"conversation_ended has exactly one listener, NpcTalk (M08.5) — found {listeners}")
SPN3, _ = scene_nodes(SPEECH_SCENE)
nb = SPN3.get("Panel/VBoxContainer/Row/NextButton", ("", ""))
if 'type="Button"' not in nb[0] or prop(nb[1], "theme_type_variation") != '&"PrimaryButton"' or prop(nb[1], "focus_mode") != "0" \
   or prop(SPN3.get("Panel", ("", ""))[1], "custom_minimum_size") is None:
    err(f"{SPEECH_SCENE}: the Next button is a primary, never-focused button (its 120 px minimum is checked with the other UI buttons)")
notes.append(f"dialogue (M08.4): dialogues {sorted(dialogues)} ({[len(v) for v in dialogues.values()]} lines) from data/dialogues; Next-only progression, one end per conversation, no listener yet")

# ------------------------------------------------------------ relationships (M08.5, D-38)
# Friendship per NPC id — one whole number, 0..MAX_FRIENDSHIP — held by the Relationships autoload (outside
# every area, so it outlives the parked Meadow), saved in its own section (save v6, D-17). A completed
# conversation (conversation_ended with completed = true, heard by the speaking NpcTalk) earns +1, at most
# once per system-calendar day per NPC (DailyDiscoveryManager's date); an early end never does. Nothing is
# shown and nothing reads it but the save; Player, InputManager and the panel know nothing of it.
RL = "scripts/autoload/relationships.gd"
rl_src = scripts.get(RL, "")
rlf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", rl_src, re.M | re.S)}
rl_code = code_only(rl_src)
if not re.match(r"extends Node\n", rl_src) or re.findall(r"^signal (.+)$", rl_src, re.M) != ["friendship_changed(npc_id: String, friendship: int)"] \
   or const_val(rl_src, "MAX_FRIENDSHIP") != 10 or 'const NPCS_PATH := "res://data/npcs/"' not in rl_src \
   or re.findall(r"^var (\w+)", rl_src, re.M) != ["_friendship", "_last_gain_date", "_known_ids"] \
   or [f for f in rlf if not f.startswith("_")] != ["get_friendship", "record_completed_conversation", "get_save_data", "apply_save_data"]:
    err(f"{RL}: Relationships is a Node with exactly friendship_changed(npc_id, friendship), MAX_FRIENDSHIP 10, the NPC data folder, "
        "the friendship / last-gain-date / known-id state and the API get_friendship, record_completed_conversation, get_save_data, apply_save_data")
if not re.search(r"for path in ResourceDirectory\.list_tres_paths\(NPCS_PATH\):\s*var definition := load\(path\) as NpcDefinition\s*"
                 r'if definition != null and definition\.id != "":\s*_known_ids\.append\(definition\.id\)', rlf.get("_ready", "")):
    err(f"{RL}: the known NPCs are the NpcDefinition ids in data/npcs/ — friendship is keyed by that stable id")
rc = rlf.get("record_completed_conversation", "")
steps = ["if not _known_ids.has(npc_id):", "return false", "var today := _today_string()", "if _last_gain_date.get(npc_id, \"\") == today:", "return false",
         "var friendship := get_friendship(npc_id)", "if friendship >= MAX_FRIENDSHIP:", "return false", "_friendship[npc_id] = friendship + 1",
         "_last_gain_date[npc_id] = today", "friendship_changed.emit(npc_id, friendship + 1)", "return true"]
pos, ok = 0, True
for st in steps:
    k = rc.find(st, pos)
    if k < 0: ok = False; break
    pos = k + len(st)
if not ok:
    err(f"{RL}: a completed conversation: unknown NPC → nothing; already earned today → nothing; at the maximum → nothing; else +1, today recorded, announced")
if rl_code.count("friendship_changed.emit(") != 1 or "friendship_changed.emit(" in rlf.get("apply_save_data", ""):
    err(f"{RL}: friendship_changed is announced only by a +1 — never by a load")
for var in ("_friendship", "_last_gain_date"):
    writers = {fn for fn, b in rlf.items() if re.search(rf"\b{var}(\[[^\]]+\]\s*=[^=]|\s*=[^=]|\.(clear|erase|merge|assign)\b)", b)}
    if writers != {"record_completed_conversation", "apply_save_data"}:
        err(f"{RL}: {var} is written only by a +1 and on load (found {sorted(writers)})")
dd_today = func_body(scripts.get("scripts/autoload/daily_discovery_manager.gd", ""), "_today_string") or ""
if not dd_today or code_only(dd_today).split("\n", 1)[1:] != code_only(func_body(rl_src, "_today_string") or "").split("\n", 1)[1:]:
    err(f"{RL}: the day is the system date exactly as DailyDiscoveryManager reads it")
ap = rlf.get("apply_save_data", "")
if not re.search(r"_friendship\.clear\(\)\s*_last_gain_date\.clear\(\)", ap) \
   or not re.search(r"if typeof\(npc_id\) != TYPE_STRING or not _known_ids\.has\(npc_id\):\s*push_warning\(.*?\)\n\s*continue", ap) \
   or not re.search(r"if typeof\(entry\) != TYPE_DICTIONARY:\s*push_warning\(.*?\)\n\s*continue", ap) \
   or not re.search(r"if typeof\(value\) != TYPE_INT and typeof\(value\) != TYPE_FLOAT:\s*push_warning\(.*?\)\n\s*continue", ap) \
   or "_friendship[npc_id] = clampi(int(value), 0, MAX_FRIENDSHIP)" not in ap \
   or re.search(r"record_completed_conversation|\.emit\(|SaveManager|PointsManager", ap):
    err(f"{RL}: a load keeps only known NPC ids, drops malformed records with a warning, clamps friendship to 0..MAX_FRIENDSHIP and announces nothing")
if not re.search(r'data\[npc_id\] = \{"friendship": _friendship\[npc_id\], "last_gain_date": _last_gain_date\.get\(npc_id, ""\)\}', rlf.get("get_save_data", "")):
    err(f"{RL}: the save holds exactly each NPC's friendship and the day it last rose")
if re.search(r"PointsManager|Wallet|Inventory|FarmManager|DiscoveryManager|ExplorationManager|Market|SaveManager|AreaRouter|GameState|get_tree\(|get_node|"
             r"\$\w|Player|InputManager|SpeechPanel|DialogueDefinition", rl_code):
    err(f"{RL}: Relationships only holds friendship — it touches no other system, saves nothing itself, holds no node and knows no dialogue")
for f, s2 in scripts.items():
    if f.startswith("tools/") or f == RL: continue
    code = code_only(s2)
    if re.search(r"\bRelationships\._|\bRelationships\.(get_save_data|apply_save_data)\(", code) and f != "scripts/autoload/save_manager.gd":
        err(f"{f}: reaches into Relationships — only SaveManager saves/loads it")
    if re.search(r"\bRelationships\.record_completed_conversation\(", code) and f != "scripts/npc/npc_talk.gd":
        err(f"{f}: changes friendship — only the speaking NpcTalk reports a completed conversation (D-38)")
    if re.search(r"\bRelationships\.get_friendship\(|\bfriendship\b", code) and f not in ("scripts/npc/npc_talk.gd",):
        err(f"{f}: reads or shows friendship — nothing does yet (no meter, toast, number, dialogue change or reward, D-38)")
    if re.search(r"friendship_changed\.connect", code) and f != "scripts/autoload/game_state.gd":
        err(f"{f}: listens to friendship changes — only GameState does, to save")
nt5 = code_only(scripts.get("scripts/npc/npc_talk.gd", ""))
oc = code_only(func_body(scripts.get("scripts/npc/npc_talk.gd", ""), "_on_conversation_ended") or "")
# (M08.6: the handler first acts on its own request step, then reports to Relationships exactly as before — every
#  completed conversation of its own, by definition id; the requests section checks the request part.)
if not re.search(r"if not _panel\.conversation_ended\.is_connected\(_on_conversation_ended\):\s*_panel\.conversation_ended\.connect\(_on_conversation_ended\)\s*"
                 r"if _panel\.get_speaker\(\) == self and _panel\.visible:\s*return true\s*var npc := get_parent\(\) as Npc\s*", code_only(func_body(scripts.get("scripts/npc/npc_talk.gd", ""), "interact") or "")) \
   or not re.search(r"^func _on_conversation_ended\(speaker: Node, completed: bool\) -> void:\s*if speaker != self:\s*return\s*", oc) \
   or not re.search(r"if not completed:\s*return\s*(.|\n)*var npc := get_parent\(\) as Npc\s*if npc != null and npc\.definition != null:\s*"
                    r"Relationships\.record_completed_conversation\(npc\.definition\.id\)\s*$", oc) \
   or nt5.count("Relationships.") != 1 or len(re.findall(r"conversation_ended\.connect\(", nt5)) != 1:
    err("scripts/npc/npc_talk.gd: NpcTalk connects to the panel once, and reports only its own completed conversations, by its NPC's definition id")
for f in ("scripts/player/player.gd", "scripts/autoload/input_manager.gd", SPEECH_GD, "scripts/npc/npc.gd", "scripts/ui/hud.gd"):
    if re.search(r"Relationships|friendship", code_only(scripts.get(f, ""))):
        err(f"{f}: knows about relationships — only NpcTalk reports to Relationships (D-38)")
sm6 = scripts.get("scripts/autoload/save_manager.gd", "")
if '"relationships": Relationships.get_save_data(),' not in code_only(func_body(sm6, "save_game") or "") \
   or 'Relationships.apply_save_data(data.get("relationships", {}))' not in code_only(func_body(sm6, "load_game") or "") \
   or not re.search(r"^\t\t\t5:\s*pass\b", code_only(func_body(sm6, "_migrate") or ""), re.M) \
   or not re.search(r'^\t"relationships": \[TYPE_DICTIONARY\],$', sm6, re.M) or (const_val(sm6, "SAVE_VERSION") or 0) < 6:
    err("scripts/autoload/save_manager.gd: save v6 — the relationships section is saved and loaded as a dictionary; step 5 -> 6 (M08.5) rewrites nothing (absent = every NPC at 0)")
if "Relationships.friendship_changed.connect(_save.unbind(2))" not in code_only(func_body(scripts.get("scripts/autoload/game_state.gd", ""), "_ready") or ""):
    err("scripts/autoload/game_state.gd: a friendship rise is saved at once (GameState, friendship_changed)")
notes.append(f"relationships (M08.5): friendship per NPC id 0..{const_val(rl_src, 'MAX_FRIENDSHIP')}, +1 per completed conversation once a day; save v6; one listener (NpcTalk), one saver (GameState)")

# ------------------------------------------------------------ requests (M08.6, D-39)
# One NPC request as data (RequestDefinition, data/requests/): the NPC voices a problem (offer), reminds
# (pending) while the player holds too few of a single-quality item, and takes them (hand-over, last button
# "Give"). The Requests autoload keeps only each request's state (absent / accepted / completed), saved in its
# own section (save v7, D-17). A completed offer conversation accepts; a completed hand-over completes:
# checked, recorded, then paid — accepted → items held → items removed → completed → reward_points once →
# announced (GameState saves; the HUD shows the usual card). No quest log, tracker or marker.
RQD, RQ = "scripts/npc/request_definition.gd", "scripts/autoload/requests.gd"
rqd_src, rq_src = scripts.get(RQD, ""), scripts.get(RQ, "")
rqf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", rq_src, re.M | re.S)}
rq_code = code_only(rq_src)
RQ_FIELDS = {"id": "String", "npc_id": "String", "item_id": "String", "quantity": "int", "reward_points": "int",
             "offer_dialogue": "DialogueDefinition", "pending_dialogue": "DialogueDefinition", "handover_dialogue": "DialogueDefinition"}
if not re.search(r"^extends Resource\s*\nclass_name RequestDefinition", rqd_src, re.M) \
   or dict(re.findall(r"^@export var (\w+): (\w+)", rqd_src, re.M)) != RQ_FIELDS \
   or re.search(r"^(func|var|const|signal|static) ", code_only(rqd_src), re.M):
    err(f"{RQD}: RequestDefinition is exactly {list(RQ_FIELDS)} — no logic, no branches, conditions or chains")
npc_ids_rq = {re.search(r'^id = "(\w+)"', open(f, encoding="utf-8").read(), re.M).group(1) for f in glob.glob("data/npcs/*.tres")}
rq_files = sorted(glob.glob("data/requests/*.tres"))
if len(rq_files) != 1:
    err(f"data/requests: exactly one request in M08.6 (found {rq_files})")
rq_npcs = []
for path in rq_files:
    txt = open(path, encoding="utf-8").read()
    vals = dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', txt, re.M))
    ext = dict((m.group(2), m.group(1)) for m in re.finditer(r'\[ext_resource type="Resource" path="res://([^"]+)" id="([^"]+)"\]', txt))
    item_path = f"data/items/{vals.get('item_id', '')}.tres"
    item_txt = open(item_path, encoding="utf-8").read() if os.path.exists(item_path) else ""
    q, r = vals.get("quantity", "1"), vals.get("reward_points", "0")
    if 'script_class="RequestDefinition"' not in txt or vals.get("id") != os.path.basename(path)[:-5] or not re.fullmatch(r"[a-z][a-z0-9_]*", vals.get("id", "")) \
       or vals.get("npc_id") not in npc_ids_rq or not item_txt or int((re.search(r"^quality_levels = (\d+)", item_txt, re.M) or re.search("()1", "1")).group(1) or 1) != 1 \
       or not q.isdigit() or not 1 <= int(q) <= 9 or not r.isdigit() or int(r) < 1:
        err(f"{path}: a RequestDefinition — lower_snake id = its file name, a real NPC, a real single-quality item, quantity 1-9, reward_points >= 1")
    for key in ("offer_dialogue", "pending_dialogue", "handover_dialogue"):
        ref = re.search(rf'^{key} = ExtResource\("([^"]+)"\)$', txt, re.M)
        if not ref or not ext.get(ref.group(1), "").startswith("data/dialogues/") or not os.path.exists(ext.get(ref.group(1), "")):
            err(f"{path}: {key} is a data/dialogues/ resource")
    rq_npcs.append(vals.get("npc_id"))
if len(rq_npcs) != len(set(rq_npcs)):
    err("data/requests: at most one request per NPC")
if not re.match(r"extends Node\n", rq_src) \
   or re.findall(r"^signal (.+)$", rq_src, re.M) != ["request_accepted(request_id: String)", "request_completed(request_id: String, item_id: String, quantity: int, points: int)"] \
   or re.findall(r"^var (\w+)", rq_src, re.M) != ["_definitions", "_states"] \
   or dict(re.findall(r'^const (\w+) := "(\w*)"$', rq_src, re.M)) != {"ACCEPTED": "accepted", "COMPLETED": "completed", "STEP_OFFER": "offer", "STEP_PENDING": "pending", "STEP_HANDOVER": "handover"} \
   or 'const REQUESTS_PATH := "res://data/requests/"' not in rq_src or const_val(rq_src, "MAX_QUANTITY") != 9 \
   or [f for f in rqf if not f.startswith("_")] != ["conversation_for", "get_state", "accept", "complete", "get_save_data", "apply_save_data"]:
    err(f"{RQ}: Requests is a Node with exactly request_accepted / request_completed(request_id, item_id, quantity, points), the definitions and "
        "the states (accepted / completed), the offer / pending / hand-over steps and the API conversation_for, get_state, accept, complete, get_save_data, apply_save_data")
cp = rqf.get("complete", "")
steps = ["var definition: RequestDefinition = _definitions.get(request_id)", "if definition == null or _states.get(request_id, \"\") != ACCEPTED:", "return false",
         "if not Inventory.has(definition.item_id, definition.quantity, 0):", "return false",
         "if not Inventory.remove(definition.item_id, definition.quantity, 0):", "return false",
         "_states[request_id] = COMPLETED", "PointsManager.add_points(definition.reward_points)",
         "request_completed.emit(request_id, definition.item_id, definition.quantity, definition.reward_points)", "return true"]
pos, ok = 0, True
for st in steps:
    k = cp.find(st, pos)
    if k < 0: ok = False; break
    pos = k + len(st)
if not ok or cp.count("Inventory.remove(") != 1 or "Inventory.add(" in rq_code or rq_code.count("Inventory.remove(") != 1 or rq_code.count("PointsManager.add_points(") != 1:
    err(f"{RQ}: complete() is checked, recorded, then paid — accepted → the items held → removed (all or nothing) → completed → reward_points once → announced")
if not re.search(r"if not _definitions\.has\(request_id\) or _states\.has\(request_id\):\s*return false\s*_states\[request_id\] = ACCEPTED\s*request_accepted\.emit\(request_id\)\s*return true", rqf.get("accept", "")):
    err(f"{RQ}: accept() accepts a known request only once, never one already accepted or completed")
writers = {fn for fn, b in rqf.items() if re.search(r"\b_states(\[[^\]]+\]\s*=[^=]|\s*=[^=]|\.(clear|erase|merge|assign)\b)", b)}
if writers != {"accept", "complete", "apply_save_data"} or rq_code.count("request_accepted.emit(") != 1 or rq_code.count("request_completed.emit(") != 1:
    err(f"{RQ}: a request's state is written only by accept(), complete() and a load; each is announced once (found {sorted(writers)})")
apq = rqf.get("apply_save_data", "")
if not re.search(r"_states\.clear\(\)", apq) \
   or not re.search(r"if typeof\(request_id\) != TYPE_STRING or not _definitions\.has\(request_id\):\s*push_warning\(.*?\)\n\s*continue", apq) \
   or not re.search(r"if typeof\(state\) == TYPE_STRING and \(state == ACCEPTED or state == COMPLETED\):\s*_states\[request_id\] = state\s*else:\s*push_warning\(.*?\)\n\s*_states\[request_id\] = COMPLETED", apq) \
   or re.search(r"\.emit\(|PointsManager|Inventory|accept\(|complete\(", apq):
    err(f"{RQ}: a load keeps known requests' states, drops unknown ids with a warning, counts a malformed state as completed (never paid twice) and announces nothing")
if "return _states.duplicate()" not in rqf.get("get_save_data", ""):
    err(f"{RQ}: the save holds exactly each request's state")
cf = rqf.get("conversation_for", "")
if not re.search(r'if state == "":\s*return \{"request_id": request_id, "step": STEP_OFFER, "lines": definition\.offer_dialogue\.lines\}', cf) \
   or not re.search(r'if state == ACCEPTED:\s*if Inventory\.has\(definition\.item_id, definition\.quantity, 0\):\s*return \{"request_id": request_id, "step": STEP_HANDOVER, "lines": definition\.handover_dialogue\.lines\}\s*'
                    r'return \{"request_id": request_id, "step": STEP_PENDING, "lines": definition\.pending_dialogue\.lines\}', cf) \
   or not cf.rstrip().endswith("return {}"):
    err(f"{RQ}: conversation_for(): not offered → the offer; accepted with the items → the hand-over; accepted without → the pending reminder; completed → the NPC's usual dialogue")
iv = rqf.get("_is_valid", "")
if "item.quality_levels != 1" not in iv or "definition.quantity < 1 or definition.quantity > MAX_QUANTITY or definition.reward_points < 1" not in iv \
   or "if other.npc_id == definition.npc_id or other.id == definition.id:" not in iv or "npc_ids.has(definition.npc_id)" not in iv:
    err(f"{RQ}: a request is used only if its NPC and single-quality item exist, its quantity is 1..MAX_QUANTITY, it pays >= 1 point and its NPC has no other request")
if re.search(r"Wallet|Market|Relationships|friendship|SaveManager|GameState|FarmManager|DiscoveryManager|ExplorationManager|AreaRouter|get_tree\(|get_node|\$\w|"
             r"Player|InputManager|SpeechPanel|HUD", rq_code):
    err(f"{RQ}: Requests touches only the Inventory (read; one removal) and PointsManager (one payment) — no coins, friendship, saving, nodes or UI")
for f, s2 in scripts.items():
    if f.startswith("tools/") or f == RQ: continue
    code = code_only(s2)
    if re.search(r"\bRequests\._|\bRequests\.(get_save_data|apply_save_data)\(", code) and f != "scripts/autoload/save_manager.gd":
        err(f"{f}: reaches into Requests — only SaveManager saves/loads it")
    if re.search(r"\bRequests\.(accept|complete|conversation_for)\(", code) and f != "scripts/npc/npc_talk.gd":
        err(f"{f}: drives a request — only the speaking NpcTalk does (D-39)")
    if re.search(r"request_accepted\.connect", code) and f != "scripts/autoload/game_state.gd":
        err(f"{f}: listens to request acceptance — only GameState does, to save")
    if re.search(r"request_completed\.connect", code) and f not in ("scripts/autoload/game_state.gd", "scripts/ui/hud.gd"):
        err(f"{f}: listens to request completion — only GameState (to save) and the HUD (the card) do")
for f in ("scripts/player/player.gd", "scripts/autoload/input_manager.gd", SPEECH_GD, "scripts/npc/npc.gd", RL, "scripts/autoload/inventory.gd", "scripts/autoload/market.gd", "scripts/autoload/wallet.gd"):
    if re.search(r"\bRequests?\b|\brequest_\w+|\bGive\b", code_only(scripts.get(f, ""))):
        err(f"{f}: knows about requests — only NpcTalk drives them, Requests keeps them (D-39)")
ntq = scripts.get("scripts/npc/npc_talk.gd", "")
ntq_f = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", ntq, re.M | re.S)}
it, oc6 = ntq_f.get("interact", ""), ntq_f.get("_on_conversation_ended", "")
if 'const GIVE_TEXT := "Give"' not in ntq \
   or not re.search(r"if _panel\.get_speaker\(\) == self and _panel\.visible:\s*return true\s*var npc := get_parent\(\) as Npc\s*var request := Requests\.conversation_for\(npc\.definition\.id\)\s*"
                    r'_request_id = request\.get\("request_id", ""\)\s*_request_step = request\.get\("step", ""\)\s*_service_id = ""\s*_service_step = ""\s*if not request\.is_empty\(\):\s*'
                    r"var end_text := GIVE_TEXT if _request_step == Requests\.STEP_HANDOVER else SpeechPanel\.END_TEXT\s*"
                    r"return _panel\.open\(self, npc\.definition\.display_name, request\.lines, end_text\)\s*"
                    r"var service := Services\.conversation_for\(npc\.definition\.id\)", it) \
   or {fn for fn, b in ntq_f.items() if re.search(r"\b_request_(id|step)\s*=[^=]", b)} != {"interact", "_on_conversation_ended"} \
   or not re.search(r'var request_id := _request_id\s*var step := _request_step\s*var service_id := _service_id\s*var service_step := _service_step\s*'
                    r'_request_id = ""\s*_request_step = ""\s*_service_id = ""\s*_service_step = ""\s*if not completed:\s*return\s*'
                    r"if step == Requests\.STEP_OFFER:\s*Requests\.accept\(request_id\)\s*elif step == Requests\.STEP_HANDOVER:\s*Requests\.complete\(request_id\)\s*"
                    r"elif service_step == Services\.STEP_TRADE:\s*Services\.trade\(service_id\)\s*var npc", oc6) \
   or code_only(ntq).count("Requests.accept(") != 1 or code_only(ntq).count("Requests.complete(") != 1:
    err("scripts/npc/npc_talk.gd: NpcTalk locks the chosen conversation while it is open (re-taps never choose again), asks its request first (M08.7: then its service), "
        "gives the hand-over its \"Give\" label, and only a completed offer accepts / a completed hand-over completes — an early end does neither")
if 'notification.show_message("✓ Request Complete", "%s ×%d" % [item_name, quantity], "+%d Wriksha Points" % points)' not in code_only(func_body(scripts.get("scripts/ui/hud.gd", ""), "_on_request_completed") or "") \
   or re.search(r"Requests\.(?!request_completed\.connect)", code_only(scripts.get("scripts/ui/hud.gd", ""))):
    err("scripts/ui/hud.gd: a completed request shows the usual card — \"✓ Request Complete\", the items given, the points — and the HUD reads nothing else of requests")
sm7 = scripts.get("scripts/autoload/save_manager.gd", "")
if '"requests": Requests.get_save_data(),' not in code_only(func_body(sm7, "save_game") or "") \
   or 'Requests.apply_save_data(data.get("requests", {}))' not in code_only(func_body(sm7, "load_game") or "") \
   or not re.search(r"^\t\t\t6:\s*pass\b", code_only(func_body(sm7, "_migrate") or ""), re.M) \
   or not re.search(r'^\t"requests": \[TYPE_DICTIONARY\],$', sm7, re.M) or (const_val(sm7, "SAVE_VERSION") or 0) < 7:  # v8 is M09.2's world_time
    err("scripts/autoload/save_manager.gd: save v7 — the requests section is saved and loaded as a dictionary; step 6 -> 7 (M08.6) rewrites nothing (absent = no request offered)")
gs7 = code_only(func_body(scripts.get("scripts/autoload/game_state.gd", ""), "_ready") or "")
if "Requests.request_accepted.connect(_save.unbind(1))" not in gs7 or "Requests.request_completed.connect(_save.unbind(4))" not in gs7:
    err("scripts/autoload/game_state.gd: an accepted and a completed request are saved at once (GameState)")
notes.append(f"requests (M08.6): {len(rq_files)} request(s) {[os.path.basename(p)[:-5] for p in rq_files]}; offer → accept, hand-over → complete (checked, recorded, paid once); save v7")

# ------------------------------------------------------------ services (M08.7, D-40)
# One repeatable NPC service as data (ServiceDefinition, data/services/): a trade of a single-quality
# collectible for coins, unlocked only once its request is completed. The Services autoload is stateless — it
# reads the Inventory and Requests to choose the conversation (pitch below the quantity, trade at or above it;
# the trade's last button reads "Sell") and hands a completed trade to Market.trade(), the transaction's owner
# (D-25 amended: the Market's two credit sites). No points, no friendship, no saved state (save v7 unchanged).
SVD, SV = "scripts/npc/service_definition.gd", "scripts/autoload/services.gd"
svd_src, sv_src = scripts.get(SVD, ""), scripts.get(SV, "")
svf = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", sv_src, re.M | re.S)}
sv_code = code_only(sv_src)
SV_FIELDS = {"id": "String", "npc_id": "String", "item_id": "String", "quantity": "int", "coins": "int", "unlocked_by_request": "String",
             "pitch_dialogue": "DialogueDefinition", "trade_dialogue": "DialogueDefinition"}
if not re.search(r"^extends Resource\s*\nclass_name ServiceDefinition", svd_src, re.M) \
   or dict(re.findall(r"^@export var (\w+): (\w+)", svd_src, re.M)) != SV_FIELDS \
   or re.search(r"^(func|var|const|signal|static) ", code_only(svd_src), re.M):
    err(f"{SVD}: ServiceDefinition is exactly {list(SV_FIELDS)} — data only, no transaction logic")
request_ids = {os.path.basename(p)[:-5] for p in glob.glob("data/requests/*.tres")}
sv_files = sorted(glob.glob("data/services/*.tres"))
if len(sv_files) != 1:
    err(f"data/services: exactly one service in M08.7 (found {sv_files})")
for path in sv_files:
    txt = open(path, encoding="utf-8").read()
    vals = dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', txt, re.M))
    ext = dict((m.group(2), m.group(1)) for m in re.finditer(r'\[ext_resource type="Resource" path="res://([^"]+)" id="([^"]+)"\]', txt))
    item_path = f"data/items/{vals.get('item_id', '')}.tres"
    item_vals = dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', open(item_path, encoding="utf-8").read(), re.M)) if os.path.exists(item_path) else {}
    q, c = vals.get("quantity", "1"), vals.get("coins", "0")
    if 'script_class="ServiceDefinition"' not in txt or vals.get("id") != os.path.basename(path)[:-5] or not re.fullmatch(r"[a-z][a-z0-9_]*", vals.get("id", "")) \
       or vals.get("npc_id") not in npc_ids_rq or item_vals.get("category") != "collectible" or int(item_vals.get("quality_levels", "1")) != 1 \
       or not q.isdigit() or not 1 <= int(q) <= 9 or not c.isdigit() or int(c) < 1 or vals.get("unlocked_by_request") not in request_ids:
        err(f"{path}: a ServiceDefinition — lower_snake id = its file name, a real NPC, a real single-quality collectible, quantity 1-9, coins >= 1, unlocked by a real request")
    for key in ("pitch_dialogue", "trade_dialogue"):
        ref = re.search(rf'^{key} = ExtResource\("([^"]+)"\)$', txt, re.M)
        if not ref or not ext.get(ref.group(1), "").startswith("data/dialogues/") or not os.path.exists(ext.get(ref.group(1), "")):
            err(f"{path}: {key} is a data/dialogues/ resource")
if not re.match(r"extends Node\n", sv_src) or re.findall(r"^signal ", sv_src, re.M) or re.findall(r"^var (\w+)", sv_src, re.M) != ["_definitions"] \
   or dict(re.findall(r'^const (\w+) := "(\w*)"$', sv_src, re.M)) != {"STEP_PITCH": "pitch", "STEP_TRADE": "trade"} \
   or 'const SERVICES_PATH := "res://data/services/"' not in sv_src or const_val(sv_src, "MAX_QUANTITY") != 9 \
   or [f for f in svf if not f.startswith("_")] != ["conversation_for", "trade"]:
    err(f"{SV}: Services is a stateless Node — only its definitions, the pitch / trade steps and the API conversation_for, trade; no signals, no saved state")
if re.search(r"\bInventory\.(add|remove|apply_save_data|get_save_data)\(|\bWallet\b|PointsManager|Relationships|friendship|SaveManager|GameState|FarmManager|FarmPlot|"
             r"get_tree\(|get_node|\$\w|Player|InputManager|SpeechPanel|HUD|Requests\.(accept|complete|conversation_for|apply_save_data|get_save_data)\(", sv_code):
    err(f"{SV}: Services only reads the Inventory and Requests and asks the Market — it never writes items or coins, pays points, touches friendship, saves, or holds nodes or UI")
if not re.search(r"var definition: ServiceDefinition = _definitions\.get\(service_id\)\s*if definition == null or not _is_unlocked\(definition\):\s*return 0\s*"
                 r"return Market\.trade\(definition\.item_id, definition\.quantity, definition\.coins, definition\.id\)\s*$", svf.get("trade", "")) \
   or sv_code.count("Market.trade(") != 1:
    err(f"{SV}: trade() trades only an unlocked service, through Market.trade() with the service's own item, quantity and coins")
if not re.search(r"return Requests\.get_state\(definition\.unlocked_by_request\) == Requests\.COMPLETED", svf.get("_is_unlocked", "")):
    err(f"{SV}: a service is unlocked only once its request is completed")
cfs = svf.get("conversation_for", "")
if not re.search(r"if definition\.npc_id != npc_id or not _is_unlocked\(definition\):\s*continue\s*if Inventory\.has\(definition\.item_id, definition\.quantity, 0\):\s*"
                 r'return \{"service_id": service_id, "step": STEP_TRADE, "lines": definition\.trade_dialogue\.lines\}\s*'
                 r'return \{"service_id": service_id, "step": STEP_PITCH, "lines": definition\.pitch_dialogue\.lines\}', cfs) or not cfs.rstrip().endswith("return {}"):
    err(f"{SV}: conversation_for(): locked → nothing; unlocked with the items → the trade; unlocked without → the pitch")
ivs = svf.get("_is_valid", "")
if 'item.category != "collectible" or item.quality_levels != 1' not in ivs or "definition.quantity < 1 or definition.quantity > MAX_QUANTITY or definition.coins < 1" not in ivs \
   or 'definition.unlocked_by_request == ""' not in ivs or "npc_ids.has(definition.npc_id)" not in ivs:
    err(f"{SV}: a service is used only for a real NPC and a single-quality collectible, quantity 1..MAX_QUANTITY, coins >= 1, with an unlocking request")
for f, s2 in scripts.items():
    if f.startswith("tools/") or f == SV: continue
    code = code_only(s2)
    if re.search(r"\bServices\.(conversation_for|trade)\(", code) and f != "scripts/npc/npc_talk.gd":
        err(f"{f}: drives a service — only the speaking NpcTalk does (D-40)")
    if re.search(r"\bMarket\.trade\(", code):
        err(f"{f}: asks the Market for a trade — only Services does (D-40)")
    if re.search(r"items_traded\.connect", code) and f not in ("scripts/autoload/game_state.gd", "scripts/ui/hud.gd"):
        err(f"{f}: listens to trades — only GameState (to save) and the HUD (the card) do")
for f in ("scripts/player/player.gd", "scripts/autoload/input_manager.gd", SPEECH_GD, "scripts/npc/npc.gd", RL, RQ, "scripts/autoload/inventory.gd",
          "scripts/autoload/wallet.gd", "scripts/autoload/farm_manager.gd", "scripts/farming/farm_plot.gd", "scripts/autoload/save_manager.gd",
          "scripts/autoload/market.gd", "scripts/ui/basket_screen.gd", "scripts/ui/hud.gd"):
    if re.search(r"\bServices?\b|\bservice_(?!id\b)\w+", code_only(scripts.get(f, ""))):
        err(f"{f}: knows about services — only NpcTalk drives them, Services keeps them, the Market trades by item and coins (D-40)")
nts = scripts.get("scripts/npc/npc_talk.gd", "")
nts_f = {m.group(1): code_only(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", nts, re.M | re.S)}
if 'const SELL_TEXT := "Sell"' not in nts \
   or not re.search(r'var service := Services\.conversation_for\(npc\.definition\.id\)\s*_service_id = service\.get\("service_id", ""\)\s*_service_step = service\.get\("step", ""\)\s*'
                    r"if not service\.is_empty\(\):\s*var sell_text := SELL_TEXT if _service_step == Services\.STEP_TRADE else SpeechPanel\.END_TEXT\s*"
                    r"return _panel\.open\(self, npc\.definition\.display_name, service\.lines, sell_text\)\s*"
                    r"return _panel\.open\(self, npc\.definition\.display_name, npc\.definition\.dialogue\.lines\)", nts_f.get("interact", "")) \
   or {fn for fn, b in nts_f.items() if re.search(r"\b_service_(id|step)\s*=[^=]", b)} != {"interact", "_on_conversation_ended"} \
   or code_only(nts).count("Services.trade(") != 1 or re.search(r"\bInventory\b|\bWallet\b|\bMarket\b", code_only(nts)):
    err("scripts/npc/npc_talk.gd: after an unfinished request, NpcTalk asks its service (pitch, or the trade labelled \"Sell\"), sells only on its own completed trade "
        "conversation, and never touches the Inventory, the Wallet or the Market itself")
if 'notification.show_message(item_name.to_upper(), "×%d" % quantity, "+%d Coins" % coins)' not in code_only(func_body(scripts.get("scripts/ui/hud.gd", ""), "_on_items_traded") or ""):
    err("scripts/ui/hud.gd: an NPC trade shows the usual sale card — the item, ×quantity, +coins — and nothing else")
if "Market.items_traded.connect(_save.unbind(3))" not in code_only(func_body(scripts.get("scripts/autoload/game_state.gd", ""), "_ready") or ""):
    err("scripts/autoload/game_state.gd: an NPC trade is saved at once (GameState, items_traded)")
if (const_val(sm7, "SAVE_VERSION") or 0) < 7 or re.search(r'"services"', sm7):  # M09.2 (D-42) bumped to v8 for world_time, not for services
    err("scripts/autoload/save_manager.gd: services save nothing — no section, and no save version of their own (D-40)")
notes.append(f"services (M08.7): {len(sv_files)} service(s) {[os.path.basename(p)[:-5] for p in sv_files]}; unlocked by a request; pitch / trade (Sell) → Market.trade(); stateless, no save section")

# ------------------------------------------------------------ NPC routine (M09.1, D-41)
# An NPC follows its area's day: its NpcDefinition's routine maps every time-of-day phase to the spot_id of an
# NpcRoutineSpot (a data-only marker in its area); its home is the current phase's spot. It hears the area's
# TimeOfDay through time_updated and reads the phase from the fraction itself (found in WorldSimulation.TIME_GROUP;
# time_of_day.gd stays pinned — its cached phase can miss a boundary right after the fraction is set): the first
# phase places it at the spot, every later change makes it walk there — talking always wins (the hold rule is
# unchanged). No saved state, no system time, no new autoload; Player and InputManager know nothing of it.
RSP_GD = "scripts/npc/npc_routine_spot.gd"
rsp_src = scripts.get(RSP_GD, "")
if not re.search(r"^extends Marker3D\s*\nclass_name NpcRoutineSpot", rsp_src, re.M) or 'const GROUP := &"npc_routine_spot"' not in rsp_src \
   or re.findall(r"^@export var (\w+)", rsp_src, re.M) != ["spot_id"] \
   or [f for f in re.findall(r"^func (\w+)\(", rsp_src, re.M)] != ["_enter_tree"] or "add_to_group(GROUP)" not in (func_body(rsp_src, "_enter_tree") or ""):
    err(f"{RSP_GD}: NpcRoutineSpot is a Marker3D with a spot_id that joins the npc_routine_spot group — data only")
for f, s2 in scripts.items():
    if f.startswith("tools/") or f in (RSP_GD, NPC_GD): continue
    if re.search(r"\bNpcRoutineSpot\b|npc_routine_spot|\bspot_id\b", code_only(s2)):
        err(f"{f}: reads routine spots — only the NPC does (D-41)")
PHASES = re.findall(r'"(\w+)"', (re.search(r"^const PHASE_ORDER := \[(.*)\]", scripts.get("scripts/world_simulation/time_of_day.gd", ""), re.M) or re.search("()", "")).group(1))
mtxt = open(MEADOW_SCENE, encoding="utf-8").read() if os.path.exists(MEADOW_SCENE) else ""
spot_nodes = re.findall(r'^\[node name="(\w+)" type="Marker3D" parent="NpcRoutine"\]\nposition = Vector3\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)\nscript = ExtResource\("routine_spot"\)\nspot_id = "(\w+)"\n', mtxt, re.M)
spot_ids = [sid for *_, sid in spot_nodes]
if not re.search(r'^\[ext_resource type="Script" path="res://scripts/npc/npc_routine_spot\.gd" id="routine_spot"\]$', mtxt, re.M) \
   or not re.search(r'^\[node name="NpcRoutine" type="Node3D" parent="\."\]\n\n', mtxt, re.M) \
   or len(spot_ids) != len(set(spot_ids)) or not all(re.fullmatch(r"[a-z][a-z0-9_]*", i) for i in spot_ids) \
   or len(re.findall(r'parent="NpcRoutine', mtxt)) != len(spot_nodes):
    err(f"{MEADOW_SCENE}: the routine spots are data-only NpcRoutineSpot markers under one NpcRoutine node, with unique lower_snake ids")
npc_spot = re.search(r'^\[node name="NpcSpot" parent="VerticalSlice" instance=ExtResource\("42"\)\]\nposition = Vector3\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)', mtxt, re.M)
homes = {sid: (float(x), float(z)) for _, x, _, z, sid in spot_nodes}
for path in sorted(glob.glob("data/npcs/*.tres")):
    txt = open(path, encoding="utf-8").read()
    rb = re.search(r"^routine = \{(.*?)\}$", txt, re.M | re.S)
    routine = dict(re.findall(r'"(\w+)": "(\w+)"', rb.group(1))) if rb else {}
    if sorted(routine) != sorted(PHASES) or not set(routine.values()) <= set(spot_ids):
        err(f"{path}: the routine names every time-of-day phase {PHASES} once, each with a routine spot in the Meadow (found {routine})")
    if os.path.basename(path) == "villager.tres" and (routine.get("morning") != routine.get("afternoon") or len({routine.get(p) for p in ("dawn", "evening", "night")}) != 1
                                                     or routine.get("morning") == routine.get("night") or not npc_spot
                                                     or homes.get(routine.get("night")) != (float(npc_spot.group(1)), float(npc_spot.group(3)))):
        err(f"{path}: the villager's routine is two spots — morning/afternoon by the pond path, dawn/evening/night at home, its existing NpcSpot (D-41)")
ws_src = scripts.get("scripts/world_simulation/world_simulation.gd", "")
if 'const TIME_GROUP := &"time_of_day"' not in ws_src or not re.search(r"func _ready\(\) -> void:\s*time_of_day\.add_to_group\(TIME_GROUP\)", ws_src):
    err("scripts/world_simulation/world_simulation.gd: the area's TimeOfDay joins WorldSimulation.TIME_GROUP (time_of_day.gd itself stays pinned)")
pp9, ft9, ap9, sw9, sa9 = (npc_fn.get(k, "") for k in ("_physics_process", "_follow_time_of_day", "_apply_phase", "_start_wander", "_step_allowed"))
if not re.search(r"if _time_of_day == null:\s*_follow_time_of_day\(\)", pp9) or "get_phase(" in pp9 + sw9 + sa9 \
   or not re.search(r"var clock := get_tree\(\)\.get_first_node_in_group\(WorldSimulation\.TIME_GROUP\) as TimeOfDay\s*if clock == null or not _navigation_ready\(\):\s*return", ft9) \
   or not re.search(r"if NavigationServer3D\.map_get_iteration_id\(map\) == 0:\s*return false\s*return _flat_distance\(NavigationServer3D\.map_get_closest_point\(map, global_position\)\) <= 1\.0", npc_fn.get("_navigation_ready", "")) \
   or "_time_of_day.time_updated.connect(_on_time_updated)" not in ft9 \
   or "_apply_phase(_time_of_day.get_phase_for_fraction(_time_of_day.day_fraction), true)" not in ft9 or "phase_changed" in code_only(np_src) \
   or not re.search(r"func _on_time_updated\(day_fraction: float\) -> void:\s*_apply_phase\(_time_of_day\.get_phase_for_fraction\(day_fraction\), false\)\s*$", npc_fn.get("_on_time_updated", "")):
    err(f"{NPC_GD}: the NPC follows its area's TimeOfDay by time_updated, reading the phase from the fraction (never the clock's cached phase, which misses a boundary after a restored time), once the navigation map is ready")
if not re.search(r'var spot_id: String = definition\.routine\.get\(phase, ""\)\s*var spot := _find_spot\(spot_id\)\s*if spot == null:\s*push_warning\(.*?\)\n\s*return\s*'
                 r"if spot_id == _spot_id:\s*return\s*_spot_id = spot_id\s*_home = spot\.global_position\s*_wandering = false\s*_idle_left = 0\.0\s*"
                 r"if place:\s*global_position = NavigationServer3D\.map_get_closest_point\(get_world_3d\(\)\.navigation_map, _home\)", ap9) \
   or "definition.routine.is_empty()" not in ap9 or "talk." in ap9 or "_turn_toward" in ap9:
    err(f"{NPC_GD}: a phase's routine spot becomes home — placed there for the first phase, walked to on any later one; a missing spot keeps the home it has")
if not re.search(r"if _is_travelling\(\):\s*nav_agent\.target_position = NavigationServer3D\.map_get_closest_point\(map, _home\)\s*_wandering = true\s*return", sw9) \
   or not re.search(r"if _is_travelling\(\):\s*return _clear_of_doors\(step\)", sa9) \
   or not re.search(r"var radius := definition\.wander_radius if definition else 0\.0\s*return _flat_distance\(_home\) > radius", npc_fn.get("_is_travelling", "")):
    err(f"{NPC_GD}: away from its routine spot it walks home first, and a step aside on the way keeps clear of doors without the home leash")
if re.search(r"Time\.get_|OS\.get_|SaveManager|WorldClock|\.day_fraction\s*=[^=]|day_length_seconds", code_only(np_src)):
    err(f"{NPC_GD}: the routine reads the area's day clock only — no system time, no saving, never setting the clock")
for f in ("scripts/player/player.gd", "scripts/autoload/input_manager.gd", NPC_TALK_GD, SPEECH_GD, "scripts/ui/hud.gd"):
    if re.search(r"\broutine\b|TimeOfDay|TIME_GROUP|phase_changed", code_only(scripts.get(f, ""))):
        err(f"{f}: knows about NPC routines or the day clock — only the NPC follows its routine (D-41)")
notes.append(f"NPC routine (M09.1): phases {PHASES}; spots {spot_ids}; first phase placed, later phases walked; event-driven, nothing saved")

# ------------------------------------------------------------ world clock (M09.2, D-42)
# One authoritative clock: the WorldClock autoload holds the day (from START_DAY) and the fraction of it, and
# advance() is called from exactly one place — the area's WorldSimulation._process — so a parked Meadow (the player
# indoors) pauses time. TimeOfDay (time_of_day.gd, pinned and unchanged) only presents it: WorldSimulation switches
# its own frame advance off, copies the clock's fraction in and emits its time_updated / phase_changed, so its
# listeners (lighting, wildlife, the M09.1 NPC) are unchanged; its cached get_phase() is never read. Saved as the
# world_time section (save v8); v7 has none → day 1 at 0.28. No time-skip: nothing else advances or sets the clock.
WC_GD, WS_GD, TOD_GD = "scripts/autoload/world_clock.gd", "scripts/world_simulation/world_simulation.gd", "scripts/world_simulation/time_of_day.gd"
wc_src, wc_code = scripts.get(WC_GD, ""), code_only(scripts.get(WC_GD, ""))
wc_fn = {m.group(1): m.group(0) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", wc_code, re.M | re.S)}
if not wc_src.startswith("extends Node\n") or re.search(r"^class_name|^signal|^@export", wc_src, re.M) \
   or (const_val(wc_src, "DAY_LENGTH_SECONDS"), const_val(wc_src, "START_DAY"), const_val(wc_src, "START_FRACTION")) != (600.0, 1, 0.28) \
   or re.findall(r"^var (\w+)", wc_src, re.M) != ["_day", "_fraction"] \
   or "var _day: int = START_DAY" not in wc_src or "var _fraction: float = START_FRACTION" not in wc_src \
   or list(wc_fn) != ["get_day", "get_fraction", "advance", "get_save_data", "apply_save_data", "_is_number"] \
   or re.search(r"\bTime\.|\bOS\.|\bEngine\.|get_tree\(", wc_code):
    err(f"{WC_GD}: WorldClock is a plain autoload — the day and the fraction (from START_DAY 1 / START_FRACTION 0.28, a 600 s day), "
        "read with get_day()/get_fraction(), advanced by advance(), saved and restored; no signals, no system time, no time-skip")
if not re.search(r"func advance\(delta: float\) -> void:\s*if not is_finite\(delta\) or delta <= 0\.0:\s*return\s*"
                 r"var total := _fraction \+ delta / DAY_LENGTH_SECONDS\s*var whole := floori\(total\)\s*_day \+= whole\s*_fraction = total - whole\s*$", wc_fn.get("advance", "")) \
   or not re.search(r"func get_save_data\(\) -> Dictionary:\s*return \{\"day\": _day, \"fraction\": _fraction\}\s*$", wc_fn.get("get_save_data", "")):
    err(f"{WC_GD}: advance() adds delta / DAY_LENGTH_SECONDS; each crossing of 1.0 raises the day by exactly one and wraps the fraction; "
        "the save holds both the day and the fraction")
ap = wc_fn.get("apply_save_data", "")
if not re.search(r"func apply_save_data\(data: Dictionary\) -> void:\s*_day = START_DAY\s*_fraction = START_FRACTION\s*if data\.is_empty\(\):\s*return\s", ap) \
   or not re.search(r"float\(day\) < START_DAY or float\(day\) != floorf\(float\(day\)\) or float\(fraction\) < 0\.0 or float\(fraction\) >= 1\.0", ap) \
   or not re.search(r"_day = int\(day\)\s*_fraction = float\(fraction\)\s*$", ap) or ap.count("return") != 3:
    err(f"{WC_GD}: apply_save_data() restores the saved day and fraction; an empty section (a v7 save) or a malformed one starts at day 1 at 0.28 — never half-restored")
tod_src = scripts.get(TOD_GD, "")
tod_len = re.search(r"^@export var day_length_seconds: float = ([0-9.]+)$", tod_src, re.M)
tod_start = re.search(r"^@export_range\(0\.0, 1\.0\) var start_fraction: float = ([0-9.]+)$", tod_src, re.M)
if not tod_len or not tod_start or (float(tod_len.group(1)), float(tod_start.group(1))) != (const_val(wc_src, "DAY_LENGTH_SECONDS"), const_val(wc_src, "START_FRACTION")):
    err(f"{TOD_GD}: TimeOfDay's day_length_seconds / start_fraction must equal WorldClock's DAY_LENGTH_SECONDS / START_FRACTION — one configuration, never two")
for path in sorted(glob.glob("scenes/**/*.tscn", recursive=True) + glob.glob("data/**/*.tres", recursive=True)):
    if re.search(r"^(day_length_seconds|start_fraction) = ", open(path, encoding="utf-8").read(), re.M):
        err(f"{path}: overrides TimeOfDay's day_length_seconds / start_fraction — the day is WorldClock's (D-42)")
ws_code = code_only(scripts.get(WS_GD, ""))
ws_fn = {m.group(1): m.group(0) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", ws_code, re.M | re.S)}
if not re.search(r"func _ready\(\) -> void:\s*time_of_day\.add_to_group\(TIME_GROUP\)\s*time_of_day\.set_process\(false\)\s*"
                 r"time_of_day\.day_fraction = WorldClock\.get_fraction\(\)\s*_phase = time_of_day\.get_phase_for_fraction\(time_of_day\.day_fraction\)\s*"
                 r"weather_controller\.apply_time\(WorldClock\.get_day\(\), time_of_day\.day_fraction\)\s*$", ws_fn.get("_ready", "")) \
   or not re.search(r"func _process\(delta: float\) -> void:\s*WorldClock\.advance\(delta\)\s*_present_time\(\)\s*$", ws_fn.get("_process", "")) \
   or not re.search(r"func _present_time\(\) -> void:\s*var fraction := WorldClock\.get_fraction\(\)\s*time_of_day\.day_fraction = fraction\s*"
                    r"weather_controller\.apply_time\(WorldClock\.get_day\(\), fraction\)\s*"  # M09.3 (D-43): the weather is given the clock, before time_updated
                    r"time_of_day\.time_updated\.emit\(fraction\)\s*var phase := time_of_day\.get_phase_for_fraction\(fraction\)\s*"
                    r"if phase != _phase:\s*_phase = phase\s*time_of_day\.phase_changed\.emit\(phase\)\s*$", ws_fn.get("_present_time", "")) \
   or "wildlife_controller.set_time_phase(_phase)" not in ws_fn.get("configure", "") or "WorldClock" in ws_fn.get("configure", ""):
    err(f"{WS_GD}: WorldSimulation drives the clock — _ready switches TimeOfDay's own advance off and gives it the clock's fraction; "
        "_process advances WorldClock and presents it (the weather given the day and fraction first, M09.3; time_updated every frame, phase_changed when the fraction's phase changes); configure() never touches the clock")
adv_sites, emits, writes = [], [], []
for f, s2 in scripts.items():
    if f.startswith("tools/") and not f.startswith("tools/fixtures/"): continue
    c = code_only(s2)
    adv_sites += [f] * len(re.findall(r"\bWorldClock\.advance\(", c))
    if f != TOD_GD:
        emits += [(f, m) for m in re.findall(r"\b(time_updated|phase_changed)\.emit\(", c)]
        writes += [f] * len(re.findall(r"\.day_fraction\s*=[^=]", c))
    if f not in (WC_GD, WS_GD, "scripts/autoload/save_manager.gd") and re.search(r"\bWorldClock\b", c):
        err(f"{f}: uses WorldClock — only WorldSimulation (advance, read) and SaveManager (save, restore) do (D-42)")
    if f != WC_GD and re.search(r"\bWorldClock\._|\bWorldClock\.(START_|DAY_LENGTH)", c):
        err(f"{f}: reaches into WorldClock — its state is only advanced, read, saved and restored through its functions")
    if re.search(r"(time_of_day|TimeOfDay|_time_of_day|clock)\.(set_process\(true|set_physics_process|process_mode|_process\()|\.get_phase\(\)", c):
        err(f"{f}: re-enables or calls TimeOfDay's own clock, or reads its cached get_phase() — it only presents WorldClock (D-42)")
if adv_sites != [WS_GD] or "WorldClock.advance(" in code_only(re.sub(r"(?ms)^func _process\(.*?(?=^func |\Z)", "", scripts.get(WS_GD, ""))):
    err(f"WorldClock.advance() must have exactly one caller, WorldSimulation._process (found {adv_sites}) — one clock, one driver")
if sorted(emits) != [(WS_GD, "phase_changed"), (WS_GD, "time_updated")] or writes != [WS_GD, WS_GD]:
    err(f"only WorldSimulation presents the clock in TimeOfDay — one time_updated / phase_changed emit and its two day_fraction writes (found {emits}, {writes})")
sm8 = scripts.get("scripts/autoload/save_manager.gd", "")
if '"world_time": WorldClock.get_save_data(),' not in code_only(func_body(sm8, "save_game") or "") \
   or 'WorldClock.apply_save_data(data.get("world_time", {}))' not in code_only(func_body(sm8, "load_game") or "") \
   or not re.search(r"^\t\t\t7:\s*pass\b", code_only(func_body(sm8, "_migrate") or ""), re.M) \
   or not re.search(r'^\t"world_time": \[TYPE_DICTIONARY\],$', sm8, re.M) or (const_val(sm8, "SAVE_VERSION") or 0) < 8:
    err("scripts/autoload/save_manager.gd: save v8 — the world_time section (day and fraction) is saved and loaded as a dictionary; "
        "step 7 -> 8 (M09.2) rewrites nothing (absent = day 1 at 0.28)")
notes.append(f"world clock (M09.2): WorldClock day from {const_val(wc_src, 'START_DAY')} at {const_val(wc_src, 'START_FRACTION')}, "
             f"{const_val(wc_src, 'DAY_LENGTH_SECONDS'):.0f} s day; one driver (WorldSimulation._process); TimeOfDay presents it; save v8 world_time")

# ------------------------------------------------------------ weather (M09.3, D-43)
# Clear or Rain, a pure function of the WeatherSchedule's fixed seed and WorldClock's day and fraction: a day is
# slots_per_day equal slots, each Rain when a 32-bit integer hash of (seed, day, slot) falls below rain_chance × 2^32;
# days up to always_clear_days are Clear; the rain fades over ramp_fraction at a spell's edges. WeatherController
# (inside WorldSimulation) never reads WorldClock — WorldSimulation hands it the day and fraction — holds no clock,
# saves nothing and emits weather_changed only on a change during play (never the first resolution). It reacts to
# nothing (M09.4 will consume the signal); farming, NPCs, wildlife and the rest never hear of the weather.
WSCH_GD, WCTL_GD, WS_TSCN, ENV_GD = ("scripts/world_simulation/weather_schedule.gd", "scripts/world_simulation/weather_controller.gd",
                                     "scenes/world_simulation/WorldSimulation.tscn", "scripts/world_simulation/environment_controller.gd")
wsch_src, wctl_src = scripts.get(WSCH_GD, ""), scripts.get(WCTL_GD, "")
wctl_code = code_only(wctl_src)
wctl_fn = {m.group(1): m.group(0) for m in re.finditer(r"^(?:static )?func (\w+)\(.*?(?=^(?:static )?func |\Z)", wctl_code, re.M | re.S)}
if not re.search(r"^extends Resource\s*\nclass_name WeatherSchedule\b", wsch_src, re.M) or re.search(r"^func ", wsch_src, re.M) \
   or re.findall(r"^@export(?:_range\([^)]*\))? var (\w+)", wsch_src, re.M) != ["weather_seed", "slots_per_day", "rain_chance", "ramp_fraction", "always_clear_days"]:
    err(f"{WSCH_GD}: WeatherSchedule is data only — weather_seed, slots_per_day, rain_chance, ramp_fraction, always_clear_days")
wtres = sorted(glob.glob("data/weather/*.tres"))
wvals = dict(re.findall(r"^(\w+) = (.+)$", open(wtres[0], encoding="utf-8").read(), re.M)) if len(wtres) == 1 else {}
if wtres != ["data/weather/weather_schedule.tres"] or wvals.get("weather_seed") != "917" \
   or (wvals.get("slots_per_day"), wvals.get("rain_chance"), wvals.get("ramp_fraction"), wvals.get("always_clear_days")) != ("4", "0.25", "0.01", "1") \
   or (const_val(scripts.get(WC_GD, ""), "DAY_LENGTH_SECONDS") or 0) / 4 != 150.0:
    err("data/weather/weather_schedule.tres: the one schedule — the fixed seed 917 (a change updates D-43 and sim_weather's calendar), 4 slots of 150 s, rain chance 0.25, a 0.01-day ramp, day 1 always Clear (D-43)")
if not re.search(r"^extends Node\s*\nclass_name WeatherController\b", wctl_src, re.M) \
   or re.findall(r"^signal (\w+)\((.*?)\)", wctl_src, re.M) != [("weather_changed", "weather: String")] \
   or not re.search(r'^const CLEAR := "clear"$', wctl_src, re.M) or not re.search(r'^const RAIN := "rain"$', wctl_src, re.M) \
   or re.findall(r"^var (\w+)", wctl_src, re.M) != ["player", "_weather", "_rain_intensity"] \
   or list(wctl_fn) != ["get_weather", "is_raining", "get_rain_intensity", "apply_time", "weather_at", "rain_intensity_at", "_slot", "_slot_rains", "_hash", "_show_rain"] \
   or re.search(r"\bWorldClock\b|\bTime\.|\bOS\.|\bEngine\.|\brand[fi]?\w*\(|RandomNumberGenerator|randomize|\bhash\(|get_tree\(|SaveManager|FileAccess|ConfigFile|ResourceSaver|user://|_process\(|_physics_process\(|\bawait\b|Timer", wctl_code):
    err(f"{WCTL_GD}: WeatherController — weather_changed(weather) its one signal; get_weather/is_raining/get_rain_intensity, apply_time, the pure weather_at/rain_intensity_at "
        "and the hash; no WorldClock, no system or engine time, no random state, no saving, no frame loop of its own (D-43)")
if not re.search(r"func apply_time\(day: int, fraction: float\) -> void:\s*var weather := weather_at\(day, fraction\)\s*_rain_intensity = rain_intensity_at\(day, fraction\)\s*_show_rain\(\)\s*"
                 r"if weather == _weather:\s*return\s*var first := _weather == \"\"\s*_weather = weather\s*if not first:\s*weather_changed\.emit\(weather\)\s*$", wctl_fn.get("apply_time", "")) \
   or wctl_code.count("weather_changed.emit(") != 1:
    err(f"{WCTL_GD}: apply_time() resolves the weather and intensity from the day and fraction; weather_changed fires only when it changes, never for the first resolution")
if not re.search(r"func weather_at\(day: int, fraction: float\) -> String:\s*return RAIN if _slot_rains\(day, _slot\(fraction\)\) else CLEAR\s*$", wctl_fn.get("weather_at", "")) \
   or not re.search(r"return clampi\(floori\(fraction \* schedule\.slots_per_day\), 0, schedule\.slots_per_day - 1\)\s*$", wctl_fn.get("_slot", "")) \
   or not re.search(r"if day <= schedule\.always_clear_days:\s*return false\s*return _hash\(schedule\.weather_seed, day, slot\) < int\(schedule\.rain_chance \* 4294967296\.0\)\s*$", wctl_fn.get("_slot_rains", "")) \
   or not re.search(r"var x := \(\(seed_value \* 73856093\) \^ \(day \* 19349663\) \^ \(slot \* 83492791\)\) & 0xFFFFFFFF\s*x = x \^ \(x >> 16\)\s*x = \(x \* 0x7feb352d\) & 0xFFFFFFFF\s*"
                    r"x = x \^ \(x >> 15\)\s*x = \(x \* 0x2c1b3c6d\) & 0xFFFFFFFF\s*x = x \^ \(x >> 16\)\s*return x\s*$", wctl_fn.get("_hash", "")):
    err(f"{WCTL_GD}: the weather is the slot's weather — slot = floor(fraction × slots_per_day); Rain when hash(seed, day, slot) < rain_chance × 2^32; days up to always_clear_days Clear")
ri = wctl_fn.get("rain_intensity_at", "")
if "if not _slot_rains(day, slot):\n\t\treturn 0.0" not in ri or "_slot_rains(day - 1, schedule.slots_per_day - 1)" not in ri or "_slot_rains(day + 1, 0)" not in ri \
   or "clampf(into / ramp, 0.0, 1.0)" not in ri or "clampf((width - into) / ramp, 0.0, 1.0)" not in ri or "return minf(fade_in, fade_out)" not in ri or re.search(r"\b_\w+ \+?=", ri):
    err(f"{WCTL_GD}: the rain intensity is derived from the position in the slot — a fade over ramp_fraction at an edge whose neighbour (across midnight too) is Clear; no state")
wtscn = open(WS_TSCN, encoding="utf-8").read() if os.path.exists(WS_TSCN) else ""
rain_node = re.search(r'^\[node name="Rain" type="CPUParticles3D" parent="\."\]\n((?:[^\[\n].*\n)+)', wtscn, re.M)
if not re.search(r'^\[node name="Weather" type="Node" parent="\."\]\nscript = ExtResource\("(\w+)"\)\nschedule = ExtResource\("(\w+)"\)\nrain_path = NodePath\("\.\./Rain"\)\n', wtscn, re.M) \
   or 'path="res://scripts/world_simulation/weather_controller.gd"' not in wtscn or 'path="res://data/weather/weather_schedule.tres"' not in wtscn \
   or not rain_node or not re.search(r"^emitting = false$", rain_node.group(1), re.M) or not re.search(r"^local_coords = false$", rain_node.group(1), re.M) \
   or int((re.search(r"^amount = (\d+)$", rain_node.group(1), re.M) or re.search("(9999)", "9999")).group(1)) > 300:
    err(f"{WS_TSCN}: one Weather node (WeatherController, the schedule) and one modest Rain emitter (CPUParticles3D, at most 300 drops, off until it rains) inside WorldSimulation")
for path in sorted(glob.glob("scenes/**/*.tscn", recursive=True)):
    if "GPUParticles" in open(path, encoding="utf-8").read():
        err(f"{path}: GPU particles — the rain stays one modest CPUParticles3D until Android performance is measured (D-43)")
if not re.search(r"^func apply_time\(day_fraction: float, rain: float = 0\.0\) -> void:", scripts.get(ENV_GD, ""), re.M) or re.search(r"\bWeather|WorldClock", code_only(scripts.get(ENV_GD, ""))) \
   or "environment_controller.apply_time(day_fraction, weather_controller.get_rain_intensity())" not in code_only(scripts.get(WS_GD, "")):
    err(f"{ENV_GD}: the lighting takes the rain intensity as a number from WorldSimulation and never knows the weather or the clock")
wapply = []
for f, s2 in scripts.items():
    if f.startswith("tools/") and not f.startswith("tools/fixtures/"): continue
    c = code_only(s2)
    wapply += [f] * len(re.findall(r"\bweather_controller\.apply_time\(", c))
    if re.search(r"weather_changed\.connect\(", c):
        err(f"{f}: reacts to weather_changed — reactions are M09.4's (D-43)")
    if f not in (WCTL_GD, WSCH_GD, WS_GD) and re.search(r"\bWeatherController\b|\bWeatherSchedule\b|\bweather_controller\b|\bis_raining\(|\bget_rain_intensity\(", c):
        err(f"{f}: reads the weather — only WorldSimulation drives it and nothing reacts in M09.3 (farming, NPCs, wildlife, saves never hear of it; D-43)")
if wapply != [WS_GD, WS_GD]:
    err(f"WeatherController.apply_time() is called only by WorldSimulation (_ready and _present_time), with WorldClock's day and fraction (found {wapply})")
if re.search(r"weather|rain", code_only(scripts.get("scripts/autoload/save_manager.gd", "")), re.I):
    err("scripts/autoload/save_manager.gd: weather is never saved — it is derived from the saved world time (D-43)")
notes.append(f"weather (M09.3): seed {wvals.get('weather_seed')}, {wvals.get('slots_per_day')} slots/day, rain chance {wvals.get('rain_chance')}, "
             f"ramp {wvals.get('ramp_fraction')} day, Clear through day {wvals.get('always_clear_days')}; given the clock by WorldSimulation; not saved; no reactions")

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
