#!/usr/bin/env python3
"""The Pond Rest Spot (E1; D-48–D-57, D1–D3): the real RestSpot, the Player's seated state and movement step, the
FollowCamera's settle transaction, Main's rest-spot routing and the HUD's quiet function, each translated from its
GDScript with gd_port and run together against a model of the engine pieces they use — physics steps (move_and_slide
as velocity × delta), a navigation agent that walks straight to its target (or, for an out-of-reach target, to the
nearest point it can reach), tweens bound to their node, InputManager's routed signals (a tap reaches an object only
while it is available, as InputManager._find_interactable rules) and a ledger of every autoload call.
1. A fresh rest spot is available, persistent, in the rest_spot group and offers exactly USE.
2. Tapping it from afar: the player walks to it (never a jump), its interaction fires in range, the player walks on to
   the seat point and is SEATED only on arriving — facing the seat's view; the spot becomes occupied; the camera eases
   to the spot's preset (distance within 7–15 m, framing offset) in 1–2 s; the HUD goes quiet with the joystick kept.
3. While seated: a ground tap changes nothing; pinch/wheel zoom is ignored; tapping the occupied seat (still available,
   offering nothing) is a no-op (D-56); tapping
   the player, joystick/keyboard movement (standing and moving in the same physics step), another object (stand, then
   its normal flow) and place_at all stand; the camera eases back to exactly the zoom and offset it had; the HUD comes
   back; the spot is free.
4. The walk to the seat (D3): a repeated tap on the same seat neither restarts nor cancels it; a ground tap, joystick,
   tapping the player, place_at, a stall or an out-of-reach seat gives it up — no camera or HUD change, the spot free.
5. The camera (D1): exact restore from every zoom (7, 9.3, 11, 13.7, 15 m); standing at 0 %, 50 %, 99 % of the settle;
   sitting again mid-release keeps the original base; ten cycles, no drift; pinch blocked for the whole transaction.
6. No side effects: no autoload is called by the rest spot, the seat code or Main's routing; nothing is saved.
Broken designs (mutated sources) are shown to fail; kills by a crash are reported separately.
"""
import math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd_port

REPO = gd_port.REPO
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
DT = 1 / 60

# ---------------------------------------------------------------- engine values
class V3:
    def __init__(v, x=0.0, y=0.0, z=0.0): v.x, v.y, v.z = float(x), float(y), float(z)
    def __add__(v, o): return V3(v.x + o.x, v.y + o.y, v.z + o.z)
    def __sub__(v, o): return V3(v.x - o.x, v.y - o.y, v.z - o.z)
    def __mul__(v, k): return V3(v.x * k, v.y * k, v.z * k)
    __rmul__ = __mul__
    def __neg__(v): return V3(-v.x, -v.y, -v.z)
    def __eq__(v, o): return isinstance(o, V3) and (v.x, v.y, v.z) == (o.x, o.y, o.z)
    def __ne__(v, o): return not v.__eq__(o)
    def __hash__(v): return id(v)
    def length(v): return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
    def length_squared(v): return v.x * v.x + v.y * v.y + v.z * v.z
    def normalized(v):
        n = v.length(); return V3(v.x / n, v.y / n, v.z / n) if n > 0 else V3()
    def distance_to(v, o): return (v - o).length()
    def lerp(v, o, t): return V3(v.x + (o.x - v.x) * t, v.y + (o.y - v.y) * t, v.z + (o.z - v.z) * t)
    def move_toward(v, to, delta):
        d = to - v; n = d.length()
        return V3(to.x, to.y, to.z) if n <= delta or n < 1e-12 else v + d * (delta / n)
    def __repr__(v): return f"({v.x:.3f}, {v.y:.3f}, {v.z:.3f})"
V3.ZERO = V3()
class V2:
    def __init__(v, x=0.0, y=0.0): v.x, v.y = float(x), float(y)
    def length(v): return math.hypot(v.x, v.y)
    def normalized(v):
        n = v.length(); return V2(v.x / n, v.y / n) if n > 0 else V2()
    def __mul__(v, k): return V2(v.x * k, v.y * k)
    def __eq__(v, o): return isinstance(o, V2) and (v.x, v.y) == (o.x, o.y)
    def __ne__(v, o): return not v.__eq__(o)
    def __hash__(v): return id(v)
    def __repr__(v): return f"({v.x:.4f}, {v.y:.4f})"
V2.ZERO = V2()
class Basis:
    def __init__(b, yaw_deg): t = math.radians(yaw_deg); b.z = V3(math.sin(t), 0, math.cos(t))   # a yaw's local +Z
class Xform:
    def __init__(x, origin, yaw_deg=0.0): x.origin, x.basis = origin, Basis(yaw_deg)
class GList(list):
    def is_empty(l): return len(l) == 0
    def has(l, x): return x in l
    def erase(l, x):
        if x in l: l.remove(x)
class Sig(gd_port.Signal):
    def is_connected(s, fn): return fn in s.handlers
    def disconnect(s, fn):
        if fn in s.handlers: s.handlers.remove(fn)
gd_port.Signal = Sig

class Ledger:
    def __init__(l, name, log): l.name, l.log = name, log
    def __getattr__(l, k):
        if k.startswith("__"): raise AttributeError(k)
        return lambda *a: l.log.append(f"{l.name}.{k}")

