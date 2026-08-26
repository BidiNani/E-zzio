class_name IsoCamera
extends Camera2D

## IsoCamera - Dynamic 2.5D Isometric Camera Controller
## Supports smooth pan (keyboard/mouse drag), exponential zoom, player focus, and map bounds clamping.

const IsoMathScript = preload("res://src/core/iso_math.gd")

@export var pan_speed: float = 650.0
@export var zoom_min: float = 0.5
@export var zoom_max: float = 2.5
@export var zoom_step: float = 1.15
@export var damping_factor: float = 12.0
@export var padding: float = 192.0

var target_position: Vector2 = Vector2.ZERO
var target_zoom: Vector2 = Vector2.ONE
var is_dragging: bool = false
var drag_start_mouse: Vector2 = Vector2.ZERO
var drag_start_camera: Vector2 = Vector2.ZERO

var map_bounds_min: Vector2 = Vector2(-2000, -2000)
var map_bounds_max: Vector2 = Vector2(2000, 2000)

var follow_target: Node2D = null

func _ready() -> void:
	target_position = position
	target_zoom = zoom

func setup_bounds(grid_width: int, grid_height: int) -> void:
	# Calculate the 4 extreme isometric world coordinates
	var c_top: Vector2 = IsoMathScript.grid_to_world(Vector2i(0, 0), 0)
	var c_right: Vector2 = IsoMathScript.grid_to_world(Vector2i(grid_width, 0), 0)
	var c_bottom: Vector2 = IsoMathScript.grid_to_world(Vector2i(grid_width, grid_height), 0)
	var c_left: Vector2 = IsoMathScript.grid_to_world(Vector2i(0, grid_height), 0)

	var min_x = min(c_top.x, min(c_right.x, min(c_bottom.x, c_left.x))) - padding
	var max_x = max(c_top.x, max(c_right.x, max(c_bottom.x, c_left.x))) + padding
	var min_y = min(c_top.y, min(c_right.y, min(c_bottom.y, c_left.y))) - padding
	var max_y = max(c_top.y, max(c_right.y, max(c_bottom.y, c_left.y))) + padding

	map_bounds_min = Vector2(min_x, min_y)
	map_bounds_max = Vector2(max_x, max_y)

func focus_on(world_pos: Vector2, immediate: bool = false) -> void:
	target_position = clamp_position(world_pos)
	follow_target = null
	if immediate:
		position = target_position

func set_follow_target(node: Node2D) -> void:
	follow_target = node

func clamp_position(pos: Vector2) -> Vector2:
	return Vector2(
		clamp(pos.x, map_bounds_min.x, map_bounds_max.x),
		clamp(pos.y, map_bounds_min.y, map_bounds_max.y)
	)

func _unhandled_input(event: InputEvent) -> void:
	# 1. Mouse Wheel Zoom
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			adjust_zoom(zoom_step)
		elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			adjust_zoom(1.0 / zoom_step)
		# 2. Mouse Drag Pan (Middle or Right button)
		elif event.button_index in [MOUSE_BUTTON_MIDDLE, MOUSE_BUTTON_RIGHT]:
			if event.pressed:
				is_dragging = true
				drag_start_mouse = event.position
				drag_start_camera = target_position
				follow_target = null
			else:
				is_dragging = false

	# 3. Mouse Drag Motion
	elif event is InputEventMouseMotion and is_dragging:
		var delta_mouse: Vector2 = (event.position - drag_start_mouse) / zoom.x
		target_position = clamp_position(drag_start_camera - delta_mouse)

	# 4. Keyboard Shortcuts (Space for Focus)
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE:
			if follow_target:
				focus_on(follow_target.position)

func adjust_zoom(factor: float) -> void:
	var new_scale: float = clamp(target_zoom.x * factor, zoom_min, zoom_max)
	target_zoom = Vector2(new_scale, new_scale)

func _process(delta: float) -> void:
	# 1. Keyboard Pan
	var move_dir: Vector2 = Vector2.ZERO
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_Z) or Input.is_key_pressed(KEY_UP):
		move_dir.y -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		move_dir.y += 1.0
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_Q) or Input.is_key_pressed(KEY_LEFT):
		move_dir.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		move_dir.x += 1.0

	if move_dir != Vector2.ZERO:
		follow_target = null
		move_dir = move_dir.normalized()
		target_position += move_dir * (pan_speed / zoom.x) * delta
		target_position = clamp_position(target_position)

	# 2. Follow Target (if active)
	if follow_target and not is_dragging:
		target_position = clamp_position(follow_target.position)

	# 3. Frame-rate independent smooth damping
	var weight: float = 1.0 - exp(-damping_factor * delta)
	position = position.lerp(target_position, weight)
	zoom = zoom.lerp(target_zoom, weight)
