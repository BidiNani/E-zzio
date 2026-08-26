class_name MissionRegistry
extends RefCounted

## MissionRegistry - Automatically discovers, validates and registers all available missions

const ContentValidatorScript = preload("res://src/loaders/content_validator.gd")

static func get_available_missions(base_dir: String = "res://data/missions") -> Array:
	var missions: Array = []
	var dir = DirAccess.open(base_dir)
	if not dir:
		return missions

	dir.list_dir_begin()
	var folder_name = dir.get_next()
	while folder_name != "":
		if dir.current_is_dir() and not folder_name.begins_with("."):
			var mis_dir = base_dir.path_join(folder_name)
			var mis_info = inspect_mission(mis_dir)
			if mis_info.get("valid", false):
				missions.append(mis_info)
		folder_name = dir.get_next()
	dir.list_dir_end()

	# Deterministic sorting by mission ID
	missions.sort_custom(func(a, b): return a["id"] < b["id"])
	return missions

static func inspect_mission(mis_dir: String) -> Dictionary:
	var map_path = mis_dir.path_join("map.json")
	var mission_path = mis_dir.path_join("mission.json")

	if not FileAccess.file_exists(map_path) or not FileAccess.file_exists(mission_path):
		return {"valid": false}

	var map_text = FileAccess.get_file_as_string(map_path)
	var map_json = JSON.parse_string(map_text)
	if not map_json or typeof(map_json) != TYPE_DICTIONARY:
		return {"valid": false}

	var map_val = ContentValidatorScript.validate_map_data(map_json)
	if not map_val[0]:
		return {"valid": false}

	var mis_text = FileAccess.get_file_as_string(mission_path)
	var mis_json = JSON.parse_string(mis_text)
	if not mis_json or typeof(mis_json) != TYPE_DICTIONARY:
		return {"valid": false}

	var mis_val = ContentValidatorScript.validate_mission_data(mis_json, map_json)
	if not mis_val[0]:
		return {"valid": false}

	return {
		"valid": true,
		"id": mis_json.get("id", ""),
		"title": mis_json.get("title", ""),
		"briefing": mis_json.get("briefing", ""),
		"max_turns": mis_json.get("max_turns", 15),
		"objectives": mis_json.get("objectives", []),
		"units": mis_json.get("units", []),
		"map_width": map_json.get("width", 16),
		"map_height": map_json.get("height", 16),
		"package_path": mis_dir
	}