class Step:
    def __init__(s, kind, target=None, prop=None, value=None, duration=0.0, fn=None, start=None):
        s.kind, s.target, s.prop, s.value, s.duration, s.fn, s.start, s.parallel = kind, target, prop, value, float(duration), fn, start, False
class Tween:
    """A Godot Tween as these scripts use it: parallel or chained steps (property, method, callback), SINE in-out,
    values captured when a step starts, exact end values; advanced by the engine; kill() stops it."""
    def __init__(t, engine):
        t.steps, t.all_parallel, t.next_parallel, t.time, t.done, t.started, t.killed = [], False, False, 0.0, False, set(), False
        engine.tweens.append(t)
    def set_parallel(t, on=True): t.all_parallel = bool(on); return t
    def set_trans(t, x): return t
    def set_ease(t, x): return t
    def chain(t): t.next_parallel = False; t.all_parallel = False; return t
    def kill(t): t.killed = t.done = True
    def _add(t, s):
        s.parallel = bool(t.steps) and (t.all_parallel or t.next_parallel); t.next_parallel = False; t.steps.append(s); return s
    def tween_property(t, target, prop, value, duration): return t._add(Step("prop", target, prop, value, duration))
    def tween_method(t, fn, start, end, duration): return t._add(Step("method", value=end, duration=duration, fn=fn, start=start))
    def tween_callback(t, fn): return t._add(Step("call", fn=fn))
    def groups(t):
        out = []
        for s in t.steps:
            if s.parallel and out: out[-1].append(s)
            else: out.append([s])
        return out
    def advance(t, dt):
        if t.done: return
        t.time += dt; start = 0.0
        for g in t.groups():
            for s in g:
                if t.time + 1e-9 < start: continue
                if id(s) not in t.started:
                    t.started.add(id(s))
                    if s.kind == "prop": s.start = _get(s.target, s.prop)
                    if s.kind == "call": s.fn(); continue
                if s.kind in ("prop", "method"):
                    k = 1.0 if s.duration <= 0 or t.time >= start + s.duration else (t.time - start) / s.duration
                    v = s.value if k >= 1.0 else s.start + (s.value - s.start) * (-(math.cos(math.pi * k) - 1) / 2)
                    if s.kind == "prop": _set(s.target, s.prop, v)
                    else: s.fn(v)
            start += max([s.duration for s in g] + [0.0])
            if t.done: return
        if t.time + 1e-9 >= start: t.done = True
def _get(o, prop): return getattr(o, prop.replace(":", "_"))
def _set(o, prop, v): setattr(o, prop.replace(":", "_"), v)
class Engine:
    def __init__(e): e.tweens, e.now = [], 0.0
    def idle(e):
        for t in list(e.tweens): t.advance(DT)
        e.tweens = [t for t in e.tweens if not t.done]

# ---------------------------------------------------------------- the scene pieces
class Thing:
    """Any other object the player can tap (a discovery, a door): counts its interactions."""
    def __init__(o, name, pos):
        o.name, o.global_position, o.monitorable, o.remove_on_harvest, o.uses = name, pos, True, False, 0
        o.tree_exiting = Sig()
        o.reach = math.sqrt((2.2 + 0.2) ** 2 - (0.65 - 0.15) ** 2)                               # WildMint's 0.2 m shape at 0.15 m
    def is_interaction_available(o): return o.monitorable
    def interact(o): o.uses += 1; return True
    def set_tap_selected(o, a): pass
    def set_highlighted(o, a): pass
    def update_proximity(o, t): pass
class Nav:
    """A NavigationAgent3D that walks straight at its target; an out-of-reach target ends `unreach` metres short."""
    def __init__(n, player): n.player, n.target_position, n.target_desired_distance, n.unreach = player, V3(), 0.3, {}
    def _final(n):
        t = n.target_position
        for (x, z), off in n.unreach.items():
            if abs(t.x - x) < 1e-6 and abs(t.z - z) < 1e-6: return t + off
        return t
    def get_next_path_position(n): return n._final()
    def get_final_position(n): return n._final()
    def get_current_navigation_path(n): return GList([n._final()])
    def is_navigation_finished(n):
        d = n._final() - n.player.global_position; d.y = 0.0; return d.length() <= n.target_desired_distance
class Visual:
    def __init__(v): v.position, v.scale, v.rotation = V3(), V3(1, 1, 1), V3()
class InputMgr:
    def __init__(i): i.move_vector = V2()
class Camera3D:
    def __init__(c, h=0.0, v=0.08): c.h_offset, c.v_offset = h, v
class Arm:
    def __init__(a, length): a.spring_length = length
class Ctl:
    """A HUD control: opacity (modulate:a), its own mouse filter and its children."""
    def __init__(c, name, children=(), filt=0): c.name, c.modulate_a, c.mouse_filter, c.children = name, 1.0, filt, list(children)
    def find_children(c, pattern, kind, recursive=True, owned=True):
        out = []
        for ch in c.children: out += [ch] + ch.find_children(pattern, kind)
        return out
class Tree:
    def __init__(t): t.groups = {}
    def join(t, g, n): t.groups.setdefault(g, []).append(n)
    def get_nodes_in_group(t, g): return list(t.groups.get(g, []))
class Area:
    def is_ancestor_of(a, n): return True

def prepare(src):
    src = re.sub(r"\\\n\s*", "", src)
    src = re.sub(r"(\w+)\.bind\(", r"_bind(\1, ", src)                 # Callable.bind
    src = re.sub(r"^\t@warning_ignore\(.*\)$", "", src, flags=re.M)
    return src

