class_name FogRenderer
extends Node2D

## FogRenderer - Renders pitch black shroud (HIDDEN) and distinguishable dark-blue mist (EXPLORED)

const IsoMathScript = preload("res://src/core/iso_math.gd")
const VisibilityMapScript = preload("res://src/vision/visibility_map.gd")

var visibility_map = null
var grid_map = null

func setup(p_vis_map, p_grid_map) -> void:
	visibility_map = p_vis_map
	grid_map = p_grid_map
	queue_redraw()

func refresh() -> void:
	queue_redraw()

func _draw() -> void:
	if not visibility_map or not grid_map:
		return

	var col_hidden   = Color(0.01, 0.02, 0.03, 0.98) # Pitch black impenetrable shroud
	var col_explored = Color(0.06, 0.10, 0.16, 0.55) # Clearly distinct cool exploration shroud

	for x in range(visibility_map.width):
		for y in range(visibility_map.height):
			var pos = Vector2i(x, y)
			var state = visibility_map.get_state(pos)
			var elev: int = grid_map.get_cell(pos).elevation if grid_map.is_valid_cell(pos) else 0
			var poly = IsoMathScript.get_cell_polygon(pos, elev)

			if state == VisibilityMapScript.FogState.HIDDEN:
				draw_colored_polygon(poly, col_hidden)
			elif state == VisibilityMapScript.FogState.EXPLORED:
				draw_colored_polygon(poly, col_explored)
				# Subtle cross grid lines for explored terrain
				draw_polyline(poly + PackedVector2Array([poly[0]]), Color(0.1, 0.18, 0.28, 0.4), 1.0)
