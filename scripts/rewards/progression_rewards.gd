extends RefCounted
class_name ProgressionRewards

## The one path of every once-ever progression reward (M13.1): the farm
## milestones (FarmManager._reach) and the once-ever exploration rewards — a
## landmark reached, a secret place found, the curiosity bonus and "every
## secret found" (ExplorationManager). Each system keeps its own record, a
## list it already saves in its own save section, and hands it here: the id
## is checked against it and recorded in it, then the reward the reward data
## names is paid. So "paid once ever" is decided in one place; the caller
## announces afterwards with its own signal, keeping the order every save
## relies on (record, pay, then announce). Session and repeatable rewards —
## D-21's discovery counts, a discovery's own points, the daily bonus,
## harvests, requests — are not progression and never come here. How
## progression is finally structured (O-04, M13.2) is still open.

## Records `id` in `record` and pays the points of the reward rule `rule_id`.
## An empty `rule_id` means the reward pays nothing (a farm milestone the
## reward data doesn't name); an unknown one pays 0 with RewardRules' own
## warning, as the exploration rewards always did. Returns the points paid,
## or -1 when `id` was already in `record` — then nothing is recorded or paid.
static func reach(record: Array[String], id: String, rewards: RewardRules, rule_id: String) -> int:
	if record.has(id):
		return -1
	record.append(id)
	var points := rewards.points(rule_id) if rule_id != "" else 0
	if points > 0:
		PointsManager.add_points(points)
	return points
