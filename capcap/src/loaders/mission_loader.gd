class_name MissionLoader
extends RefCounted

## MissionLoader - Declarative loader for Map and Mission packages

const GridMapScript = preload("res://src/core/grid_map.gd")
const GameStateScript = preload("res://src/state/game_state.gd")
const UnitScript = preload("res://src/entities/unit.gd")
const MissionObjectiveScript = preload("res://src/objectives/mission_objective.gd")
const ContentValidatorScript = preload("res://src/loaders/content_validator.gd")

static func load_mission_package(dir_path: String) -> Dictionary:
	var map_path = dir_path.path_join("map.json")
	var mission_path = dir_path.path_join("mission.json")

	if not FileAccess.file_exists(map_path) or not FileAccess.file_exists(mission_path):
		return {"success": false, "error": "Missing map.json or mission.json in package."}

	var map_text = FileAccess.get_file_as_string(map_path)
	var map_json = JSON.parse_string(map_text)
	if not map_json or typeof(map_json) != TYPE_DICTIONARY:
		return {"success": false, "error": "Invalid or corrupt map.json syntax."}

	var map_val = ContentValidatorScript.validate_map_data(map_json)
	if not map_val[0]:
		return {"success": false, "error": "Map validation failed: " + map_val[1]}

	var mission_text = FileAccess.get_file_as_string(mission_path)
	var mission_json = JSON.parse_string(mission_text)
	if not mission_json or typeof(mission_json) != TYPE_DICTIONARY:
		return {"success": false, "error": "Invalid or corrupt mission.json syntax."}

	var mis_val = ContentValidatorScript.validate_mission_data(mission_json, map_json)
	if not mis_val[0]:
		return {"success": false, "error": "Mission validation failed: " + mis_val[1]}

	# Build Game World
	var width = map_json.get("width", 16)
	var height = map_json.get("height", 16)
	var grid_map = GridMapScript.new(width, height)

	for p in map_json.get("plateaus", []):
		var pos = p.get("pos", [0, 0])
		var size = p.get("size", [0, 0])
		var elev = p.get("elevation", 0)
		grid_map.create_plateau(Vector2i(pos[0], pos[1]), Vector2i(size[0], size[1]), elev)

	for s in map_json.get("stairs", []):
		var pos = s.get("pos", [0, 0])
		var elev = s.get("elevation", 1)
		var dir = s.get("dir", [1, 0])
		grid_map.set_cell_stair(Vector2i(pos[0], pos[1]), elev, Vector2i(dir[0], dir[1]))

	for c in map_json.get("covers", []):
		var pos = c.get("pos", [0, 0])
		var c_type = c.get("type", "cover_half")
		if grid_map.is_valid_cell(Vector2i(pos[0], pos[1])):
			grid_map.get_cell(Vector2i(pos[0], pos[1])).tile_theme = c_type

	var game_state = GameStateScript.new(grid_map)
	game_state.max_turns = mission_json.get("max_turns", 15)

	# Build Objectives
	for obj_data in mission_json.get("objectives", []):
		var obj_type_str = obj_data.get("type", "ELIMINATION")
		var obj_type = MissionObjectiveScript.Type.ELIMINATION
		if obj_type_str == "CAPTURE_POINT":
			obj_type = MissionObjectiveScript.Type.CAPTURE_POINT
		elif obj_type_str == "EXTRACTION":
			obj_type = MissionObjectiveScript.Type.EXTRACTION
		elif obj_type_str == "SURVIVAL":
			obj_type = MissionObjectiveScript.Type.SURVIVAL

		var obj = MissionObjectiveScript.new(
			obj_data.get("id", ""),
			obj_data.get("title", ""),
			obj_type,
			obj_data.get("mandatory", true),
			obj_data.get("required", 1)
		)
		obj.target_id = obj_data.get("target_id", "")
		var t_pos = obj_data.get("target_pos", [0, 0])
		obj.target_pos = Vector2i(t_pos[0], t_pos[1])
		game_state.add_objective(obj)

	# Build Units
	var spawned_units: Array = []
	for u_data in mission_json.get("units", []):
		var u = UnitScript.new()
		var pos = u_data.get("pos", [0, 0])
		var team = u_data.get("team", "Player")
		var col = Color(0.2, 0.6, 1.0) if team == "Player" else Color(0.9, 0.2, 0.2)
		u.setup(
			u_data.get("id", ""),
			u_data.get("name", ""),
			Vector2i(pos[0], pos[1]),
			col,
			u_data.get("elevation", 0),
			u_data.get("max_ap", 6),
			team,
			u_data.get("range", 5.0),
			u_data.get("damage", 8)
		)
		game_state.register_unit(u)
		spawned_units.append(u)

	return {
		"success": true,
		"grid_map": grid_map,
		"game_state": game_state,
		"units": spawned_units,
		"mission_data": mission_json,
		"map_data": map_json
	}