def build(S):
    log = []
    autoloads = re.findall(r'^(\w+)="\*?res://', re.search(r"\[autoload\]\n(.*?)(?:\n\[|\Z)", S["project"], re.S).group(1), re.M)
    verbs = dict((n, int(v)) for n, v in re.findall(r"(\w+) = (\d+)", re.search(r"^enum Verb \{([^}]*)\}", S["base"], re.M).group(1)))
    anim = [x.strip() for x in re.search(r"^enum AnimState \{([^}]*)\}", S["player"], re.M).group(1).split(",") if x.strip()]
    ledgers = {a: Ledger(a, log) for a in autoloads}
    inp = InputMgr()
    gd_port.NODE_METHODS[:] = ["get_tree", "get_node_or_null", "add_to_group", "create_tween", "move_and_slide", "get_real_velocity",
                               "is_on_floor", "queue_free", "is_inside_tree"]
    gd_port.GDict.has = lambda d, k: k in d
    tree = Tree()
    gd_port.WORLD.tree = tree
    gd_port.HELPERS.update(V3=V3, V2=V2, clamp=lambda v, a, b: max(a, min(b, v)), lerp=lambda a, b, t: a + (b - a) * t,
                           lerp_angle=lambda a, b, t: a + math.remainder(b - a, math.tau) * t, atan2=math.atan2, sin=math.sin,
                           exp=math.exp, pow=pow, abs=abs, preload=lambda p: None, INF=math.inf, _bind=lambda f, *a: (lambda *b: f(*a, *b)),
                           VERB=gd_port.Mock(**verbs), TWEENC=gd_port.Mock(TRANS_SINE=1, EASE_IN_OUT=2),
                           CONTROLC=gd_port.Mock(MOUSE_FILTER_IGNORE=2, MOUSE_FILTER_STOP=0, MOUSE_FILTER_PASS=1),
                           PLAYERC=gd_port.Mock(AnimState=gd_port.Mock(**{n: i for i, n in enumerate(anim)})),
                           RESTC=gd_port.Mock(GROUP="rest_spot"), INPUT=inp, **{f"LEDGER_{a}": l for a, l in ledgers.items()})
    ext_al = {a: ("INPUT" if a == "InputManager" else f"LEDGER_{a}") for a in autoloads}
    ext = {"Vector3": "V3", "Vector2": "V2", "Verb": "VERB", "Tween": "TWEENC", "Control": "CONTROLC", "velocity": "self.velocity",
           "global_position": "self.global_position", "monitorable": "self.monitorable", **ext_al}
    # --- RestSpot
    rs_src = "var monitorable = true\nvar remove_on_harvest = true\n" + prepare(S["rest"])
    RS, rs_consts = gd_port.translate(rs_src, "RestSpot", ext)
    # --- Player (its interaction call site _interact_with is driven below, in its own order; the destination marker is a stub)
    pl_src = prepare(S["player"])
    pl_funcs = ["_physics_process", "_shape_input", "_update_facing", "_update_walk_bob", "_update_footsteps", "_update_nearby_proximity",
                "_find_nearest_interactable", "_on_interact_target_requested", "_on_move_target_requested", "_on_stop_requested",
                "sit", "stand", "_cancel_pending_seat", "_finish_navigation", "_start_navigation", "_stop_navigation",
                "_navigation_direction", "_update_navigation_progress", "place_at", "_face_target", "get_animation_state",
                "_set_animation_state", "_actual_horizontal_speed", "_update_movement_animation_state", "_begin_interaction",
                "_end_interaction", "_on_interaction_target_exiting", "_release_interaction_target", "_set_selected_target",
                "_on_movement_mode_changed"]
    PL, pl_consts = gd_port.translate(pl_src, "Player", ext, pl_funcs)
    iw = re.search(r"^func _interact_with\(.*?(?=^## |^func )", S["player"], re.M | re.S).group(0)
    iw_ok = re.search(r"if _spent_interactables\.has\(target\) or not target\.is_interaction_available\(\):\s*return\s*_face_target\(target\)"
                      r".*var serial := _begin_interaction\(target\).*await target\.interact\(\)\s*_end_interaction\(serial\)", iw, re.S) is not None
    def _interact_with(self, target):                     # Player._interact_with, as its source orders it (checked above)
        self._set_selected_target(None)
        if not iw_ok or not target.is_interaction_available(): return
        self._face_target(target)
        serial = self._begin_interaction(target)
        target.interact()
        self._end_interaction(serial)
    PL._interact_with = _interact_with
    PL._spawn_destination_marker = lambda self, d: None
    # --- FollowCamera (the settle transaction and zoom)
    cam_src = prepare(S["camera"])
    CAM, cam_consts = gd_port.translate(cam_src, "FollowCamera", ext, ["zoom_by", "set_zoom_distance", "get_zoom_distance", "settle",
                                                                      "release", "_ease_to", "_finish_ease"])
    # --- Main's rest-spot routing
    main_src = prepare(S["main"])
    MAIN, _ = gd_port.translate(main_src, "Main", {**ext, "Player": "PLAYERC", "RestSpot": "RESTC"},
                                ["_connect_rest_spots", "_on_sit_requested", "_on_player_state_changed", "_on_seat_ended"])
    # --- the HUD's quiet function
    hud_src = prepare(S["hud"])
    HUD, hud_consts = gd_port.translate(hud_src, "GameHUD", ext, ["set_quiet"])
    return dict(RS=RS, PL=PL, CAM=CAM, MAIN=MAIN, HUD=HUD, log=log, inp=inp, verbs=verbs, anim=anim, tree=tree,
                pl=pl_consts, cam=cam_consts, iw_ok=iw_ok, ledgers=ledgers)

