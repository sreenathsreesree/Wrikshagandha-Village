#!/usr/bin/env python3
"""The floating joystick (D-58): InputManager's touch handling (_unhandled_input and every helper it calls, the mode
switch, focus loss, set_move_vector) and the VirtualJoystick view, each translated from its GDScript with gd_port and
run together against scripted touch streams on a 1920×1080 canvas. Tap routing itself (_handle_tap) is a recorder here:
its rays are sim_tap_movement's and sim_interaction's subject.
1. A short touch anywhere — the left half included, jitter up to TAP_MAX_MOVE — is a tap and never a joystick; nothing
   moves while a finger is still within a tap's reach.
2. In Joystick mode a lone finger landing on the left half becomes the joystick once it has dragged past TAP_MAX_MOVE:
   no tap; the ring appears at the touch-down point; the thumb follows within knob_max_distance; direction is measured
   from the touch-down point (diagonals and every direction alike, length clamped to 1, the dead zone kept); release
   hides it and the movement returns to zero. The right half, Tap to Move mode, and the left/right boundary never start it.
3. Near a screen edge the ring is moved inward just enough to be seen whole, and the direction is unchanged.
4. Multitouch: while it is held, a right-side tap still taps and a two-finger pinch still zooms (its own drags never
   zoom); a second finger before it starts makes a pinch and no joystick; another left-side finger is no second joystick.
5. Mode switch, focus loss and a new press on its index (a lost release) end it; no stale deflection or tap is left.
6. The keyboard's share of move_vector is untouched by the joystick starting, moving and ending.
Broken designs (mutated sources) are shown to fail; kills by a crash are reported separately.
"""
import math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd_port

REPO = gd_port.REPO
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
DT = 1 / 60
SCREEN = (1920.0, 1080.0)

class V2:
    def __init__(v, x=0.0, y=0.0): v.x, v.y = float(x), float(y)
    def __add__(v, o): return V2(v.x + o.x, v.y + o.y)
    def __sub__(v, o): return V2(v.x - o.x, v.y - o.y)
    def __mul__(v, k): return V2(v.x * k, v.y * k)
    def __truediv__(v, k): return V2(v.x / k, v.y / k) if isinstance(k, (int, float)) else V2(v.x / k.x, v.y / k.y)
    def __eq__(v, o): return isinstance(o, V2) and (v.x, v.y) == (o.x, o.y)
    def __ne__(v, o): return not v.__eq__(o)
    def __hash__(v): return id(v)
    def length(v): return math.hypot(v.x, v.y)
    def distance_to(v, o): return (v - o).length()
    def limit_length(v, n):
        l = v.length(); return v * (n / l) if l > n and l > 0 else V2(v.x, v.y)
    def lerp(v, o, t): return V2(v.x + (o.x - v.x) * t, v.y + (o.y - v.y) * t)
    def __repr__(v): return f"({v.x:.4f}, {v.y:.4f})"
V2.ZERO = V2()

class Clock:
    def __init__(c): c.ms = 0
    def get_ticks_msec(c): return c.ms

class Ev:
    """An input event: kind touch / drag / wheel / mouse."""
    def __init__(e, kind, index=0, pressed=False, pos=(0, 0), button=0, device=0):
        e.kind, e.index, e.pressed, e.position, e.button_index, e.device = kind, index, pressed, V2(*pos), button, device

class Ctl:
    def __init__(c, size): c.size, c.position, c.visible = V2(*size), V2(), True
    @property
    def global_position(c): return c.position
    @global_position.setter
    def global_position(c, v): c.position = v

def prepare_im(src):
    src = re.sub(r"\\\n\s*", "", src)
    for a, b in ((r"event is InputEventScreenTouch", 'event.kind == "touch"'), (r"event is InputEventScreenDrag", 'event.kind == "drag"'),
                 (r"event is InputEventMouseButton and _is_wheel\(event as InputEventMouseButton\)", 'event.kind == "wheel"'),
                 (r"event is InputEventMouseButton and not _mouse_emulates_touch", 'event.kind == "mouse" and not _mouse_emulates_touch')):
        src = re.sub(a, b, src)
    return src

