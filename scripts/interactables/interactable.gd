extends Area3D
class_name Interactable

## Base script for anything in the world the player can walk up to and
## interact with (plants now; animals, resources, secrets later). Placed on
## an Area3D so proximity is detected without blocking movement.

@export var discovery_id: String = ""
@export var remove_on_harvest: bool = true

func interact() -> bool:
	if discovery_id == "":
		push_warning("Interactable: no discovery_id set on %s" % name)
		return false
	var success := DiscoveryManager.discover(discovery_id)
	if success and remove_on_harvest:
		queue_free()
	return success