class World:
    """One Meadow: the player, the camera, the HUD, Main's routing, the Pond Rest Spot and one other object."""
    def __init__(w, K, seat=(4.3, -12.12), yaw=-118.7, start=(1.0, -4.0), zoom=11.0, preset=None):
        w.K, w.eng = K, Engine()
        K["tree"].groups.clear()
        w.log = K["log"]; w.log.clear()
        w.inp = K["inp"]; w.inp.move_vector = V2()
        # rest spot
        rs = K["RS"](); rs.global_position = V3(seat[0], 0, seat[1]); rs._seat_point = gd_port.Mock(global_transform=Xform(V3(seat[0], 0, seat[1]), yaw))
        rs.tree_exiting = Sig()
        rs.set_tap_selected = lambda a: None; rs.set_highlighted = lambda a: None; rs.update_proximity = lambda t: None
        rs.is_interaction_available = lambda: rs.monitorable
        rs.reach = math.sqrt((K["pl"]["INTERACTION_RADIUS"] + 0.45) ** 2 - (0.65 - 0.3) ** 2)   # zone 2.2 m at 0.65 m; seat shape 0.45 m at 0.3 m
        for k, v in (preset or {}).items(): setattr(rs, k, v)
        rs._ready()
        w.rs = rs
        # player
        p = K["PL"](); p.global_position = V3(start[0], 0, start[1]); p.velocity = V3(); p.visual = Visual(); p.nav_agent = Nav(p)
        p._nearby_interactables = GList(); p._spent_interactables = GList()
        p.move_and_slide = lambda: setattr(p, "global_position", p.global_position + V3(p.velocity.x, 0, p.velocity.z) * DT)
        p.get_real_velocity = lambda: p.velocity
        p.is_on_floor = lambda: True
        w.p = p
        # camera
        c = K["CAM"](); c._camera = Camera3D(); c._spring_arm = Arm(zoom); c.create_tween = lambda: Tween(w.eng)
        w.cam = c
        # HUD
        h = K["HUD"](); h.create_tween = lambda: Tween(w.eng)
        w.joystick = Ctl("Joystick", filt=0)
        h.mobile_controls = Ctl("MobileControls", [w.joystick], filt=2)
        h.top_bar = Ctl("TopBar", [Ctl("PointsPill", filt=0), Ctl("MenuButtons", [Ctl("JournalButton"), Ctl("MovementButton")], filt=1)], filt=1)
        h.screen_buttons = Ctl("ScreenButtons", [Ctl("BasketButton"), Ctl("InventoryButton")], filt=1)
        w.hud = h
        # main
        m = K["MAIN"](); m.player, m.follow_camera, m.hud = p, c, h
        m._connect_rest_spots(Area())
        p.animation_state_changed.connect(m._on_player_state_changed)
        p.seat_ended.connect(m._on_seat_ended)
        w.main = m
        w.other = Thing("WildMint", V3(9.5, 0, -10.8))
        w.things = [rs, w.other]
        w.track = []
        w.zone()                                            # InteractionZone already holds what starts in range
    # -- input as InputManager routes it
    def tap_object(w, o):
        if o.is_interaction_available(): w.p._on_interact_target_requested(o); return "interact"
        return w.tap_ground(o.global_position)
    def tap_ground(w, pos): w.p._on_move_target_requested(pos); return "move"
    def tap_player(w): w.p._on_stop_requested(); return "stop"
    def zone(w):
        """InteractionZone (radius INTERACTION_RADIUS at 0.65 m) against each object's shape: overlap is geometric — an
        object that turns available or unavailable while overlapping is neither entered nor left again (as the runtime
        showed: Earth Nurture's repeats and standing up from the seat to collect a discovery). Entering range adds it to
        the nearby list and, if it is the approach target, the player stops and interacts; leaving drops it from the list
        (_on_interaction_zone_area_entered / _exited)."""
        for o in w.things:
            near = (o.global_position - w.p.global_position).length() <= o.reach
            if near and o not in w.p._nearby_interactables:
                w.p._nearby_interactables.append(o)
                if o is w.p._approach_target:
                    w.p._stop_navigation(); w.p._interact_with(o)
            elif not near and o in w.p._nearby_interactables:
                w.p._nearby_interactables.erase(o)
    def step(w, n=1):
        for _ in range(n):
            before = V3(w.p.global_position.x, 0, w.p.global_position.z)
            w.p._physics_process(DT)
            w.zone()
            w.eng.idle()
            w.track.append((before - w.p.global_position).length())
    def run(w, seconds, until=None):
        for _ in range(int(round(seconds / DT))):
            w.step()
            if until and until(): return True
        return until() if until else True
    def seated(w): return w.p._animation_state == w.K["anim"].index("SEATED")
    def cam_state(w): return (w.cam._spring_arm.spring_length, w.cam._camera.h_offset, w.cam._camera.v_offset)
    def quiet(w): return w.hud.top_bar.modulate_a, w.hud.screen_buttons.modulate_a

