extends Resource
class_name DiscoveryDefinition

## Data-driven definition for one discoverable thing (plant, animal, insect,
## resource, secret...). Add new content by creating another .tres resource
## in res://data/discoveries/ — no gameplay code changes required.

@export var id: String = ""
@export var display_name: String = ""
@export_multiline var description: String = ""
@export_enum("plant", "animal", "insect", "resource", "secret") var category: String = "plant"
@export var points_value: int = 10
@export var harvestable: bool = true
