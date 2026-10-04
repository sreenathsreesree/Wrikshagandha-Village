#!/usr/bin/env python3
"""Services (M08.7, D-40) — a model of the villager's stone trade, its rules read from services.gd, market.gd,
npc_talk.gd, game_state.gd, hud.gd and save_manager.gd, the service from data/services.
1. Locked until its request (villager_stones) is completed; then the NPC pitches it while the player holds fewer
   than 3 River Stones and offers the trade (last button "Sell") at 3 or more. An unfinished request always comes
   first. The choice is locked while a conversation is open.
2. Only a completed trade conversation trades — never ✕, an early end, walking away, the house or another NPC.
   Market.trade(): validate → remove exactly 3 → one credit of exactly 6 coins ("trade:<id>") → if refused, put
   the exact items back → announce (saved). Repeatable, no cap. No points, no friendship beyond D-38's ordinary
   once-a-day conversation rule, no items given, no saved service state (save v7).
3. The Basket still sells produce only: a collectible never sells there, so no other coin source appears.
20,000 random sessions (stones collected mid-conversation, re-taps, early ends, refused credits, relaunches, new
days); designs that credit before checking the items, skip the restore, drop the lock, trade on ✕, skip the
unlock, pay points or let the Basket sell collectibles are shown to break the rules.
"""
import glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
SV, MK, NT = _src("scripts", "autoload", "services.gd"), _src("scripts", "autoload", "market.gd"), _src("scripts", "npc", "npc_talk.gd")
GS, HUD, SM = _src("scripts", "autoload", "game_state.gd"), _src("scripts", "ui", "hud.gd"), _src("scripts", "autoload", "save_manager.gd")
trade_src = re.search(r"^func trade\(item_id: String, quantity: int, coins: int, service_id: String\) -> int:.*?(?=^func |\Z)", MK, re.M | re.S).group(0)
ORDER = ['if item.category != "collectible":', "if item.quality_levels != 1:", "if quantity < 1 or coins < 1:", "if not Inventory.has(item_id, quantity, 0):",
         "if not Inventory.remove(item_id, quantity, 0):", 'if not Wallet.credit(coins, "trade:%s" % service_id):', "Inventory.add(item_id, quantity, 0)",
         "items_traded.emit(item_id, quantity, coins)"]
assert all(trade_src.find(s) >= 0 for s in ORDER) and [trade_src.find(s) for s in ORDER] == sorted(trade_src.find(s) for s in ORDER), "Market.trade(): validate, remove, credit, restore, announce"
assert "PointsManager" not in trade_src and trade_src.count("Wallet.credit(") == 1, "one credit, no points"
sell_src = re.search(r"^func sell\(.*?(?=^func )", MK, re.M | re.S).group(0)
assert 'if item.category != "produce":' in sell_src, "the Basket's sell() still takes produce only"
assert "return Requests.get_state(definition.unlocked_by_request) == Requests.COMPLETED" in SV
assert "return Market.trade(definition.item_id, definition.quantity, definition.coins, definition.id)" in SV
assert not re.search(r"\bWallet\b|Inventory\.(add|remove)\(|PointsManager|Relationships", re.sub(r"(?m)^\s*##.*$", "", SV)), "Services writes no items, coins, points or friendship"
assert 'const SELL_TEXT := "Sell"' in NT and "elif service_step == Services.STEP_TRADE:\n\t\tServices.trade(service_id)" in NT
assert NT.find("if not completed:\n\t\treturn") < NT.find("Services.trade(service_id)"), "only a completed conversation trades"
assert NT.find("Requests.conversation_for(") < NT.find("Services.conversation_for("), "the request comes first"
assert "Market.items_traded.connect(_save.unbind(3))" in GS and "Market.items_traded.connect(_on_items_traded)" in HUD
assert int(re.search(r"^const SAVE_VERSION := (\d+)", SM, re.M).group(1)) == 7 and '"services"' not in SM, "no saved service state; save v7"
def _vals(f): return dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', open(f, encoding="utf-8").read(), re.M))
SVCS = {v["id"]: v for v in map(_vals, glob.glob(os.path.join(REPO, "data", "services", "*.tres")))}
assert list(SVCS) == ["villager_stone_trade"], SVCS
S = SVCS["villager_stone_trade"]; SID, ITEM, QTY, COINS, UNLOCK = S["id"], S["item_id"], int(S["quantity"]), int(S["coins"]), S["unlocked_by_request"]
assert (ITEM, QTY, COINS, UNLOCK, S["npc_id"]) == ("river_stone", 3, 6, "villager_stones", "villager")
item = _vals(os.path.join(REPO, "data", "items", f"{ITEM}.tres")); assert item["category"] == "collectible" and int(item.get("quality_levels", 1)) == 1
PRODUCE = "wild_carrot"; assert _vals(os.path.join(REPO, "data", "items", "wild_carrot.tres"))["category"] == "produce"

