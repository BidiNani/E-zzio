class_name IsoMath
extends RefCounted

## IsoMath - 2.5D Isometric Coordinate Transformations, Geometry & Raycasting

const TILE_WIDTH: float = 64.0
const TILE_HEIGHT: float = 32.0
const ELEVATION_STEP: float = 16.0

## Projects Grid (x, y) with elevation z into World 2D screen coordinates
static func grid_to_world(grid_pos: Vector2i, elevation: int = 0) -> Vector2:
	var wx: float = (grid_pos.x - grid_pos.y) * (TILE_WIDTH / 2.0)
	var wy: float = (grid_pos.x + grid_pos.y) * (TILE_HEIGHT / 2.0) - (elevation * ELEVATION_STEP)
	return Vector2(wx, wy)

## Inverts World 2D coordinates on a fixed elevation plane z
static func world_to_grid_plane(world_pos: Vector2, elevation: int = 0) -> Vector2i:
	var adjusted_y: float = world_pos.y + (elevation * ELEVATION_STEP)
	var gx: float = (world_pos.x / TILE_WIDTH) + (adjusted_y / TILE_HEIGHT)
	var gy: float = (adjusted_y / TILE_HEIGHT) - (world_pos.x / TILE_WIDTH)
	return Vector2i(int(floor(gx)), int(floor(gy)))

## Backward compatible alias for planar inversion at z=0
static func world_to_grid(world_pos: Vector2, elevation: int = 0) -> Vector2i:
	return world_to_grid_plane(world_pos, elevation)

## Checks if a 2D world point lies inside an isometric diamond polygon
static func is_point_in_diamond(world_pos: Vector2, grid_pos: Vector2i, elevation: int = 0) -> bool:
	var center: Vector2 = grid_to_world(grid_pos, elevation)
	var dx: float = abs(world_pos.x - center.x) / (TILE_WIDTH / 2.0)
	var dy: float = abs(world_pos.y - center.y) / (TILE_HEIGHT / 2.0)
	return (dx + dy) <= 1.0

## Returns the 4 polygon vertices of an isometric diamond cell top face in world space
static func get_cell_polygon(grid_pos: Vector2i, elevation: int = 0) -> PackedVector2Array:
	var center: Vector2 = grid_to_world(grid_pos, elevation)
	var half_w: float = TILE_WIDTH / 2.0
	var half_h: float = TILE_HEIGHT / 2.0
	return PackedVector2Array([
		center + Vector2(0, -half_h),      # Top
		center + Vector2(half_w, 0),       # Right
		center + Vector2(0, half_h),       # Bottom
		center + Vector2(-half_w, 0)       # Left
	])

## Returns the vertical Left Wall Face polygon of a cliff (South-West facing)
static func get_left_wall_polygon(grid_pos: Vector2i, top_z: int, bottom_z: int) -> PackedVector2Array:
	var top_center: Vector2 = grid_to_world(grid_pos, top_z)
	var bot_center: Vector2 = grid_to_world(grid_pos, bottom_z)
	var half_w: float = TILE_WIDTH / 2.0
	var half_h: float = TILE_HEIGHT / 2.0
	return PackedVector2Array([
		top_center + Vector2(-half_w, 0),      # Top-Left
		top_center + Vector2(0, half_h),       # Top-Bottom
		bot_center + Vector2(0, half_h),       # Bottom-Bottom
		bot_center + Vector2(-half_w, 0)       # Bottom-Left
	])

## Returns the vertical Right Wall Face polygon of a cliff (South-East facing)
static func get_right_wall_polygon(grid_pos: Vector2i, top_z: int, bottom_z: int) -> PackedVector2Array:
	var top_center: Vector2 = grid_to_world(grid_pos, top_z)
	var bot_center: Vector2 = grid_to_world(grid_pos, bottom_z)
	var half_w: float = TILE_WIDTH / 2.0
	var half_h: float = TILE_HEIGHT / 2.0
	return PackedVector2Array([
		top_center + Vector2(0, half_h),       # Top-Bottom
		top_center + Vector2(half_w, 0),       # Top-Right
		bot_center + Vector2(half_w, 0),       # Bottom-Right
		bot_center + Vector2(0, half_h)        # Bottom-Bottom
	])

## Multi-height raycast: tests elevated tiles and wall faces from front/top down to bottom
static func world_to_grid_raycast(world_pos: Vector2, grid_map, max_elevation: int = 4) -> Vector2i:
	# Test from highest elevation down to 0
	for z in range(max_elevation, -1, -1):
		var candidate: Vector2i = world_to_grid_plane(world_pos, z)
		if grid_map.is_valid_cell(candidate):
			var cell = grid_map.get_cell(candidate)
			if cell and cell.elevation == z and is_point_in_diamond(world_pos, candidate, z):
				return candidate

	# Fallback to ground plane z=0
	return world_to_grid_plane(world_pos, 0)
