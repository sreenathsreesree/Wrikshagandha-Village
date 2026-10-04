#!/usr/bin/env python3
"""Requests (M08.6, D-39) — a model of one NPC request, its rules read from requests.gd, npc_talk.gd,
speech_panel.gd, save_manager.gd and game_state.gd, the request from data/requests.
1. The NPC chooses a whole conversation: not offered → the offer; accepted without the items → the pending
   reminder; accepted with them → the hand-over (last button "Give"); completed → its usual dialogue. The
   choice is locked while that conversation is open (re-taps never choose again).
2. Only a completed offer accepts; only a completed hand-over completes — never an early end (✕, walking
   away, the house). Completing is checked, recorded, then paid: the items are removed (all or nothing),
   the request recorded completed, reward_points paid exactly once; never twice, never without the items.
3. Save v7: the requests section survives save -> JSON -> load; a v6 save loads with no request offered and
   every other section untouched; unknown request ids are dropped; a malformed state for a known request
   counts as completed (its reward can never be paid twice); invalid request data is ignored.
20,000 random sessions (stones collected even mid-conversation, re-taps, early ends, relaunches); designs that
pay before checking the items, accept on any end, read a malformed state as not offered, or re-choose the
conversation on a re-tap are shown to break the rules.
"""
import glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
RQ, NT, SP = _src("scripts", "autoload", "requests.gd"), _src("scripts", "npc", "npc_talk.gd"), _src("scripts", "ui", "speech_panel.gd")
SM, GS = _src("scripts", "autoload", "save_manager.gd"), _src("scripts", "autoload", "game_state.gd")
COMPLETE_ORDER = ['if definition == null or _states.get(request_id, "") != ACCEPTED:', "if not Inventory.has(definition.item_id, definition.quantity, 0):",
                  "if not Inventory.remove(definition.item_id, definition.quantity, 0):", "_states[request_id] = COMPLETED",
                  "PointsManager.add_points(definition.reward_points)", "request_completed.emit("]
body = re.search(r"^func complete\(.*?(?=^func )", RQ, re.M | re.S).group(0)
assert [body.find(s) for s in COMPLETE_ORDER] == sorted(body.find(s) for s in COMPLETE_ORDER) and all(body.find(s) >= 0 for s in COMPLETE_ORDER), "complete(): checked, recorded, then paid"
for rule in ("if not _definitions.has(request_id) or _states.has(request_id):\n\t\treturn false", "_states[request_id] = COMPLETED\n",
             'push_warning("Requests: saved state for \'%s\' is malformed; counts as completed" % request_id)', "item.quality_levels != 1"):
    assert rule in RQ, f"requests.gd rule: {rule!r}"
assert "if _panel.get_speaker() == self and _panel.visible:\n\t\treturn true\n\tvar npc := get_parent() as Npc\n\tvar request := Requests.conversation_for(" in NT, "the choice is locked"
assert 0 <= NT.find("Requests.conversation_for(") < NT.find("Services.conversation_for(") and NT.find("if not request.is_empty():") < NT.find("Services.conversation_for("), \
    "an unfinished request comes before the service (M08.7)"
assert "if not completed:\n\t\treturn\n\tif step == Requests.STEP_OFFER:\n\t\tRequests.accept(request_id)\n\telif step == Requests.STEP_HANDOVER:\n\t\tRequests.complete(request_id)" in NT
assert 'const GIVE_TEXT := "Give"' in NT and "_end_text = end_text" in SP and "next_button.text = _end_text if _index >= _lines.size() - 1 else NEXT_TEXT" in SP
SAVE_VERSION = int(re.search(r"^const SAVE_VERSION := (\d+)", SM, re.M).group(1))
assert SAVE_VERSION == 7 and re.search(r"^\t\t\t6:\s*pass", SM, re.M) and '"requests": Requests.get_save_data(),' in SM
assert "Requests.request_accepted.connect(_save.unbind(1))" in GS and "Requests.request_completed.connect(_save.unbind(4))" in GS
def _vals(f): return dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', open(f, encoding="utf-8").read(), re.M))
REQS = {v["id"]: v for v in map(_vals, glob.glob(os.path.join(REPO, "data", "requests", "*.tres")))}
assert list(REQS) == ["villager_stones"], REQS
R = REQS["villager_stones"]; RID, NPC, ITEM, QTY, PTS = R["id"], R["npc_id"], R["item_id"], int(R["quantity"]), int(R["reward_points"])
item = _vals(os.path.join(REPO, "data", "items", f"{ITEM}.tres")); assert int(item.get("quality_levels", 1)) == 1 and item["category"] == "collectible"
assert (NPC, ITEM, QTY, PTS) == ("villager", "river_stone", 2, 20)

