class_name CampaignState
extends RefCounted

## CampaignState - Persistent Meta-Progression State (Missions Unlocked, Completed, Stats & Records)

var campaign_id: String = "campaign_alpha"
var completed_missions: Array = []
var unlocked_missions: Array = ["alpha_01"]
var stats: Dictionary = {
	"victories": 0,
	"defeats": 0,
	"total_turns": 0,
	"total_damage_dealt": 0,
	"total_damage_taken": 0,
	"total_enemies_killed": 0
}
var mission_records: Dictionary = {}

func is_mission_unlocked(mission_id: String) -> bool:
	return unlocked_missions.has(mission_id)

func is_mission_completed(mission_id: String) -> bool:
	return completed_missions.has(mission_id)

func unlock_mission(mission_id: String) -> void:
	if not unlocked_missions.has(mission_id):
		unlocked_missions.append(mission_id)

func mark_mission_completed(mission_id: String) -> void:
	if not completed_missions.has(mission_id):
		completed_missions.append(mission_id)

func serialize() -> Dictionary:
	return {
		"campaign_id": campaign_id,
		"completed_missions": completed_missions.duplicate(),
		"unlocked_missions": unlocked_missions.duplicate(),
		"stats": stats.duplicate(),
		"mission_records": mission_records.duplicate()
	}

func deserialize(data: Dictionary) -> bool:
	if not data.has("campaign_id"):
		return false
	campaign_id = data.get("campaign_id", "campaign_alpha")
	completed_missions = data.get("completed_missions", []).duplicate()
	unlocked_missions = data.get("unlocked_missions", ["alpha_01"]).duplicate()
	stats = data.get("stats", {
		"victories": 0, "defeats": 0, "total_turns": 0,
		"total_damage_dealt": 0, "total_damage_taken": 0, "total_enemies_killed": 0
	}).duplicate()
	mission_records = data.get("mission_records", {}).duplicate()
	return true

func save_to_file(path: String = "user://campaign_save.json") -> bool:
	var file = FileAccess.open(path, FileAccess.WRITE)
	if not file:
		return false
	file.store_string(JSON.stringify(serialize(), "  "))
	return true

func load_from_file(path: String = "user://campaign_save.json") -> bool:
	if not FileAccess.file_exists(path):
		return false
	var text = FileAccess.get_file_as_string(path)
	var json = JSON.parse_string(text)
	if not json or typeof(json) != TYPE_DICTIONARY:
		return false
	return deserialize(json)
