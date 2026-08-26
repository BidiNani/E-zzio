class_name CampaignEvaluator
extends RefCounted

## CampaignEvaluator - Single Authority for validating mission results and applying persistent campaign updates

const UNLOCK_GRAPH: Dictionary = {
	"alpha_01": "bravo_01",
	"bravo_01": "gamma_01",
	"gamma_01": ""
}

static func apply_mission_result(campaign_state, result: Dictionary) -> Dictionary:
	var mission_id = result.get("mission_id", "")
	if mission_id == "" or not UNLOCK_GRAPH.has(mission_id):
		return {"success": false, "error": "Invalid or unknown mission_id (Fail-Closed)."}

	var is_victory = result.get("is_victory", false)
	var turns = result.get("turns", 1)
	var dmg_dealt = result.get("damage_dealt", 0)
	var dmg_taken = result.get("damage_taken", 0)
	var kills = result.get("enemies_killed", 0)

	var newly_unlocked_id = ""
	var is_new_record = false

	# Global statistics accumulation
	if is_victory:
		campaign_state.stats["victories"] += 1
		var was_completed_before = campaign_state.is_mission_completed(mission_id)
		campaign_state.mark_mission_completed(mission_id)

		# Sequential unlocking
		var next_mis = UNLOCK_GRAPH.get(mission_id, "")
		if next_mis != "" and not campaign_state.is_mission_unlocked(next_mis):
			campaign_state.unlock_mission(next_mis)
			newly_unlocked_id = next_mis
	else:
		campaign_state.stats["defeats"] += 1

	campaign_state.stats["total_turns"] += turns
	campaign_state.stats["total_damage_dealt"] += dmg_dealt
	campaign_state.stats["total_damage_taken"] += dmg_taken
	campaign_state.stats["total_enemies_killed"] += kills

	# Per-mission best record tracking
	var prev_record = campaign_state.mission_records.get(mission_id, {})
	var prev_best = prev_record.get("best_turns", 999)
	var best_turns = prev_best

	if is_victory:
		if turns < prev_best or prev_best == 999:
			best_turns = turns
			is_new_record = true

	campaign_state.mission_records[mission_id] = {
		"completed": campaign_state.is_mission_completed(mission_id),
		"best_turns": best_turns if best_turns != 999 else turns,
		"last_played_victory": is_victory
	}

	campaign_state.save_to_file()

	return {
		"success": true,
		"mission_id": mission_id,
		"is_victory": is_victory,
		"newly_unlocked_id": newly_unlocked_id,
		"is_new_record": is_new_record,
		"best_turns": best_turns
	}
