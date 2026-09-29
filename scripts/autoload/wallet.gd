extends Node

## The player's coins (M05.1, D-20): one balance and the append-only ledger
## of every change to it. Coins are the future buying/selling currency
## (D-10: internal only); they are not Wriksha Points, which stay the
## score (PointsManager). How the two relate is O-02 (M05.5).
##
## The ledger is the truth: each entry is {"amount": signed whole number,
## "reason": what it was for}; the balance is always the sum of the
## entries, never below 0. Only credit() and debit() add entries; both
## refuse an amount below 1 or an empty reason, and debit() refuses more
## than the balance — a refused call changes nothing. Entries are never
## edited or removed.
##
## Nothing credits or debits coins yet: earn rules are M05.3, harvest/sell
## M06.2. Saved by SaveManager as "wallet" ({"ledger": [...]}); anything
## may read the balance or a copy of the ledger.

signal balance_changed(balance: int)

var _balance: int = 0
var _ledger: Array[Dictionary] = []

func get_balance() -> int:
	return _balance

func can_afford(amount: int) -> bool:
	return amount >= 1 and amount <= _balance

## A copy of every entry, oldest first.
func get_ledger() -> Array[Dictionary]:
	return _ledger.duplicate(true)

func credit(amount: int, reason: String) -> bool:
	if amount < 1 or reason == "":
		push_warning("Wallet: refused credit of %d ('%s')" % [amount, reason])
		return false
	_record(amount, reason)
	return true

func debit(amount: int, reason: String) -> bool:
	if amount < 1 or reason == "":
		push_warning("Wallet: refused debit of %d ('%s')" % [amount, reason])
		return false
	if amount > _balance:
		return false
	_record(-amount, reason)
	return true

## For SaveManager: the ledger (the balance is its sum).
func get_save_data() -> Dictionary:
	return {"ledger": _ledger.duplicate(true)}

## For SaveManager. Replays the saved ledger from an empty wallet, entry by
## entry; at the first entry that isn't a whole non-zero amount with a
## reason, or that would take the balance below 0, the rest is dropped with
## a warning — so the result is always a valid ledger and its sum.
func apply_save_data(data: Dictionary) -> void:
	_ledger.clear()
	_balance = 0
	var entries: Variant = data.get("ledger", [])
	if typeof(entries) != TYPE_ARRAY:
		push_warning("Wallet: saved ledger is not a list; starting empty")
		entries = []
	for entry: Variant in entries:
		var parsed := _parse_entry(entry)
		if parsed.is_empty() or _balance + int(parsed.amount) < 0:
			push_warning("Wallet: saved ledger entry %d is invalid; it and the rest are dropped" % _ledger.size())
			break
		_ledger.append(parsed)
		_balance += int(parsed.amount)
	balance_changed.emit(_balance)

func _record(amount: int, reason: String) -> void:
	_ledger.append({"amount": amount, "reason": reason})
	_balance += amount
	balance_changed.emit(_balance)

## {amount, reason} from a saved entry, or {} if it isn't one.
func _parse_entry(entry: Variant) -> Dictionary:
	if typeof(entry) != TYPE_DICTIONARY:
		return {}
	var amount: Variant = entry.get("amount")
	var reason: Variant = entry.get("reason")
	if (typeof(amount) != TYPE_INT and typeof(amount) != TYPE_FLOAT) or typeof(reason) != TYPE_STRING:
		return {}
	if float(amount) != floorf(float(amount)) or int(amount) == 0 or reason == "":
		return {}
	return {"amount": int(amount), "reason": String(reason)}