def build(S):
    clock = Clock()
    gd_port.NODE_METHODS[:] = ["get_tree", "get_node_or_null", "add_to_group", "get_viewport", "get_viewport_rect", "is_visible_in_tree"]
    gd_port.GDict.has = lambda d, k: k in d
    gd_port.GDict.erase = lambda d, k: d.pop(k, None)
    gd_port.GDict.size = lambda d: len(d)
    gd_port.GDict.values = lambda d: list(dict.values(d))
    slot = {}
    gd_port.HELPERS.update(V2=V2, clamp=lambda v, a, b: max(a, min(b, v)), clampf=lambda v, a, b: max(a, min(b, v)),
                           maxf=max, CLOCK=clock, IMI=gd_port.Mock(set_move_vector=lambda v: slot["im"].set_move_vector(v)),
                           EVC=gd_port.Mock(DEVICE_ID_EMULATION=-1))
    ext = {"Vector2": "V2", "Time": "CLOCK", "InputEvent": "EVC", "MOUSE_BUTTON_WHEEL_UP": "4", "MOUSE_BUTTON_WHEEL_DOWN": "5",
           "MOUSE_BUTTON_LEFT": "1", "NOTIFICATION_APPLICATION_FOCUS_OUT": "2017"}
    IM, im_c = gd_port.translate(prepare_im(S["im"]), "InputManager", ext,
                                 ["set_move_vector", "_update_move_vector", "set_movement_mode", "set_tap_to_move", "is_tap_to_move",
                                  "_notification", "_unhandled_input", "_track_touch", "_track_pinch", "_two_finger_distance", "_track_tap",
                                  "_track_joystick_candidate", "_start_joystick", "_end_joystick"])
    JOY, joy_c = gd_port.translate(S["joy"], "VirtualJoystick", {**ext, "InputManager": "IMI"},
                                   ["_on_visibility_changed", "_on_joystick_started", "_ring_centre", "_on_joystick_moved", "_release", "_process"])
    return dict(IM=IM, JOY=JOY, im=im_c, clock=clock, slot=slot)

class World:
    def __init__(w, K, mode="joystick"):
        w.K, w.clock = K, K["clock"]
        im = K["IM"](); K["slot"]["im"] = im
        im._mouse_emulates_touch = True
        im.get_viewport = lambda: gd_port.Mock(get_visible_rect=lambda: gd_port.Mock(size=V2(*SCREEN)))
        w.taps, w.zooms, w.events = [], [], []
        im._handle_tap = lambda p: w.taps.append((p.x, p.y))
        im.zoom_requested.connect(lambda f: w.zooms.append(f))
        im.joystick_started.connect(lambda o, p: w.events.append(("start", (o.x, o.y), (p.x, p.y))))
        im.joystick_moved.connect(lambda p: w.events.append(("move", (p.x, p.y))))
        im.joystick_ended.connect(lambda: w.events.append(("end",)))
        w.im = im
        j = K["JOY"](); j.base, j.thumb = Ctl((160, 160)), Ctl((70, 70))
        j.shown = True
        j.is_visible_in_tree = lambda: j.shown
        j.get_viewport_rect = lambda: gd_port.Mock(size=V2(*SCREEN))
        j._release()
        im.joystick_started.connect(j._on_joystick_started)
        im.joystick_moved.connect(j._on_joystick_moved)
        im.joystick_ended.connect(j._release)
        w.joy = j
        if mode == "tap": w.set_mode(True)
    # input
    def ev(w, e): w.im._unhandled_input(e)
    def down(w, i, x, y): w.ev(Ev("touch", i, True, (x, y)))
    def up(w, i, x, y): w.ev(Ev("touch", i, False, (x, y)))
    def drag(w, i, x, y): w.ev(Ev("drag", i, pos=(x, y)))
    def wait(w, ms): w.clock.ms += ms
    def frames(w, n=1):
        for _ in range(n): w.joy._process(DT)
    def set_mode(w, tap):
        w.im.set_tap_to_move(tap); w.joy.shown = not tap; w.joy._on_visibility_changed()
    def tap(w, i, x, y, jitter=(0, 0)):
        w.down(i, x, y); w.wait(80)
        if jitter != (0, 0): w.drag(i, x + jitter[0], y + jitter[1])
        w.up(i, x + jitter[0], y + jitter[1]); w.wait(20)
    def mv(w): return w.im.move_vector
    def ring_centre(w): return w.joy.base.position + w.joy.base.size / 2.0
    def thumb_centre(w): return w.joy.base.position + w.joy.thumb.position + w.joy.thumb.size / 2.0
    def starts(w): return [e for e in w.events if e[0] == "start"]

