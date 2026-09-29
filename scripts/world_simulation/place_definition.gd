extends Resource
class_name PlaceDefinition

## Data-driven definition for one named place (M03.6, A5): the landmarks and
## secret spots the Journal's "Places" list shows. Add a place by creating
## another .tres in res://data/places/ and an ExplorationLandmark with the
## same location_id in its area — no script changes. ExplorationManager
## loads them all; nothing about a specific place lives in a script.

@export var id: String = ""
@export var display_name: String = ""
## Shown instead of the name on first arrival; empty = the name.
@export var arrival_text: String = ""
## Position in the Journal's fixed "Places" list (ascending, unique).
@export var order: int = 0
## A secret location (ExplorationLandmark kind SECRET_LOCATION) rather than
## a landmark; "every secret found" counts these.
@export var secret: bool = false
## The garden's place (exactly one): reaching it is the garden being found.
@export var garden: bool = false
## A discovery near this place: reaching the place before finding it earns
## the one-time curiosity bonus. Empty = no pairing.
@export var curiosity_discovery_id: String = ""
