#!/usr/bin/env python3
"""Relationships (M08.5, D-38) — a model of friendship per NPC, its rules read from relationships.gd,
npc_talk.gd, speech_panel.gd, save_manager.gd and game_state.gd, the NPC ids from data/npcs.
1. Friendship is one whole number per NPC id (NpcDefinition.id), 0 until earned, at most MAX_FRIENDSHIP.
2. A completed conversation (Goodbye) earns +1, at most once per calendar day per NPC; an early end
   (✕, walking away, entering the house) never does; re-taps never add an ending, so never a gain.
3. Other NPCs are never affected; unknown ids change nothing.
4. Save v6: the relationships section survives save -> JSON -> load (the day too, so a relaunch on the
   same day earns nothing more); a v5 save loads with every NPC at 0 and every other section untouched;
   malformed saved data is clamped or dropped, never reaching another section.
20,000 random sessions over several days; designs that count any ending, have no daily limit, forget the
day on relaunch or skip the clamp on load are shown to break the rules.
"""
import glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
RL, NT, SP = _src("scripts", "autoload", "relationships.gd"), _src("scripts", "npc", "npc_talk.gd"), _src("scripts", "ui", "speech_panel.gd")
SM, GS, DD = _src("scripts", "autoload", "save_manager.gd"), _src("scripts", "autoload", "game_state.gd"), _src("scripts", "autoload", "daily_discovery_manager.gd")
MAX = int(re.search(r"^const MAX_FRIENDSHIP := (\d+)", RL, re.M).group(1))
SAVE_VERSION = int(re.search(r"^const SAVE_VERSION := (\d+)", SM, re.M).group(1))
for rule in ("if not _known_ids.has(npc_id):\n\t\tpush_warning", "if _last_gain_date.get(npc_id, \"\") == today:\n\t\treturn false",
             "if friendship >= MAX_FRIENDSHIP:\n\t\treturn false", "_friendship[npc_id] = friendship + 1\n\t_last_gain_date[npc_id] = today",
             "_friendship[npc_id] = clampi(int(value), 0, MAX_FRIENDSHIP)", "if typeof(npc_id) != TYPE_STRING or not _known_ids.has(npc_id):"):
    assert rule in RL, f"relationships.gd rule: {rule!r}"
assert "if speaker != self:\n\t\treturn" in NT and "if not completed:\n\t\treturn" in NT and "Relationships.record_completed_conversation(npc.definition.id)" in NT  # M08.6: own, completed
assert "conversation_ended.emit(speaker, completed)" in SP and "if _index >= _lines.size() - 1:\n\t\t_end(true)" in SP
assert re.search(r"^\t\t\t5:\s*pass", SM, re.M) and '"relationships": Relationships.get_save_data(),' in SM and SAVE_VERSION >= 6  # v6 = M08.5; M08.6 made it 7
assert "Relationships.friendship_changed.connect(_save.unbind(2))" in GS
today_body = lambda s: re.search(r"func _today_string\(\) -> String:\n((?:\t.*\n?)+)", s).group(1)
assert today_body(RL) == today_body(DD), "the same system date as DailyDiscoveryManager"
NPC_IDS = sorted(re.search(r'^id = "(\w+)"', open(f, encoding="utf-8").read(), re.M).group(1) for f in glob.glob(os.path.join(REPO, "data", "npcs", "*.tres")))
assert NPC_IDS == ["villager"], NPC_IDS
KNOWN = NPC_IDS + ["model_second_npc"]   # a second NPC exists only in this model, to show NPCs stay independent

