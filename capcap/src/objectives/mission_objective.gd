class_name MissionObjective
extends RefCounted

## MissionObjective - Data-driven mission objective model (Elimination, Capture, Extraction, Survival)

enum Type { ELIMINATION = 0, CAPTURE_POINT = 1, EXTRACTION = 2, SURVIVAL = 3 }

var objective_id: String = ""
var title: String = ""
var team_id: String = "Player"
var objective_type: Type = Type.ELIMINATION
var target_pos: Vector2i = Vector2i.ZERO
var target_id: String = ""
var required_progress: int = 1
var current_progress: int = 0
var is_mandatory: bool = true
var is_completed: bool = false
var is_failed: bool = false

func _init(p_id: String = "", p_title: String = "", p_type: Type = Type.ELIMINATION, p_mandatory: bool = true, p_required: int = 1) -> void:
	objective_id = p_id
	title = p_title
	objective_type = p_type
	is_mandatory = p_mandatory
	required_progress = max(1, p_required)

func check_progress(game_state) -> void:
	if is_completed or is_failed:
		return

	match objective_type:
		Type.ELIMINATION:
			if target_id != "":
				var target_unit = game_state.get_unit(target_id)
				if target_unit and not target_unit.stats.is_alive():
					current_progress = required_progress
					is_completed = true
			else:
				# All enemy units eliminated
				var enemies_alive: int = 0
				for uid in game_state.units.keys():
					var u = game_state.units[uid]
					if u.team_id != team_id and u.stats.is_alive():
						enemies_alive += 1
				if enemies_alive == 0:
					current_progress = required_progress
					is_completed = true

		Type.CAPTURE_POINT:
			var occupied_by_team: bool = false
			for uid in game_state.units.keys():
				var u = game_state.units[uid]
				if u.team_id == team_id and u.stats.is_alive() and u.grid_pos == target_pos:
					occupied_by_team = true
					break
			if occupied_by_team:
				current_progress += 1
				if current_progress >= required_progress:
					is_completed = true

		Type.EXTRACTION:
			for uid in game_state.units.keys():
				var u = game_state.units[uid]
				if u.team_id == team_id and u.stats.is_alive() and u.grid_pos == target_pos:
					current_progress = required_progress
					is_completed = true
					break

		Type.SURVIVAL:
			current_progress = game_state.turn_number
			if current_progress >= required_progress:
				is_completed = true

func serialize() -> Dictionary:
	return {
		"id": objective_id,
		"title": title,
		"team_id": team_id,
		"type": int(objective_type),
		"target_pos": [target_pos.x, target_pos.y],
		"target_id": target_id,
		"required_progress": required_progress,
		"current_progress": current_progress,
		"is_mandatory": is_mandatory,
		"is_completed": is_completed,
		"is_failed": is_failed
	}

func deserialize(data: Dictionary) -> bool:
	objective_id = data.get("id", "")
	title = data.get("title", "")
	team_id = data.get("team_id", "Player")
	objective_type = data.get("type", Type.ELIMINATION)
	var pos = data.get("target_pos", [0, 0])
	target_pos = Vector2i(pos[0], pos[1])
	target_id = data.get("target_id", "")
	required_progress = data.get("required_progress", 1)
	current_progress = data.get("current_progress", 0)
	is_mandatory = data.get("is_mandatory", true)
	is_completed = data.get("is_completed", false)
	is_failed = data.get("is_failed", false)
	return true
