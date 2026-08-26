class_name IsoGridRenderer
extends Node2D

## IsoGridRenderer - Procedural 2.5D Isometric Terrain, Reliefs & Cover Barricades Visualizer

const IsoMathScript = preload("res://src/core/iso_math.gd")
const GridCellScript = preload("res://src/core/grid_cell.gd")

var grid_map
var active_path: Array[Vector2i] = []

func _init(p_grid_map = null) -> void:
	grid_map = p_grid_map

func set_grid_map(p_grid_map) -> void:
	grid_map = p_grid_map
	queue_redraw()

func set_active_path(p_path: Array[Vector2i]) -> void:
	active_path = p_path
	queue_redraw()

func _draw() -> void:
	if not grid_map:
		return

	var sorted_positions = grid_map.cells.keys()
	sorted_positions.sort_custom(func(a: Vector2i, b: Vector2i):
		var depth_a = (a.x + a.y) * 100 + grid_map.cells[a].elevation
		var depth_b = (b.x + b.y) * 100 + grid_map.cells[b].elevation
		return depth_a < depth_b
	)

	var col_grass_top = Color(0.35, 0.62, 0.35, 0.95)
	var col_stone_top = Color(0.55, 0.58, 0.62, 0.95)
	var col_stair_top = Color(0.68, 0.52, 0.32, 0.95)
	var col_cover_top = Color(0.48, 0.42, 0.36, 0.95)
	var col_blocked   = Color(0.85, 0.25, 0.25, 0.9)
	var col_path      = Color(0.95, 0.85, 0.15, 0.95)

	var col_wall_left_grass  = Color(0.22, 0.38, 0.22, 0.98)
	var col_wall_right_grass = Color(0.28, 0.48, 0.28, 0.98)
	var col_wall_left_stone  = Color(0.35, 0.38, 0.42, 0.98)
	var col_wall_right_stone = Color(0.45, 0.48, 0.52, 0.98)

	var line_color = Color(0.15, 0.2, 0.25, 0.4)

	for pos in sorted_positions:
		var cell = grid_map.cells[pos]
		var elev: int = cell.elevation

		var is_stone: bool = (cell.tile_theme == "stone")
		var left_wall_col  = col_wall_left_stone if is_stone else col_wall_left_grass
		var right_wall_col = col_wall_right_stone if is_stone else col_wall_right_grass

		var sw_pos = Vector2i(pos.x, pos.y + 1)
		var sw_elev: int = grid_map.get_cell(sw_pos).elevation if grid_map.is_valid_cell(sw_pos) else 0
		if elev > sw_elev:
			var left_poly = IsoMathScript.get_left_wall_polygon(pos, elev, sw_elev)
			draw_colored_polygon(left_poly, left_wall_col)
			draw_polyline(left_poly + PackedVector2Array([left_poly[0]]), line_color, 1.0)

		var se_pos = Vector2i(pos.x + 1, pos.y)
		var se_elev: int = grid_map.get_cell(se_pos).elevation if grid_map.is_valid_cell(se_pos) else 0
		if elev > se_elev:
			var right_poly = IsoMathScript.get_right_wall_polygon(pos, elev, se_elev)
			draw_colored_polygon(right_poly, right_wall_col)
			draw_polyline(right_poly + PackedVector2Array([right_poly[0]]), line_color, 1.0)

		var top_poly = IsoMathScript.get_cell_polygon(pos, elev)
		var top_col: Color = col_grass_top

		if not cell.is_walkable:
			top_col = col_blocked
		elif cell.cell_type == GridCellScript.Type.STAIR:
			top_col = col_stair_top
		elif cell.tile_theme in ["cover_half", "cover_full"]:
			top_col = col_cover_top
		elif is_stone:
			top_col = col_stone_top

		if pos in active_path:
			top_col = col_path

		draw_colored_polygon(top_poly, top_col)
		draw_polyline(top_poly + PackedVector2Array([top_poly[0]]), line_color, 1.0)

		# Cover barricade marker (shield symbol / low wall graphic)
		if cell.tile_theme in ["cover_half", "cover_full"]:
			var center = IsoMathScript.grid_to_world(pos, elev)
			draw_rect(Rect2(center + Vector2(-8, -4), Vector2(16, 8)), Color(0.2, 0.2, 0.2, 0.6))

	if active_path.size() > 1:
		var line_points: PackedVector2Array = PackedVector2Array()
		for p in active_path:
			var e: int = grid_map.get_cell(p).elevation if grid_map.get_cell(p) else 0
			line_points.append(IsoMathScript.grid_to_world(p, e))
		draw_polyline(line_points, Color(1.0, 0.95, 0.1, 1.0), 3.0)
