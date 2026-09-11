class_name TouchVirtualJoystick
extends Control

signal joystick_moved(direction: Vector2)

@export var max_distance: float = 60.0

@onready var tip: TextureRect = $Tip
@onready var base: TextureRect = $Base

var is_dragging: bool = false
var touch_index: int = -1
var output_vector: Vector2 = Vector2.ZERO

func _ready() -> void:
	reset_tip()

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and not is_dragging:
			var local_pos = get_local_mouse_position()
			if local_pos.length() <= max_distance * 1.8:
				is_dragging = true
				touch_index = event.index
				update_joystick(local_pos)
		elif not event.pressed and event.index == touch_index:
			is_dragging = false
			touch_index = -1
			reset_tip()
	elif event is InputEventScreenDrag and event.index == touch_index:
		update_joystick(get_local_mouse_position())
	elif event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				var local_pos = get_local_mouse_position()
				if local_pos.length() <= max_distance * 1.8:
					is_dragging = true
					update_joystick(local_pos)
			else:
				is_dragging = false
				reset_tip()
	elif event is InputEventMouseMotion and is_dragging:
		update_joystick(get_local_mouse_position())

func update_joystick(pos: Vector2) -> void:
	var clamped_pos = pos.limit_length(max_distance)
	if tip:
		tip.position = clamped_pos - (tip.size / 2.0)
	output_vector = clamped_pos / max_distance
	joystick_moved.emit(output_vector)

func reset_tip() -> void:
	output_vector = Vector2.ZERO
	if tip:
		tip.position = -tip.size / 2.0
	joystick_moved.emit(Vector2.ZERO)
