#!/usr/bin/env python3
"""Model checks for the Wallet + ledger (M05.1, D-20) — a Python port of
scripts/autoload/wallet.gd and its save path, not the engine.
1. Read from the project: the Wallet's rule lines, SaveManager's wallet
   section and 3 -> 4 step, the autoload order.
2. Port: credit / debit / can_afford / get_ledger / save / load (Godot's
   JSON: every number a float).
3. Cases: a new wallet is empty (0, no entries); valid credits and debits;
   an insufficient debit, zero/negative amounts and an empty reason are
   refused and change nothing; repeated transactions; the balance always
   equals the sum of the ledger and is never negative; ledger order is call
   order; save -> load -> save is identical (relaunch); a malformed saved
   ledger keeps exactly its valid prefix; an M04 (v3) save has no wallet and
   loads an empty one, its items untouched; 5,000 random sequences against
   a reference, deterministic.
"""
import copy, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _funcs(src): return {m.group(1): m.group(0) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", src, re.M | re.S)}

# ---------------------------------------------------------------- 1. read from the project
WL, SMS, CFG = _funcs(_src("scripts", "autoload", "wallet.gd")), _src("scripts", "autoload", "save_manager.gd"), _src("project.godot")
assert 'if amount < 1 or reason == "":' in WL["credit"] and "_record(amount, reason)" in WL["credit"]
assert 'if amount < 1 or reason == "":' in WL["debit"] and "if amount > _balance:" in WL["debit"] and "_record(-amount, reason)" in WL["debit"]
assert '_ledger.append({"amount": amount, "reason": reason})' in WL["_record"] and "_balance += amount" in WL["_record"]
assert "if parsed.is_empty() or _balance + int(parsed.amount) < 0:" in WL["apply_save_data"] and "break" in WL["apply_save_data"]
assert "int(amount) == 0" in WL["_parse_entry"] and "typeof(reason) != TYPE_STRING" in WL["_parse_entry"]
assert '"wallet": Wallet.get_save_data(),' in SMS and 'Wallet.apply_save_data(data.get("wallet", {}))' in SMS
assert int(re.search(r"^const SAVE_VERSION := (\d+)", SMS, re.M).group(1)) >= 4 and re.search(r"^\t\t\t3:\s*pass", SMS, re.M)
al = re.findall(r'^(\w+)="\*?res://', CFG.split("[autoload]", 1)[1].split("\n[", 1)[0], re.M)
assert al.index("Wallet") < al.index("SaveManager") < al.index("GameState"), "the Wallet exists before the save is loaded"

# ---------------------------------------------------------------- 2. port
def is_num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
class Wallet:
    def __init__(w): w.balance, w.ledger, w.warnings, w.emits = 0, [], 0, 0
    def can_afford(w, n): return n >= 1 and n <= w.balance
    def get_ledger(w): return copy.deepcopy(w.ledger)
    def _record(w, n, reason): w.ledger.append({"amount": n, "reason": reason}); w.balance += n; w.emits += 1
    def credit(w, n, reason):
        if n < 1 or reason == "": w.warnings += 1; return False
        w._record(n, reason); return True
    def debit(w, n, reason):
        if n < 1 or reason == "": w.warnings += 1; return False
        if n > w.balance: return False
        w._record(-n, reason); return True
    def get_save_data(w): return {"ledger": copy.deepcopy(w.ledger)}
    @staticmethod
    def _parse(e):
        if not isinstance(e, dict): return {}
        a, r = e.get("amount"), e.get("reason")
        if not is_num(a) or not isinstance(r, str): return {}
        if float(a) != int(a) or int(a) == 0 or r == "": return {}
        return {"amount": int(a), "reason": r}
    def apply_save_data(w, data):
        w.ledger, w.balance = [], 0
        entries = data.get("ledger", [])
        if not isinstance(entries, list): w.warnings += 1; entries = []
        for e in entries:
            p = w._parse(e)
            if not p or w.balance + p["amount"] < 0: w.warnings += 1; break
            w.ledger.append(p); w.balance += p["amount"]
        w.emits += 1
def godot_json(text):
    def conv(x):
        if isinstance(x, bool): return x
        if isinstance(x, int): return float(x)
        if isinstance(x, list): return [conv(v) for v in x]
        if isinstance(x, dict): return {k: conv(v) for k, v in x.items()}
        return x
    return conv(json.loads(text))
def relaunch(w):  # save_game -> JSON -> load_game into a fresh Wallet
    fresh = Wallet(); fresh.apply_save_data(godot_json(json.dumps(w.get_save_data()))); return fresh
def invariant(w):
    assert w.balance == sum(e["amount"] for e in w.ledger) >= 0, "balance = sum of the ledger, never negative"
    run = 0
    for e in w.ledger:
        run += e["amount"]; assert run >= 0 and e["amount"] != 0 and e["reason"], "every prefix valid"

# ---------------------------------------------------------------- 3. cases
w = Wallet(); assert w.balance == 0 and w.get_ledger() == [] and not w.can_afford(1), "a new wallet is empty"
assert w.credit(100, "test") and w.balance == 100 and w.debit(30, "test") and w.balance == 70
assert not w.debit(71, "test") and w.balance == 70 and len(w.ledger) == 2, "insufficient debit refused, nothing recorded"
assert w.debit(70, "test") and w.balance == 0 and not w.debit(1, "test"), "exactly the balance can be spent; then nothing"
for n in (0, -1, -100):
    assert not w.credit(n, "x") and not w.debit(n, "x") and not w.can_afford(n), n
assert not w.credit(5, "") and not w.debit(0, "") and w.balance == 0 and len(w.ledger) == 3, "refused calls leave no entry"
assert [e["amount"] for e in w.ledger] == [100, -30, -70], "ledger order is call order, signed amounts"
led = w.get_ledger(); led.append({"amount": 999, "reason": "hack"}); led[0]["amount"] = 1
assert w.balance == 0 and w.ledger[0]["amount"] == 100 and len(w.ledger) == 3, "get_ledger() is a copy"
w2 = Wallet()
for i in range(1000): assert w2.credit(1, "tick")
for i in range(1000): assert w2.debit(1, "tock")
assert w2.balance == 0 and len(w2.ledger) == 2000 and not w2.debit(1, "tock"), "repeated transactions"
# relaunch: save -> load -> save identical
w3 = Wallet(); w3.credit(40, "a"); w3.debit(15, "b"); w3.credit(7, "c")
r = relaunch(w3); assert r.balance == 32 and r.ledger == w3.ledger and r.get_save_data() == w3.get_save_data()
assert relaunch(r).get_save_data() == r.get_save_data(), "stable across relaunches"
# malformed saved ledgers: exactly the valid prefix survives, with a warning
good = [{"amount": 10.0, "reason": "a"}, {"amount": -4.0, "reason": "b"}]
for bad in ({"amount": 1.5, "reason": "x"}, {"amount": 0.0, "reason": "x"}, {"amount": 3.0, "reason": ""}, {"amount": "3", "reason": "x"},
            {"amount": 3.0}, {"reason": "x"}, [3, "x"], None, {"amount": -7.0, "reason": "overdraw"}, {"amount": True, "reason": "x"}):
    z = Wallet(); z.apply_save_data({"ledger": good + [bad, {"amount": 100.0, "reason": "after"}]})
    assert z.balance == 6 and len(z.ledger) == 2 and z.warnings == 1, bad
for bad_ledger in ("x", 5, {"a": 1}, None):
    z = Wallet(); z.apply_save_data({"ledger": bad_ledger}); assert z.balance == 0 and z.ledger == [] and z.warnings == 1
z = Wallet(); z.apply_save_data({}); assert z.balance == 0 and z.ledger == [] and z.warnings == 0, "an absent wallet (an M04 save) is empty"
# an M04 (v3) save: no wallet section -> empty wallet; its other sections are SaveManager's business, untouched by the 3 -> 4 step
v3 = {"save_version": 3, "points": 57, "items": {"wild_carrot_seed": [2]}, "farm": {"starter_seeds": ["wild_carrot"]}}
migrated = copy.deepcopy(v3); migrated["save_version"] = 4               # step 3 -> 4: pass
assert {k: v for k, v in migrated.items() if k != "save_version"} == {k: v for k, v in v3.items() if k != "save_version"}
z = Wallet(); z.apply_save_data(migrated.get("wallet", {})); assert z.balance == 0 and z.ledger == []
# random sequences vs a reference; determinism; relaunch at random points
rnd = random.Random(51); ops = 0
for _ in range(5000):
    a, b, ref = Wallet(), Wallet(), []
    for _ in range(rnd.randint(1, 30)):
        kind, n, reason = rnd.choice(["credit", "debit", "debit"]), rnd.choice([-3, 0, 1, 2, 5, 10, 50]), rnd.choice(["r", "q", ""])
        bal = sum(ref)
        ok = n >= 1 and reason != "" and (kind == "credit" or n <= bal)
        before = a.emits
        assert getattr(a, kind)(n, reason) == ok == getattr(b, kind)(n, reason)
        assert a.emits == before + ok, "balance_changed exactly once per recorded change, never for a refusal"
        if ok: ref.append(n if kind == "credit" else -n)
        invariant(a); ops += 1
        assert [e["amount"] for e in a.ledger] == ref and a.balance == sum(ref) and a.ledger == b.ledger, "matches the reference, deterministic"
        if rnd.random() < 0.1: a = relaunch(a); b = relaunch(b)
print(f"wallet: empty start; credit/debit/refusals; repeated; ledger order; relaunch stable; malformed ledgers keep their valid prefix; "
      f"v3 save -> empty wallet; 5000 random sequences ({ops} ops) = reference, deterministic")
print("ALL WALLET SIMULATIONS PASSED")
