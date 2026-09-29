extends RefCounted
class_name RewardRules

## The reward table (M05.3): every RewardRule in res://data/rewards/, looked
## up by id. A plain class, not an autoload — each system that pays a
## reward builds one in its _ready() and asks it for amounts. It decides
## nothing about *when* a reward pays; the systems' own guards do.

const REWARDS_PATH := "res://data/rewards/"

var _rules: Dictionary = {}

func _init() -> void:
	for path in ResourceDirectory.list_tres_paths(REWARDS_PATH):
		var rule := load(path) as RewardRule
		if rule == null or rule.id == "" or rule.points < 0 or rule.threshold < 0 or _rules.has(rule.id):
			push_warning("RewardRules: %s is not a usable RewardRule" % path)
			continue
		_rules[rule.id] = rule

## The points a reward pays; 0 (with a warning) for an unknown id.
func points(rule_id: String) -> int:
	var rule: RewardRule = _rules.get(rule_id)
	if rule == null:
		push_warning("RewardRules: no reward '%s'" % rule_id)
		return 0
	return rule.points

## {threshold: points} for every threshold reward.
func thresholds() -> Dictionary:
	var result := {}
	for rule_id: String in _rules:
		var rule: RewardRule = _rules[rule_id]
		if rule.threshold > 0:
			result[rule.threshold] = rule.points
	return result
