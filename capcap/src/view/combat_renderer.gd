class_name CombatRenderer
extends Node2D

## CombatRenderer - Visualizes bullet/laser tracers and sightlines in 2.5D space

const IsoMathScript = preload("res://src/core/iso_math.gd")

var tracer_lines: Array = [] # Array of {start: Vector2, end: Vector2, time_left: float}

func fire_tracer(from_grid: Vector2i, from_z: int, to_grid: Vector2i, to_z: int) -> void:
	var start_w = IsoMathScript.grid_to_world(from_grid, from_z) + Vector2(0, -16)
	var end_w = IsoMathScript.grid_to_world(to_grid, to_z) + Vector2(0, -16)
	tracer_lines.append({"start": start_w, "end": end_w, "time_left": 0.35})
	queue_redraw()

func _process(delta: float) -> void:
	if tracer_lines.size() > 0:
		var active: Array = []
		for t in tracer_lines:
			t.time_left -= delta
			if t.time_left > 0:
				active.append(t)
		tracer_lines = active
		queue_redraw()

func _draw() -> void:
	for t in tracer_lines:
		var alpha: float = clamp(t.time_left / 0.35, 0.0, 1.0)
		draw_line(t.start, t.end, Color(1.0, 0.9, 0.2, alpha), 2.5)
		draw_circle(t.end, 4.0, Color(1.0, 0.3, 0.1, alpha))