def close(a, b, eps=1e-9): return abs(a - b) <= eps
def vclose(v, x, y, eps=1e-9): return close(v.x, x, eps) and close(v.y, y, eps)

def run(S):
    p_ = []
    K = build(S)
    TAP_MOVE, R = K["im"]["TAP_MAX_MOVE"], None
    w = World(K); R = w.joy.knob_max_distance; DZ = w.joy.dead_zone
    if not (0 < TAP_MOVE < R): p_.append(f"a tap's reach is inside the joystick radius ({TAP_MOVE} vs {R})")
    # 1. taps
    for (x, y), jit in (((300, 700), (0, 0)), ((120, 1000), (TAP_MOVE * 0.7, -TAP_MOVE * 0.7)), ((1500, 500), (0, 0)), ((900, 300), (TAP_MOVE, 0))):
        w = World(K); w.tap(0, x, y, jit); w.frames(30)
        if w.taps != [(x + jit[0], y + jit[1])] or w.events or w.joy.base.visible or w.mv() != V2.ZERO:
            p_.append(f"a short touch at {(x, y)} (jitter {jit}) is a tap and never a joystick (taps {w.taps}, events {w.events})")
    w = World(K); w.down(0, 400, 700)
    for k in range(1, 25):
        w.drag(0, 400 + TAP_MOVE * k / 25, 700); w.frames()
    if w.events or w.mv() != V2.ZERO or w.joy.base.visible:
        p_.append("nothing moves and nothing shows while the finger is still within a tap's reach")
    # 2. the joystick: start, follow, release
    w = World(K); w.down(3, 400, 700); w.wait(60); w.drag(3, 415, 700); w.drag(3, 430, 700)
    if w.starts() != [("start", (400.0, 700.0), (430.0, 700.0))] or not w.joy.base.visible:
        p_.append(f"past TAP_MAX_MOVE the finger becomes the joystick, its ring shown (events {w.events})")
    if not vclose(w.ring_centre(), 400, 700): p_.append(f"the ring appears at the touch-down point ({w.ring_centre()})")
    if not vclose(w.thumb_centre(), 430, 700): p_.append(f"the thumb is under the finger within the radius ({w.thumb_centre()})")
    w.drag(3, 400 + 3 * R, 700); w.frames(240)
    if not vclose(w.mv(), 1.0, 0.0, 1e-6) or not vclose(w.thumb_centre(), 400 + R, 700):
        p_.append(f"beyond the radius the deflection is clamped to 1 and the thumb to the rim (mv {w.mv()}, thumb {w.thumb_centre()})")
    w.up(3, 400 + 3 * R, 700); w.frames(240)
    if w.taps or w.events[-1:] != [("end",)] or w.joy.base.visible or w.mv().length() > 1e-6 or w.im._joystick_index != -1:
        p_.append(f"release hides the joystick, movement returns to zero, and it was never a tap (taps {w.taps}, mv {w.mv()})")
    # every direction alike; diagonals not faster; the dead zone
    for deg in range(0, 360, 15):
        w = World(K); w.down(0, 500, 600); a = math.radians(deg)
        w.drag(0, 500 + math.cos(a) * 0.7 * R, 600 + math.sin(a) * 0.7 * R); w.frames(240)
        v = w.mv()
        if not (close(v.length(), 0.7, 1e-6) and close(math.atan2(v.y, v.x) % math.tau, a % math.tau, 1e-6)):
            p_.append(f"direction {deg}°: the deflection points where the finger is, length 0.7 (got {v})"); break
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        w = World(K); w.down(0, 500, 600); w.drag(0, 500 + sx * 2 * R, 600 + sy * 2 * R); w.frames(240)
        if not vclose(w.mv(), sx / math.sqrt(2), sy / math.sqrt(2), 1e-6) or not close((w.thumb_centre() - w.ring_centre()).length(), R, 1e-6) \
           or not close(w.joy._raw_vector.length(), 1.0, 1e-9):
            p_.append(f"a diagonal beyond the radius is no faster than a straight push: length 1 at 45° (got {w.mv()})"); break
    w = World(K); w.down(0, 500, 600); w.drag(0, 500 + R, 600); w.drag(0, 500 + DZ * R * 0.5, 600 + DZ * R * 0.5); w.frames(240)
    if w.mv().length() > 1e-6 or not w.joy.base.visible: p_.append("back inside the dead zone the joystick, still held, gives no movement")
    # never from the right half, in Tap to Move, or across the boundary
    for (x, mode) in ((1500, "joystick"), (961, "joystick"), (SCREEN[0] / 2, "joystick"), (300, "tap")):
        w = World(K, mode); w.down(0, x, 600); w.drag(0, x + 2 * R, 640); w.frames(30); w.up(0, x + 2 * R, 640)
        if w.events or w.mv() != V2.ZERO or w.taps:
            p_.append(f"a drag from x={x} in {mode} mode never starts the joystick, and is no tap (events {w.events})")
    w = World(K); w.down(0, SCREEN[0] / 2 - 0.1, 600); w.drag(0, SCREEN[0] / 2 - 0.1 + R, 600)
    if len(w.starts()) != 1: p_.append("the left half reaches up to the middle of the screen")
    # 3. screen edges
    for (x, y), d in (((6, 1074), (R * 0.8, 0)), ((6, 1074), (R * 0.4, -R * 0.4)), ((955, 4), (0, R * 0.6)), ((40, 540), (-R * 0.5, R * 0.5))):
        w = World(K); w.down(0, x, y); w.drag(0, x + d[0] * 1.0001, y + d[1] * 1.0001); w.drag(0, x + d[0], y + d[1]); w.frames(240)
        c, half = w.ring_centre(), w.joy.base.size / 2.0
        on = half.x - 1e-9 <= c.x <= SCREEN[0] - half.x + 1e-9 and half.y - 1e-9 <= c.y <= SCREEN[1] - half.y + 1e-9
        want = V2(*d) / R
        if not on or not vclose(w.mv(), want.x, want.y, 1e-6) or (c - V2(x, y)).length() > half.length() + 1e-9:
            p_.append(f"near an edge at {(x, y)} the ring is whole on screen ({c}) and the direction unchanged ({w.mv()} vs {want})")
        if not vclose(w.thumb_centre() - c, d[0] if V2(*d).length() <= R else 0, d[1], 1e-6):
            p_.append(f"near an edge the thumb sits off the ring's centre by the finger's own offset ({w.thumb_centre() - c})")
    # 4. multitouch
    w = World(K); w.down(0, 300, 700); w.drag(0, 300 + R, 700)
    w.tap(1, 1500, 400)
    w.down(2, 1300, 500); w.down(4, 1500, 500)
    for k in range(1, 11): w.drag(4, 1500 + 10 * k, 500)
    w.drag(0, 300, 700 + R); w.drag(0, 300 - R, 700)
    z = list(w.zooms); w.up(4, 1600, 500); w.up(2, 1300, 500)
    w.frames(240)
    if w.taps != [(1500.0, 400.0)]: p_.append(f"while the joystick is held a right-side tap still taps ({w.taps})")
    if not z or not all(f < 1.0 for f in z) or abs(math.prod(z) - 200 / 300) > 1e-9:
        p_.append(f"while the joystick is held two other fingers still pinch, and only they zoom ({z})")
    if not vclose(w.mv(), -1.0, 0.0, 1e-6) or len(w.starts()) != 1: p_.append(f"…and the joystick keeps steering through it ({w.mv()})")
    w = World(K); w.down(0, 300, 700); w.down(1, 1400, 700); w.drag(0, 300 + R, 700); w.drag(0, 300 + 2 * R, 700)
    w.up(0, 300 + 2 * R, 700); w.up(1, 1400, 700)
    if w.events or not w.zooms or w.taps: p_.append(f"a second finger before the joystick starts makes a pinch, and no joystick (events {w.events})")
    w = World(K); w.down(0, 300, 700); w.drag(0, 300 + R, 700)
    w.down(1, 500, 500); w.drag(1, 500 + R, 500); w.drag(0, 300, 700 - R)
    if len(w.starts()) != 1 or w.taps or w.im._joystick_index != 0 or w.events[-1:] != [("move", (300.0, 700.0 - R))]:
        p_.append(f"another left-side finger is no second joystick, and the first keeps it ({w.events})")
    w.up(1, 500 + R, 500); w.tap(1, 700, 800)
    if w.taps != [(700.0, 800.0)]: p_.append("…and once lifted, a left-side tap still taps while the joystick is held")
    # 5. mode switch, focus loss, lost release
    w = World(K); w.down(0, 300, 700); w.drag(0, 300 + R, 700); w.frames(60)
    w.set_mode(True); w.frames(240)
    if w.events[-1:] != [("end",)] or w.mv().length() > 1e-6 or w.joy.base.visible or w.im._joystick_index != -1:
        p_.append("switching to Tap to Move ends the joystick, no deflection left")
    w.set_mode(False); n = len(w.events); w.drag(0, 300, 700 + R); w.frames(30); w.up(0, 300, 700)
    if len(w.events) != n or w.mv().length() > 1e-6 or w.taps or w.zooms:
        p_.append("…and the old finger, still down, neither steers, taps nor zooms afterwards")
    w = World(K); w.down(0, 300, 700); w.drag(0, 300 + R, 700); w.drag(0, 300 + R * 0.1, 700 + R * 0.1)
    w.set_mode(True); w.set_mode(False); w.up(0, 301, 701)
    if w.taps: p_.append("a joystick finger brought back to its start and lifted after the joystick ended is no tap")
    w = World(K); w.down(0, 300, 700); w.drag(0, 300 + R, 700); w.frames(60)
    w.joy.shown = False; w.joy._on_visibility_changed(); w.frames(10)
    if w.mv().length() > 1e-6 or w.joy.base.visible: p_.append("the joystick view hidden by itself leaves no deflection behind")
    w = World(K); w.down(0, 300, 700); w.drag(0, 300 + R, 700); w.frames(60)
    w.im._notification(2017); w.frames(240)
    if w.events[-1:] != [("end",)] or w.mv().length() > 1e-6 or w.joy.base.visible: p_.append("losing focus ends the joystick, no deflection left")
    n = len(w.events); w.drag(0, 300, 700 + R); w.frames(10)
    if len(w.events) != n or w.mv().length() > 1e-6: p_.append("…and its finger no longer steers")
    w.tap(1, 350, 650); w.down(2, 300, 700); w.drag(2, 300, 700 - R)
    if w.taps != [(350.0, 650.0)] or len(w.starts()) != 2: p_.append("after focus loss a tap taps and a new drag starts the joystick again")
    w = World(K); w.down(0, 300, 700); w.drag(0, 300 + R, 700)          # its release is lost ...
    w.tap(0, 320, 720); w.frames(240)                                     # ... the next touch reuses index 0
    if w.taps != [(320.0, 720.0)] or ("end",) not in w.events or w.mv().length() > 1e-6 or w.joy.base.visible:
        p_.append(f"a new press on the joystick's index (its release lost) ends it and is an ordinary touch (taps {w.taps})")
    # 6. the keyboard's share
    w = World(K); w.im._keyboard_vector = V2(0, -1); w.im._update_move_vector()
    w.down(0, 300, 700); w.drag(0, 300 + R, 700); w.frames(240)
    held = w.mv()
    w.up(0, 300 + R, 700); w.frames(240)
    if not vclose(held, 1 / math.sqrt(2), -1 / math.sqrt(2), 1e-6) or not vclose(w.mv(), 0, -1, 1e-6):
        p_.append(f"the keyboard's share combines with the joystick and survives its release ({held}, {w.mv()})")
    return p_