class Requests:
    def __init__(r, design="real"): r.design, r.states, r.points, r.inv, r.events = design, {}, 0, {ITEM: 0}, []
    def conversation_for(r, npc):
        if npc != NPC: return None
        s = r.states.get(RID, "")
        if s == "": return "offer"
        if s == "accepted": return "handover" if r.inv[ITEM] >= QTY else "pending"
        return None                                                    # completed → the usual dialogue
    def accept(r):
        if RID in r.states: return False
        r.states[RID] = "accepted"; r.events.append("accepted"); return True
    def complete(r):
        if r.states.get(RID) != "accepted": return False
        if r.design == "pay_before_check":
            r.points += PTS; r.states[RID] = "completed"
            if r.inv[ITEM] >= QTY: r.inv[ITEM] -= QTY
            r.events.append("completed"); return True
        if r.inv[ITEM] < QTY: return False
        r.inv[ITEM] -= QTY; r.states[RID] = "completed"; r.points += PTS; r.events.append("completed"); return True
    def save(r): return json.dumps({"save_version": SAVE_VERSION, "points": r.points, "items": {ITEM: [r.inv[ITEM]]}, "requests": dict(r.states)})
    @staticmethod
    def load(text, design="real"):
        data = json.loads(text); r = Requests(design)
        if data.get("save_version", 0) < 7: data["save_version"] = 7      # step 6 -> 7: nothing to rewrite
        r.points = int(data.get("points", 0)); r.inv[ITEM] = int((data.get("items", {}).get(ITEM) or [0])[0])
        rq = data.get("requests", {}); rq = rq if isinstance(rq, dict) else {}
        for k, v in rq.items():
            if k != RID: continue                                          # unknown id: dropped
            if isinstance(v, str) and v in ("accepted", "completed"): r.states[k] = v
            else: r.states[k] = "" if r.design == "malformed_as_offered" else "completed"
            if r.states[k] == "": del r.states[k]
        return r

class Talk:
    """NpcTalk + the SpeechPanel: one open conversation, its step and its last button."""
    def __init__(t, req, design="real"): t.req, t.design, t.open_step, t.end_text, t.visible = req, design, None, None, False
    def tap_npc(t):
        if t.visible and t.design != "no_lock": return                   # locked: the open conversation stays as chosen
        step = t.req.conversation_for(NPC)
        t.open_step = step
        if not t.visible: t.end_text = "Give" if step == "handover" else "Goodbye"; t.visible = True
    def end(t, completed):
        if not t.visible: return None
        step, t.open_step, t.visible = t.open_step, None, False
        if not completed and t.design != "accept_on_any_end": return None
        shown_give = t.end_text == "Give"
        if step == "offer": t.req.accept()
        elif step == "handover":
            if t.req.complete() and not shown_give: return "completed without Give"
        return None

# ---------------------------------------------------------------- scripted checks
q = Requests(); t = Talk(q)
assert q.conversation_for(NPC) == "offer" and q.conversation_for("someone_else") is None
t.tap_npc(); t.end(False); assert q.states == {} and q.conversation_for(NPC) == "offer", "an early end of the offer accepts nothing"
t.tap_npc(); t.end(True); assert q.states == {RID: "accepted"} and q.events == ["accepted"], "a completed offer accepts (saved: request_accepted)"
assert q.conversation_for(NPC) == "pending"; q.inv[ITEM] = QTY - 1; assert q.conversation_for(NPC) == "pending", "too few: still pending"
t.tap_npc(); t.end(True); assert q.states[RID] == "accepted" and q.inv[ITEM] == QTY - 1 and q.points == 0, "completing the reminder changes nothing"
q.inv[ITEM] = QTY + 1; assert q.conversation_for(NPC) == "handover"
t.tap_npc(); assert t.end_text == "Give"; t.end(False); assert q.inv[ITEM] == QTY + 1 and q.points == 0, "✕ on the hand-over keeps the items"
t.tap_npc(); t.end(True); assert (q.states[RID], q.inv[ITEM], q.points) == ("completed", 1, PTS), "Give: exactly the items removed, the reward once"
assert q.complete() is False and q.points == PTS and q.inv[ITEM] == 1, "never completed twice"
assert q.conversation_for(NPC) is None, "completed: the NPC's usual dialogue again"
assert Requests().complete() is False and Requests().accept() and True, "only an accepted request completes"
w = Requests(); w.accept(); w.inv[ITEM] = QTY - 1; assert w.complete() is False and w.points == 0 and w.inv[ITEM] == QTY - 1, "never without the items"
# save / load / migration / malformed
h = Requests.load(q.save()); assert (h.states, h.points, h.inv[ITEM]) == (q.states, PTS, 1) and h.complete() is False, "reload keeps it completed — no second reward"
a = Requests(); a.accept(); assert Requests.load(a.save()).conversation_for(NPC) == "pending", "an accepted request survives a relaunch"
v6 = json.dumps({"save_version": 6, "points": 33, "items": {ITEM: [5]}, "relationships": {"villager": {"friendship": 2, "last_gain_date": ""}}})
o = Requests.load(v6); assert o.states == {} and o.points == 33 and o.inv[ITEM] == 5 and o.conversation_for(NPC) == "offer", "v6 -> v7: no request offered, the rest untouched"
for bad in (3, None, "done", ["accepted"], {"s": 1}, True):
    m = Requests.load(json.dumps({"save_version": 7, "requests": {RID: bad}, "items": {ITEM: [9]}}))
    assert m.states == {RID: "completed"} and m.complete() is False and m.points == 0, f"malformed {bad!r} counts as completed"