class Relationships:
    def __init__(r, design="real", known=KNOWN):
        r.design, r.known, r.friendship, r.last, r.announced = design, list(known), {}, {}, []
    def get(r, npc): return r.friendship.get(npc, 0)
    def record_completed(r, npc, today):
        if npc not in r.known: return False
        if r.design != "no_daily_limit" and r.last.get(npc, "") == today: return False
        f = r.get(npc)
        if f >= MAX: return False
        r.friendship[npc] = f + 1; r.last[npc] = today; r.announced.append((npc, f + 1))
        return True
    def save_data(r):
        if r.design == "forget_day": return {n: {"friendship": f} for n, f in r.friendship.items()}
        return {n: {"friendship": f, "last_gain_date": r.last.get(n, "")} for n, f in r.friendship.items()}
    def apply(r, data):
        r.friendship, r.last = {}, {}
        for npc, entry in data.items():
            if not isinstance(npc, str) or npc not in r.known: continue
            if not isinstance(entry, dict): continue
            v = entry.get("friendship")
            if isinstance(v, bool) or not isinstance(v, (int, float)): continue
            r.friendship[npc] = int(v) if r.design == "no_clamp" else max(0, min(MAX, int(v)))
            d = entry.get("last_gain_date", "")
            r.last[npc] = d if isinstance(d, str) and (d == "" or re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)) else ""

class Game:
    """The save-touching parts of one launch: other sections stand in for points/coins/items/farm."""
    def __init__(g, design="real"):
        g.design, g.rel, g.other, g.saves = design, Relationships(design), {"points": 7, "items": {"x": [1]}, "wallet": {"ledger": []}, "farm": {"plots": {}}}, 0
        g.disk = None
    def conversation_ended(g, npc, completed, today):        # NpcTalk._on_conversation_ended (+ GameState saving on a rise)
        if not completed and g.design != "count_any_end": return
        if g.rel.record_completed(npc, today): g.save()
    def save(g):
        g.saves += 1
        g.disk = json.dumps(dict(g.other, save_version=SAVE_VERSION, relationships=g.rel.save_data()))
    @staticmethod
    def load(text, design="real"):
        g = Game(design); data = json.loads(text)            # Godot's JSON: whole numbers arrive as floats — json keeps them int; both handled
        if data.get("save_version", 0) < 6: data["save_version"] = 6   # step 5 -> 6: nothing to rewrite
        rel = data.get("relationships", {})
        g.rel.apply(rel if isinstance(rel, dict) else {})
        g.other = {k: data[k] for k in ("points", "items", "wallet", "farm") if k in data}
        return g

# ---------------------------------------------------------------- scripted checks
g = Game(); V, W = "villager", "model_second_npc"
assert g.rel.get(V) == 0 and g.rel.get(W) == 0 and g.rel.get("nobody") == 0, "every NPC starts at 0"
for early in range(3): g.conversation_ended(V, False, "2026-10-03")               # ✕, walking away, entering the house
assert g.rel.get(V) == 0 and g.saves == 0, "an early end earns nothing and saves nothing"
g.conversation_ended(V, True, "2026-10-03"); assert g.rel.get(V) == 1 and g.saves == 1, "a completed conversation: +1, saved at once"
g.conversation_ended(V, True, "2026-10-03"); assert g.rel.get(V) == 1 and g.saves == 1, "a second completed conversation the same day: nothing"
assert g.rel.get(W) == 0, "another NPC is unaffected"
g.conversation_ended(V, True, "2026-10-04"); assert g.rel.get(V) == 2, "the next day: +1 again"
assert g.rel.record_completed("nobody", "2026-10-05") is False and g.rel.friendship.keys() == {V}, "an unknown id changes nothing"
c = Game()
for d in range(1, 30): c.conversation_ended(V, True, f"2026-11-{d:02d}")
assert c.rel.get(V) == MAX and len(c.rel.announced) == MAX, f"capped at {MAX}, announced once per rise"
# save -> JSON -> load, relaunch the same day
h = Game.load(g.disk); assert (h.rel.get(V), h.rel.get(W), h.other) == (2, 0, g.other), "reload keeps friendship (and every other section)"
h.conversation_ended(V, True, "2026-10-04"); assert h.rel.get(V) == 2, "relaunched the same day: the day is remembered, nothing more"
h.conversation_ended(V, True, "2026-10-05"); assert h.rel.get(V) == 3
assert Game.load(h.disk).rel.save_data() == h.rel.save_data(), "save -> load -> save stable"
# a v5 save (before M08.5)
v5 = json.dumps({"save_version": 5, "points": 900, "items": {"x": [2]}, "wallet": {"ledger": [["sell:x:1", 4]]}, "farm": {"plots": {"a": 1}}})
o = Game.load(v5); assert o.rel.friendship == {} and o.rel.get(V) == 0, "v5 -> v6: every NPC at 0"
assert o.other == {k: json.loads(v5)[k] for k in ("points", "items", "wallet", "farm")}, "v5 -> v6 touches no other section"
# malformed saved data
bad = {"villager": {"friendship": 15, "last_gain_date": "yesterday"}}
m = Game.load(json.dumps({"save_version": 6, "relationships": bad})); assert m.rel.get(V) == MAX and m.rel.last[V] == "", "over the maximum clamps; a bad date is ignored"
for val, want in ((-4, 0), (3.7, 3), ("7", 0), (None, 0), ([1], 0), (True, 0)):
    m = Game.load(json.dumps({"save_version": 6, "relationships": {"villager": {"friendship": val}}}))
    assert m.rel.get(V) == want, (val, m.rel.get(V))