S0 = {"im": _src("scripts", "autoload", "input_manager.gd"), "joy": _src("scripts", "ui", "virtual_joystick.gd")}
S = dict(S0)
bad = run(S)
for b in bad: print("FAIL:", b)
assert not bad, "floating joystick simulation failed"

def mutate(key, old, new):
    s = dict(S0); assert old in s[key], (key, old); s[key] = s[key].replace(old, new, 1); return s
MUTANTS = {
    "im: the whole screen starts it": mutate("im", "const JOYSTICK_ZONE_FRACTION := 0.5", "const JOYSTICK_ZONE_FRACTION := 1.0"),
    "im: the right half starts it": mutate("im", "if screen_position.x < get_viewport", "if screen_position.x >= get_viewport"),
    "im: starts at once (no tap reach)": mutate("im", "drag.position.distance_to(_joystick_origin) > TAP_MAX_MOVE", "drag.position.distance_to(_joystick_origin) > 0.0"),
    "im: starts in Tap to Move too": mutate("im", "if movement_mode != MovementMode.JOYSTICK or _joystick_index != NO_TOUCH:", "if _joystick_index != NO_TOUCH:"),
    "im: a second joystick while one is held": mutate("im", "if movement_mode != MovementMode.JOYSTICK or _joystick_index != NO_TOUCH:", "if movement_mode != MovementMode.JOYSTICK:"),
    "im: the joystick finger stays a world finger": mutate("im", "\t_world_touches.erase(index)\n\tjoystick_started", "\tjoystick_started"),
    "im: the joystick finger keeps its tap start": mutate("im", "\t_tap_starts.erase(index)\n", ""),
    "im: a pinch keeps the candidate": mutate("im", "\t\t\t_tap_starts.clear()\n\t\t\t_joystick_candidate = NO_TOUCH\n", "\t\t\t_tap_starts.clear()\n"),
    "im: a lifted candidate stays one": mutate("im", "\t\tif index == _joystick_candidate:\n\t\t\t_joystick_candidate = NO_TOUCH\n", "\t\tpass\n"),
    "im: the joystick's drags also pinch": mutate("im", "\t\t\tjoystick_moved.emit(drag.position)\n", "\t\t\tjoystick_moved.emit(drag.position)\n\t\t\t_track_pinch(drag.index, drag.position)\n"),
    "im: a mode switch keeps it": mutate("im", "\tmovement_mode = mode\n\t_end_joystick()\n", "\tmovement_mode = mode\n"),
    "im: focus loss keeps it": mutate("im", "\t\t_keyboard_vector = Vector2.ZERO\n\t\t_end_joystick()\n", "\t\t_keyboard_vector = Vector2.ZERO\n"),
    "im: a new press on its index keeps it": mutate("im", "\t\t\t_end_joystick()\n\t\t\tif not touch.pressed:\n\t\t\t\treturn\n", "\t\t\tif not touch.pressed:\n\t\t\t\t_end_joystick()\n\t\t\t\treturn\n"),
    "im: its release also taps": mutate("im", "\t\t\t_end_joystick()\n\t\t\tif not touch.pressed:\n\t\t\t\treturn\n", "\t\t\t_end_joystick()\n\t\t\tif not touch.pressed:\n\t\t\t\t_handle_tap(touch.position)\n\t\t\t\treturn\n"),
    "im: the ended signal never sent": mutate("im", "\t_joystick_index = NO_TOUCH\n\tjoystick_ended.emit()", "\t_joystick_index = NO_TOUCH"),
    "im: started from the current point": mutate("im", "joystick_started.emit(_joystick_origin, screen_position)", "joystick_started.emit(screen_position, screen_position)"),
    "im: the joystick clears the keyboard": mutate("im", "func _start_joystick(index: int, screen_position: Vector2) -> void:\n", "func _start_joystick(index: int, screen_position: Vector2) -> void:\n\t_keyboard_vector = Vector2.ZERO\n"),
    "joy: direction from the shifted ring": mutate("joy", "var offset := (screen_position - _origin)", "var offset := (screen_position - _ring_centre(_origin))"),
    "joy: no edge clamp": mutate("joy", "base.global_position = _ring_centre(origin) - base.size / 2.0", "base.global_position = origin - base.size / 2.0"),
    "joy: no radius clamp": mutate("joy", ".limit_length(knob_max_distance)", ""),
    "joy: no dead zone": mutate("joy", "_raw_vector = normalized if normalized.length() >= dead_zone else Vector2.ZERO", "_raw_vector = normalized"),
    "joy: release keeps the deflection": mutate("joy", "\tbase.visible = false\n\tthumb.position = base.size / 2.0 - thumb.size / 2.0\n\t_raw_vector = Vector2.ZERO", "\tbase.visible = false\n\tthumb.position = base.size / 2.0 - thumb.size / 2.0"),
    "joy: release keeps the ring shown": mutate("joy", "\t_active = false\n\tbase.visible = false\n", "\t_active = false\n"),
    "joy: never shown": mutate("joy", "\tbase.visible = true\n", ""),
    "joy: hiding keeps the joystick": mutate("joy", "\tif not is_visible_in_tree():\n\t\t_release()\n\t\t_smoothed_vector", "\tif not is_visible_in_tree():\n\t\t_smoothed_vector"),
    "joy: diagonals faster (per-axis clamp)": mutate("joy", "var offset := (screen_position - _origin).limit_length(knob_max_distance)", "var offset := (screen_position - _origin)\n\toffset = V2(clampf(offset.x, -knob_max_distance, knob_max_distance), clampf(offset.y, -knob_max_distance, knob_max_distance))"),
}
# Equivalent by construction (shown to change nothing observable, so not counted): no drag ever follows a release, so a
# lifted candidate left set is never read; the joystick's finger is no world finger, so _track_pinch ignores its drags.
EQUIVALENT = {
    "im: a lifted candidate stays one": mutate("im", "\t\tif index == _joystick_candidate:\n\t\t\t_joystick_candidate = NO_TOUCH\n", "\t\tpass\n"),
    "im: the joystick's drags also pinch": mutate("im", "\t\t\tjoystick_moved.emit(drag.position)\n", "\t\t\tjoystick_moved.emit(drag.position)\n\t\t\t_track_pinch(drag.index, drag.position)\n"),
}
for name in EQUIVALENT: MUTANTS.pop(name)
for name, src in EQUIVALENT.items(): assert not run(src), f"{name} is meant to be equivalent"
caught = crash = 0; survivors, crashes = [], []
for name, src in MUTANTS.items():
    try:
        if run(src): caught += 1
        else: survivors.append(name)
    except Exception as ex:                      # a crash is a kill, but not a behavioural one: reported separately
        crash += 1; crashes.append(f"{name}: {type(ex).__name__}")
print("floating joystick: short touches tap anywhere and never move; a lone left-half finger past TAP_MAX_MOVE (Joystick mode) "
      "is the joystick — ring at the touch-down point, kept whole on screen, direction from that point, clamped, dead zone; "
      "right-side taps and pinch kept while held; mode switch / focus loss / lost release end it; keyboard share kept")
print(f"broken designs: {caught + crash} caught — {caught} by behaviour, {crash} by a crash {crashes}; "
      f"{len(EQUIVALENT)} equivalent (not counted)")
if survivors:
    print("SURVIVED:", survivors); sys.exit(1)
print("ALL FLOATING JOYSTICK SIMULATIONS PASSED")
