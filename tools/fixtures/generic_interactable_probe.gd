extends Interactable

## Verification fixture only — never game content. tools/ is ignored by
## Godot (tools/.gdignore), so this is never imported, placed or loaded.
## The smallest object that is neither a discovery nor a farm plot, built
## only on the generic Interactable contract: persistent, counts its
## interactions, and can be switched off. The static checks analyse it
## like any game script (it must compile against the contract), and
## tools/sims/sim_interaction.py models the Player interacting with it.

var interaction_count: int = 0

func _ready() -> void:
	remove_on_harvest = false

func interact() -> bool:
	interaction_count += 1
	return true

func set_available(value: bool) -> void:
	monitorable = value

func get_interaction_metadata() -> Dictionary:
	return {"probe": true}
