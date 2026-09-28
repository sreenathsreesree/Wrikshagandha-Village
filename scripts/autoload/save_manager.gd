extends Node

## Local save/load only. Reads and writes a single JSON file under the
## platform-specific user:// directory (app-private storage on Android).
## Every field is read with a default, so a save written before Journal /
## Daily Discovery existed still loads cleanly.

const SAVE_PATH := "user://save.json"

func save_game() -> void:
	var data := {
		"points": PointsManager.get_points(),
		"discovered_ids": DiscoveryManager.get_discovered_ids(),
		"journal_entries": JournalManager.get_save_data(),
		"daily_discovery": DailyDiscoveryManager.get_save_data(),
	}
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		push_warning("SaveManager: failed to open save file for writing")
		return
	file.store_string(JSON.stringify(data))
	file.close()

func load_game() -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		return false
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		push_warning("SaveManager: failed to open save file for reading")
		return false
	var text := file.get_as_text()
	file.close()
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("SaveManager: save file corrupted, ignoring")
		return false
	PointsManager.set_points(int(parsed.get("points", 0)))
	DiscoveryManager.set_discovered_ids(parsed.get("discovered_ids", []))
	JournalManager.apply_save_data(parsed.get("journal_entries", {}))
	DailyDiscoveryManager.apply_save_data(parsed.get("daily_discovery", {}))
	return true

func has_save_file() -> bool:
	return FileAccess.file_exists(SAVE_PATH)
