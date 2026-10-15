#!/usr/bin/env python3
"""The Pond Rest Spot (E1; D-48–D-57, D1–D3; Rest Mode controls D-62 R1): the real RestSpot, the Player's seated state and
movement step, the FollowCamera's settle transaction, Main's rest-spot routing and the HUD's quiet function, Stand Up
button and joystick suppression, each translated from its
GDScript with gd_port and run together against a model of the engine pieces they use — physics steps (move_and_slide
as velocity × delta), a navigation agent that walks straight to its target (or, for an out-of-reach target, to the
nearest point it can reach), tweens bound to their node, InputManager's routed signals (a tap reaches an object only
while it is available, as InputManager._find_interactable rules) and a ledger of every autoload call.
1. A fresh rest spot is available, persistent, in the rest_spot group and offers exactly USE.
2. Tapping it from afar: the player walks to it (never a jump), its interaction fires in range, the player walks on to
   the seat point and is SEATED only on arriving — facing the seat's view; the spot becomes occupied; the camera eases
   to the spot's preset (distance within 7–15 m, framing offset) in 1–2 s; the HUD goes quiet (the Stand Up button
   kept); movement is locked, the joystick hidden and the Stand Up button shown (D-62).
3. While seated: a ground tap changes nothing; once the settle has eased in, pinch/wheel zoom stays within the spot's
   seated range (7–10 m, D-62 R2) and never moves the framing; tapping the occupied seat (still available,
   offering nothing) is a no-op (D-56); joystick/keyboard movement neither stands nor moves the player (D-62), even
   without Main's lock; the Stand Up button, tapping the player, another object (stand, then its normal flow) and
   place_at all stand; the camera eases back to exactly the zoom and offset it had; the HUD comes back; the spot is
   free; Stand Up hides at once, but movement and the joystick come back only when the release has finished
   (settle_ended) — a tap-started walk is not held back — and at once after an area swap (its release(0.0)). In Tap to Move the
   joystick stays hidden after it.
4. The walk to the seat (D3): a repeated tap on the same seat neither restarts nor cancels it; a ground tap, joystick (not
   locked before sitting),
   tapping the player, place_at, a stall or an out-of-reach seat gives it up — no camera or HUD change, the spot free.
5. The camera (D1, D-62 R2): the seated start is 8 m; exact restore from every zoom (7, 9.3, 11, 13.7, 15 m) whatever
   the seated pinch did (at 7 m or 10 m); standing at 0 %, 50 %, 99 % of the settle; sitting again mid-release keeps the
   original base and the movement lock and starts again at 8 m; ten cycles with pinches, no drift; pinch ignored while
   the settle or release eases; after the transaction the normal 7–15 m zoom; an area swap with a pinched seated view
   restores at once; settle_ended once per transaction.
6. No side effects: no autoload is called by the rest spot, the seat code or Main's routing (the Stand Up button's
   own UI click aside, as every HUD button, and the rest ambience below); nothing is saved.
7. The rest ambience (D-62 R4; the real AmbientAudioManager rest functions on a mock player that counts play/stop): it
   fades in from silence when SEATED begins and out when standing — then stops; the HUD's mute (shown only while
   seated) silences and restores it and lasts across sits (session state, never reset); sitting again during the
   fade-out picks the same playback up (never a second one); a given-up walk plays nothing; five quick cycles leave
   nothing playing; the camera release, movement unlock and joystick return keep their exact timing with it.
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
    def is_finite(v): return math.isfinite(v.x) and math.isfinite(v.y)
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

class AudioPlayer:
    """An AudioStreamPlayer as the rest ambience uses it: playing, stream, volume_db; counts play() and stop()."""
    def __init__(pl): pl.playing, pl.stream, pl.volume_db, pl.plays, pl.stops = False, None, 0.0, 0, 0
    def play(pl): pl.playing = True; pl.plays += 1
    def stop(pl): pl.playing = False; pl.stops += 1
class AudioProxy:
    """AmbientAudioManager for the translated scripts: the real rest-ambience functions of the current world's manager
    (each call also logged), every other hook a ledger entry."""
    def __init__(p, ledger): p.__dict__.update(ledger=ledger, target=None)
    def __getattr__(p, k):
        t = p.__dict__["target"]
        if t is not None and hasattr(type(t), k):
            fn = getattr(t, k)
            return lambda *a: (p.__dict__["ledger"].log.append(f"AmbientAudioManager.{k}"), fn(*a))[1]
        return getattr(p.__dict__["ledger"], k)

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
    def __init__(i): i.move_vector, i.movement_mode, i.joystick_enabled = V2(), 0, True       # MovementMode.JOYSTICK
    def is_tap_to_move(i): return i.movement_mode == 1
    def set_joystick_enabled(i, on): i.joystick_enabled = bool(on)
class Camera3D:
    def __init__(c, h=0.0, v=0.08): c.h_offset, c.v_offset = h, v
class Arm:
    def __init__(a, length): a.spring_length = length
class Ctl:
    """A HUD control: opacity (modulate:a), its own mouse filter and its children."""
    def __init__(c, name, children=(), filt=0, visible=True):
        c.name, c.modulate_a, c.mouse_filter, c.children, c.visible = name, 1.0, filt, list(children), visible
        c.text = c.tooltip_text = ""
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
                           exp=math.exp, pow=pow, abs=abs, deg_to_rad=math.radians, PI=math.pi, preload=lambda p: None, INF=math.inf, _bind=lambda f, *a: (lambda *b: f(*a, *b)),
                           VERB=gd_port.Mock(**verbs), TWEENC=gd_port.Mock(TRANS_SINE=1, EASE_IN_OUT=2),
                           CONTROLC=gd_port.Mock(MOUSE_FILTER_IGNORE=2, MOUSE_FILTER_STOP=0, MOUSE_FILTER_PASS=1),
                           PLAYERC=gd_port.Mock(AnimState=gd_port.Mock(**{n: i for i, n in enumerate(anim)})),
                           RESTC=gd_port.Mock(GROUP="rest_spot"), INPUT=inp, **{f"LEDGER_{a}": l for a, l in ledgers.items()})
    audio = AudioProxy(ledgers["AmbientAudioManager"])
    gd_port.HELPERS["LEDGER_AmbientAudioManager"] = audio
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
                "_on_movement_mode_changed", "set_movement_locked"]
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
    CAM, cam_consts = gd_port.translate(cam_src, "FollowCamera", {**ext, "rotation": "self.rotation"},
                                        ["zoom_by", "_zoom_seated", "set_zoom_distance", "get_zoom_distance", "settle", "release",
                                         "_ease_to", "_finish_ease", "yaw_by", "_set_yaw"])
    # --- Main's rest-spot routing
    main_src = prepare(S["main"])
    MAIN, _ = gd_port.translate(main_src, "Main", {**ext, "Player": "PLAYERC", "RestSpot": "RESTC"},
                                ["_connect_rest_spots", "_on_sit_requested", "_on_player_state_changed", "_on_seat_ended",
                                 "_on_stand_up_requested", "_on_camera_released"])
    # --- the HUD's quiet function, the Stand Up button and joystick suppression (D-62)
    hud_src = prepare(S["hud"])
    HUD, hud_consts = gd_port.translate(hud_src, "GameHUD", ext, ["set_quiet", "set_stand_up_visible", "set_movement_control_suppressed",
                                                                  "_on_movement_mode_changed", "_on_stand_up_button_pressed",
                                                                  "set_mute_visible", "_on_mute_button_pressed", "_update_mute_button"])
    # --- the rest ambience and its session mute (D-62 R4); the placeholder's generation is not modelled
    AAM, aam_consts = gd_port.translate(prepare(S["audio"]), "AmbientAudioManager", ext,
                                        ["start_rest_ambience", "stop_rest_ambience", "set_rest_ambience_muted", "is_rest_ambience_muted",
                                         "_fade_rest", "_placeholder_rest_ambience"])
    AAM._make_placeholder_ambience = lambda self: "PLACEHOLDER"
    return dict(RS=RS, PL=PL, CAM=CAM, MAIN=MAIN, HUD=HUD, AAM=AAM, aam=aam_consts, audio=audio, log=log, inp=inp, verbs=verbs,
                anim=anim, tree=tree, pl=pl_consts, cam=cam_consts, iw_ok=iw_ok, ledgers=ledgers)

class World:
    """One Meadow: the player, the camera, the HUD, Main's routing, the Pond Rest Spot and one other object."""
    def __init__(w, K, seat=(4.3, -12.12), yaw=-118.7, start=(1.0, -4.0), zoom=11.0, preset=None, tap_mode=False, yaw0=0.0):
        w.K, w.eng = K, Engine()
        K["tree"].groups.clear()
        w.log = K["log"]; w.log.clear()
        w.inp = K["inp"]; w.inp.move_vector = V2(); w.inp.movement_mode = 1 if tap_mode else 0
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
        c.rotation = V3(0, math.radians(yaw0), 0)
        w.yaw_at_end = []
        c.settle_ended.connect(lambda: w.yaw_at_end.append(c.rotation.y))   # before Main's handler: the yaw as movement returns
        w.cam = c
        # HUD
        h = K["HUD"](); h.create_tween = lambda: Tween(w.eng)
        w.joystick = Ctl("Joystick", filt=0)
        h.mobile_controls = Ctl("MobileControls", [w.joystick], filt=2)
        h.top_bar = Ctl("TopBar", [Ctl("PointsPill", filt=0), Ctl("MenuButtons", [Ctl("JournalButton"), Ctl("MovementButton")], filt=1)], filt=1)
        h.screen_buttons = Ctl("ScreenButtons", [Ctl("BasketButton"), Ctl("InventoryButton")], filt=1)
        h.stand_up_button = Ctl("StandUpButton", filt=0, visible=False)
        h.mute_button = Ctl("MuteButton", filt=0, visible=False)
        a = K["AAM"](); a._rest_player = AudioPlayer(); a.create_tween = lambda: Tween(w.eng)
        K["audio"].target = a; w.audio = a
        h.movement_button = Ctl("MovementButton")
        h._on_movement_mode_changed(w.inp.movement_mode)     # as GameHUD._ready does
        w.hud = h
        # main
        m = K["MAIN"](); m.player, m.follow_camera, m.hud = p, c, h
        m._connect_rest_spots(Area())
        p.animation_state_changed.connect(m._on_player_state_changed)
        p.seat_ended.connect(m._on_seat_ended)
        c.settle_ended.connect(m._on_camera_released)       # as Main._ready wires them (the checker pins the lines)
        h.stand_up_requested.connect(m._on_stand_up_requested)
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
    def cam_state(w): return (w.cam._spring_arm.spring_length, w.cam._camera.h_offset, w.cam._camera.v_offset, w.cam.rotation.y)
    def yaw_deg(w): return math.degrees(w.cam.rotation.y)
    def quiet(w): return w.hud.top_bar.modulate_a, w.hud.screen_buttons.modulate_a
    def controls(w):
        """(movement locked, joystick shown, Stand Up shown) — Rest Mode's controls (D-62); the joystick taking no drags
        (InputManager's joystick off, R3) goes with it being hidden."""
        locked, shown = w.p._movement_locked, w.hud.mobile_controls.visible
        if w.inp.joystick_enabled == locked and not w.inp.is_tap_to_move():
            return ("joystick enabled", w.inp.joystick_enabled, "while locked", locked)
        return locked, shown, w.hud.stand_up_button.visible
    def press_stand_up(w): w.hud._on_stand_up_button_pressed()
    def press_mute(w): w.hud._on_mute_button_pressed()
    def sound(w):
        """(playing, volume dB, muted, mute button shown and its icon) — the rest ambience (R4)."""
        pl = w.audio._rest_player
        return pl.playing, round(pl.volume_db, 6), w.audio._rest_muted, (w.hud.mute_button.visible, w.hud.mute_button.text)

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
    zr = rs.seated_zoom_range
    if rs.settle_distance != 8.0 or (zr.x, zr.y) != (7.0, 10.0) or not (cam_c["ZOOM_MIN_DISTANCE"] <= zr.x < zr.y <= cam_c["ZOOM_MAX_DISTANCE"]):
        p_.append(f"the seated view is D-62's: start at 8 m, pinch within 7–10 m inside the zoom limits (got {rs.settle_distance}, {zr})")
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
    want = (min(max(rs.settle_distance, cam_c["ZOOM_MIN_DISTANCE"]), cam_c["ZOOM_MAX_DISTANCE"]), rs.framing_offset.x, rs.framing_offset.y, base[3])
    if w.cam_state() != want or w.cam_state()[0] != rs.settle_distance:
        p_.append(f"seated, the camera settles to the spot's preset within its ease time ({w.cam_state()} vs {want}, preset {rs.settle_distance})")
    if w.quiet() != (0.0, 0.0) or w.hud.mobile_controls.modulate_a != 1.0 or w.joystick.mouse_filter != 0 \
       or any(c.mouse_filter != 2 for c in w.hud.top_bar.find_children("*", "Control") + w.hud.screen_buttons.children):
        p_.append("seated, the HUD is quiet (top bar and thumb buttons faded and not taking touches) and the joystick untouched")
    if w.controls() != (True, False, True) or w.hud.stand_up_button.modulate_a != 1.0 or w.hud.stand_up_button.mouse_filter != 0:
        p_.append(f"seated (D-62): movement locked, the joystick hidden and the Stand Up button shown and taking touches ({w.controls()})")
    if not w.seated() or w.p.visual.position.y > -0.05 or w.p.visual.scale.y > 0.95: p_.append("seated, the visual settles lower and wider (the seated cue)")
    # 3. while seated
    pos = V3(w.p.global_position.x, 0, w.p.global_position.z)
    w.tap_ground(pos + V3(2, 0, 1.5)); w.run(1.0)
    if not w.seated() or (w.p.global_position - pos).length() > 1e-9 or w.p._navigating: p_.append("a ground tap while seated changes nothing")
    held = w.cam_state(); seen = []
    for f in (0.5, 0.8, 2.0, 1.1, 0.9):
        w.cam.zoom_by(f); seen.append(round(w.cam_state()[0], 6))
    if seen != [7.0, 7.0, 10.0, 10.0, 9.0] or w.cam_state()[1:] != held[1:] or w.cam._base_distance != base[0]:
        p_.append(f"seated, pinch/wheel zoom stays within 7–10 m and never moves the framing or the base (D-62; {seen})")
    asked, held, ends = rs.sit_requested.emitted, w.cam_state(), len(w.log)
    if w.tap_object(rs) != "interact" or not w.seated() or w.p._navigating or rs.sit_requested.emitted != asked:
        p_.append("tapping the occupied seat is a no-op (D-56): it names the seat, the player stays seated and nothing is asked")
    w.run(0.5)
    if not w.seated() or w.cam_state() != held or w.quiet() != (0.0, 0.0) or not rs._occupied:
        p_.append("…and the camera, the quiet HUD and the occupied seat are untouched")
    if rs.interact() is not False or rs.sit_requested.emitted != asked: p_.append("an occupied rest spot refuses a direct interact() and asks nothing")
    w.tap_player()
    if w.seated() or rs._occupied: p_.append("tapping the player stands, and the seat is free again")
    if w.controls() != (True, False, False): p_.append(f"standing, Stand Up hides at once; movement and the joystick wait for the camera ({w.controls()})")
    w.run(rs.release_seconds + 0.2)
    if w.cam_state() != base: p_.append(f"standing, the camera eases back to exactly where it was ({w.cam_state()} vs {base})")
    if w.controls() != (False, True, False): p_.append(f"the release finished: movement and the joystick are back ({w.controls()})")
    if w.quiet() != (1.0, 1.0) or any(c.mouse_filter == 2 for c in w.hud.top_bar.find_children("*", "Control") + w.hud.screen_buttons.children) \
       or w.hud.top_bar.mouse_filter != 1 or w.hud.top_bar.children[0].mouse_filter != 0:
        p_.append("standing, the HUD comes back with every control's own mouse filter")
    # joystick / keyboard while seated (D-62): neither stands nor moves; the camera, the quiet HUD and the seat stay
    w.tap_object(rs); w.run(5.0, w.seated); w.run(2.0)
    held, pos = w.cam_state(), V3(w.p.global_position.x, 0, w.p.global_position.z)
    w.inp.move_vector = V2(-1.0, 0.2); w.run(1.0)
    if not w.seated() or (w.p.global_position - pos).length() > 1e-9 or w.cam_state() != held or not rs._occupied \
       or w.quiet() != (0.0, 0.0) or w.controls() != (True, False, True):
        p_.append(f"joystick/keyboard movement while seated neither stands nor moves the player (D-62; moved {(w.p.global_position - pos).length():.4f} m)")
    # the Stand Up button, the joystick still held and the view pinched to 10 m: stands; movement and the joystick wait
    # for the whole release, which ends at the exact pre-sit view
    w.cam.zoom_by(1.5); w.cam.yaw_by(V2(400, 0))            # and turned to the 45° limit (D-62 R3)
    turned = w.yaw_deg()
    asked = rs.sit_requested.emitted
    w.press_stand_up()
    if w.seated() or rs._occupied or w.controls() != (True, False, False) or rs.sit_requested.emitted != asked:
        p_.append(f"the Stand Up button stands and frees the seat; it hides at once, movement stays locked and the joystick hidden ({w.controls()})")
    released_at = unlocked_at = None; moved_locked = 0.0
    for i in range(int(round((rs.release_seconds + 0.5) / DT))):
        locked = w.p._movement_locked
        w.step()
        if locked: moved_locked = max(moved_locked, w.track[-1])
        if released_at is None and not w.cam._settle_active: released_at = i
        if unlocked_at is None and not w.p._movement_locked: unlocked_at = i
    if moved_locked > 0.0: p_.append(f"a held joystick moves nothing until the camera has fully restored ({moved_locked:.4f} m in a step)")
    if released_at is None or unlocked_at != released_at or w.controls() != (False, True, False) or w.cam_state() != base:
        p_.append(f"movement and the joystick come back exactly when the release finishes (released at step {released_at}, unlocked at {unlocked_at}; {w.controls()})")
    if abs(turned - 45.0) > 1e-9 or w.yaw_at_end[-1:] != [base[3]]:
        p_.append(f"the view turned to 45° is back at its base yaw exactly when movement returns (turned {turned}; yaw at settle_ended {w.yaw_at_end})")
    pos = V3(w.p.global_position.x, 0, w.p.global_position.z); w.run(0.3)
    if (w.p.global_position - pos).length() <= 0.0 or w.seated(): p_.append("after the release the held joystick moves the player as usual")
    w.inp.move_vector = V2(); w.run(1.0)
    # the Player's own rule, without Main's lock: a sit nobody routes still ignores movement while seated
    q = World(K, start=(2.6, -10.9)); q.p.sit(q.rs.get_seat_transform(), None); q.run(5.0, q.seated); q.run(1.0)
    pos = V3(q.p.global_position.x, 0, q.p.global_position.z)
    q.inp.move_vector = V2(0.0, -1.0); q.run(0.5); q.inp.move_vector = V2()
    if not q.seated() or q.p._movement_locked or (q.p.global_position - pos).length() > 1e-9:
        p_.append("the Player itself ignores joystick/keyboard movement while seated, whoever asked it to sit (D-62)")
    # another object while seated: stand, then its normal flow
    w.tap_object(rs); w.run(6.0, w.seated); w.run(1.0)
    uses = w.other.uses
    w.tap_object(w.other)
    if w.seated(): p_.append("tapping another object stands")
    pos = V3(w.p.global_position.x, 0, w.p.global_position.z); w.run(0.5)
    if not w.p._movement_locked or (w.p.global_position - pos).length() <= 0.0:
        p_.append("the walk to another object goes on while the camera restores (only joystick/keyboard movement waits)")
    w.run(6.0, lambda: w.other.uses > uses)
    if w.other.uses != uses + 1: p_.append("…and carries on with that object's normal interaction")
    # place_at (an area swap) while seated
    w.tap_object(rs); w.run(8.0, w.seated); w.run(2.0); w.cam.zoom_by(0.7); w.cam.yaw_by(V2(-150, 0))
    if w.cam_state()[0] != 7.0 or abs(w.yaw_deg() + 22.5) > 1e-9: p_.append(f"seated, a pinch in reaches the seated minimum and a drag turns the view ({w.cam_state()})")
    w.cam.release(0.0)                                      # Main's _swap_area releases at once, then places the player
    w.p.place_at(Xform(V3(-21, 0, 0), 90))
    if w.seated() or rs._occupied or w.cam_state() != base: p_.append("place_at (an area swap) stands, frees the seat and the camera is back at once")
    if w.controls() != (False, True, False): p_.append(f"after an area swap movement and the joystick are back at once (its release(0.0); {w.controls()})")
    # Tap to Move: the joystick is hidden by its mode, and stays hidden after the release
    t = World(K, start=(2.6, -10.9), tap_mode=True)
    shown = t.hud.mobile_controls.visible
    t.tap_object(t.rs); t.run(5.0, t.seated); t.run(1.0); seated_controls = t.controls()
    t.press_stand_up(); t.run(t.rs.release_seconds + 0.3)
    if shown or seated_controls != (True, False, True) or t.seated() or t.controls() != (False, False, False):
        p_.append(f"in Tap to Move the joystick stays hidden before, during and after a seated spell (Stand Up still works; {seated_controls} -> {t.controls()})")
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
        mid = y.cam_state(); y.cam.zoom_by(0.5 if z < 11.0 else 3.0); pinched = y.cam_state()[0]
        y.tap_player(); y.run(2.0)
        if y.cam_state() != b or mid[0] != y.rs.settle_distance or pinched != (7.0 if z < 11.0 else 10.0):
            p_.append(f"exact restore from {z} m after a seated pinch to {pinched} m ({y.cam_state()} vs {b}; settled {mid})")
    mid_ease = 0
    for frac in (0.0, 0.5, 0.99):
        y = World(K, start=(2.6, -10.9))
        b = y.cam_state(); y.tap_object(y.rs); y.run(5.0, y.seated)
        y.run(y.rs.settle_seconds * frac)
        if y.cam._settle_tween is not None:                  # still easing in (at 99 % the frames may have finished it)
            mid_ease += 1
            easing = y.cam_state(); y.cam.zoom_by(0.5); y.cam.zoom_by(2.0)
            if y.cam_state() != easing: p_.append(f"pinch is ignored while the settle eases (at {frac:.0%}: {easing} -> {y.cam_state()})")
        y.tap_player(); y.run(2.2)
        if y.cam_state() != b: p_.append(f"standing at {frac:.0%} of the settle restores exactly ({y.cam_state()} vs {b})")
    if mid_ease < 2: p_.append(f"the pinch-while-settling check ran mid-ease ({mid_ease} of 3 cases)")
    # the seated range is the spot's data (D-49 ownership): a spot with 8–10 m keeps both bounds, then restores exactly
    y = World(K, start=(2.6, -10.9), zoom=13.7, preset={"seated_zoom_range": V2(8.0, 10.0), "settle_distance": 9.0})
    b = y.cam_state(); y.tap_object(y.rs); y.run(5.0, y.seated); y.run(2.0); seen = [y.cam_state()[0]]
    for f in (0.5, 3.0): y.cam.zoom_by(f); seen.append(y.cam_state()[0])
    y.tap_player(); y.run(2.2)
    if seen != [9.0, 8.0, 10.0] or y.cam_state() != b:
        p_.append(f"a spot's own seated range bounds pinch at both ends and the release still restores exactly ({seen}; {y.cam_state()} vs {b})")
    y = World(K, start=(2.6, -10.9))
    b = y.cam_state(); y.tap_object(y.rs); y.run(5.0, y.seated); y.run(2.0); y.cam.zoom_by(1.25)
    y.tap_player(); y.run(y.rs.release_seconds * 0.5)
    releasing = y.cam_state()
    for f in (0.5, 2.0): y.cam.zoom_by(f)
    mid_rel = y.cam_state()
    if mid_rel != releasing: p_.append(f"pinch is ignored while the release eases ({releasing} -> {mid_rel})")
    y.run(DT)
    y.tap_object(y.rs); y.run(5.0, y.seated)
    if not y.seated(): p_.append("the seat can be sat on again during the release")
    if y.controls() != (True, False, True) or y.cam.settle_ended.emitted != 0:
        p_.append(f"sitting again mid-release keeps movement locked and the joystick hidden, the transaction unfinished ({y.controls()})")
    y.run(2.0); settled2 = y.cam_state(); y.tap_player(); y.run(2.2)
    if y.cam_state() != b or settled2[0] != y.rs.settle_distance:
        p_.append(f"sitting again mid-release (after a seated pinch to 10 m) starts again at 8 m and keeps the original base ({y.cam_state()} vs {b}; resettled {settled2})")
    if y.controls() != (False, True, False) or y.cam.settle_ended.emitted != 1:
        p_.append(f"one transaction, one settle_ended: movement and the joystick back after the last release ({y.controls()}, {y.cam.settle_ended.emitted})")
    y = World(K, start=(2.6, -10.9), zoom=13.7)
    b = y.cam_state()
    starts = []
    for k in range(10):
        y.tap_object(y.rs); y.run(5.0, y.seated); y.run(0.4 + 0.15 * k)
        if not y.cam._settle_tween: starts.append(y.cam_state()[0])
        y.cam.zoom_by((0.6, 1.7, 0.95)[k % 3]); y.cam.yaw_by(V2((250, -400, 90)[k % 3], 0)); y.tap_player(); y.run(0.3 + 0.12 * k)
    y.run(2.5)
    if y.cam_state() != b or any(d != y.rs.settle_distance for d in starts):
        p_.append(f"ten sit/stand cycles with pinches leave no drift and every sit starts at 8 m ({y.cam_state()} vs {b}; starts {starts})")
    y.cam.zoom_by(0.5)
    if y.cam_state()[0] != max(b[0] * 0.5, cam_c["ZOOM_MIN_DISTANCE"]): p_.append("after the transaction pinch zoom works again")
    y.cam.zoom_by(3.0)
    if y.cam_state()[0] != cam_c["ZOOM_MAX_DISTANCE"]: p_.append(f"after the transaction the normal zoom limits apply again, not the seated range ({y.cam_state()[0]})")
    # 5b. seated yaw (D-62 R3): a drag turns the view within ±45° of the base yaw — only seated, never while easing — and
    # every sit starts at the base yaw, every release restores it exactly, before movement returns
    y = World(K, start=(2.6, -10.9))
    b = y.cam_state(); y.cam.yaw_by(V2(200, 0))
    if y.cam_state() != b: p_.append("standing, a drag does not turn the view")
    y.tap_object(y.rs); y.run(5.0, y.seated)
    if y.cam._settle_tween is None: p_.append("the yaw-while-settling check ran mid-ease")
    easing = y.cam_state(); y.cam.yaw_by(V2(200, 0))
    if y.cam_state() != easing: p_.append(f"a drag is ignored while the settle eases ({easing} -> {y.cam_state()})")
    y.run(2.0); settled = y.cam_state(); seen = []
    for dx in (100, 100, 200, -1000, -500, 300):
        y.cam.yaw_by(V2(dx, 37)); seen.append(round(y.yaw_deg(), 9))
    y.cam.yaw_by(V2(float("inf"), 0))
    if seen != [15.0, 30.0, 45.0, -45.0, -45.0, 0.0] or y.cam_state()[:3] != settled[:3] or settled[3] != b[3] or y.yaw_deg() != 0.0:
        p_.append(f"seated, a drag turns the view by its x only, within ±45°, never the zoom or framing; a non-finite drag is ignored (D-62 R3; {seen})")
    y.cam.yaw_by(V2(200, 0)); y.tap_player(); y.run(y.rs.release_seconds * 0.5)
    releasing = y.cam_state(); y.cam.yaw_by(V2(-300, 0))
    if y.cam_state() != releasing or releasing[3] in (b[3], math.radians(30.0)):
        p_.append(f"a drag is ignored while the release eases the yaw back ({releasing} -> {y.cam_state()})")
    y.run(2.0)
    if y.cam_state() != b or y.yaw_at_end != [b[3]]: p_.append(f"standing restores the exact base yaw with the view, before movement returns ({y.cam_state()} vs {b}; {y.yaw_at_end})")
    y.cam.yaw_by(V2(200, 0))
    if y.cam_state() != b: p_.append("after a seated spell, standing, a drag does not turn the view")
    y.tap_object(y.rs); y.run(5.0, y.seated); y.run(2.0)
    if y.cam_state()[3] != b[3]: p_.append("sitting again starts at the default (base) yaw")
    y.cam.yaw_by(V2(300, 0)); y.tap_player(); y.run(0.5); y.tap_object(y.rs); y.run(5.0, y.seated); y.run(2.0)
    if y.cam_state()[3] != b[3] or y.cam.settle_ended.emitted != 1:
        p_.append(f"sitting again mid-release (turned to 45°) starts again at the default yaw ({y.yaw_deg()})")
    y.cam.yaw_by(V2(-300, 0)); y.tap_player(); y.run(2.2)
    if y.cam_state() != b or y.yaw_at_end[-1:] != [b[3]]: p_.append(f"…and standing then restores the exact base view ({y.cam_state()} vs {b})")
    y = World(K, start=(2.6, -10.9), yaw0=30.0)                 # a camera already turned (the base is whatever it was)
    b = y.cam_state(); y.tap_object(y.rs); y.run(5.0, y.seated); y.run(2.0); seen = [round(y.yaw_deg(), 9)]
    for dx in (-1000, 2000): y.cam.yaw_by(V2(dx, 0)); seen.append(round(y.yaw_deg(), 9))
    y.press_stand_up(); y.run(2.2)
    if seen != [30.0, -15.0, 75.0] or y.cam_state() != b or y.yaw_at_end != [b[3]]:
        p_.append(f"the ±45° limit and the restore are relative to the camera's own yaw before sitting ({seen}; {y.cam_state()} vs {b})")
    # 7. the rest ambience and its session mute (D-62 R4)
    A = K["aam"]; LOUD, QUIET = A["REST_AMBIENCE_DB"], A["REST_SILENT_DB"]
    a = World(K, start=(2.6, -10.9)); pl = a.audio._rest_player
    if a.sound() != (False, 0.0, False, (False, "")) or pl.plays: p_.append(f"standing, no rest ambience plays ({a.sound()})")
    a.tap_object(a.rs); a.run(5.0, a.seated)
    started = (pl.playing, pl.plays, pl.stream, pl.volume_db)
    if started[:3] != (True, 1, "PLACEHOLDER") or not QUIET <= started[3] < LOUD:
        p_.append(f"sitting starts the (placeholder) rest ambience once, from silence ({started})")
    a.run(A["REST_FADE_IN_SECONDS"] * 0.5); mid = pl.volume_db
    a.run(A["REST_FADE_IN_SECONDS"] * 0.5 + 0.2)
    if not QUIET < mid < LOUD or a.sound() != (True, LOUD, False, (True, "🔊")):
        p_.append(f"it fades in to its level; the mute button shows while seated ({mid}; {a.sound()})")
    a.press_mute(); a.run(A["REST_MUTE_FADE_SECONDS"] + 0.1); muted = a.sound()
    a.press_mute(); a.run(A["REST_MUTE_FADE_SECONDS"] + 0.1); unmuted = a.sound()
    if muted != (True, QUIET, True, (True, "🔇")) or unmuted != (True, LOUD, False, (True, "🔊")) or pl.plays != 1:
        p_.append(f"the mute silences the playing ambience and the second press restores it ({muted} -> {unmuted})")
    a.press_mute(); a.press_stand_up()
    if a.hud.mute_button.visible: p_.append("standing hides the mute button at once")
    a.run(A["REST_FADE_OUT_SECONDS"] + 0.2)
    if a.sound() != (False, QUIET, True, (False, "🔇")) or pl.stops != 1:
        p_.append(f"standing fades the ambience out and stops it; the mute lasts (session state) ({a.sound()}, stops {pl.stops})")
    a.tap_object(a.rs); a.run(5.0, a.seated); a.run(A["REST_FADE_IN_SECONDS"] + 0.2)
    if a.sound() != (True, QUIET, True, (True, "🔇")) or pl.plays != 2:
        p_.append(f"sitting again while muted: it plays silent, the button shows muted ({a.sound()})")
    a.press_mute(); a.run(A["REST_MUTE_FADE_SECONDS"] + 0.1)
    a.press_stand_up(); a.run(A["REST_FADE_OUT_SECONDS"] * 0.4); fading = pl.volume_db
    a.tap_object(a.rs); a.run(5.0, a.seated); a.run(0.05)
    if pl.plays != 2 or not pl.playing or pl.volume_db <= fading - 1e-9 or pl.stops != 1:
        p_.append(f"sitting again during the fade-out carries on with the same playback (plays {pl.plays}, {fading} -> {pl.volume_db})")
    a.run(A["REST_FADE_IN_SECONDS"] + 0.2)
    if a.sound()[:2] != (True, LOUD): p_.append(f"…and fades back in ({a.sound()})")
    # five quick sit/stand cycles: one playback at a time, nothing left playing
    for k in range(5):
        a.press_stand_up(); a.run(0.2 + 0.3 * k); a.tap_object(a.rs); a.run(5.0, a.seated); a.run(0.1 * k)
        if pl.plays - pl.stops != 1: p_.append(f"one playback at a time through sit/stand cycles (cycle {k}: plays {pl.plays}, stops {pl.stops})")
    a.press_stand_up(); a.run(A["REST_FADE_OUT_SECONDS"] + 0.3)
    if pl.playing or pl.plays != pl.stops or a.sound()[1] != QUIET: p_.append(f"after the cycles nothing is left playing ({a.sound()}, plays {pl.plays}, stops {pl.stops})")
    # the camera, movement and joystick keep their exact timing while the ambience fades
    released_at = unlocked_at = None
    a.tap_object(a.rs); a.run(5.0, a.seated); a.run(2.0); a.cam.yaw_by(V2(300, 0)); a.press_stand_up()
    for i in range(int(round(3.0 / DT))):
        a.step()
        if released_at is None and not a.cam._settle_active: released_at = i
        if unlocked_at is None and not a.p._movement_locked: unlocked_at = i
    if released_at is None or unlocked_at != released_at or a.controls() != (False, True, False) or pl.playing:
        p_.append(f"with the ambience fading, movement and the joystick still return exactly at the camera's restore (released {released_at}, unlocked {unlocked_at})")
    # a walk to the seat given up plays nothing; an area swap while seated fades it out
    g = World(K, start=(2.6, -10.9)); g.tap_object(g.rs); g.step(2); g.tap_ground(g.p.global_position + V3(-2, 0, 1)); g.run(3.0)
    if g.audio._rest_player.plays or g.sound()[0]: p_.append("a walk to the seat given up plays no ambience")
    g.tap_object(g.rs); g.run(6.0, g.seated); g.run(1.0); g.cam.release(0.0); g.p.place_at(Xform(V3(-21, 0, 0), 90)); g.run(A["REST_FADE_OUT_SECONDS"] + 0.2)
    if g.sound()[0] or g.hud.mute_button.visible or g.audio._rest_player.stops != 1: p_.append(f"an area swap while seated fades the ambience out ({g.sound()})")
    # 6. no side effects
    calls = sorted(set(c for c in w.log if c not in ("AmbientAudioManager.play_footstep_sound",          # walking's own footsteps (pre-existing)
                                                     "AmbientAudioManager.play_ui_feedback",           # the Stand Up button's click, as every HUD button
                                                     "AmbientAudioManager.start_rest_ambience",        # the rest ambience (D-62 R4)
                                                     "AmbientAudioManager.stop_rest_ambience",
                                                     "AmbientAudioManager.is_rest_ambience_muted")))   # the mute button shows the session's state
    if calls: p_.append(f"no side effects: no autoload is called by sitting ({calls})")
    return p_