def run(S):
    p_ = []
    K = build(S)
    pl, cam_c = K["pl"], K["cam"]
    max_step = pl["MAX_SPEED"] * DT + 1e-6
    # 1. a fresh rest spot
    w = World(K)
    rs = w.rs
    if not (rs.monitorable and rs.remove_on_harvest is False and rs._get_interaction_verbs() == [K["verbs"]["USE"]] and rs in K["tree"].get_nodes_in_group("rest_spot")):
        p_.append("a fresh rest spot is available, persistent, in the rest_spot group and offers exactly USE")
    if not (7.0 <= rs.settle_distance <= 15.0 and 1.0 <= rs.settle_seconds <= 2.0 and 1.0 <= rs.release_seconds <= 2.0):
        p_.append(f"the preset is inside D-49's limits (distance 7–15 m, eases 1–2 s; got {rs.settle_distance}, {rs.settle_seconds}, {rs.release_seconds})")
    # 2. tap it from afar
    base = w.cam_state()
    w.tap_object(rs)
    walked_at, cam_walk = None, []
    def watch():
        nonlocal walked_at
        if walked_at is None and w.p._seat_pending: walked_at = (w.p.global_position - rs.global_position).length()
        if not w.seated(): cam_walk.append(w.cam_state())
        return w.seated()
    if not w.run(15.0, watch): return p_ + ["tapping the rest spot from afar ends with the player SEATED"]
    if walked_at is None or walked_at < 1.0:
        p_.append(f"the player walks on to the seat after its interaction fires in range (pending from {walked_at})")
    if max(w.track) > max_step: p_.append(f"the player walks to the seat, never jumps ({max(w.track):.3f} m in a step)")
    seat_d = (w.p.global_position - rs.global_position); seat_d.y = 0
    if seat_d.length() > pl["SEAT_ARRIVAL_TOLERANCE"]: p_.append(f"SEATED begins only at the seat ({seat_d.length():.2f} m away)")
    fwd = -rs._seat_point.global_transform.basis.z
    if abs(math.remainder(w.p._facing_angle - math.atan2(fwd.x, -fwd.z), math.tau)) > 1e-6: p_.append("seated, the player faces the seat's view")
    if not rs._occupied or not rs.monitorable or rs._get_interaction_verbs() != []:
        p_.append("the seat is occupied while the player sits: still tappable (available), offering nothing")
    if any(c != base for c in cam_walk): p_.append("the camera does not move before the player sits")
    w.run(rs.settle_seconds + 0.2)
    want = (min(max(rs.settle_distance, cam_c["ZOOM_MIN_DISTANCE"]), cam_c["ZOOM_MAX_DISTANCE"]), rs.framing_offset.x, rs.framing_offset.y)
    if w.cam_state() != want or w.cam_state()[0] != rs.settle_distance:
        p_.append(f"seated, the camera settles to the spot's preset within its ease time ({w.cam_state()} vs {want}, preset {rs.settle_distance})")
    if w.quiet() != (0.0, 0.0) or w.hud.mobile_controls.modulate_a != 1.0 or w.joystick.mouse_filter != 0 \
       or any(c.mouse_filter != 2 for c in w.hud.top_bar.find_children("*", "Control") + w.hud.screen_buttons.children):
        p_.append("seated, the HUD is quiet (top bar and thumb buttons faded and not taking touches) and the joystick untouched")
    if not w.seated() or w.p.visual.position.y > -0.05 or w.p.visual.scale.y > 0.95: p_.append("seated, the visual settles lower and wider (the seated cue)")
    # 3. while seated
    pos = V3(w.p.global_position.x, 0, w.p.global_position.z)
    w.tap_ground(pos + V3(2, 0, 1.5)); w.run(1.0)
    if not w.seated() or (w.p.global_position - pos).length() > 1e-9 or w.p._navigating: p_.append("a ground tap while seated changes nothing")
    held = w.cam_state()
    for f in (0.5, 2.0, 1.1): w.cam.zoom_by(f)
    if w.cam_state() != held: p_.append("pinch/wheel zoom is ignored while seated")
    asked, held, ends = rs.sit_requested.emitted, w.cam_state(), len(w.log)
    if w.tap_object(rs) != "interact" or not w.seated() or w.p._navigating or rs.sit_requested.emitted != asked:
        p_.append("tapping the occupied seat is a no-op (D-56): it names the seat, the player stays seated and nothing is asked")
    w.run(0.5)
    if not w.seated() or w.cam_state() != held or w.quiet() != (0.0, 0.0) or not rs._occupied:
        p_.append("…and the camera, the quiet HUD and the occupied seat are untouched")
    if rs.interact() is not False or rs.sit_requested.emitted != asked: p_.append("an occupied rest spot refuses a direct interact() and asks nothing")
    w.tap_player()
    if w.seated() or rs._occupied: p_.append("tapping the player stands, and the seat is free again")
    w.run(rs.release_seconds + 0.2)
    if w.cam_state() != base: p_.append(f"standing, the camera eases back to exactly where it was ({w.cam_state()} vs {base})")
    if w.quiet() != (1.0, 1.0) or any(c.mouse_filter == 2 for c in w.hud.top_bar.find_children("*", "Control") + w.hud.screen_buttons.children) \
       or w.hud.top_bar.mouse_filter != 1 or w.hud.top_bar.children[0].mouse_filter != 0:
        p_.append("standing, the HUD comes back with every control's own mouse filter")
    # joystick / keyboard: stand and move in the same physics step
    w.tap_object(rs); w.run(5.0, w.seated); w.run(2.0)
    w.inp.move_vector = V2(-1.0, 0.2); w.step()
    moved = w.track[-1]
    w.inp.move_vector = V2(); w.run(0.3)
    if w.seated() or moved <= 0.0: p_.append(f"joystick/keyboard movement stands and moves in the same physics step (moved {moved:.4f} m)")
    w.run(2.0)
    if w.cam_state() != base: p_.append("after a joystick stand the camera is back exactly")
    # another object while seated: stand, then its normal flow
    w.tap_object(rs); w.run(6.0, w.seated); w.run(1.0)
    uses = w.other.uses
    w.tap_object(w.other)
    if w.seated(): p_.append("tapping another object stands")
    w.run(6.0, lambda: w.other.uses > uses)
    if w.other.uses != uses + 1: p_.append("…and carries on with that object's normal interaction")
    # place_at (an area swap) while seated
    w.tap_object(rs); w.run(8.0, w.seated); w.run(1.0)
    w.cam.release(0.0)                                      # Main's _swap_area releases at once, then places the player
    w.p.place_at(Xform(V3(-21, 0, 0), 90))
    if w.seated() or rs._occupied or w.cam_state() != base: p_.append("place_at (an area swap) stands, frees the seat and the camera is back at once")
    # 4. the walk to the seat (D3) and giving it up
    def pending_world(**kw):
        x = World(K, start=(2.6, -10.9), **kw); x.tap_object(x.rs)
        if not x.p._seat_pending: p_.append("in range, tapping the seat starts the walk to it")
        return x
    x = pending_world(); ends = []
    x.p.seat_ended.connect(lambda was: ends.append(was))
    x.step(3); x.tap_object(x.rs)
    if not x.p._seat_pending or ends: p_.append(f"a repeated tap on the same seat while walking neither restarts nor cancels the sit (D3; ends {ends})")
    x.run(5.0, x.seated)
    if not x.seated(): p_.append("after a repeated tap the player still sits")
    for label, act in (("a ground tap", lambda x: x.tap_ground(x.p.global_position + V3(-2, 0, 1))),
                       ("joystick movement", lambda x: (setattr(x.inp, "move_vector", V2(-1, 0)), x.step(), setattr(x.inp, "move_vector", V2()))),
                       ("tapping the player", lambda x: x.tap_player()),
                       ("place_at", lambda x: x.p.place_at(Xform(V3(0, 0, 5))))):
        x = pending_world(); ends = []
        x.p.seat_ended.connect(lambda was: ends.append(was))
        b0 = x.cam_state(); x.step(2); act(x)
        if x.p._seat_pending or ends != [False]: p_.append(f"{label} during the walk gives the sit up at once (pending {x.p._seat_pending}, ends {ends})")
        x.run(3.0)
        if x.seated() or x.p._seat_pending or ends != [False] or x.rs._occupied or x.cam_state() != b0 or x.quiet() != (1.0, 1.0):
            p_.append(f"{label} during the walk gives the sit up: not seated, seat_ended(false) once, seat free, camera and HUD untouched (ends {ends})")
    x = World(K, start=(2.6, -10.9))
    x.p.nav_agent.unreach[(4.3, -12.12)] = V3(-1.5, 0, 0.0)          # the seat out of reach: the walk ends 1.5 m short
    ends = []; x.p.seat_ended.connect(lambda was: ends.append(was))
    x.tap_object(x.rs); x.run(5.0)
    if x.seated() or ends != [False] or x.rs._occupied: p_.append(f"an out-of-reach seat is given up, never sat from afar (ends {ends})")
    # 5. the camera transaction (D1)
    for z in (7.0, 9.3, 11.0, 13.7, 15.0):
        y = World(K, start=(2.6, -10.9), zoom=z)
        b = y.cam_state(); y.tap_object(y.rs); y.run(5.0, y.seated); y.run(2.0)
        mid = y.cam_state(); y.tap_player(); y.run(2.0)
        if y.cam_state() != b or mid[0] != y.rs.settle_distance: p_.append(f"exact restore from {z} m ({y.cam_state()} vs {b}; settled {mid})")
    for frac in (0.0, 0.5, 0.99):
        y = World(K, start=(2.6, -10.9))
        b = y.cam_state(); y.tap_object(y.rs); y.run(5.0, y.seated)
        y.run(y.rs.settle_seconds * frac); y.tap_player(); y.run(2.2)
        if y.cam_state() != b: p_.append(f"standing at {frac:.0%} of the settle restores exactly ({y.cam_state()} vs {b})")
    y = World(K, start=(2.6, -10.9))
    b = y.cam_state(); y.tap_object(y.rs); y.run(5.0, y.seated); y.run(2.0)
    y.tap_player(); y.run(y.rs.release_seconds * 0.5)
    for f in (0.5, 2.0): y.cam.zoom_by(f)
    mid_rel = y.cam_state()
    y.run(DT)
    y.tap_object(y.rs); y.run(5.0, y.seated)
    if not y.seated(): p_.append("the seat can be sat on again during the release")
    y.run(2.0); settled2 = y.cam_state(); y.tap_player(); y.run(2.2)
    if y.cam_state() != b or settled2[0] != y.rs.settle_distance:
        p_.append(f"sitting again mid-release keeps the original base and pinch stays blocked ({y.cam_state()} vs {b}; mid-release {mid_rel})")
    y = World(K, start=(2.6, -10.9), zoom=13.7)
    b = y.cam_state()
    for k in range(10):
        y.tap_object(y.rs); y.run(5.0, y.seated); y.run(0.4 + 0.15 * k); y.tap_player(); y.run(0.3 + 0.12 * k)
    y.run(2.5)
    if y.cam_state() != b: p_.append(f"ten sit/stand cycles leave no drift ({y.cam_state()} vs {b})")
    y.cam.zoom_by(0.5)
    if y.cam_state()[0] != max(b[0] * 0.5, cam_c["ZOOM_MIN_DISTANCE"]): p_.append("after the transaction pinch zoom works again")
    # 6. no side effects
    calls = sorted(set(c for c in w.log if c != "AmbientAudioManager.play_footstep_sound"))   # walking's own footsteps (pre-existing)
    if calls: p_.append(f"no side effects: no autoload is called by sitting ({calls})")
    return p_