for rel in ({"ghost": {"friendship": 5}}, {"villager": 5}, {"villager": "lots"}, [], "x", 3):
    m = Game.load(json.dumps({"save_version": 6, "points": 1, "relationships": rel}))
    assert m.rel.get(V) == 0 and "ghost" not in m.rel.friendship and m.other == {"points": 1}, f"malformed {rel!r} dropped, other sections intact"

# ---------------------------------------------------------------- random sessions
def session(seed, design="real"):
    rnd = random.Random(seed); g = Game(design); day = 0; problems = []
    gained = {n: set() for n in KNOWN}; completed_days = {n: set() for n in KNOWN}
    for _ in range(rnd.randint(5, 80)):
        a = rnd.random(); npc = rnd.choice(KNOWN + ["nobody"]); today = f"2026-12-{day + 1:02d}"
        before = dict(g.rel.friendship)
        if a < 0.35:
            g.conversation_ended(npc, True, today)
            if npc in KNOWN: completed_days[npc].add(today)
        elif a < 0.65: g.conversation_ended(npc, False, today)                       # an early end of any kind
        elif a < 0.72: pass                                                          # re-taps: no ending at all (sim_dialogue)
        elif a < 0.82 and g.disk: g = Game.load(g.disk, design)                     # relaunch
        elif a < 0.9: day = min(day + 1, 27)
        changed = {n for n in set(before) | set(g.rel.friendship) if before.get(n, 0) != g.rel.get(n)}
        if len(changed) > 1: problems.append("one event changed two NPCs")
        for n in changed:
            if g.rel.get(n) != before.get(n, 0) + 1: problems.append("a change other than +1")
            if today in gained[n]: problems.append("two gains on one day")
            gained[n].add(today)
        if "nobody" in g.rel.friendship: problems.append("an unknown id was recorded")
        if any(not 0 <= v <= MAX for v in g.rel.friendship.values()): problems.append("out of range")
    for n in KNOWN:
        if g.rel.get(n) != min(MAX, len(completed_days[n])): problems.append(f"{n}: {g.rel.get(n)} != completed days {len(completed_days[n])}")
    return problems

N = 20000
broken = [s for s in range(N) if session(s)]
assert not broken, f"{len(broken)} sessions broke a rule, e.g. {session(broken[0])}"
for design in ("count_any_end", "no_daily_limit", "forget_day"):
    assert any(session(s, design) for s in range(2000)), f"the {design} design is shown to break a rule"
nc = Game.load(json.dumps({"save_version": 6, "relationships": {"villager": {"friendship": 99}}}), "no_clamp")
assert nc.rel.get(V) > MAX, "without the clamp a malformed save escapes the range"
print(f"relationships: NPC ids {NPC_IDS}; 0 at start, +1 per completed conversation once a day, early ends and re-taps earn nothing, cap {MAX}, "
      f"other NPCs untouched, unknown ids ignored; save v{SAVE_VERSION} round trip keeps friendship and its day; v5 saves load at 0 with other sections intact; "
      f"malformed data clamped/dropped; {N} random sessions OK; count-any-end, no-daily-limit, forget-the-day and no-clamp shown to break")
print("ALL RELATIONSHIP SIMULATIONS PASSED")