class World:
    def __init__(w, design="real"):
        w.design, w.request, w.stones, w.carrots, w.coins, w.points, w.ledger = design, "", 0, 0, 0, 0, []
        w.refuse_next_credit, w.friend, w.friend_days, w.today = False, 0, set(), 1
        w.request_defined = True                                                    # False: the request's data is missing / ignored
    # Wallet.credit
    def credit(w, n, reason):
        if w.refuse_next_credit: w.refuse_next_credit = False; return False
        w.coins += n; w.ledger.append((n, reason)); return True
    # Market.trade
    def trade(w, item, q, c, sid):
        if item != ITEM and w.design != "produce_trade": return 0
        if q < 1 or c < 1: return 0
        if w.design == "credit_without_items":
            if not w.credit(c, f"trade:{sid}"): return 0
            w.stones = max(0, w.stones - q); return c
        if w.stones < q: return 0
        w.stones -= q
        if not w.credit(c, f"trade:{sid}"):
            if w.design != "no_restore": w.stones += q
            return 0
        if w.design == "points_on_trade": w.points += 1
        return c
    # Market.sell at the Basket
    def basket_sell(w, item):
        if item == ITEM and w.design == "basket_sells_collectibles":
            if w.stones < 1: return 0
            w.stones -= 1; w.credit(2, "sell:river_stone:0"); return 2
        if item != PRODUCE or w.carrots < 1: return 0
        w.carrots -= 1; w.credit(5, "sell:wild_carrot:1"); return 5
    # Services
    def unlocked(w): return w.request == "completed" or w.design == "no_unlock"
    def conversation(w):
        if w.request_defined and w.request in ("", "accepted"): return ("request", w.request)   # the request first (M08.6)
        if w.unlocked(): return ("service", "trade" if w.stones >= QTY else "pitch")
        return ("usual", None)
    def friendship_on_completed(w):
        if w.today not in w.friend_days and w.friend < 10: w.friend += 1; w.friend_days.add(w.today)
    def save(w): return json.dumps({"save_version": 7, "items": {ITEM: [w.stones], PRODUCE: [w.carrots]}, "wallet": {"ledger": [list(e) for e in w.ledger]},
                                     "points": w.points, "requests": {"villager_stones": w.request} if w.request else {}})
    @staticmethod
    def load(text, design="real"):
        d = json.loads(text); w = World(design)
        w.stones, w.carrots = d["items"][ITEM][0], d["items"][PRODUCE][0]
        w.ledger = [tuple(e) for e in d["wallet"]["ledger"]]; w.coins = sum(e[0] for e in w.ledger)
        w.points, w.request = d["points"], d["requests"].get("villager_stones", "")
        return w

class Talk:
    def __init__(t, w, design="real"): t.w, t.design, t.kind, t.step, t.label, t.visible = w, design, None, None, None, False
    def tap(t):
        if t.visible and t.design != "no_lock": return
        kind, step = t.w.conversation()
        t.kind, t.step = kind, step
        if not t.visible: t.label = "Sell" if (kind, step) == ("service", "trade") else "Goodbye"; t.visible = True
    def end(t, completed, other_npc=False):
        if not t.visible: return None
        kind, step, label = t.kind, t.step, t.label; t.visible, t.kind, t.step = False, None, None
        if other_npc: return None                                                   # another speaker's conversation: not ours
        if not completed and t.design != "trade_on_any_end": return None
        if completed: t.w.friendship_on_completed()
        if kind == "service" and step == "trade":
            paid = t.w.trade(ITEM, QTY, COINS, SID) if t.w.unlocked() else 0
            if paid and label != "Sell": return "traded without Sell shown"
        return None

# ---------------------------------------------------------------- scripted checks
w = World(); t = Talk(w)
w.stones = 5; t.tap(); assert t.kind == "request", "before villager_stones is completed: no service, the request first"; t.end(False)
w.request = "accepted"; t.tap(); assert t.kind == "request"; t.end(False)
w.request = "completed"
for n in (0, 1, 2):
    w.stones = n; t.tap(); assert (t.kind, t.step, t.label) == ("service", "pitch", "Goodbye"), n; t.end(True); assert w.coins == 0 and w.stones == n