def sources():
    return {"rest": _src("scripts", "peaceful", "rest_spot.gd"), "player": _src("scripts", "player", "player.gd"),
            "camera": _src("scripts", "camera", "follow_camera.gd"), "main": _src("scripts", "main.gd"), "hud": _src("scripts", "ui", "hud.gd"),
            "audio": _src("scripts", "autoload", "ambient_audio_manager.gd"),
            "base": _src("scripts", "interactables", "interactable.gd"), "project": _src("project.godot")}

S = sources()
bad = run(S)
assert not bad, f"Rest spot: {bad}"

def mutate(key, old, new):
    s = dict(S); assert old in s[key], (key, old); s[key] = s[key].replace(old, new, 1); return s
def mutate2(key, *edits):
    s = dict(S)
    for old, new in edits:
        assert old in s[key], (key, old); s[key] = s[key].replace(old, new, 1)
    return s
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
    "rest: preset 20 m (beyond the zoom limits)": mutate("rest", "var settle_distance: float = 8.0", "var settle_distance: float = 20.0"),
    "rest: the old 12 m start (before D-62)": mutate("rest", "var settle_distance: float = 8.0", "var settle_distance: float = 12.0"),
    "rest: seated range 7–15 m": mutate("rest", "var seated_zoom_range := Vector2(7.0, 10.0)", "var seated_zoom_range := Vector2(7.0, 15.0)"),
    "rest: a 3 s settle": mutate("rest", "var settle_seconds: float = 1.5", "var settle_seconds: float = 3.0"),
    # the player
    "player: sit() teleports": mutate("player", "\t_start_navigation(spot.origin)\n\t_seat_spot = spot", "\tglobal_position = spot.origin\n\t_start_navigation(spot.origin)\n\t_seat_spot = spot"),
    "player: SEATED at once in sit()": mutate("player", "\t_seat_pending = true\n", "\t_seat_pending = true\n\t_set_animation_state(AnimState.SEATED)\n"),
    "player: seated from afar (no arrival check)": mutate("player", "\tif offset.length() > SEAT_ARRIVAL_TOLERANCE:", "\tif false:"),
    "player: no facing on arrival": mutate("player", "\t\t_facing_angle = atan2(forward.x, -forward.z)\n\t_set_animation_state(AnimState.SEATED)", "\t\tpass\n\t_set_animation_state(AnimState.SEATED)"),
    "player: ground taps not ignored while seated": mutate("player", "\tif _animation_state == AnimState.SEATED:\n\t\treturn\n\t_start_navigation(destination)", "\t_start_navigation(destination)"),
    "player: tapping the player does not stand": mutate("player", "func _on_stop_requested() -> void:\n\tstand()\n", "func _on_stop_requested() -> void:\n"),
    "player: seated movement stands and moves again (D-56)": mutate("player", "\tvar direction := Vector3.ZERO\n\tif _animation_state != AnimState.SEATED and not _movement_locked:\n\t\tdirection = _shape_input(InputManager.move_vector)\n\tif direction != Vector3.ZERO:\n\t\t_stop_navigation()\n",
                                                                     "\tvar direction := _shape_input(InputManager.move_vector)\n\tif direction != Vector3.ZERO:\n\t\t_stop_navigation()\n\t\tstand()\n"),
    "player: seated movement ignored only through Main's lock": mutate("player", "\tif _animation_state != AnimState.SEATED and not _movement_locked:", "\tif not _movement_locked:"),
    "player: the movement lock ignored": mutate("player", "\tif _animation_state != AnimState.SEATED and not _movement_locked:", "\tif _animation_state != AnimState.SEATED:"),
    "player: set_movement_locked() does nothing": mutate("player", "\t_movement_locked = locked", "\tpass"),
    "player: the lock also stops a tap-started walk": mutate("player", "\telif _navigating:\n\t\tdirection = _navigation_direction()", "\telif _navigating and not _movement_locked:\n\t\tdirection = _navigation_direction()"),
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
    "camera: seated pinch still ignored (before D-62 R2)": mutate("camera", "\tif _settle_active:\n\t\t_zoom_seated(factor)\n\t\treturn", "\tif _settle_active:\n\t\treturn"),
    "camera: seated pinch with the normal limits": mutate("camera", "\tif _settle_active:\n\t\t_zoom_seated(factor)\n\t\treturn\n", ""),
    "camera: seated pinch unbounded above": mutate("camera", "_settle_zoom_range.x, _settle_zoom_range.y))", "_settle_zoom_range.x, ZOOM_MAX_DISTANCE))"),
    "camera: seated pinch unbounded below": mutate("camera", "_settle_zoom_range.x, _settle_zoom_range.y))", "ZOOM_MIN_DISTANCE, _settle_zoom_range.y))"),
    "camera: pinch during the settle/release eases": mutate("camera", "\tif _settle_tween != null or _spring_arm == null", "\tif _spring_arm == null"),
    "camera: seated pinch moves the base": mutate("camera", "_settle_zoom_range.x, _settle_zoom_range.y))\n", "_settle_zoom_range.x, _settle_zoom_range.y))\n\t_base_distance = _spring_arm.spring_length\n"),
    "camera: settle ignores its zoom range": mutate("camera", "\t_settle_zoom_range = zoom_range\n", ""),
    "camera: seated yaw unbounded": mutate("camera", "clampf(rotation.y - _base_yaw + deg_to_rad(drag.x * SEATED_YAW_DEGREES_PER_PIXEL), -_settle_yaw_limit, _settle_yaw_limit)", "rotation.y - _base_yaw + deg_to_rad(drag.x * SEATED_YAW_DEGREES_PER_PIXEL)"),
    "camera: seated yaw bounded on one side": mutate("camera", ", -_settle_yaw_limit, _settle_yaw_limit)", ", -INF, _settle_yaw_limit)"),
    "camera: yaw limit about zero, not the base yaw": mutate("camera", "\tvar turn := clampf(rotation.y - _base_yaw + ", "\tvar turn := -_base_yaw + clampf(rotation.y + "),
    "camera: yaw during the eases": mutate("camera", "\tif not _settle_active or _settle_tween != null or not drag.is_finite():", "\tif not _settle_active or not drag.is_finite():"),
    "camera: yaw while standing": mutate("camera", "\tif not _settle_active or _settle_tween != null or not drag.is_finite():", "\tif _settle_tween != null or not drag.is_finite():"),
    "camera: yaw by the vertical drag": mutate("camera", "deg_to_rad(drag.x * SEATED_YAW_DEGREES_PER_PIXEL)", "deg_to_rad(drag.y * SEATED_YAW_DEGREES_PER_PIXEL)"),
    "camera: no reset when sitting (yaw kept)": mutate2("camera", ("_settle_tween.tween_method(_set_yaw, rotation.y, _base_yaw, seconds)", "_settle_tween.tween_method(_set_yaw, rotation.y, _base_yaw if ending else rotation.y, seconds)"),
                                                     ("\t_set_yaw(_base_yaw)\n\tif ending:", "\tif ending:\n\t\t_set_yaw(_base_yaw)")),
    "camera: the release does not restore the yaw": mutate2("camera", ("_settle_tween.tween_method(_set_yaw, rotation.y, _base_yaw, seconds)", "_settle_tween.tween_method(_set_yaw, rotation.y, rotation.y if ending else _base_yaw, seconds)"),
                                                     ("\t_set_yaw(_base_yaw)\n\tif ending:", "\tif not ending:\n\t\t_set_yaw(_base_yaw)\n\tif ending:")),
    "camera: the yaw restored only after settle_ended (movement first)": mutate2("camera", ("\t_settle_tween.tween_method(_set_yaw, rotation.y, _base_yaw, seconds)\n", ""),
                                                     ("\t_set_yaw(_base_yaw)\n\tif ending:\n\t\t_settle_active = false\n\t\tsettle_ended.emit()", "\tif ending:\n\t\t_settle_active = false\n\t\tsettle_ended.emit()\n\t_set_yaw(_base_yaw)")),
    "camera: base yaw recaptured on every settle": mutate2("camera", ("\t\t_base_yaw = rotation.y\n", ""), ("\t_settle_zoom_range = zoom_range\n", "\t_base_yaw = rotation.y\n\t_settle_zoom_range = zoom_range\n")),
    "camera: settle ignores its yaw limit": mutate("camera", "\t_settle_yaw_limit = deg_to_rad(yaw_limit_degrees)\n", "\t_settle_yaw_limit = PI\n"),
    "rest: yaw limit 90°": mutate("rest", "var seated_yaw_limit_degrees: float = 45.0", "var seated_yaw_limit_degrees: float = 90.0"),
    "main: the yaw limit not passed (90°)": mutate("main", "_rest_spot.seated_yaw_limit_degrees, _rest_spot.settle_seconds)", "90.0, _rest_spot.settle_seconds)"),
    "main: the joystick left on while seated": mutate("main", "\tInputManager.set_joystick_enabled(false)\n", ""),
    "main: the joystick never back on": mutate("main", "\tInputManager.set_joystick_enabled(true)", "\tpass"),
    "camera: the seated range kept after the transaction": mutate("camera", "\tif _settle_active:\n\t\t_zoom_seated(factor)\n\t\treturn\n", "\tif true:\n\t\t_zoom_seated(factor)\n\t\treturn\n"),
    "camera: the transaction never ends": mutate("camera", "\tif ending:\n\t\t_settle_active = false\n", "\tif ending:\n"),
    "camera: a running ease not replaced": mutate("camera", "\t\t_settle_tween.kill()\n", ""),
    "camera: settle_ended never announced": mutate("camera", "\t\tsettle_ended.emit()\n", ""),
    "camera: settle_ended as the release starts": mutate2("camera", ("\t\tsettle_ended.emit()\n", ""), ("\t_ease_to(_base_distance, _base_offset, seconds, true)", "\tsettle_ended.emit()\n\t_ease_to(_base_distance, _base_offset, seconds, true)")),
    # Main
    "main: the camera never settles": mutate("main", "\tfollow_camera.settle(_rest_spot.settle_distance, _rest_spot.framing_offset, _rest_spot.seated_zoom_range, _rest_spot.seated_yaw_limit_degrees, _rest_spot.settle_seconds)\n", ""),
    "main: settles as soon as the sit is asked": mutate("main", "\tplayer.sit(rest_spot.get_seat_transform(), rest_spot)\n\t_rest_spot = rest_spot", "\tplayer.sit(rest_spot.get_seat_transform(), rest_spot)\n\t_rest_spot = rest_spot\n\tfollow_camera.settle(rest_spot.settle_distance, rest_spot.framing_offset, rest_spot.seated_zoom_range, rest_spot.seated_yaw_limit_degrees, rest_spot.settle_seconds)"),
    "main: the full zoom limits passed as the seated range": mutate("main", "_rest_spot.seated_zoom_range, _rest_spot.seated_yaw_limit_degrees, _rest_spot.settle_seconds)", "Vector2(7.0, 15.0), _rest_spot.seated_yaw_limit_degrees, _rest_spot.settle_seconds)"),
    "main: no release on standing": mutate("main", "\t\tfollow_camera.release(rest_spot.release_seconds)\n", ""),
    "main: the seat never occupied": mutate("main", "\t_rest_spot.set_occupied(true)\n", ""),
    "main: the seat stays occupied": mutate("main", "\trest_spot.set_occupied(false)\n", ""),
    "main: the HUD never quiet": mutate("main", "\thud.set_quiet(true)\n", ""),
    "main: the HUD stays quiet": mutate("main", "\t\thud.set_quiet(false)\n", ""),
    "main: movement never locked": mutate("main", "\tplayer.set_movement_locked(true)\n", ""),
    "main: movement unlocked as soon as the player stands": mutate("main", "\t\thud.set_stand_up_visible(false)\n", "\t\thud.set_stand_up_visible(false)\n\t\t_on_camera_released()\n"),
    "main: movement never unlocked": mutate("main", "\tplayer.set_movement_locked(false)\n", ""),
    "main: the joystick not hidden while seated": mutate("main", "\thud.set_movement_control_suppressed(true)\n", ""),
    "main: the joystick never comes back": mutate("main", "\thud.set_movement_control_suppressed(false)", "\tpass"),
    "main: Stand Up not wired to stand()": mutate("main", "func _on_stand_up_requested() -> void:\n\tplayer.stand()", "func _on_stand_up_requested() -> void:\n\tpass"),
    "main: Stand Up never shown": mutate("main", "\thud.set_stand_up_visible(true)\n", ""),
    "main: Stand Up stays shown after standing": mutate("main", "\t\thud.set_stand_up_visible(false)\n", ""),
    # the HUD
    "hud: the joystick quieted too": mutate("hud", "[top_bar, screen_buttons]", "[top_bar, screen_buttons, mobile_controls]"),
    "audio: a second playback on every sit": mutate("audio", "\tif not _rest_player.playing:\n\t\t_rest_player.stream", "\tif true:\n\t\t_rest_player.stream"),
    "audio: no fade-in (starts at full level)": mutate("audio", "\t\t_rest_player.volume_db = REST_SILENT_DB\n", "\t\t_rest_player.volume_db = REST_AMBIENCE_DB\n"),
    "audio: never stops after fading out": mutate("audio", "\tif not _rest_active:\n\t\t_rest_tween.tween_callback(_rest_player.stop)\n", ""),
    "audio: stops at once (no fade-out)": mutate("audio", "\t_rest_active = false\n\t_fade_rest(REST_FADE_OUT_SECONDS)", "\t_rest_active = false\n\t_fade_rest(0.0)\n\t_rest_player.stop()"),
    "audio: the mute ignored": mutate("audio", "var audible := _rest_active and not _rest_muted", "var audible := _rest_active"),
    "audio: the mute applied only from the next sit": mutate("audio", "\t_rest_muted = muted\n\tif _rest_active:\n\t\t_fade_rest(REST_MUTE_FADE_SECONDS)", "\t_rest_muted = muted"),
    "audio: the mute reset on every sit (not session state)": mutate("audio", "\t_rest_active = true\n", "\t_rest_active = true\n\t_rest_muted = false\n"),
    "main: the ambience never started": mutate("main", "\tAmbientAudioManager.start_rest_ambience()", "\tpass"),
    "main: the ambience never stopped": mutate("main", "\t\tAmbientAudioManager.stop_rest_ambience()\n", ""),
    "main: the ambience started when the sit is asked": mutate2("main", ("\tAmbientAudioManager.start_rest_ambience()", "\tpass"),
                                                            ("\t_rest_spot = rest_spot\n", "\t_rest_spot = rest_spot\n\tAmbientAudioManager.start_rest_ambience()\n")),
    "main: the mute button never shown": mutate("main", "\thud.set_mute_visible(true)\n", ""),
    "main: the mute button stays after standing": mutate("main", "\t\thud.set_mute_visible(false)\n", ""),
    "hud: the mute button mutes nothing": mutate("hud", "\tAmbientAudioManager.set_rest_ambience_muted(not AmbientAudioManager.is_rest_ambience_muted())\n", ""),
    "hud: the mute icon never updated": mutate("hud", "\tmute_button.text = \"🔇\" if muted else \"🔊\"\n", ""),
    "hud: quiet controls still take touches": mutate("hud", "\t\t\t\tcontrol.mouse_filter = Control.MOUSE_FILTER_IGNORE\n", ""),
    "hud: mouse filters not given back": mutate("hud", "\t\t\t\tcontrol.mouse_filter = _quiet_filters[control]\n", "\t\t\t\tpass\n"),
    "hud: the Stand Up button quieted too": mutate("hud", "[top_bar, screen_buttons]", "[top_bar, screen_buttons, stand_up_button]"),
    "hud: the Stand Up button asks nothing": mutate("hud", "\tstand_up_requested.emit()", "\tpass"),
    "hud: set_stand_up_visible() does nothing": mutate("hud", "\tstand_up_button.visible = shown", "\tpass"),
    "hud: joystick suppression ignored": mutate("hud", "mobile_controls.visible = not tap and not _movement_control_suppressed", "mobile_controls.visible = not tap"),
    "hud: un-suppressing shows the joystick in Tap to Move": mutate("hud", "mobile_controls.visible = not tap and not _movement_control_suppressed", "mobile_controls.visible = not _movement_control_suppressed"),
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
      "(8 m) and eases back exactly (7 / 9.3 / 11 / 13.7 / 15 m after seated pinches to 7 / 10 m, stands at 0 / 50 / 99 %, "
      "re-sit mid-release restarting at 8 m, ten cycles with pinches); seated pinch within 7–10 m, ignored while easing, "
      "normal 7–15 m after (D-62 R2); HUD quiet (Stand Up kept); ground taps, the occupied seat and joystick/keyboard "
      "movement ignored while seated (D-62); Stand Up / tap-player / another object / place_at stand; movement and the "
      "joystick locked until the release finishes (at once after an area swap; Tap to Move keeps it hidden); D3 repeat keeps "
      "the walk, ground / joystick / player / place_at / out-of-reach give it up; no autoload called")
print(f"broken designs: {len(MUTANTS)} caught — {len(MUTANTS) - len(crashes)} by behaviour, {len(crashes)} by a crash {crashes}")
print("ALL REST SPOT SIMULATIONS PASSED")
