class_name AStarPathfinder
extends RefCounted

var grid_map
var max_elevation_delta: int = 1

func _init(p_grid_map) -> void:
	grid_map = p_grid_map

func heuristic(a: Vector2i, b: Vector2i) -> float:
	return float(abs(a.x - b.x) + abs(a.y - b.y))

func find_path(start: Vector2i, goal: Vector2i, allow_diagonals: bool = false) -> Array[Vector2i]:
	if not grid_map.is_valid_cell(start) or not grid_map.is_valid_cell(goal):
		return []
	if not grid_map.is_cell_walkable(goal) or not grid_map.is_cell_walkable(start):
		return []
	if start == goal:
		return [start]

	var open_set: Array[Vector2i] = [start]
	var came_from: Dictionary = {}
	var g_score: Dictionary = {start: 0.0}
	var f_score: Dictionary = {start: heuristic(start, goal)}

	while open_set.size() > 0:
		var current: Vector2i = open_set[0]
		var lowest_f: float = f_score.get(current, INF)
		for node in open_set:
			var f: float = f_score.get(node, INF)
			if f < lowest_f:
				lowest_f = f
				current = node

		if current == goal:
			return reconstruct_path(came_from, current)

		open_set.erase(current)

		var current_cell = grid_map.get_cell(current)
		var current_elev: int = current_cell.elevation if current_cell else 0

		for neighbor in grid_map.get_neighbors(current, allow_diagonals):
			if not grid_map.is_cell_walkable(neighbor):
				continue

			var neighbor_cell = grid_map.get_cell(neighbor)
			var neighbor_elev: int = neighbor_cell.elevation if neighbor_cell else 0

			if abs(neighbor_elev - current_elev) > max_elevation_delta:
				continue

			var step_cost: float = 1.414 if (neighbor.x != current.x and neighbor.y != current.y) else 1.0
			step_cost *= neighbor_cell.movement_cost

			var tentative_g: float = g_score.get(current, INF) + step_cost

			if tentative_g < g_score.get(neighbor, INF):
				came_from[neighbor] = current
				g_score[neighbor] = tentative_g
				f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
				if not open_set.has(neighbor):
					open_set.append(neighbor)

	return []

func reconstruct_path(came_from: Dictionary, current: Vector2i) -> Array[Vector2i]:
	var total_path: Array[Vector2i] = [current]
	while came_from.has(current):
		current = came_from[current]
		total_path.push_front(current)
	return total_path