m = Requests.load(json.dumps({"save_version": 7, "requests": {"ghost": "accepted", RID: "accepted"}})); assert m.states == {RID: "accepted"}, "unknown ids dropped"
for sec in ([], "x", 5): assert Requests.load(json.dumps({"save_version": 7, "requests": sec})).states == {}, "a wrongly typed section is no requests"

# ---------------------------------------------------------------- random sessions
def session(seed, design="real"):
    rnd = random.Random(seed); req = Requests(design if design in ("pay_before_check", "malformed_as_offered") else "real")
    talk = Talk(req, design if design in ("no_lock", "accept_on_any_end") else "real"); problems = []; disk = None
    for _ in range(rnd.randint(5, 70)):
        a = rnd.random(); before = (dict(req.states), req.points, req.inv[ITEM]); relaunched = False; action = "other"
        if a < 0.25: talk.tap_npc()
        elif a < 0.45:
            action = "end_completed"
            p = talk.end(True)
            if p: problems.append(p)
        elif a < 0.6: talk.end(False)                                          # ✕ / walk away / house
        elif a < 0.75: req.inv[ITEM] += 1                                      # a stone collected — even mid-conversation
        elif a < 0.88: disk = req.save()
        elif a < 0.94 and disk:
            if design == "malformed_as_offered" and rnd.random() < 0.3:
                d = json.loads(disk); d["requests"] = {RID: 7}; disk = json.dumps(d)
            talk.end(False); req = Requests.load(disk, req.design); talk.req = req; relaunched = True
        if relaunched: continue                                               # the save's state, by design
        if req.states.get(RID) != before[0].get(RID) and action != "end_completed":
            problems.append("accepted or completed without a completed conversation")
        if req.points - before[1] not in (0, PTS): problems.append("a payment other than the reward")
        if req.points > before[1] and (before[0].get(RID) != "accepted" or before[2] < QTY or req.inv[ITEM] != before[2] - QTY):
            problems.append("paid without exactly the items")
        if req.points > PTS: problems.append("completed or paid twice")
        if req.inv[ITEM] < 0: problems.append("negative items")
    return problems

N = 20000
bad = [s for s in range(N) if session(s)]
assert not bad, f"{len(bad)} sessions broke a rule, e.g. {session(bad[0])}"
for design in ("accept_on_any_end", "no_lock"):
    assert any(session(s, design) for s in range(4000)), f"the {design} design is shown to break a rule"
# pay_before_check: nothing else removes the stones in play, so it is shown directly — too few items, still paid
pb = Requests("pay_before_check"); pb.accept(); pb.inv[ITEM] = QTY - 1; pb.complete()
assert pb.points == PTS and pb.inv[ITEM] == QTY - 1, "paying before checking the items pays without them"
# malformed_as_offered: a completed request read back as never offered pays again
mo = Requests("malformed_as_offered"); mo.accept(); mo.inv[ITEM] = 2 * QTY; mo.complete()
d = json.loads(mo.save()); d["requests"] = {RID: 7}; again = Requests.load(json.dumps(d), "malformed_as_offered"); again.accept(); again.complete()
assert again.points == 2 * PTS, "reading a malformed state as 'not offered' pays the reward twice"
any_end = Requests(); te = Talk(any_end, "accept_on_any_end"); te.tap_npc(); te.end(False)
assert any_end.states.get(RID) == "accepted", "accepting on any end accepts on ✕"
print(f"requests: {RID} ({NPC} asks for {QTY} × {ITEM}, {PTS} points); offer → accept, pending, hand-over with Give → complete "
      f"(checked, recorded, paid once); early ends accept/complete nothing; the choice locked while open; save v{SAVE_VERSION} round trip, "
      f"v6 migration, unknown ids dropped, malformed = completed; {N} random sessions OK; pay-before-check, accept-on-any-end, "
      f"no-lock and malformed-as-offered shown to break")
print("ALL REQUEST SIMULATIONS PASSED")