w.stones = 3; t.tap(); assert (t.step, t.label) == ("trade", "Sell")
t.end(False); assert (w.stones, w.coins) == (3, 0), "✕ / early end / walking away / the house: nothing traded"
t.tap(); t.end(True, other_npc=True); assert (w.stones, w.coins) == (3, 0), "another NPC's conversation trades nothing"
t.tap(); t.end(True); assert (w.stones, w.coins, w.ledger[-1]) == (0, COINS, (COINS, f"trade:{SID}")), "Sell: exactly 3 removed, exactly 6 coins, one entry"
w.stones = 7; t.tap(); t.end(True); t.tap(); t.end(True); assert (w.stones, w.coins) == (1, 3 * COINS), "repeatable, no cap"
assert w.points == 0, "a trade pays no points"
w.stones = 3; w.refuse_next_credit = True; t.tap(); t.end(True); assert (w.stones, w.coins) == (3, 3 * COINS), "a refused credit puts the exact items back"
w.carrots = 1; assert w.basket_sell(ITEM) == 0 and w.basket_sell(PRODUCE) == 5, "the Basket sells produce, never a collectible"
r = World.load(w.save()); assert (r.stones, r.coins, r.request) == (w.stones, w.coins, "completed"), "items and coins survive a relaunch; nothing else saved"
fr = World(); fr.request = "completed"; ft = Talk(fr); fr.stones = 6; ft.tap(); ft.end(True); ft.tap(); ft.end(True)
assert fr.friend == 1, "two trades the same day: friendship +1 once (D-38), no extra reward"

# ---------------------------------------------------------------- random sessions
def session(seed, design="real"):
    rnd = random.Random(seed); w = World(design if design not in ("no_lock", "trade_on_any_end") else "real")
    t = Talk(w, design if design in ("no_lock", "trade_on_any_end") else "real"); problems = []; disk = None
    for _ in range(rnd.randint(5, 80)):
        a = rnd.random(); before = (w.stones, w.coins, w.points, w.request, w.friend); kind_open = (t.kind, t.step, t.visible); action = "other"
        if a < 0.2: t.tap()
        elif a < 0.36:
            action = "end_completed"; p = t.end(True)
            if p: problems.append(p)
        elif a < 0.46: t.end(False)                                                 # ✕ / early end / walking away / the house
        elif a < 0.5: t.end(True, other_npc=True)
        elif a < 0.64: w.stones += 1                                                # a stone collected, even mid-conversation
        elif a < 0.68: w.carrots += 1
        elif a < 0.72: action = "basket"; w.basket_sell(rnd.choice([ITEM, PRODUCE]))
        elif a < 0.76: w.refuse_next_credit = True
        elif a < 0.8 and w.request != "completed": w.request = {"": "accepted", "accepted": "completed"}[w.request]
        elif a < 0.86: disk = w.save()
        elif a < 0.9 and disk: t.end(False); w = World.load(disk, w.design); t.w = w; continue
        elif a < 0.94: w.today += 1
        dc, ds = w.coins - before[1], w.stones - before[0]
        if w.points != before[2]: problems.append("points moved")
        if dc not in (0, COINS) and not (action == "basket" and dc == 5): problems.append(f"an unexpected coin change {dc}")
        if dc == COINS:
            if action != "end_completed" or kind_open[:2] != ("service", "trade") or before[3] != "completed": problems.append("coins without a completed, unlocked trade conversation")
            if ds != -QTY: problems.append("coins without exactly the items")
        if dc == 0 and ds < 0 and action != "basket": problems.append("items lost without coins")
        if action == "basket" and dc > 0 and ds < 0: problems.append("the Basket sold a collectible")
        if w.friend - before[4] > 1 or len(w.friend_days) < w.friend: problems.append("friendship beyond once a day")
    return problems

N = 20000
bad = [s for s in range(N) if session(s)]
assert not bad, f"{len(bad)} sessions broke a rule, e.g. {session(bad[0])}"
for design in ("no_restore", "no_lock", "trade_on_any_end", "points_on_trade", "basket_sells_collectibles"):
    assert any(session(s, design) for s in range(4000)), f"the {design} design is shown to break a rule"
# no_unlock: the request normally hides the service until it is completed, so the unlock check is what still holds if
# the request is missing — shown directly: the real design keeps the service locked, the broken one opens it
lk = World(); lk.request_defined = False; lk.stones = 3; assert lk.conversation() == ("usual", None), "no completed request, no service — even with the request missing"
nu = World("no_unlock"); nu.request_defined = False; nu.stones = 3; assert nu.conversation() == ("service", "trade"), "skipping the unlock check opens the trade without the request"
cw = World("credit_without_items"); cw.request = "completed"; assert cw.trade(ITEM, QTY, COINS, SID) == COINS and cw.stones == 0, "crediting before checking pays without the items"
print(f"services: {SID} (villager buys {QTY} × {ITEM} for {COINS} coins once {UNLOCK} is completed); request first, pitch below {QTY}, trade (Sell) at {QTY}+; "
      f"only a completed trade conversation trades: exactly {QTY} removed, exactly {COINS} coins, refused credit restores; repeatable, no points, "
      f"friendship only D-38's once a day; the Basket still sells produce only; {N} random sessions OK; credit-without-items, no-restore, no-lock, "
      f"trade-on-any-end, no-unlock, points-on-trade and basket-sells-collectibles shown to break")
print("ALL SERVICE SIMULATIONS PASSED")
