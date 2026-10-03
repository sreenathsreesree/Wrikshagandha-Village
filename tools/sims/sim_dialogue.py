#!/usr/bin/env python3
"""Dialogue (M08.4) — a model of the SpeechPanel's conversation, its rules read from
speech_panel.gd / npc_talk.gd and the lines from data/dialogues.
1. A conversation shows its lines in order, one per Next; Next on the last line ends it complete;
   the ✕, walking away (close_for) and parking (the speaker leaving the tree) end it early.
2. Every conversation ends exactly once (conversation_ended), complete only after the last line.
3. Re-tapping the NPC while its conversation is shown never restarts, skips or duplicates it; a
   new conversation always starts at the first line.
4. Only the Next button advances: a tap on the sheet, the world or any other HUD control never does.
5. While a conversation is open the player is inside the interaction reach, which is inside the
   NPC's notice distance — so the NPC is still and facing the player throughout.
20,000 random sessions of taps, Nexts, ✕s, walks away, house trips and re-taps; designs that
restart on a re-tap, close without announcing, announce twice, or advance on any tap are shown
to break the rules.
"""
import os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
SP, NT, NPC = _src("scripts", "ui", "speech_panel.gd"), _src("scripts", "npc", "npc_talk.gd"), _src("scripts", "npc", "npc.gd")
for rule in ("if speaker == _speaker and visible:\n\t\treturn true", "_end(false)\n\t_speaker = speaker", "_index = 0",
             "if _index >= _lines.size() - 1:\n\t\t_end(true)", "_index += 1", "conversation_ended.emit(speaker, completed)",
             "if _speaker == null:\n\t\tvisible = false\n\t\treturn", "_speaker.tree_exiting.connect(close)", "func close() -> void:\n\t_end(false)"):
    assert rule in SP, f"speech_panel.gd rule: {rule!r}"
assert "_panel.close_for(self)" in NT and "npc.definition.dialogue.lines" in NT
LINES = re.findall(r'"((?:[^"\\]|\\.)*)"', re.search(r'^lines = PackedStringArray\((.*)\)$', _src("data", "dialogues", "villager_hello.tres"), re.M).group(1))
assert len(LINES) >= 2, LINES
NOTICE = float(re.search(r"^const NOTICE_DISTANCE := ([0-9.]+)", NPC, re.M).group(1))
ZONE = float(re.search(r'id="SphereShape3D_interact"\]\nradius = ([0-9.]+)', _src("scenes", "player", "Player.tscn")).group(1))
TALK_R = float(re.search(r'id="SphereShape3D_talk"\]\nradius = ([0-9.]+)', _src("scenes", "npc", "Npc.tscn")).group(1))
assert ZONE + TALK_R < NOTICE, "an open conversation keeps the player within the NPC's notice distance"

class Panel:
    def __init__(p, design="real"):
        p.design, p.speaker, p.lines, p.index, p.visible, p.events = design, None, [], 0, False, []
    def open(p, speaker, lines):
        if speaker is None or not lines: return False
        if speaker == p.speaker and p.visible and p.design != "restart_on_retap": return True
        p._end(False)
        p.speaker, p.lines, p.index, p.visible = speaker, list(lines), 0, True
        return True
    def advance(p):
        if p.speaker is None: return
        if p.index >= len(p.lines) - 1: p._end(True); return
        p.index += 1
    def close_for(p, speaker):
        if speaker == p.speaker: p.close()
    def close(p):
        if p.design == "silent_close": p.speaker, p.visible = None, False; return
        p._end(False)
    def _end(p, completed):
        if p.speaker is None: p.visible = False; return
        speaker = p.speaker
        if p.design != "double_announce": p.speaker = None
        p.visible = False
        p.events.append((speaker, completed))
        if p.design == "double_announce": p.events.append((speaker, completed)); p.speaker = None
    def tap_elsewhere(p):                    # a sheet / world / other HUD touch
        if p.design == "any_tap_advances": p.advance()

def session(seed, design="real"):
    r = random.Random(seed); panel = Panel(design); npc = "villager"
    started, shown_seq, problems = 0, [], []
    for _ in range(r.randint(5, 60)):
        a = r.random()
        before = (panel.speaker, panel.index, panel.visible)
        if a < 0.25:                                          # tap the NPC (walk into range -> interact)
            was_open = panel.visible and panel.speaker == npc
            panel.open(npc, LINES)
            if not was_open: started += 1
            elif (panel.speaker, panel.index) != before[:2]: problems.append("re-tap changed the conversation")
        elif a < 0.6:
            if panel.visible: panel.advance()
        elif a < 0.7: panel.close()                           # the ✕
        elif a < 0.8: panel.close_for(npc)                    # walked out of range
        elif a < 0.85: panel.close()                          # house: the speaker leaves the tree
        else:
            panel.tap_elsewhere()
            if (panel.speaker, panel.index, panel.visible) != before: problems.append("a stray tap moved the conversation")
        if panel.visible:
            if not (0 <= panel.index < len(panel.lines)): problems.append("index out of range")
    panel.close()
    ends = panel.events
    if len(ends) != started: problems.append(f"{started} conversations, {len(ends)} endings")
    return problems

N = 20000
bad = [s for s in range(N) if session(s)]
assert not bad, f"{len(bad)} sessions broke a rule, e.g. {session(bad[0])}"
# completion only after the last line, in order
p = Panel(); p.open("v", LINES); seen = [p.index]
for _ in range(len(LINES) - 1): p.advance(); seen.append(p.index)
assert seen == list(range(len(LINES))) and p.visible and not p.events, "lines in order, still open on the last"
p.advance(); assert not p.visible and p.events == [("v", True)], "Goodbye on the last line ends it complete"
p.open("v", LINES); p.advance(); p.close_for("v"); assert p.events[-1] == ("v", False), "walking away ends it early"
p.open("v", LINES); p.close_for("someone else"); assert p.visible, "another speaker's request leaves it open"
p.advance(); p.open("v", LINES); assert p.index == 1, "a re-tap neither restarts nor skips"
p.close(); p.open("v", LINES); assert p.index == 0, "a new conversation starts at the first line"
for design in ("restart_on_retap", "silent_close", "double_announce", "any_tap_advances"):
    assert any(session(s, design) for s in range(2000)), f"the {design} design is shown to break a rule"
print(f"dialogue: villager_hello {len(LINES)} lines; order, Goodbye ends complete, ✕/walk-away/park end early, one ending per conversation, "
      f"re-taps neither restart nor skip, only Next advances; open conversation keeps the player within notice ({ZONE + TALK_R:.1f} < {NOTICE} m); "
      f"{N} random sessions OK; restart-on-retap, silent close, double announce and any-tap-advances shown to break")
print("ALL DIALOGUE SIMULATIONS PASSED")
