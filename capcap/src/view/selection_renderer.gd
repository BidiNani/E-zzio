class_name SelectionRenderer
extends Node2D

## SelectionRenderer - Renders screen drag selection box and formation target markers

const IsoMathScript = preload("res://src/core/iso_math.gd")

var is_selecting: bool = false
var select_rect: Rect2 = Rect2()
var destination_markers: Array = [] # Array of {pos: Vector2i, elevation: int}

func set_selection_rect(active: bool, rect: Rect2) -> void:
	is_selecting = active
	select_rect = rect
	queue_redraw()

func set_destination_markers(markers: Array) -> void:
	destination_markers = markers
	queue_redraw()

func clear_destination_markers() -> void:
	destination_markers.clear()
	queue_redraw()

func _draw() -> void:
	# 1. Draw formation destination markers
	for marker in destination_markers:
		var center = IsoMathScript.grid_to_world(marker.pos, marker.elevation)
		draw_circle(center, 6.0, Color(0.2, 0.8, 1.0, 0.7))
		draw_arc(center, 12.0, 0, TAU, 16, Color(0.2, 0.8, 1.0, 0.9), 1.5)
