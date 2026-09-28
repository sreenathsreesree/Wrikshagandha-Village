extends Node

## Read-only aggregation layer on top of DiscoveryDatabase + DiscoveryManager
## for the Collection screen. Holds no state of its own — it exists so UI
## code never has to know how discovery data is stored or grouped.

const CATEGORY_ORDER := ["plant", "flower", "fungus", "mineral", "insect", "animal", "mystery"]

const CATEGORY_LABELS := {
	"plant": "🌿 Plants",
	"flower": "🌸 Flowers",
	"fungus": "🍄 Fungi",
	"mineral": "🪨 Minerals",
	"insect": "🐝 Insects",
	"animal": "🐾 Animals",
	"mystery": "✨ Mysteries",
}

func get_category_label(category: String) -> String:
	return CATEGORY_LABELS.get(category, category.capitalize())

func get_entries_for_category(category: String) -> Array:
	var entries: Array = []
	for definition in DiscoveryDatabase.get_all_definitions():
		if definition.category == category:
			entries.append(definition)
	return entries

func get_category_progress(category: String) -> Dictionary:
	var entries := get_entries_for_category(category)
	var found := 0
	for definition in entries:
		if DiscoveryManager.is_discovered(definition.id):
			found += 1
	return {"found": found, "total": entries.size()}

## One row per category in a fixed, readable order — even categories with
## zero entries so far still show up as "0/0", making room for future
## content without any UI changes.
func get_all_category_progress() -> Array:
	var rows: Array = []
	for category in CATEGORY_ORDER:
		var progress := get_category_progress(category)
		rows.append({
			"category": category,
			"label": get_category_label(category),
			"found": progress.found,
			"total": progress.total,
		})
	return rows