def sources():
    return {"rest": _src("scripts", "peaceful", "rest_spot.gd"), "player": _src("scripts", "player", "player.gd"),
            "camera": _src("scripts", "camera", "follow_camera.gd"), "main": _src("scripts", "main.gd"), "hud": _src("scripts", "ui", "hud.gd"),
            "base": _src("scripts", "interactables", "interactable.gd"), "project": _src("project.godot")}

S = sources()
bad = run(S)
assert not bad, f"Rest spot: {bad}"

def mutate(key, old, new):
    s = dict(S); assert old in s[key], (key, old); s[key] = s[key].replace(old, new, 1); return s
MUTANTS = {
    # the rest spot
    "rest: offers COLLECT": mutate("rest", "verbs.append(Verb.USE)", "verbs.append(Verb.COLLECT)"),
    "rest: one-shot (remove_on_harvest stays true)": mutate("rest", "\tremove_on_harvest = false\n", ""),
    "rest: asks to be sat on while occupied": mutate("rest", "\tif _occupied:\n\t\treturn false\n", ""),
    "rest: never occupied": mutate("rest", "\t_occupied = occupied", "\tpass"),
    "rest: the occupied seat unavailable (a tap falls through to the player)": mutate("rest", "\t_occupied = occupied", "\t_occupied = occupied\n\tmonitorable = not occupied"),
    "rest: offers USE while occupied": mutate("rest", "\tif not _occupied:\n\t\tverbs.append(Verb.USE)", "\tverbs.append(Verb.USE)"),
    "rest: a reward": mutate("rest", "\tsit_requested.emit(self)\n", "\tsit_requested.emit(self)\n\tPointsManager.add_points(5)\n"),
    "rest: a save": mutate("rest", "\tsit_requested.emit(self)\n", "\tsit_requested.emit(self)\n\tSaveManager.save_game()\n"),
    "rest: preset 20 m (beyond the zoom limits)": mutate("rest", "var settle_distance: float = 12.0", "var settle_distance: float = 20.0"),
    "rest: a 3 s settle": mutate("rest", "var settle_seconds: float = 1.5", "var settle_seconds: float = 3.0"),
    # the player
    "player: sit() teleports": mutate("player", "\t_start_navigation(spot.origin)\n\t_seat_spot = spot", "\tglobal_position = spot.origin\n\t_start_navigation(spot.origin)\n\t_seat_spot = spot"),
    "player: SEATED at once in sit()": mutate("player", "\t_seat_pending = true\n", "\t_seat_pending = true\n\t_set_animation_state(AnimState.SEATED)\n"),
    "player: seated from afar (no arrival check)": mutate("player", "\tif offset.length() > SEAT_ARRIVAL_TOLERANCE:", "\tif false:"),
    "player: no facing on arrival": mutate("player", "\t\t_facing_angle = atan2(forward.x, -forward.z)\n\t_set_animation_state(AnimState.SEATED)", "\t\tpass\n\t_set_animation_state(AnimState.SEATED)"),
    "player: ground taps not ignored while seated": mutate("player", "\tif _animation_state == AnimState.SEATED:\n\t\treturn\n\t_start_navigation(destination)", "\t_start_navigation(destination)"),
    "player: tapping the player does not stand": mutate("player", "func _on_stop_requested() -> void:\n\tstand()\n", "func _on_stop_requested() -> void:\n"),
    "player: joystick does not stand": mutate("player", "\t\t_stop_navigation()\n\t\tstand()", "\t\t_stop_navigation()"),
    "player: another object does not stand": mutate("player", "\t\treturn\n\tstand()\n\tif _nearby_interactables.has(target):", "\t\treturn\n\tif _nearby_interactables.has(target):"),
    "player: a repeated seat tap cancels (no D3 guard)": mutate("player", "\tif target == _seat_source and (_seat_pending or _animation_state == AnimState.SEATED):\n\t\treturn\n", ""),
    "player: tapping the occupied seat stands (no D-56 guard)": mutate("player", "\tif target == _seat_source and (_seat_pending or _animation_state == AnimState.SEATED):\n\t\treturn\n", "\tif target == _seat_source and _seat_pending:\n\t\treturn\n"),
    "player: the walk to the seat cancelled by its own tap (no D3 guard)": mutate("player", "\tif target == _seat_source and (_seat_pending or _animation_state == AnimState.SEATED):\n\t\treturn\n", "\tif target == _seat_source and _animation_state == AnimState.SEATED:\n\t\treturn\n"),
    "player: every tap ignored while seated": mutate("player", "\tif target == _seat_source and (_seat_pending or _animation_state == AnimState.SEATED):\n\t\treturn\n", "\tif _animation_state == AnimState.SEATED or (target == _seat_source and _seat_pending):\n\t\treturn\n"),
    "player: a ground tap keeps the pending sit": mutate("player", "func _start_navigation(destination: Vector3) -> void:\n\t_cancel_pending_seat()\n", "func _start_navigation(destination: Vector3) -> void:\n"),
    "player: a stopped walk keeps the pending sit": mutate("player", "func _stop_navigation() -> void:\n\t_cancel_pending_seat()\n", "func _stop_navigation() -> void:\n"),
    "player: place_at does not stand": mutate("player", "\tglobal_position = spot.origin\n\tstand()", "\tglobal_position = spot.origin"),
    "player: speed logic leaves SEATED": mutate("player", "\tif _animation_state == AnimState.INTERACT or _animation_state == AnimState.SEATED:", "\tif _animation_state == AnimState.INTERACT:"),
    "player: no seated cue": mutate("player", "\t\tvar rest_height := -SEATED_VISUAL_DROP if _animation_state == AnimState.SEATED else 0.0", "\t\tvar rest_height := 0.0"),
    "player: a cancelled sit reports nothing": mutate("player", "\t_seat_pending = false\n\t_seat_source = null\n\tseat_ended.emit(false)\n", "\t_seat_pending = false\n\t_seat_source = null\n"),
    # the camera
    "camera: base recaptured on every settle": mutate("camera", "\tif not _settle_active:\n\t\t_settle_active = true\n\t\t_base_distance", "\tif true:\n\t\t_settle_active = true\n\t\t_base_distance"),
    "camera: release forgets the offset": mutate("camera", "\t_ease_to(_base_distance, _base_offset, seconds, true)", "\t_ease_to(_base_distance, Vector2(_camera.h_offset, _camera.v_offset), seconds, true)"),
    "camera: pinch not blocked": mutate("camera", "\tif _settle_active:\n\t\treturn\n", ""),
    "camera: the transaction never ends": mutate("camera", "\tif ending:\n\t\t_settle_active = false", "\tpass"),
    "camera: a running ease not replaced": mutate("camera", "\t\t_settle_tween.kill()\n", ""),
    # Main
    "main: the camera never settles": mutate("main", "\tfollow_camera.settle(_rest_spot.settle_distance, _rest_spot.framing_offset, _rest_spot.settle_seconds)\n", ""),
    "main: settles as soon as the sit is asked": mutate("main", "\tplayer.sit(rest_spot.get_seat_transform(), rest_spot)\n\t_rest_spot = rest_spot", "\tplayer.sit(rest_spot.get_seat_transform(), rest_spot)\n\t_rest_spot = rest_spot\n\tfollow_camera.settle(rest_spot.settle_distance, rest_spot.framing_offset, rest_spot.settle_seconds)"),
    "main: no release on standing": mutate("main", "\t\tfollow_camera.release(rest_spot.release_seconds)\n", ""),
    "main: the seat never occupied": mutate("main", "\t_rest_spot.set_occupied(true)\n", ""),
    "main: the seat stays occupied": mutate("main", "\trest_spot.set_occupied(false)\n", ""),
    "main: the HUD never quiet": mutate("main", "\thud.set_quiet(true)\n", ""),
    "main: the HUD stays quiet": mutate("main", "\t\thud.set_quiet(false)\n", ""),
    # the HUD
    "hud: the joystick quieted too": mutate("hud", "[top_bar, screen_buttons]", "[top_bar, screen_buttons, mobile_controls]"),
    "hud: quiet controls still take touches": mutate("hud", "\t\t\t\tcontrol.mouse_filter = Control.MOUSE_FILTER_IGNORE\n", ""),
    "hud: mouse filters not given back": mutate("hud", "\t\t\t\tcontrol.mouse_filter = _quiet_filters[control]\n", "\t\t\t\tpass\n"),
}
killed = {}
for name, s in MUTANTS.items():
    try:
        r = run(s)
        killed[name] = ("behaviour", r[0]) if r else None
    except Exception as e:  # noqa: BLE001 — a mutant that breaks the run is reported separately
        killed[name] = ("crash", f"{type(e).__name__}: {e}")
survivors = [n for n, k in killed.items() if k is None]
assert not survivors, f"broken designs not caught: {survivors}"
crashes = [n for n, k in killed.items() if k[0] == "crash"]
print("rest spot: walked to (never a jump), SEATED only at the seat facing its view, seat occupied; camera settles to the preset "
      "and eases back exactly (7 / 9.3 / 11 / 13.7 / 15 m, stands at 0 / 50 / 99 %, re-sit mid-release, ten cycles); pinch "
      "blocked for the whole transaction; HUD quiet with the joystick kept; ground taps and the occupied seat ignored, tap-player / joystick / "
      "another object / place_at stand; D3 repeat keeps the walk, ground / joystick / player / place_at / out-of-reach give "
      "it up; no autoload called")
print(f"broken designs: {len(MUTANTS)} caught — {len(MUTANTS) - len(crashes)} by behaviour, {len(crashes)} by a crash {crashes}")
print("ALL REST SPOT SIMULATIONS PASSED")
