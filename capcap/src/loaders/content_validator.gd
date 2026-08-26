class_name ContentValidator
extends RefCounted

## ContentValidator - Validates Map and Mission JSON data structures with fail-closed security

static func validate_map_data(data: Dictionary) -> Array:
	var width = data.get("width", 0)
	var height = data.get("height", 0)
	if width < 4 or height < 4:
		return [false, "Map dimensions too small (min 4x4, got %dx%d)." % [width, height]]

	# Validate plateaus
	var plateaus = data.get("plateaus", [])
	for p in plateaus:
		var pos = p.get("pos", [])
		var size = p.get("size", [])
		if pos.size() != 2 or size.size() != 2:
			return [false, "Invalid plateau definition."]
		if pos[0] < 0 or pos[1] < 0 or pos[0] + size[0] > width or pos[1] + size[1] > height:
			return [false, "Plateau exceeds map boundaries."]

	# Validate stairs
	var stairs = data.get("stairs", [])
	for s in stairs:
		var pos = s.get("pos", [])
		if pos.size() != 2 or pos[0] < 0 or pos[0] >= width or pos[1] < 0 or pos[1] >= height:
			return [false, "Stair coordinates out of bounds."]

	# Validate covers
	var covers = data.get("covers", [])
	for c in covers:
		var pos = c.get("pos", [])
		if pos.size() != 2 or pos[0] < 0 or pos[0] >= width or pos[1] < 0 or pos[1] >= height:
			return [false, "Cover coordinates out of bounds."]

	return [true, "OK"]

static func validate_mission_data(mission_data: Dictionary, map_data: Dictionary) -> Array:
	if not mission_data.has("id") or str(mission_data.get("id", "")) == "":
		return [false, "Mission missing required id."]
	if not mission_data.has("title"):
		return [false, "Mission missing required title."]

	var width = map_data.get("width", 16)
	var height = map_data.get("height", 16)

	var units = mission_data.get("units", [])
	if units.size() == 0:
		return [false, "Mission has no units."]

	var unit_ids: Dictionary = {}
	var unit_positions: Dictionary = {}
	var has_player_unit: bool = false

	for u in units:
		var uid = u.get("id", "")
		if uid == "":
			return [false, "Unit has empty id."]
		if unit_ids.has(uid):
			return [false, "Duplicate unit id: %s" % uid]
		unit_ids[uid] = true

		var team = u.get("team", "")
		if team != "Player" and team != "Enemy":
			return [false, "Invalid unit team: %s" % team]
		if team == "Player":
			has_player_unit = true

		var pos = u.get("pos", [])
		if pos.size() != 2 or pos[0] < 0 or pos[0] >= width or pos[1] < 0 or pos[1] >= height:
			return [false, "Unit %s position out of map bounds." % uid]

		var pos_key = "%d,%d" % [pos[0], pos[1]]
		if unit_positions.has(pos_key):
			return [false, "Multiple units spawn on same tile (%d, %d)." % [pos[0], pos[1]]]
		unit_positions[pos_key] = true

	if not has_player_unit:
		return [false, "Mission must contain at least one Player unit."]

	# Validate objectives
	var objectives = mission_data.get("objectives", [])
	if objectives.size() == 0:
		return [false, "Mission must contain at least one objective."]

	for obj in objectives:
		var target_id = obj.get("target_id", "")
		if target_id != "" and not unit_ids.has(target_id):
			return [false, "Objective references non-existent unit target_id: %s" % target_id]

		var target_pos = obj.get("target_pos", [])
		if target_pos.size() == 2:
			if target_pos[0] < 0 or target_pos[0] >= width or target_pos[1] < 0 or target_pos[1] >= height:
				return [false, "Objective target_pos out of bounds."]

	return [true, "OK"]
