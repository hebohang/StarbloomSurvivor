"""Deterministically generate the Verdant Rift low-poly arena and its assets.

This tool intentionally uses only Python's standard library.  Run it from any
working directory; output locations are resolved relative to this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import stat
import struct
import uuid
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence, Tuple


SEED = 0x5EED_2026
UUID_NAMESPACE = uuid.UUID("63b0caa0-b714-52da-a3fc-c3dd85ce3094")
ASSET_MODEL_ROOT = "Assets/Models/VerdantRift"
HDR_ASSET_PATH = "Assets/Textures/Hdr/VerdantRift.hdr"
SCENE_ASSET_PATH = "Assets/Scenes/MainGame.he"
CAT_ROOT = "Assets/Models/Quaternius/UltimateMonsters/Cat"
PLAYER_MESH_PATH = f"{CAT_ROOT}/Cat.hmesh"
PLAYER_ANIMATION_PATH = f"{CAT_ROOT}/CharacterArmature_Idle.hanim"
PLAYER_CONTROLLER_PATH = f"{CAT_ROOT}/Cat_Locomotion.hanimctrl"
NATURE_ASSET_ROOT = "Assets/Models/Quaternius/UltimateStylizedNature"
RUINS_ASSET_ROOT = "Assets/Models/Quaternius/UltimateModularRuins"
EXTERNAL_MESH_PATHS = {
    "NatureBushFlowers": f"{NATURE_ASSET_ROOT}/Bush_Large_Flowers/Bush_Large_Flowers.hmesh",
    "NatureDeadTree": f"{NATURE_ASSET_ROOT}/DeadTree_3/DeadTree_3.hmesh",
    "NatureTree": f"{NATURE_ASSET_ROOT}/NormalTree_2/NormalTree_2.hmesh",
    "RuinsArch": f"{RUINS_ASSET_ROOT}/Arch_Round_RoundColumn/Arch_Round_RoundColumn.hmesh",
    "RuinsColumn": f"{RUINS_ASSET_ROOT}/Column_Round_Short/Column_Round_Short.hmesh",
}
EXTERNAL_ASSET_SHA256 = {
    f"{NATURE_ASSET_ROOT}/NormalTree_2/NormalTree_2.hmesh": "5E01DB71664E4AF62D6E0EFD46F0A2459DAC29AB96F854D7883A512E1042AF78",
    f"{NATURE_ASSET_ROOT}/NormalTree_2/NormalTree_2.bin": "FF55B2D27CEDC2307B2162A6343B659726D60F6AAFFC5469975F53E7E09801ED",
    f"{NATURE_ASSET_ROOT}/Bush_Large_Flowers/Bush_Large_Flowers.hmesh": "DDE246C25E51AE57B68725D8297EBDC4A5B8D35730088934E03E260598F2FA29",
    f"{NATURE_ASSET_ROOT}/Bush_Large_Flowers/Bush_Large_Flowers.bin": "38D1F4225298C7A9E5659C17CBBE4FDC18AB4A6160A3B538637D8BD56B2B6354",
    f"{NATURE_ASSET_ROOT}/DeadTree_3/DeadTree_3.hmesh": "FC5E4C031ABBB4C0BB70EBEBF4CB3FF90F443C9A2C4A64E95ECF1C75CD32D0BA",
    f"{NATURE_ASSET_ROOT}/DeadTree_3/DeadTree_3.bin": "5CBFBBB019736FA18EC838DDD3B8CEB4BC8810541E735068D243D56EE2C53414",
    f"{RUINS_ASSET_ROOT}/Arch_Round_RoundColumn/Arch_Round_RoundColumn.hmesh": "5DBC6A1F088034D18259B098EFEFF2F741C49E3ACFF227BF8EBDEC13D0406392",
    f"{RUINS_ASSET_ROOT}/Arch_Round_RoundColumn/Arch_Round_RoundColumn.bin": "1A13569818A7ECCF2547139ACB575260903E5558076E115BA3E18944466D9C82",
    f"{RUINS_ASSET_ROOT}/Column_Round_Short/Column_Round_Short.hmesh": "327E2A2F0DCAD984378267E506B30A29C2A60D4D5C0AA3634E74090BD8D370E1",
    f"{RUINS_ASSET_ROOT}/Column_Round_Short/Column_Round_Short.bin": "87D0CD43BA33FB86B8E5CDCF5D53A74FA9A7FAE8DCC2B359D0D2C84524345319",
}
DETAIL_TEXTURE_ROOT = "Assets/Textures/VerdantRift"
DETAIL_ALBEDO_PATH = f"{DETAIL_TEXTURE_ROOT}/StylizedMacroAlbedo.png"
DETAIL_NORMAL_PATH = f"{DETAIL_TEXTURE_ROOT}/StylizedMacroNormal.png"
DETAIL_AO_PATH = f"{DETAIL_TEXTURE_ROOT}/StylizedMacroAO.png"
DETAIL_MR_PATH = f"{DETAIL_TEXTURE_ROOT}/StylizedMacroMetallicRoughness.png"

# 1.9 keeps the physical boundary diameter at 174.8 m.  The gameplay script
# intentionally uses a slightly smaller recovery/spawn extent than this wall.
ARENA_LINEAR_SCALE = 1.9
ARENA_FLOOR_HALF_EXTENT = 52.0 * ARENA_LINEAR_SCALE
PLAYABLE_HALF_EXTENT = 46.0 * ARENA_LINEAR_SCALE
BOUNDARY_TREE_COUNT_PER_SIDE = 20
BOUNDARY_WALL_HEIGHT = 12.0
BOUNDARY_WALL_THICKNESS = 3.0
EXPECTED_ARCHITECTURE_BOX_COLLIDER_COUNT = 15
EXPECTED_ARCHITECTURE_CONVEX_HULL_COUNT = 3
EVENT_MARKER_SEGMENTS = 72
BARRIER_DOME_RADIAL_SEGMENTS = 32
BARRIER_DOME_HEIGHT_SEGMENTS = 8

# These IDs were authored by the Editor before this arena became generator-owned.
# Keeping them explicit makes regeneration byte-stable without churning every
# entity's folder assignment.
EDITOR_FOLDERS = (
    ("13c1b132-e76f-4d4d-9fc2-9f189c6281a1", "Gameplay", "", True),
    ("f3a20c43-626a-4052-8957-03f8c31ec1a2", "Event Anchors", "13c1b132-e76f-4d4d-9fc2-9f189c6281a1", False),
    ("955031f8-7717-4e68-93df-d693316611a3", "World", "", True),
    ("277dd45a-836e-41b5-842a-4c73641371a4", "Terrain", "955031f8-7717-4e68-93df-d693316611a3", False),
    ("c5ed942d-ac30-49b1-a997-58922aeab1a5", "Architecture", "955031f8-7717-4e68-93df-d693316611a3", False),
    ("8fd35199-81f9-4773-b184-396afc4fe1a6", "Vegetation", "955031f8-7717-4e68-93df-d693316611a3", False),
    ("328152c2-b52a-46a9-9813-0c42b3cc11a7", "Rocks & Crystals", "955031f8-7717-4e68-93df-d693316611a3", False),
    ("9cb38fba-b841-4fd3-8341-93c15d02b1a8", "Water", "955031f8-7717-4e68-93df-d693316611a3", False),
    ("540e60ec-456a-4ca2-aea0-a84e8da731a9", "Background", "955031f8-7717-4e68-93df-d693316611a3", False),
    ("cd733c3e-db90-4baa-b141-6a4ecf8631aa", "Collision", "955031f8-7717-4e68-93df-d693316611a3", False),
    ("44daaf4d-edbd-4f7a-91a3-fd4e2579d1ab", "Lighting & Rendering", "", False),
)

EDITOR_FOLDER_IDS = {name: folder_id for folder_id, name, _, _ in EDITOR_FOLDERS}

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]
Color = Tuple[float, float, float, float]


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def rounded(value: float) -> float:
    result = round(float(value), 6)
    return 0.0 if result == -0.0 else result


def vec3(values: Sequence[float]) -> list[float]:
    return [rounded(values[0]), rounded(values[1]), rounded(values[2])]


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(value: Vec3) -> Vec3:
    length = math.sqrt(value[0] ** 2 + value[1] ** 2 + value[2] ** 2)
    if length <= 1.0e-8:
        return 0.0, 1.0, 0.0
    return value[0] / length, value[1] / length, value[2] / length


def material_path(name: str) -> str:
    return f"{ASSET_MODEL_ROOT}/Materials/{name}.hmat"


@dataclass
class MeshBuilder:
    name: str
    positions: list[Vec3] = field(default_factory=list)
    normals: list[Vec3] = field(default_factory=list)
    texcoords: list[Vec2] = field(default_factory=list)
    primitive_indices: dict[str, list[int]] = field(default_factory=dict)

    def triangle(
        self,
        material: str,
        a: Vec3,
        b: Vec3,
        c: Vec3,
        uvs: tuple[Vec2, Vec2, Vec2] = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0)),
    ) -> None:
        face_cross = cross(subtract(b, a), subtract(c, a))
        if sum(component * component for component in face_cross) <= 1.0e-12:
            return
        normal = normalize(face_cross)
        first = len(self.positions)
        self.positions.extend((a, b, c))
        self.normals.extend((normal, normal, normal))
        self.texcoords.extend(uvs)
        self.primitive_indices.setdefault(material, []).extend(
            (first, first + 1, first + 2)
        )

    def quad(
        self,
        material: str,
        a: Vec3,
        b: Vec3,
        c: Vec3,
        d: Vec3,
    ) -> None:
        self.triangle(material, a, b, c, ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0)))
        self.triangle(material, a, c, d, ((0.0, 0.0), (1.0, 1.0), (1.0, 0.0)))

    @property
    def triangle_count(self) -> int:
        return sum(len(indices) for indices in self.primitive_indices.values()) // 3


def add_box(
    mesh: MeshBuilder,
    center: Vec3,
    size: Vec3,
    top_material: str,
    side_material: str | None = None,
    bottom_material: str | None = None,
) -> None:
    side_material = side_material or top_material
    bottom_material = bottom_material or side_material
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    x0, x1 = center[0] - hx, center[0] + hx
    y0, y1 = center[1] - hy, center[1] + hy
    z0, z1 = center[2] - hz, center[2] + hz
    mesh.quad(top_material, (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0))
    mesh.quad(bottom_material, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
    mesh.quad(side_material, (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
    mesh.quad(side_material, (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))
    mesh.quad(side_material, (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))
    mesh.quad(side_material, (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))


def add_ramp(mesh: MeshBuilder, top_material: str, side_material: str) -> None:
    low_left = (-0.5, -0.5, -0.5)
    low_right = (0.5, -0.5, -0.5)
    base_left = (-0.5, -0.5, 0.5)
    base_right = (0.5, -0.5, 0.5)
    high_left = (-0.5, 0.5, 0.5)
    high_right = (0.5, 0.5, 0.5)
    mesh.triangle(top_material, low_left, high_left, high_right)
    mesh.triangle(top_material, low_left, high_right, low_right)
    mesh.triangle(side_material, low_left, low_right, base_right)
    mesh.triangle(side_material, low_left, base_right, base_left)
    mesh.triangle(side_material, low_left, base_left, high_left)
    mesh.triangle(side_material, low_right, high_right, base_right)
    mesh.triangle(side_material, base_left, base_right, high_right)
    mesh.triangle(side_material, base_left, high_right, high_left)


def polygon_signed_area(outline: Sequence[Vec2]) -> float:
    return 0.5 * sum(
        outline[index][0] * outline[(index + 1) % len(outline)][1]
        - outline[(index + 1) % len(outline)][0] * outline[index][1]
        for index in range(len(outline))
    )


def clockwise_outline(outline: Sequence[Vec2]) -> tuple[Vec2, ...]:
    if len(outline) < 3:
        raise ValueError("A terrain outline needs at least three vertices")
    result = tuple(outline)
    return tuple(reversed(result)) if polygon_signed_area(result) > 0.0 else result


def add_polygon_prism(
    mesh: MeshBuilder,
    outline: Sequence[Vec2],
    top_y: float,
    bottom_y: float,
    top_material: str,
    side_materials: str | Sequence[str],
) -> None:
    """Add a convex low-poly terrace with a distinct top and faceted skirt."""
    points = clockwise_outline(outline)
    if bottom_y >= top_y:
        raise ValueError(f"Terrain prism bottom {bottom_y} must be below top {top_y}")
    side_palette = (
        (side_materials,)
        if isinstance(side_materials, str)
        else tuple(side_materials)
    )
    if not side_palette:
        raise ValueError("Terrain prism needs at least one side material")

    center_x = sum(point[0] for point in points) / len(points)
    center_z = sum(point[1] for point in points) / len(points)
    top_center = (center_x, top_y, center_z)
    bottom_center = (center_x, bottom_y, center_z)
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        top_current = (point[0], top_y, point[1])
        top_following = (following[0], top_y, following[1])
        bottom_current = (point[0], bottom_y, point[1])
        bottom_following = (following[0], bottom_y, following[1])
        mesh.triangle(top_material, top_center, top_current, top_following)
        mesh.triangle(side_palette[index % len(side_palette)], bottom_current, top_current, top_following)
        mesh.triangle(side_palette[index % len(side_palette)], bottom_current, top_following, bottom_following)
        mesh.triangle(side_palette[0], bottom_center, bottom_following, bottom_current)


def add_wide_ramp(
    mesh: MeshBuilder,
    low_center: Vec2,
    high_center: Vec2,
    width: float,
    low_y: float,
    high_y: float,
    bottom_y: float,
    top_material: str,
    side_material: str,
) -> None:
    """Add a broad convex wedge between two world-space centers."""
    delta_x = high_center[0] - low_center[0]
    delta_z = high_center[1] - low_center[1]
    length = math.sqrt(delta_x * delta_x + delta_z * delta_z)
    if length <= 1.0e-5 or width <= 0.0 or high_y <= low_y:
        raise ValueError("Wide ramp dimensions must be positive")
    direction_x = delta_x / length
    direction_z = delta_z / length
    right_x = direction_z * width * 0.5
    right_z = -direction_x * width * 0.5

    low_left = (low_center[0] - right_x, low_y, low_center[1] - right_z)
    low_right = (low_center[0] + right_x, low_y, low_center[1] + right_z)
    high_left = (high_center[0] - right_x, high_y, high_center[1] - right_z)
    high_right = (high_center[0] + right_x, high_y, high_center[1] + right_z)
    base_low_left = (low_left[0], bottom_y, low_left[2])
    base_low_right = (low_right[0], bottom_y, low_right[2])
    base_high_left = (high_left[0], bottom_y, high_left[2])
    base_high_right = (high_right[0], bottom_y, high_right[2])

    mesh.quad(top_material, low_left, high_left, high_right, low_right)
    mesh.quad(side_material, base_low_left, low_left, low_right, base_low_right)
    mesh.quad(side_material, base_high_right, high_right, high_left, base_high_left)
    mesh.quad(side_material, base_low_left, base_high_left, high_left, low_left)
    mesh.quad(side_material, base_low_right, low_right, high_right, base_high_right)
    mesh.quad(side_material, base_low_left, base_low_right, base_high_right, base_high_left)


def add_flat_polygon(
    mesh: MeshBuilder,
    outline: Sequence[Vec2],
    y: float,
    material: str,
) -> None:
    points = clockwise_outline(outline)
    center = (
        sum(point[0] for point in points) / len(points),
        y,
        sum(point[1] for point in points) / len(points),
    )
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        mesh.triangle(
            material,
            center,
            (point[0], y, point[1]),
            (following[0], y, following[1]),
        )


def add_flat_ring(
    mesh: MeshBuilder,
    inner_radius: float,
    outer_radius: float,
    y: float,
    material: str,
    segments: int = 24,
) -> None:
    for index in range(segments):
        angle0 = math.tau * index / segments
        angle1 = math.tau * (index + 1) / segments
        inner0 = (math.cos(angle0) * inner_radius, y, math.sin(angle0) * inner_radius)
        outer0 = (math.cos(angle0) * outer_radius, y, math.sin(angle0) * outer_radius)
        inner1 = (math.cos(angle1) * inner_radius, y, math.sin(angle1) * inner_radius)
        outer1 = (math.cos(angle1) * outer_radius, y, math.sin(angle1) * outer_radius)
        mesh.quad(material, inner0, inner1, outer1, outer0)


def add_flat_arc(
    mesh: MeshBuilder,
    inner_radius: float,
    outer_radius: float,
    start_angle: float,
    end_angle: float,
    y: float,
    material: str,
    segments: int = 20,
) -> None:
    for index in range(segments):
        alpha0 = index / segments
        alpha1 = (index + 1) / segments
        angle0 = start_angle + (end_angle - start_angle) * alpha0
        angle1 = start_angle + (end_angle - start_angle) * alpha1
        inner0 = (math.cos(angle0) * inner_radius, y, math.sin(angle0) * inner_radius)
        outer0 = (math.cos(angle0) * outer_radius, y, math.sin(angle0) * outer_radius)
        inner1 = (math.cos(angle1) * inner_radius, y, math.sin(angle1) * inner_radius)
        outer1 = (math.cos(angle1) * outer_radius, y, math.sin(angle1) * outer_radius)
        mesh.quad(material, inner0, inner1, outer1, outer0)


def add_star_disc(
    mesh: MeshBuilder,
    outer_radius: float,
    inner_radius: float,
    y: float,
    material: str,
    points: int = 6,
) -> None:
    outline = []
    for index in range(points * 2):
        angle = -math.pi * 0.5 + math.pi * index / points
        radius = outer_radius if index % 2 == 0 else inner_radius
        outline.append((math.cos(angle) * radius, math.sin(angle) * radius))
    add_flat_polygon(mesh, outline, y, material)


def add_vertical_torus(
    mesh: MeshBuilder,
    center: Vec3,
    major_radius: float,
    minor_radius: float,
    material: str,
    major_segments: int = 24,
    minor_segments: int = 5,
) -> None:
    """Add a low-poly torus in the local XY plane."""
    cx, cy, cz = center

    def point(major_index: int, minor_index: int) -> Vec3:
        major_angle = math.tau * major_index / major_segments
        minor_angle = math.tau * minor_index / minor_segments
        radial = major_radius + math.cos(minor_angle) * minor_radius
        return (
            cx + math.cos(major_angle) * radial,
            cy + math.sin(major_angle) * radial,
            cz + math.sin(minor_angle) * minor_radius,
        )

    for major_index in range(major_segments):
        for minor_index in range(minor_segments):
            mesh.quad(
                material,
                point(major_index, minor_index),
                point(major_index + 1, minor_index),
                point(major_index + 1, minor_index + 1),
                point(major_index, minor_index + 1),
            )


def add_vertical_beam(
    mesh: MeshBuilder,
    start: Vec2,
    end: Vec2,
    width: float,
    depth: float,
    material: str,
) -> None:
    """Add a closed rectangular beam between XY points."""
    delta_x = end[0] - start[0]
    delta_y = end[1] - start[1]
    length = math.sqrt(delta_x * delta_x + delta_y * delta_y)
    if length <= 1.0e-6:
        return
    offset_x = -delta_y / length * width * 0.5
    offset_y = delta_x / length * width * 0.5
    front_z = depth * 0.5
    back_z = -front_z
    front = (
        (start[0] + offset_x, start[1] + offset_y, front_z),
        (end[0] + offset_x, end[1] + offset_y, front_z),
        (end[0] - offset_x, end[1] - offset_y, front_z),
        (start[0] - offset_x, start[1] - offset_y, front_z),
    )
    back = tuple((point[0], point[1], back_z) for point in front)
    mesh.quad(material, front[3], front[2], front[1], front[0])
    mesh.quad(material, back[0], back[1], back[2], back[3])
    for index in range(4):
        following = (index + 1) % 4
        mesh.quad(
            material,
            front[index],
            front[following],
            back[following],
            back[index],
        )


def add_helical_ribbon(
    mesh: MeshBuilder,
    base_y: float,
    height: float,
    radius: float,
    width: float,
    turns: float,
    phase: float,
    material: str,
    segments: int = 28,
) -> None:
    """Add a double-sided-looking ribbon around the local Y axis."""
    for index in range(segments):
        alpha0 = index / segments
        alpha1 = (index + 1) / segments
        angle0 = phase + math.tau * turns * alpha0
        angle1 = phase + math.tau * turns * alpha1
        inner_radius = max(0.05, radius - width * 0.5)
        outer_radius = radius + width * 0.5
        y0 = base_y + height * alpha0
        y1 = base_y + height * alpha1
        mesh.quad(
            material,
            (math.cos(angle0) * inner_radius, y0, math.sin(angle0) * inner_radius),
            (math.cos(angle1) * inner_radius, y1, math.sin(angle1) * inner_radius),
            (math.cos(angle1) * outer_radius, y1, math.sin(angle1) * outer_radius),
            (math.cos(angle0) * outer_radius, y0, math.sin(angle0) * outer_radius),
        )


def add_hemisphere(
    mesh: MeshBuilder,
    material: str,
    radial_segments: int = 32,
    height_segments: int = 8,
) -> None:
    """Add a sparse unit-radius energy dome rooted on the local XZ plane.

    A filled transparent hemisphere layers color across nearly every screen
    pixel while the camera is inside it.  Thin latitude and meridian ribbons
    retain a readable protective-dome silhouette without obscuring combat.
    """
    if radial_segments < 8 or height_segments < 2:
        raise ValueError("Hemisphere tessellation is too low")

    def point(azimuth: float, elevation: float) -> Vec3:
        horizontal_radius = math.cos(elevation)
        return (
            math.cos(azimuth) * horizontal_radius,
            math.sin(elevation),
            math.sin(azimuth) * horizontal_radius,
        )

    latitude_indices = sorted(set((
        0,
        max(1, height_segments // 3),
        max(1, height_segments * 2 // 3),
        max(1, height_segments - 1),
    )))
    elevation_step = math.pi * 0.5 / height_segments
    for height_index in latitude_indices:
        center_elevation = elevation_step * height_index
        half_width = 0.012 if height_index == 0 else 0.008
        low_elevation = max(0.0, center_elevation - half_width)
        high_elevation = min(math.pi * 0.5 - 0.002, center_elevation + half_width)
        for radial_index in range(radial_segments):
            azimuth0 = math.tau * radial_index / radial_segments
            azimuth1 = math.tau * (radial_index + 1) / radial_segments
            mesh.quad(
                material,
                point(azimuth0, low_elevation),
                point(azimuth0, high_elevation),
                point(azimuth1, high_elevation),
                point(azimuth1, low_elevation),
            )

    meridian_count = 8
    meridian_half_width = math.tau / radial_segments * 0.065
    for meridian_index in range(meridian_count):
        center_azimuth = math.tau * meridian_index / meridian_count
        for height_index in range(height_segments):
            elevation0 = elevation_step * height_index
            elevation1 = elevation_step * (height_index + 1)
            mesh.quad(
                material,
                point(center_azimuth - meridian_half_width, elevation0),
                point(center_azimuth - meridian_half_width, elevation1),
                point(center_azimuth + meridian_half_width, elevation1),
                point(center_azimuth + meridian_half_width, elevation0),
            )


def add_path_strip(
    mesh: MeshBuilder,
    centers: Sequence[Vec2],
    width: float,
    material: str,
    closed: bool = False,
    vertical_offset: float = 0.035,
) -> None:
    if len(centers) < (3 if closed else 2):
        raise ValueError("A path strip needs at least two center points")
    source_centers = tuple(centers)
    dense_centers: list[Vec2] = []
    source_segment_count = len(source_centers) if closed else len(source_centers) - 1
    for index in range(source_segment_count):
        start = source_centers[index]
        end = source_centers[(index + 1) % len(source_centers)]
        length = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
        subdivision_count = max(1, math.ceil(length / 0.5))
        for subdivision in range(subdivision_count):
            progress = subdivision / subdivision_count
            dense_centers.append((
                start[0] + (end[0] - start[0]) * progress,
                start[1] + (end[1] - start[1]) * progress,
            ))
    if not closed:
        dense_centers.append(source_centers[-1])
    centers = dense_centers

    left_edge: list[Vec3] = []
    right_edge: list[Vec3] = []
    for index, center in enumerate(centers):
        previous = centers[(index - 1) % len(centers)] if closed else centers[max(0, index - 1)]
        following = centers[(index + 1) % len(centers)] if closed else centers[min(len(centers) - 1, index + 1)]
        tangent_x = following[0] - previous[0]
        tangent_z = following[1] - previous[1]
        tangent_length = max(1.0e-6, math.sqrt(tangent_x * tangent_x + tangent_z * tangent_z))
        right_x = tangent_z / tangent_length * width * 0.5
        right_z = -tangent_x / tangent_length * width * 0.5
        left_x, left_z = center[0] - right_x, center[1] - right_z
        right_edge_x, right_edge_z = center[0] + right_x, center[1] + right_z
        left_surface_y = terrain_surface_height(left_x, left_z)
        right_surface_y = terrain_surface_height(right_edge_x, right_edge_z)
        if left_surface_y is None or right_surface_y is None:
            raise ValueError(f"Path cross section at {center} has no terrain surface")
        if abs(left_surface_y - right_surface_y) > 0.12:
            raise ValueError(f"Path cross section at {center} straddles a terrain step")
        left_edge.append((left_x, left_surface_y + vertical_offset, left_z))
        right_edge.append((right_edge_x, right_surface_y + vertical_offset, right_edge_z))
    segment_count = len(centers) if closed else len(centers) - 1
    for index in range(segment_count):
        following_index = (index + 1) % len(centers)
        if max(
            abs(left_edge[following_index][1] - left_edge[index][1]),
            abs(right_edge[following_index][1] - right_edge[index][1]),
        ) > 0.12:
            raise ValueError(f"Path segment {index} crosses a terrain step")
        mesh.quad(
            material,
            left_edge[index],
            left_edge[following_index],
            right_edge[following_index],
            right_edge[index],
        )


def add_cylinder(
    mesh: MeshBuilder,
    center: Vec3,
    radius: float,
    height: float,
    material: str,
    segments: int = 7,
) -> None:
    bottom_y = center[1]
    top_y = center[1] + height
    bottom_center = (center[0], bottom_y, center[2])
    top_center = (center[0], top_y, center[2])
    for index in range(segments):
        angle0 = math.tau * index / segments
        angle1 = math.tau * (index + 1) / segments
        bottom0 = (center[0] + math.cos(angle0) * radius, bottom_y, center[2] + math.sin(angle0) * radius)
        bottom1 = (center[0] + math.cos(angle1) * radius, bottom_y, center[2] + math.sin(angle1) * radius)
        top0 = (bottom0[0], top_y, bottom0[2])
        top1 = (bottom1[0], top_y, bottom1[2])
        mesh.quad(material, bottom0, top0, top1, bottom1)
        mesh.triangle(material, top_center, top1, top0)
        mesh.triangle(material, bottom_center, bottom0, bottom1)


def add_cone(
    mesh: MeshBuilder,
    center: Vec3,
    radius: float,
    height: float,
    material: str,
    segments: int = 8,
) -> None:
    apex = (center[0], center[1] + height, center[2])
    for index in range(segments):
        angle0 = math.tau * index / segments
        angle1 = math.tau * (index + 1) / segments
        base0 = (center[0] + math.cos(angle0) * radius, center[1], center[2] + math.sin(angle0) * radius)
        base1 = (center[0] + math.cos(angle1) * radius, center[1], center[2] + math.sin(angle1) * radius)
        mesh.triangle(material, base0, apex, base1)
        mesh.triangle(material, center, base0, base1)


def add_ellipsoid(
    mesh: MeshBuilder,
    center: Vec3,
    radii: Vec3,
    material: str,
    rings: int = 4,
    segments: int = 7,
) -> None:
    def point(ring: int, segment: int) -> Vec3:
        theta = math.pi * ring / rings
        phi = math.tau * segment / segments
        return (
            center[0] + math.sin(theta) * math.cos(phi) * radii[0],
            center[1] + math.cos(theta) * radii[1],
            center[2] + math.sin(theta) * math.sin(phi) * radii[2],
        )

    for ring in range(rings):
        for segment in range(segments):
            p00 = point(ring, segment)
            p01 = point(ring, segment + 1)
            p10 = point(ring + 1, segment)
            p11 = point(ring + 1, segment + 1)
            mesh.triangle(material, p00, p01, p11)
            mesh.triangle(material, p00, p11, p10)


def add_octahedron(
    mesh: MeshBuilder,
    center: Vec3,
    radius: float,
    height: float,
    material: str,
) -> None:
    top = (center[0], center[1] + height * 0.5, center[2])
    bottom = (center[0], center[1] - height * 0.5, center[2])
    ring = (
        (center[0] + radius, center[1], center[2]),
        (center[0], center[1], center[2] + radius),
        (center[0] - radius, center[1], center[2]),
        (center[0], center[1], center[2] - radius),
    )
    for index in range(4):
        current = ring[index]
        following = ring[(index + 1) % 4]
        mesh.triangle(material, top, following, current)
        mesh.triangle(material, bottom, current, following)


def add_grass_blade(mesh: MeshBuilder, x: float, z: float, angle: float, height: float, material: str) -> None:
    width = height * 0.18
    right = (math.cos(angle) * width, 0.0, math.sin(angle) * width)
    forward = (-math.sin(angle) * width * 0.22, height, math.cos(angle) * width * 0.22)
    left_base = (x - right[0], 0.0, z - right[2])
    right_base = (x + right[0], 0.0, z + right[2])
    tip = (x + forward[0], forward[1], z + forward[2])
    mesh.triangle(material, left_base, tip, right_base)


@dataclass(frozen=True)
class MaterialSpec:
    color: Color
    metallic: float
    roughness: float
    emissive: Color | None = None
    double_sided: bool = False
    alpha_mode: str = "OPAQUE"
    detail_family: str = ""


def build_materials() -> dict[str, MaterialSpec]:
    """Shared Verdant Rift palette; large surfaces reuse one macro texture set."""
    return {
        "MeadowLight": MaterialSpec((0.42, 0.68, 0.25, 1.0), 0.0, 0.86, detail_family="ground"),
        "MeadowMid": MaterialSpec((0.23, 0.53, 0.25, 1.0), 0.0, 0.90, detail_family="ground"),
        "MeadowDark": MaterialSpec((0.11, 0.34, 0.25, 1.0), 0.0, 0.94, detail_family="ground"),
        "EarthWarm": MaterialSpec((0.53, 0.31, 0.16, 1.0), 0.0, 0.93, detail_family="stone"),
        "CliffDark": MaterialSpec((0.31, 0.20, 0.18, 1.0), 0.0, 0.97, detail_family="stone"),
        "PathDirt": MaterialSpec((0.67, 0.45, 0.23, 1.0), 0.0, 0.91, detail_family="ground"),
        "Bark": MaterialSpec((0.34, 0.19, 0.11, 1.0), 0.0, 0.95, detail_family="organic"),
        "Foliage": MaterialSpec((0.16, 0.50, 0.25, 1.0), 0.0, 0.89, double_sided=True, detail_family="organic"),
        "Blossom": MaterialSpec((0.97, 0.53, 0.68, 1.0), 0.0, 0.84, double_sided=True, detail_family="organic"),
        "ShrineCoral": MaterialSpec((0.82, 0.18, 0.17, 1.0), 0.0, 0.78, detail_family="stone"),
        "ShrineGold": MaterialSpec((0.96, 0.64, 0.18, 1.0), 0.12, 0.61),
        "RuinStone": MaterialSpec((0.48, 0.51, 0.52, 1.0), 0.0, 0.94, detail_family="stone"),
        "RiftCrystal": MaterialSpec((0.18, 0.65, 0.86, 1.0), 0.04, 0.42, (0.02, 0.12, 0.19, 1.0)),
        "RiftGlow": MaterialSpec((0.54, 0.93, 1.00, 1.0), 0.06, 0.30, (0.10, 0.42, 0.60, 1.0)),
        "WetlandTeal": MaterialSpec((0.12, 0.43, 0.41, 1.0), 0.0, 0.88, detail_family="ground"),
        "Water": MaterialSpec((0.16, 0.57, 0.69, 1.0), 0.0, 0.22, (0.02, 0.07, 0.10, 1.0), True),
        "BarrierStar": MaterialSpec(
            (0.50, 0.64, 1.00, 0.12), 0.0, 0.26,
            (0.08, 0.12, 0.30, 1.0), True, "BLEND",
        ),
        "BarrierThunder": MaterialSpec(
            (1.00, 0.72, 0.18, 0.13), 0.0, 0.28,
            (0.30, 0.16, 0.02, 1.0), True, "BLEND",
        ),
        "BarrierWater": MaterialSpec(
            (0.16, 0.78, 1.00, 0.11), 0.0, 0.22,
            (0.02, 0.18, 0.28, 1.0), True, "BLEND",
        ),
        "BarrierWind": MaterialSpec(
            (0.38, 1.00, 0.72, 0.10), 0.0, 0.30,
            (0.04, 0.24, 0.14, 1.0), True, "BLEND",
        ),
    }


def texture_slot(source: str = "") -> dict[str, object]:
    return {
        "texCoord": 0,
        "textureRes": {
            "sampler": {
                "magFilter": 9729,
                "minFilter": 9729,
                "wrapS": 33071,
                "wrapT": 33071,
            },
            "textureSourcePath": source,
        },
    }


def material_json(
    name: str,
    specification: MaterialSpec,
) -> dict[str, object]:
    bUseDetail = bool(specification.detail_family)
    normal_texture = texture_slot(DETAIL_NORMAL_PATH if bUseDetail else "")
    normal_texture["scale"] = 0.32 if bUseDetail else 1.0
    occlusion_texture = texture_slot(DETAIL_AO_PATH if bUseDetail else "")
    occlusion_texture["strength"] = 0.42 if bUseDetail else 1.0
    return {
        "Properties": {
            "alphaCutoff": 0.5,
            "alphaMode": specification.alpha_mode,
            "bUseAlbedoMap": bUseDetail,
            "bUseAoMap": bUseDetail,
            "bUseEmissiveMap": specification.emissive is not None,
            "bUseMetallicRoughnessMap": bUseDetail,
            "bUseNormalMap": bUseDetail,
            "doubleSided": specification.double_sided,
            "emissiveFactor": list((specification.emissive or (0.0, 0.0, 0.0, 1.0))[:3]),
            "emissiveTexture": texture_slot("white" if specification.emissive is not None else ""),
            "name": name,
            "normalTexture": normal_texture,
            "occlusionTexture": occlusion_texture,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(specification.color),
                "baseColorTexture": texture_slot(DETAIL_ALBEDO_PATH if bUseDetail else ""),
                "metallicFactor": specification.metallic,
                "metallicRoughnessTexture": texture_slot(DETAIL_MR_PATH if bUseDetail else ""),
                "roughnessFactor": specification.roughness,
            },
        },
        "ShaderPath": "Shaders/BasePBR.hlsl",
        "Type": "Default",
    }


def build_meshes() -> dict[str, MeshBuilder]:
    meshes: dict[str, MeshBuilder] = {}

    for plate in TERRAIN_PLATES:
        terrain = MeshBuilder(f"TerrainPlate_{plate.name}")
        add_polygon_prism(
            terrain,
            plate.outline,
            plate.top_y,
            plate.bottom_y,
            plate.top_material,
            plate.side_materials,
        )
        meshes[terrain.name] = terrain

    for ramp_spec in RAMP_SPECS:
        ramp = MeshBuilder(f"TerrainRamp_{ramp_spec.name}")
        add_wide_ramp(
            ramp,
            ramp_spec.low_center,
            ramp_spec.high_center,
            ramp_spec.width,
            ramp_spec.low_y,
            ramp_spec.high_y,
            ramp_spec.bottom_y,
            ramp_spec.top_material,
            ramp_spec.side_material,
        )
        meshes[ramp.name] = ramp

    paths = MeshBuilder("DirtPaths")
    for centers, width, closed, vertical_offset in authored_path_specs():
        add_path_strip(paths, centers, width, "PathDirt", closed, vertical_offset)
    # These short aprons bridge the staggered lower/upper north-ridge ramps on
    # the same +3 m terrace without sampling across either sloped footprint.
    add_flat_polygon(paths, ((-18.5, 44.1), (-9.5, 44.1), (-3.5, 46.1), (-12.5, 46.1)), 3.064, "PathDirt")
    add_flat_polygon(paths, ((9.5, 44.1), (18.5, 44.1), (12.5, 46.1), (3.5, 46.1)), 3.064, "PathDirt")
    meshes[paths.name] = paths

    star_plinth = MeshBuilder("StarPlinth")
    add_cylinder(star_plinth, (0.0, 0.0, 0.0), 4.8, 0.16, "RuinStone", 12)
    add_star_disc(star_plinth, 4.1, 1.9, 0.17, "RiftGlow", 6)
    meshes[star_plinth.name] = star_plinth

    for name, material, motif in (
        ("West", "ShrineGold", "thunder"),
        ("North", "RiftGlow", "star"),
        ("East", "Foliage", "wind"),
        ("South", "RiftCrystal", "water"),
    ):
        marker = MeshBuilder(f"EventRing_{name}")
        add_flat_ring(
            marker,
            0.88,
            1.0,
            0.0,
            material,
            EVENT_MARKER_SEGMENTS,
        )
        if motif == "star":
            add_star_disc(marker, 0.54, 0.24, 0.008, material, 6)
        elif motif == "thunder":
            add_flat_polygon(
                marker,
                (
                    (-0.12, 0.58), (0.31, 0.16), (0.10, 0.14),
                    (0.28, -0.55), (-0.34, 0.02), (-0.10, 0.04),
                ),
                0.008,
                material,
            )
        elif motif == "water":
            for offset in (-0.26, 0.0, 0.26):
                centers = tuple(
                    (
                        -0.58 + index * 0.145,
                        offset + math.sin(index * math.pi * 0.5) * 0.07,
                    )
                    for index in range(9)
                )
                add_path_strip(marker, centers, 0.055, material, False, 0.008)
        else:
            add_flat_arc(marker, 0.18, 0.25, -0.25, math.pi * 1.30, 0.008, material, 18)
            add_flat_arc(marker, 0.36, 0.43, 0.60, math.pi * 1.72, 0.008, material, 22)
            add_flat_arc(marker, 0.54, 0.61, 1.55, math.pi * 2.05, 0.008, material, 24)
        meshes[marker.name] = marker

    star_landmark = MeshBuilder("RegionLandmark_Star")
    add_cylinder(star_landmark, (0.0, 0.0, 0.0), 1.25, 0.34, "RuinStone", 12)
    add_cylinder(star_landmark, (0.0, 0.34, 0.0), 0.52, 4.85, "RuinStone", 10)
    add_vertical_torus(
        star_landmark, (0.0, 5.05, 0.0), 2.30, 0.15, "RiftGlow", 32, 5,
    )
    for ray_index in range(8):
        angle = math.tau * ray_index / 8.0
        add_vertical_beam(
            star_landmark,
            (math.cos(angle) * 0.30, 5.05 + math.sin(angle) * 0.30),
            (math.cos(angle) * 1.62, 5.05 + math.sin(angle) * 1.62),
            0.13,
            0.16,
            "RiftGlow",
        )
    add_octahedron(star_landmark, (0.0, 5.05, 0.0), 0.72, 1.48, "RiftCrystal")
    for center, radii in (
        ((-3.15, 3.10, 0.55), (0.68, 0.45, 0.58)),
        ((2.95, 4.15, -0.45), (0.56, 0.38, 0.49)),
        ((-2.30, 6.25, -0.20), (0.38, 0.28, 0.34)),
    ):
        add_ellipsoid(star_landmark, center, radii, "RuinStone", 2, 7)
    meshes[star_landmark.name] = star_landmark

    thunder_landmark = MeshBuilder("RegionLandmark_Thunder")
    add_cylinder(thunder_landmark, (0.0, 0.0, 0.0), 2.35, 0.32, "CliffDark", 10)
    add_flat_ring(thunder_landmark, 1.55, 2.10, 0.33, "ShrineGold", 32)
    add_cone(thunder_landmark, (0.0, 0.32, 0.0), 0.88, 7.10, "CliffDark", 9)
    for x, z, height in ((-1.48, -0.55, 4.70), (1.42, 0.62, 5.35)):
        add_cone(thunder_landmark, (x, 0.32, z), 0.42, height, "RuinStone", 7)
        add_octahedron(
            thunder_landmark,
            (x, height + 0.32, z),
            0.26,
            0.72,
            "ShrineGold",
        )
    bolt_points = ((-0.95, 7.55), (0.28, 6.15), (-0.32, 4.92), (0.92, 3.35), (0.20, 2.88), (1.20, 1.12))
    for start, end in zip(bolt_points, bolt_points[1:]):
        add_vertical_beam(thunder_landmark, start, end, 0.42, 0.30, "ShrineGold")
    add_vertical_beam(thunder_landmark, (0.28, 6.15), (1.48, 5.65), 0.24, 0.24, "ShrineGold")
    add_vertical_beam(thunder_landmark, (-0.32, 4.92), (-1.42, 4.18), 0.24, 0.24, "ShrineGold")
    meshes[thunder_landmark.name] = thunder_landmark

    water_landmark = MeshBuilder("RegionLandmark_Water")
    add_cylinder(water_landmark, (0.0, 0.0, 0.0), 3.00, 0.28, "RuinStone", 16)
    add_flat_ring(water_landmark, 1.82, 2.72, 0.29, "Water", 48)
    add_cylinder(water_landmark, (0.0, 0.28, 0.0), 0.48, 2.45, "RiftCrystal", 10)
    add_octahedron(water_landmark, (0.0, 2.92, 0.0), 0.62, 1.42, "RiftGlow")
    for index in range(5):
        angle = math.tau * index / 5.0 + 0.25
        radius = 1.75
        add_octahedron(
            water_landmark,
            (math.cos(angle) * radius, 0.74, math.sin(angle) * radius),
            0.30,
            0.96 + (index % 2) * 0.24,
            "RiftCrystal",
        )
    add_helical_ribbon(water_landmark, 0.42, 3.90, 1.34, 0.18, 0.82, 0.0, "BarrierWater", 30)
    add_helical_ribbon(water_landmark, 0.42, 3.90, 1.34, 0.18, 0.82, math.pi, "BarrierWater", 30)
    meshes[water_landmark.name] = water_landmark

    wind_landmark = MeshBuilder("RegionLandmark_Wind")
    add_cylinder(wind_landmark, (0.0, 0.0, 0.0), 2.70, 0.28, "RuinStone", 14)
    for x in (-2.30, 2.30):
        add_cone(wind_landmark, (x, 0.28, 0.0), 0.48, 5.20, "RuinStone", 8)
        add_octahedron(wind_landmark, (x, 5.52, 0.0), 0.28, 0.76, "RiftCrystal")
    add_vertical_torus(
        wind_landmark, (0.0, 4.35, 0.0), 2.45, 0.14, "BarrierWind", 32, 5,
    )
    add_helical_ribbon(wind_landmark, 0.45, 6.60, 1.48, 0.22, 1.35, 0.0, "BarrierWind", 38)
    add_helical_ribbon(wind_landmark, 0.75, 5.85, 2.05, 0.16, 1.05, math.pi, "BarrierWind", 34)
    add_flat_arc(wind_landmark, 1.05, 1.24, -0.25, math.pi * 1.25, 0.31, "Foliage", 26)
    add_flat_arc(wind_landmark, 1.50, 1.69, 0.75, math.pi * 1.85, 0.32, "Foliage", 30)
    meshes[wind_landmark.name] = wind_landmark

    for region_name, material in (
        ("Star", "BarrierStar"),
        ("Thunder", "BarrierThunder"),
        ("Water", "BarrierWater"),
        ("Wind", "BarrierWind"),
    ):
        dome = MeshBuilder(f"BarrierDome_{region_name}")
        add_hemisphere(
            dome,
            material,
            BARRIER_DOME_RADIAL_SEGMENTS,
            BARRIER_DOME_HEIGHT_SEGMENTS,
        )
        meshes[dome.name] = dome

    deciduous = MeshBuilder("DeciduousTree")
    add_cylinder(deciduous, (0.0, 0.0, 0.0), 0.28, 3.0, "Bark")
    add_ellipsoid(deciduous, (-0.55, 3.2, 0.0), (1.35, 1.15, 1.15), "Foliage")
    add_ellipsoid(deciduous, (0.65, 3.25, 0.20), (1.30, 1.25, 1.20), "Foliage")
    add_ellipsoid(deciduous, (0.0, 4.05, -0.20), (1.45, 1.20, 1.30), "Foliage")
    meshes[deciduous.name] = deciduous

    blossom = MeshBuilder("BlossomTree")
    add_cylinder(blossom, (0.0, 0.0, 0.0), 0.24, 2.9, "Bark")
    add_ellipsoid(blossom, (-0.60, 3.05, 0.10), (1.25, 1.00, 1.10), "Blossom")
    add_ellipsoid(blossom, (0.65, 3.20, -0.10), (1.20, 1.10, 1.15), "Blossom")
    add_ellipsoid(blossom, (0.05, 3.95, 0.05), (1.38, 1.15, 1.25), "Blossom")
    meshes[blossom.name] = blossom

    pine = MeshBuilder("PineTree")
    add_cylinder(pine, (0.0, 0.0, 0.0), 0.23, 3.8, "Bark")
    add_cone(pine, (0.0, 1.25, 0.0), 1.55, 2.55, "MeadowDark", 8)
    add_cone(pine, (0.0, 2.25, 0.0), 1.20, 2.45, "MeadowDark", 8)
    add_cone(pine, (0.0, 3.20, 0.0), 0.82, 2.10, "MeadowDark", 8)
    meshes[pine.name] = pine

    rock = MeshBuilder("Rock")
    add_ellipsoid(rock, (0.0, 0.62, 0.0), (0.95, 0.72, 0.78), "RuinStone", 3, 7)
    meshes[rock.name] = rock

    grass = MeshBuilder("GrassTuft")
    for index in range(9):
        angle = math.tau * index / 9.0 + (index % 2) * 0.23
        radius = 0.16 if index else 0.0
        add_grass_blade(grass, math.cos(angle) * radius, math.sin(angle) * radius, angle, 0.72 + (index % 3) * 0.11, "Foliage")
    meshes[grass.name] = grass

    flower = MeshBuilder("Flower")
    add_cylinder(flower, (0.0, 0.0, 0.0), 0.045, 0.72, "Foliage", 5)
    for index in range(6):
        angle = math.tau * index / 6.0
        inner = (math.cos(angle) * 0.06, 0.72, math.sin(angle) * 0.06)
        left = (math.cos(angle - 0.34) * 0.28, 0.76, math.sin(angle - 0.34) * 0.28)
        right = (math.cos(angle + 0.34) * 0.28, 0.76, math.sin(angle + 0.34) * 0.28)
        flower.triangle("Blossom", inner, right, left)
    add_octahedron(flower, (0.0, 0.77, 0.0), 0.09, 0.12, "ShrineGold")
    meshes[flower.name] = flower

    mushroom = MeshBuilder("Mushroom")
    add_cylinder(mushroom, (0.0, 0.0, 0.0), 0.13, 0.48, "RuinStone", 6)
    add_ellipsoid(mushroom, (0.0, 0.50, 0.0), (0.47, 0.25, 0.47), "ShrineCoral", 3, 8)
    for angle in (0.2, 2.25, 4.35):
        add_ellipsoid(mushroom, (math.cos(angle) * 0.28, 0.70, math.sin(angle) * 0.28), (0.07, 0.035, 0.07), "ShrineGold", 2, 5)
    meshes[mushroom.name] = mushroom

    reeds = MeshBuilder("Reeds")
    for index in range(11):
        angle = math.tau * index / 11.0
        radius = 0.12 + (index % 3) * 0.09
        add_grass_blade(
            reeds,
            math.cos(angle) * radius,
            math.sin(angle) * radius,
            angle + 0.2,
            1.15 + (index % 4) * 0.16,
            "WetlandTeal",
        )
    meshes[reeds.name] = reeds

    shrine = MeshBuilder("ShrineGate")
    add_box(shrine, (-1.25, 2.05, 0.0), (0.34, 4.10, 0.44), "ShrineCoral")
    add_box(shrine, (1.25, 2.05, 0.0), (0.34, 4.10, 0.44), "ShrineCoral")
    add_box(shrine, (0.0, 3.65, 0.0), (3.45, 0.38, 0.62), "ShrineCoral")
    add_box(shrine, (0.0, 4.18, 0.0), (4.15, 0.30, 0.78), "Bark")
    add_box(shrine, (0.0, 3.66, -0.34), (0.72, 0.50, 0.16), "ShrineGold")
    meshes[shrine.name] = shrine

    crystal = MeshBuilder("Crystal")
    add_octahedron(crystal, (0.0, 0.90, 0.0), 0.50, 1.80, "RiftGlow")
    add_octahedron(crystal, (-0.42, 0.48, 0.12), 0.28, 0.96, "RiftCrystal")
    add_octahedron(crystal, (0.38, 0.40, -0.18), 0.24, 0.80, "RiftCrystal")
    meshes[crystal.name] = crystal

    for variant in range(1, 4):
        mountain = MeshBuilder(f"DistantMountain_{variant:02d}")
        mountain_material = ("MeadowDark", "CliffDark", "RuinStone")[variant - 1]
        add_cone(mountain, (0.0, 0.0, 0.0), 0.62 + variant * 0.05, 1.0, mountain_material, 7 + variant)
        add_cone(mountain, (0.0, 0.70, 0.0), 0.23 + variant * 0.015, 0.30, "RiftGlow", 7 + variant)
        meshes[mountain.name] = mountain

    experience = MeshBuilder("ExperienceCrystal")
    # Pickups need to remain visibly blue under bloom.  RiftGlow is intentionally
    # near-white for landmarks and washes out at this small on-screen size.
    add_octahedron(experience, (0.0, 0.50, 0.0), 0.32, 1.0, "RiftCrystal")
    meshes[experience.name] = experience

    water = MeshBuilder("WaterPlane")
    water.quad("Water", (-0.5, 0.0, -0.5), (-0.5, 0.0, 0.5), (0.5, 0.0, 0.5), (0.5, 0.0, -0.5))
    meshes[water.name] = water

    broken_obelisk = MeshBuilder("BrokenObelisk")
    add_box(broken_obelisk, (0.0, 0.8, 0.0), (0.9, 1.6, 0.9), "RuinStone")
    add_box(broken_obelisk, (0.08, 2.0, -0.03), (0.72, 0.9, 0.72), "RuinStone")
    add_octahedron(broken_obelisk, (0.08, 2.62, -0.03), 0.38, 0.75, "RiftCrystal")
    meshes[broken_obelisk.name] = broken_obelisk

    return meshes


def pack_float_vectors(values: Iterable[Sequence[float]]) -> bytes:
    output = bytearray()
    for value in values:
        output.extend(struct.pack("<" + "f" * len(value), *value))
    return bytes(output)


def mesh_payload(mesh: MeshBuilder) -> tuple[dict[str, object], bytes]:
    if not mesh.positions or not mesh.primitive_indices:
        raise ValueError(f"Mesh {mesh.name} has no geometry")

    position_bytes = pack_float_vectors(mesh.positions)
    normal_bytes = pack_float_vectors(mesh.normals)
    texcoord_bytes = pack_float_vectors(mesh.texcoords)
    binary = bytearray(position_bytes + normal_bytes + texcoord_bytes)

    views: list[dict[str, object]] = []
    accessors: list[dict[str, object]] = []

    def add_attribute_view(data: bytes, component_count: int, value_type: str, values: Sequence[Sequence[float]]) -> int:
        offset = sum(view["byteLength"] for view in views)
        view_index = len(views)
        views.append({
            "bufferIndex": 0,
            "byteLength": len(data),
            "byteOffset": offset,
            "byteStride": 0,
            "name": "",
            "target": 34962,
        })
        accessor_index = len(accessors)
        accessors.append({
            "bufferViewIndex": view_index,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(values),
            "max": [max(value[index] for value in values) for index in range(component_count)],
            "min": [min(value[index] for value in values) for index in range(component_count)],
            "name": "",
            "normalized": False,
            "type": value_type,
        })
        return accessor_index

    position_accessor = add_attribute_view(position_bytes, 3, "VEC3", mesh.positions)
    normal_accessor = add_attribute_view(normal_bytes, 3, "VEC3", mesh.normals)
    texcoord_accessor = add_attribute_view(texcoord_bytes, 2, "VEC2", mesh.texcoords)

    primitives: list[dict[str, object]] = []
    for material, indices in mesh.primitive_indices.items():
        index_offset = len(binary)
        index_bytes = struct.pack("<" + "I" * len(indices), *indices)
        binary.extend(index_bytes)
        view_index = len(views)
        views.append({
            "bufferIndex": 0,
            "byteLength": len(index_bytes),
            "byteOffset": index_offset,
            "byteStride": 0,
            "name": "",
            "target": 34963,
        })
        accessor_index = len(accessors)
        accessors.append({
            "bufferViewIndex": view_index,
            "byteOffset": 0,
            "componentType": 5125,
            "count": len(indices),
            "max": [max(indices)],
            "min": [min(indices)],
            "name": "",
            "normalized": False,
            "type": "SCALAR",
        })
        primitives.append({
            "attributes": {
                "POSITION": position_accessor,
                "NORMAL": normal_accessor,
                "TEXCOORD_0": texcoord_accessor,
            },
            "indices": accessor_index,
            "materialResPath": material_path(material),
            "mode": 4,
            "targets": [],
        })

    resource = {
        "accessorVec": accessors,
        "bufferVec": [{
            "byteLength": len(binary),
            "data": [],
            "name": "",
            "uri": f"{ASSET_MODEL_ROOT}/{mesh.name}.bin",
        }],
        "bufferViewVec": views,
        "name": mesh.name,
        "primitives": primitives,
        "skeletonPath": "",
        "version": 1,
        "weights": [],
    }
    return resource, bytes(binary)


def transform_component(
    translation: Vec3 = (0.0, 0.0, 0.0),
    rotation: Vec3 = (0.0, 0.0, 0.0),
    scale: Vec3 = (1.0, 1.0, 1.0),
) -> dict[str, object]:
    return {
        "ParentUuid": "",
        "Rotation": vec3(rotation),
        "Scale": vec3(scale),
        "Translation": vec3(translation),
    }


def rigidbody_component(shape: int) -> dict[str, object]:
    return {
        "AllowSleeping": True,
        "ColliderOffset": [0.0, 0.0, 0.0],
        "ColliderRotation": [0.0, 0.0, 0.0],
        "ColliderScale": [1.0, 1.0, 1.0],
        "EnableCCD": False,
        "IsTrigger": False,
        "Shape": shape,
        "Type": 0,
        "angularDamping": 0.05,
        "friction": 0.82,
        "linearDamping": 0.05,
        "mass": 0.0,
        "restitution": 0.0,
    }


def editor_folder_for_label(label: str) -> str:
    if label in ("Core/Player", "Core/GameDirector"):
        return EDITOR_FOLDER_IDS["Gameplay"]
    if label.startswith("Events/"):
        return EDITOR_FOLDER_IDS["Event Anchors"]
    if label.startswith("Terrain/"):
        return EDITOR_FOLDER_IDS["Terrain"]
    if label.startswith("Water/"):
        return EDITOR_FOLDER_IDS["Water"]
    if label.startswith("Backdrop/"):
        return EDITOR_FOLDER_IDS["Background"]
    if label.startswith("Boundary/Wall/") or label.startswith("Collision/"):
        return EDITOR_FOLDER_IDS["Collision"]
    if label.startswith((
        "Landmark/CentralStar",
        "Landmark/Ruins/",
        "Landmark/WestShrineGate/",
        "Landmark/Region/",
    )):
        return EDITOR_FOLDER_IDS["Architecture"]
    if label.startswith((
        "Landmark/FloatingRock/",
        "Landmark/Obelisk/",
        "Props/Crystal/",
        "Props/Rock/",
    )):
        return EDITOR_FOLDER_IDS["Rocks & Crystals"]
    if label.startswith(("Core/", "Lights/")):
        return EDITOR_FOLDER_IDS["Lighting & Rendering"]
    return EDITOR_FOLDER_IDS["Vegetation"]


class SceneBuilder:
    def __init__(self) -> None:
        self.entities: dict[str, dict[str, object]] = {}
        self.labels: set[str] = set()
        self.mesh_usage: Counter[str] = Counter()
        for folder_id, name, parent_folder_id, b_expanded in EDITOR_FOLDERS:
            self.entities[folder_id] = {
                "EditorEntityStateComponent": {
                    "bVisible": True,
                    "bLocked": False,
                    "FolderUuid": parent_folder_id,
                },
                "SceneFolderComponent": {"bExpanded": b_expanded},
                "TagComponent": {"Tag": name},
                "TransformComponent": transform_component(),
            }

    def stable_id(self, label: str) -> str:
        return str(uuid.uuid5(UUID_NAMESPACE, f"VerdantRift/{label}"))

    def add(self, label: str, components: dict[str, object]) -> str:
        if label in self.labels:
            raise ValueError(f"Duplicate entity label: {label}")
        entity_id = self.stable_id(label)
        if entity_id in self.entities:
            raise ValueError(f"UUID collision for entity label: {label}")
        self.labels.add(label)
        self.entities[entity_id] = {
            "EditorEntityStateComponent": {
                "bVisible": True,
                "bLocked": False,
                "FolderUuid": editor_folder_for_label(label),
            },
            **components,
        }
        mesh_component = components.get("MeshComponent")
        if isinstance(mesh_component, dict):
            self.mesh_usage[str(mesh_component["Path"])] += 1
        return entity_id

    def add_mesh(
        self,
        label: str,
        tag: str,
        mesh_name_or_path: str,
        translation: Vec3,
        rotation: Vec3 = (0.0, 0.0, 0.0),
        scale: Vec3 = (1.0, 1.0, 1.0),
        collider_shape: int | None = None,
    ) -> str:
        mesh_path = (
            mesh_name_or_path
            if mesh_name_or_path.endswith(".hmesh")
            else f"{ASSET_MODEL_ROOT}/{mesh_name_or_path}.hmesh"
        )
        components: dict[str, object] = {
            "MeshComponent": {"Path": mesh_path, "meshResPath": ""},
            "TagComponent": {"Tag": tag},
            "TransformComponent": transform_component(translation, rotation, scale),
        }
        if collider_shape is not None:
            components["Rigidbody3DComponent"] = rigidbody_component(collider_shape)
        return self.add(label, components)

    def add_box_collider(
        self,
        label: str,
        tag: str,
        translation: Vec3,
        scale: Vec3,
        rotation: Vec3 = (0.0, 0.0, 0.0),
    ) -> str:
        return self.add(
            label,
            {
                "Rigidbody3DComponent": rigidbody_component(1),
                "TagComponent": {"Tag": tag},
                "TransformComponent": transform_component(translation, rotation, scale),
            },
        )

    def add_local_box_collider(
        self,
        label: str,
        tag: str,
        mesh_translation: Vec3,
        mesh_rotation: Vec3,
        mesh_scale: Vec3,
        local_center: Vec3,
        local_size: Vec3,
    ) -> str:
        """Add a simple collider matching a yaw-rotated authored mesh part."""
        if abs(mesh_rotation[0]) > 1.0e-6 or abs(mesh_rotation[2]) > 1.0e-6:
            raise ValueError(f"{tag} local box collision currently supports yaw-only meshes")
        scaled_center = (
            local_center[0] * mesh_scale[0],
            local_center[1] * mesh_scale[1],
            local_center[2] * mesh_scale[2],
        )
        yaw = mesh_rotation[1]
        cosine = math.cos(yaw)
        sine = math.sin(yaw)
        world_center = (
            mesh_translation[0] + cosine * scaled_center[0] + sine * scaled_center[2],
            mesh_translation[1] + scaled_center[1],
            mesh_translation[2] - sine * scaled_center[0] + cosine * scaled_center[2],
        )
        world_size = (
            local_size[0] * mesh_scale[0],
            local_size[1] * mesh_scale[1],
            local_size[2] * mesh_scale[2],
        )
        return self.add_box_collider(
            label,
            tag,
            world_center,
            world_size,
            mesh_rotation,
        )


@dataclass(frozen=True)
class TerrainPlate:
    name: str
    outline: tuple[Vec2, ...]
    top_y: float
    bottom_y: float
    top_material: str
    side_materials: tuple[str, ...]


@dataclass(frozen=True)
class RampSpec:
    name: str
    region: str
    low_center: Vec2
    high_center: Vec2
    width: float
    low_y: float
    high_y: float
    bottom_y: float
    top_material: str = "PathDirt"
    side_material: str = "EarthWarm"

    @property
    def length(self) -> float:
        return math.sqrt(
            (self.high_center[0] - self.low_center[0]) ** 2
            + (self.high_center[1] - self.low_center[1]) ** 2
        )


@dataclass(frozen=True)
class EventAnchorSpec:
    name: str
    position: Vec3
    clear_radius: float
    marker_vertical_offset: float = 0.025


@dataclass(frozen=True)
class EventSpawnGroupSpec:
    tag_prefix: str
    anchor_name: str
    offsets: tuple[Vec2, ...]


@dataclass(frozen=True)
class ClusterSpec:
    name: str
    center: Vec2
    radius: Vec2
    count: int


@dataclass(frozen=True)
class RegionVisualSpec:
    region_id: str
    anchor_name: str
    landmark_mesh: str
    landmark_position: Vec2
    landmark_yaw: float
    footprint_radius: float


def irregular_ellipse_outline(
    center_x: float,
    center_z: float,
    radius_x: float,
    radius_z: float,
    segments: int,
    phase: float,
) -> tuple[Vec2, ...]:
    points = []
    for index in range(segments):
        angle = math.tau * index / segments
        modulation = 1.0 + 0.055 * math.sin(angle * 3.0 + phase) + 0.025 * math.sin(angle * 5.0 - phase)
        points.append((
            center_x + math.cos(angle) * radius_x * modulation,
            center_z + math.sin(angle) * radius_z * modulation,
        ))
    return clockwise_outline(points)


TERRAIN_PLATES = (
    TerrainPlate(
        "Foundation",
        clockwise_outline((
            (-80.0, -ARENA_FLOOR_HALF_EXTENT),
            (80.0, -ARENA_FLOOR_HALF_EXTENT),
            (ARENA_FLOOR_HALF_EXTENT, -80.0),
            (ARENA_FLOOR_HALF_EXTENT, 80.0),
            (80.0, ARENA_FLOOR_HALF_EXTENT),
            (-80.0, ARENA_FLOOR_HALF_EXTENT),
            (-ARENA_FLOOR_HALF_EXTENT, 80.0),
            (-ARENA_FLOOR_HALF_EXTENT, -80.0),
        )),
        -1.0,
        -4.0,
        "WetlandTeal",
        ("CliffDark", "EarthWarm"),
    ),
    TerrainPlate("WestLowland", irregular_ellipse_outline(-55.0, 5.0, 35.0, 34.0, 12, 0.2), -0.02, -1.0, "MeadowMid", ("EarthWarm", "CliffDark")),
    TerrainPlate("NorthLowland", clockwise_outline(((-44.0, 20.0), (35.0, 20.0), (49.0, 42.0), (49.0, 73.0), (34.0, 87.0), (-34.0, 87.0), (-50.0, 73.0), (-51.0, 43.0))), -0.04, -1.0, "MeadowDark", ("EarthWarm", "CliffDark")),
    TerrainPlate("EastLowland", irregular_ellipse_outline(52.0, 4.0, 37.0, 39.0, 12, 2.2), -0.06, -1.0, "MeadowMid", ("EarthWarm", "CliffDark")),
    TerrainPlate("SouthWestLowland", irregular_ellipse_outline(-58.0, -49.0, 35.0, 38.0, 11, 1.7), -0.10, -1.0, "MeadowDark", ("EarthWarm", "CliffDark")),
    TerrainPlate("SouthEastLowland", irregular_ellipse_outline(58.0, -49.0, 35.0, 38.0, 11, 0.7), -0.08, -1.0, "MeadowMid", ("EarthWarm", "CliffDark")),
    TerrainPlate("CentralMeadow", clockwise_outline(((-18.0, -28.0), (18.0, -28.0), (29.0, -17.0), (30.0, 2.0), (26.0, 21.0), (13.0, 28.0), (-10.0, 29.0), (-26.0, 21.0), (-30.0, 2.0), (-28.0, -17.0))), 0.02, -1.0, "MeadowLight", ("EarthWarm", "CliffDark")),
    TerrainPlate("WestShrineShoulder", clockwise_outline(((-36.5, -18.0), (-36.5, 30.0), (-56.0, 34.0), (-74.0, 31.0), (-84.0, 18.0), (-83.0, -8.0), (-72.0, -19.0), (-55.0, -22.0))), 2.0, -0.02, "MeadowMid", ("EarthWarm", "CliffDark")),
    TerrainPlate("WestShrine", clockwise_outline(((-44.0, -14.0), (-44.0, 26.0), (-54.0, 29.0), (-70.0, 27.0), (-79.0, 16.0), (-78.0, -6.0), (-68.0, -15.0), (-53.0, -18.0))), 4.0, -0.02, "MeadowLight", ("EarthWarm", "CliffDark")),
    TerrainPlate("NorthRidgeShoulder", clockwise_outline(((-23.0, 38.0), (23.0, 38.0), (36.0, 54.0), (37.0, 74.0), (27.0, 87.0), (-28.0, 87.0), (-38.0, 75.0), (-36.0, 54.0))), 1.48, -0.04, "MeadowMid", ("CliffDark", "EarthWarm")),
    TerrainPlate("NorthRidgeLower", clockwise_outline(((-23.0, 44.0), (23.0, 44.0), (30.0, 54.0), (32.0, 75.0), (22.0, 86.0), (-23.0, 86.0), (-33.0, 75.0), (-31.0, 54.0))), 3.0, -0.04, "MeadowDark", ("CliffDark", "RuinStone")),
    TerrainPlate("NorthRidgeMid", clockwise_outline(((-15.0, 51.6), (15.0, 51.6), (21.0, 64.0), (20.0, 79.0), (13.0, 85.0), (-15.0, 85.0), (-22.0, 78.0), (-21.0, 64.0))), 4.4, 3.0, "MeadowDark", ("CliffDark", "RuinStone")),
    TerrainPlate("NorthRidgeUpper", clockwise_outline(((-14.0, 57.0), (14.0, 57.0), (18.0, 64.0), (17.0, 78.0), (11.0, 84.0), (-13.0, 84.0), (-19.0, 77.0), (-18.0, 64.0))), 5.8, 4.4, "MeadowMid", ("CliffDark", "RuinStone")),
    TerrainPlate("EastBasin", clockwise_outline(((36.0, -18.0), (36.0, 22.0), (47.0, 30.0), (68.0, 29.0), (80.0, 18.0), (80.0, -15.0), (69.0, -25.0), (48.0, -27.0))), 1.4, -0.06, "MeadowDark", ("EarthWarm", "RuinStone")),
    TerrainPlate("WetlandIslandWest", irregular_ellipse_outline(-23.0, -58.0, 8.0, 7.0, 8, 0.4), -0.62, -1.0, "MeadowDark", ("EarthWarm",)),
    TerrainPlate("WetlandIslandEast", irregular_ellipse_outline(24.0, -68.0, 9.0, 7.0, 8, 1.4), -0.58, -1.0, "MeadowMid", ("EarthWarm",)),
)


RAMP_SPECS = (
    RampSpec("WestSouth", "WestShrine", (-29.1, -5.0), (-44.1, -5.0), 9.0, -0.02, 4.0, -1.0),
    RampSpec("WestNorth", "WestShrine", (-29.1, 12.0), (-44.1, 12.0), 9.0, -0.02, 4.0, -1.0),
    RampSpec("NorthLowerWest", "NorthRidgeLower", (-14.0, 32.1), (-14.0, 44.1), 9.0, -0.04, 3.0, -1.0),
    RampSpec("NorthLowerEast", "NorthRidgeLower", (14.0, 32.1), (14.0, 44.1), 9.0, -0.04, 3.0, -1.0),
    RampSpec("NorthUpperWest", "NorthRidgeUpper", (-8.0, 46.1), (-8.0, 57.1), 9.0, 3.0, 5.8, 2.2, "PathDirt", "CliffDark"),
    RampSpec("NorthUpperEast", "NorthRidgeUpper", (8.0, 46.1), (8.0, 57.1), 9.0, 3.0, 5.8, 2.2, "PathDirt", "CliffDark"),
    RampSpec("EastBasinSouth", "EastBasin", (30.6, -8.0), (36.1, -8.0), 9.0, -0.06, 1.4, -1.0),
    RampSpec("EastBasinNorth", "EastBasin", (30.6, 14.0), (36.1, 14.0), 9.0, -0.06, 1.4, -1.0),
    RampSpec("WetlandWest", "SouthWetland", (-14.0, -39.9), (-14.0, -27.9), 8.0, -1.0, 0.02, -1.7),
    RampSpec("WetlandEast", "SouthWetland", (14.0, -39.9), (14.0, -27.9), 8.0, -1.0, 0.02, -1.7),
)


def authored_path_specs() -> tuple[tuple[tuple[Vec2, ...], float, bool, float], ...]:
    """Return authored flat road strips as (centers, width, closed, y offset)."""
    ring_points = []
    for index in range(72):
        angle = math.tau * index / 72.0
        radius = 22.7 + math.sin(angle * 3.0 + 0.45) * 0.7
        ring_points.append((math.cos(angle) * radius, math.sin(angle) * radius * 0.94))
    regional_segments = (
        ((-44.1, -5.0), (-56.0, -5.0), (-66.0, 3.0), (-56.0, 12.0), (-44.1, 12.0)),
        ((-29.1, 12.0), (-24.0, 12.0), (-18.0, 22.0), (-14.0, 26.0), (-14.0, 32.1)),
        ((-8.0, 57.1), (-8.0, 62.0), (-9.0, 67.0), (-2.0, 76.0), (7.0, 68.0), (8.0, 62.0), (8.0, 57.1)),
        ((14.0, 32.1), (14.0, 27.0), (10.0, 22.0), (10.0, 16.0), (20.0, 12.0), (26.0, 14.0), (30.6, 14.0)),
        ((36.1, 14.0), (42.0, 14.0), (48.0, 20.0), (61.0, 17.0), (69.0, 3.0), (59.0, -10.0), (47.0, -13.0), (42.0, -8.0), (36.1, -8.0)),
        ((30.6, -8.0), (26.0, -8.0), (24.0, -16.0), (14.0, -22.0), (14.0, -27.9)),
        ((14.0, -39.9), (14.0, -44.0), (7.0, -49.0), (3.0, -57.0), (0.0, -60.0), (-1.0, -54.0), (-6.0, -48.0), (-14.0, -44.0), (-14.0, -39.9)),
        ((-14.0, -27.9), (-14.0, -23.0), (-20.0, -15.0), (-24.0, -5.0), (-29.1, -5.0)),
    )
    return (
        (tuple(ring_points), 6.5, True, 0.031),
        (((-24.0, 0.0), (-12.0, 0.0), (0.0, 0.0), (12.0, 0.0), (24.0, 0.0)), 7.0, False, 0.034),
        (((0.0, 24.0), (0.0, 12.0), (0.0, 0.0), (0.0, -12.0), (0.0, -24.0)), 7.0, False, 0.037),
        *((tuple(segment), 5.5, False, 0.040 + index * 0.003) for index, segment in enumerate(regional_segments)),
    )


EVENT_ANCHORS = (
    EventAnchorSpec("EventAnchor_WestShrine", (-61.0, 4.04, 6.0), 7.5),
    EventAnchorSpec("EventAnchor_NorthRift", (-2.0, 5.84, 67.0), 9.0),
    EventAnchorSpec("EventAnchor_EastBasin", (57.0, 1.44, 3.0), 11.0),
    # The wetland water reaches y=-0.935. Keep this marker visibly above it
    # instead of sharing the same depth plane and flickering.
    EventAnchorSpec("EventAnchor_SouthWetland", (0.0, -0.96, -60.0), 9.0, 0.10),
)


def polar_offsets(radius: float, angles_degrees: Sequence[float]) -> tuple[Vec2, ...]:
    return tuple((
        math.cos(math.radians(angle)) * radius,
        math.sin(math.radians(angle)) * radius,
    ) for angle in angles_degrees)


EVENT_SPAWN_GROUPS = (
    EventSpawnGroupSpec(
        "EventSpawn_Star_",
        "EventAnchor_NorthRift",
        polar_offsets(10.5, (0, 36, 72, 108, 144, 180, 216, 240, 300, 324)),
    ),
    EventSpawnGroupSpec(
        "EventSpawn_Thunder_",
        "EventAnchor_WestShrine",
        polar_offsets(8.3, (0, 35, 70, 105, 150, 180, 220, 255, 290, 325)),
    ),
    EventSpawnGroupSpec(
        "EventSpawn_Water_",
        "EventAnchor_SouthWetland",
        (
            (11.313708, 11.313708),
            (6.761892, 14.500925),
            (-1.568803, 17.931505),
            (-7.0, 12.124356),
            (-13.7888, 11.570177),
            (-18.0, 0.0),
            (-14.141328, -16.852977),
            (3.235238, -12.074073),
            (11.313708, -11.313708),
            (19.318517, -5.176381),
        ),
    ),
    EventSpawnGroupSpec(
        "EventSpawn_Wind_",
        "EventAnchor_EastBasin",
        polar_offsets(11.8, tuple(range(0, 360, 36))),
    ),
)
EVENT_SPAWN_SURFACE_OFFSET = 0.04


REGION_VISUALS = (
    RegionVisualSpec(
        "star",
        "EventAnchor_NorthRift",
        "RegionLandmark_Star",
        (27.0, 68.0),
        -math.pi * 0.55,
        4.0,
    ),
    RegionVisualSpec(
        "thunder",
        "EventAnchor_WestShrine",
        "RegionLandmark_Thunder",
        (-75.0, -2.0),
        math.pi * 0.35,
        2.8,
    ),
    RegionVisualSpec(
        "water",
        "EventAnchor_SouthWetland",
        "RegionLandmark_Water",
        (-1.0, -82.0),
        0.0,
        3.2,
    ),
    RegionVisualSpec(
        "wind",
        "EventAnchor_EastBasin",
        "RegionLandmark_Wind",
        (75.0, 15.0),
        -math.pi * 0.35,
        3.4,
    ),
)


WETLAND_WATER_SPECS = (
    ((-12.0, -0.94, -61.0), (0.0, -0.10, 0.0), (42.0, 1.0, 25.0)),
    ((17.0, -0.935, -61.0), (0.0, 0.18, 0.0), (31.0, 1.0, 20.0)),
    ((1.0, -0.93, -78.0), (0.0, -0.04, 0.0), (29.0, 1.0, 10.0)),
)


TREE_CLUSTERS = (
    ClusterSpec("WestOuterNorth", (-78.0, 28.0), (7.0, 9.0), 6),
    ClusterSpec("WestOuterSouth", (-77.0, -25.0), (8.0, 10.0), 6),
    ClusterSpec("WestShrineBloom", (-68.0, 18.0), (7.0, 5.0), 5),
    ClusterSpec("WestCrossing", (-38.0, -25.0), (8.0, 6.0), 4),
    ClusterSpec("NorthWest", (-35.0, 69.0), (8.0, 9.0), 6),
    ClusterSpec("NorthEast", (27.0, 75.0), (8.0, 8.0), 6),
    ClusterSpec("NorthShoulderWest", (-33.0, 42.0), (7.0, 6.0), 4),
    ClusterSpec("NorthShoulderEast", (31.0, 47.0), (7.0, 7.0), 5),
    ClusterSpec("EastOuterNorth", (78.0, 27.0), (7.0, 9.0), 6),
    ClusterSpec("EastOuterSouth", (77.0, -26.0), (8.0, 10.0), 6),
    ClusterSpec("EastBasinRim", (47.0, 29.0), (7.0, 5.0), 4),
    ClusterSpec("SouthWest", (-52.0, -72.0), (9.0, 7.0), 6),
    ClusterSpec("SouthEast", (55.0, -72.0), (9.0, 7.0), 6),
    ClusterSpec("WetlandEdgeWest", (-31.0, -52.0), (6.0, 7.0), 4),
    ClusterSpec("WetlandEdgeEast", (33.0, -55.0), (6.0, 7.0), 4),
)


SMALL_PROP_CLUSTERS = (
    ClusterSpec("CenterFlowers", (-19.0, 18.0), (7.0, 5.0), 10),
    ClusterSpec("ShrineFlowers", (-54.0, 20.0), (8.0, 4.0), 12),
    ClusterSpec("NorthGrass", (20.0, 55.0), (8.0, 7.0), 10),
    ClusterSpec("BasinGrass", (47.0, -18.0), (8.0, 6.0), 10),
    ClusterSpec("WetlandMushrooms", (-6.0, -67.0), (18.0, 9.0), 18),
    ClusterSpec("WetlandReeds", (3.0, -53.0), (24.0, 12.0), 20),
)


def point_in_polygon(x: float, z: float, outline: Sequence[Vec2]) -> bool:
    if any(
        point_segment_distance_squared((x, z), outline[index], outline[(index + 1) % len(outline)])
        <= 1.0e-10
        for index in range(len(outline))
    ):
        return True
    inside = False
    previous = outline[-1]
    for current in outline:
        x0, z0 = previous
        x1, z1 = current
        cross_z = (z0 > z) != (z1 > z)
        if cross_z and x < (x1 - x0) * (z - z0) / (z1 - z0) + x0:
            inside = not inside
        previous = current
    return inside


def point_segment_distance_squared(point: Vec2, start: Vec2, end: Vec2) -> float:
    delta_x = end[0] - start[0]
    delta_z = end[1] - start[1]
    length_squared = delta_x * delta_x + delta_z * delta_z
    if length_squared <= 1.0e-8:
        return (point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2
    projection = max(0.0, min(1.0, (
        (point[0] - start[0]) * delta_x + (point[1] - start[1]) * delta_z
    ) / length_squared))
    closest_x = start[0] + delta_x * projection
    closest_z = start[1] + delta_z * projection
    return (point[0] - closest_x) ** 2 + (point[1] - closest_z) ** 2


def terrain_surface_height(x: float, z: float, margin: float = 0.0) -> float | None:
    heights: list[float] = []
    for plate in TERRAIN_PLATES:
        if not point_in_polygon(x, z, plate.outline):
            continue
        if margin > 0.0 and min(
            point_segment_distance_squared((x, z), plate.outline[index], plate.outline[(index + 1) % len(plate.outline)])
            for index in range(len(plate.outline))
        ) < margin * margin:
            continue
        heights.append(plate.top_y)

    for ramp_spec in RAMP_SPECS:
        delta_x = ramp_spec.high_center[0] - ramp_spec.low_center[0]
        delta_z = ramp_spec.high_center[1] - ramp_spec.low_center[1]
        length = ramp_spec.length
        direction_x = delta_x / length
        direction_z = delta_z / length
        relative_x = x - ramp_spec.low_center[0]
        relative_z = z - ramp_spec.low_center[1]
        along = relative_x * direction_x + relative_z * direction_z
        lateral = abs(relative_x * direction_z - relative_z * direction_x)
        if margin <= along <= length - margin and lateral <= ramp_spec.width * 0.5 - margin:
            progress = along / length
            heights.append(ramp_spec.low_y + (ramp_spec.high_y - ramp_spec.low_y) * progress)
    return max(heights) if heights else None


def event_spawn_xz(group: EventSpawnGroupSpec, index: int) -> Vec2:
    anchor = next(anchor for anchor in EVENT_ANCHORS if anchor.name == group.anchor_name)
    offset_x, offset_z = group.offsets[index]
    return anchor.position[0] + offset_x, anchor.position[2] + offset_z


def wetland_water_surface_height(x: float, z: float) -> float | None:
    heights: list[float] = []
    for position, rotation, scale in WETLAND_WATER_SPECS:
        delta_x = x - position[0]
        delta_z = z - position[2]
        cosine = math.cos(rotation[1])
        sine = math.sin(rotation[1])
        local_x = cosine * delta_x - sine * delta_z
        local_z = sine * delta_x + cosine * delta_z
        if abs(local_x) <= scale[0] * 0.5 and abs(local_z) <= scale[2] * 0.5:
            heights.append(position[1])
    return max(heights) if heights else None


def placement_allowed(x: float, z: float, large: bool) -> bool:
    if x * x + z * z < (24.0 if large else 8.0) ** 2:
        return False
    for anchor in EVENT_ANCHORS:
        padding = 3.0 if large else 1.5
        if (x - anchor.position[0]) ** 2 + (z - anchor.position[2]) ** 2 < (anchor.clear_radius + padding) ** 2:
            return False
    for visual in REGION_VISUALS:
        padding = 2.2 if large else 0.75
        if (
            (x - visual.landmark_position[0]) ** 2
            + (z - visual.landmark_position[1]) ** 2
            < (visual.footprint_radius + padding) ** 2
        ):
            return False
    socket_padding = 3.0 if large else 1.4
    for group in EVENT_SPAWN_GROUPS:
        for index in range(len(group.offsets)):
            socket_x, socket_z = event_spawn_xz(group, index)
            if (x - socket_x) ** 2 + (z - socket_z) ** 2 < socket_padding ** 2:
                return False
    for ramp_spec in RAMP_SPECS:
        padding = 3.0 if large else 1.0
        if point_segment_distance_squared((x, z), ramp_spec.low_center, ramp_spec.high_center) < (ramp_spec.width * 0.5 + padding) ** 2:
            return False
    for centers, width, closed, _vertical_offset in authored_path_specs():
        segment_count = len(centers) if closed else len(centers) - 1
        padding = 2.8 if large else 0.45
        if any(
            point_segment_distance_squared(
                (x, z),
                centers[index],
                centers[(index + 1) % len(centers)],
            ) < (width * 0.5 + padding) ** 2
            for index in range(segment_count)
        ):
            return False
    return True


def clustered_positions(
    rng: random.Random,
    clusters: Sequence[ClusterSpec],
    large: bool,
    minimum_spacing: float,
    occupied: list[tuple[float, float]],
) -> list[tuple[float, float, float, str]]:
    placements: list[tuple[float, float, float, str]] = []
    for cluster in clusters:
        cluster_count = 0
        attempts = 0
        while cluster_count < cluster.count and attempts < cluster.count * 300:
            attempts += 1
            angle = rng.uniform(0.0, math.tau)
            radius = math.sqrt(rng.uniform(0.08, 1.0))
            x = cluster.center[0] + math.cos(angle) * cluster.radius[0] * radius
            z = cluster.center[1] + math.sin(angle) * cluster.radius[1] * radius
            if not placement_allowed(x, z, large):
                continue
            safe_surface_height = terrain_surface_height(x, z, 0.75 if large else 0.18)
            if safe_surface_height is None:
                continue
            surface_height = terrain_surface_height(x, z)
            if surface_height is None or abs(surface_height - safe_surface_height) > 0.02:
                continue
            if minimum_spacing > 0.0 and any(
                (x - other_x) ** 2 + (z - other_z) ** 2 < minimum_spacing ** 2
                for other_x, other_z in occupied
            ):
                continue
            placements.append((x, surface_height, z, cluster.name))
            occupied.append((x, z))
            cluster_count += 1
        if cluster_count != cluster.count:
            raise RuntimeError(f"Could not fill cluster {cluster.name}: {cluster_count}/{cluster.count}")
    return placements


def boundary_tree_positions(
    rng: random.Random,
) -> list[tuple[str, int, float, float, float]]:
    placements: list[tuple[str, int, float, float, float]] = []
    tree_inset = 1.15
    for side in ("North", "East", "South", "West"):
        for index in range(BOUNDARY_TREE_COUNT_PER_SIDE):
            fraction = (index + 0.5) / BOUNDARY_TREE_COUNT_PER_SIDE
            tangent = -PLAYABLE_HALF_EXTENT + 2.0 * PLAYABLE_HALF_EXTENT * fraction
            tangent += rng.uniform(-1.0, 1.0)
            inset = tree_inset + rng.uniform(-0.45, 0.55)
            if side == "North":
                x, z = tangent, PLAYABLE_HALF_EXTENT - inset
            elif side == "East":
                x, z = PLAYABLE_HALF_EXTENT - inset, tangent
            elif side == "South":
                x, z = tangent, -PLAYABLE_HALF_EXTENT + inset
            else:
                x, z = -PLAYABLE_HALF_EXTENT + inset, tangent

            surface_height = terrain_surface_height(x, z)
            if surface_height is None:
                raise ValueError(f"Boundary tree is outside the arena at ({x}, {z})")
            placements.append((side, index, x, surface_height, z))
    return placements


def build_scene(meshes: dict[str, MeshBuilder], rng: random.Random) -> SceneBuilder:
    scene = SceneBuilder()

    player_id = scene.add(
        "Core/Player",
        {
            "AnimatorComponent": {
                "animResPath": PLAYER_ANIMATION_PATH,
                "bEnableRootMotion": False,
                "bLockRootMotionXZ": True,
                "bLoop": True,
                "bPlay": True,
                "controllerPath": PLAYER_CONTROLLER_PATH,
                "currentClipIndex": 0,
                "playSpeed": 1.0,
            },
            "AudioListenerComponent": {
                "bActive": True,
                "bUsePrimaryCameraOrientation": True,
            },
            "CapsuleCollider3DComponent": {
                "Center": [0.0, 0.9, 0.0],
                "Height": 245.0,
                "IsTrigger": False,
                "Radius": 58.0,
            },
            "CharacterMovementComponent": {
                "Acceleration": 16.0,
                "Deceleration": 18.0,
                "Gravity": -9.8,
                "MaxSlopeAngleDegrees": 50.0,
                "MaxSpeed": 4.25,
                "SprintAccelerationMultiplier": 1.0,
                "SprintSpeedMultiplier": 1.0,
                "StepUpHeight": 0.4,
                "StickToFloorDistance": 0.5,
                "TurnRate": 14.0,
                "JumpSpeed": 5.8,
                "bEnableJump": True,
                "bEnableSprint": False,
                "bOrientRotationToMovement": True,
                "bUseWorldUp": True,
            },
            "MeshComponent": {"Path": PLAYER_MESH_PATH, "meshResPath": ""},
            "TagComponent": {"Tag": "Player"},
            "TransformComponent": transform_component((0.0, 0.05, 0.0), (0.0, 0.0, 0.0), (0.0075, 0.0075, 0.0075)),
        },
    )

    scene.add(
        "Core/GameDirector",
        {
            "PythonScriptComponent": {"Path": "Scripts.SurvivorGame.py"},
            "TagComponent": {"Tag": "GameDirector"},
            "TransformComponent": transform_component(),
        },
    )
    scene.add(
        "Core/PostProcessing",
        {
            "PostProcessingComponent": {
                "BlendRadius": 0.0,
                "BlendWeight": 1.0,
                "Exposure": 0.74,
                "Priority": 0.0,
                "bEnabled": True,
                "bGlobal": True,
                "bLocalVolumeEnabled": False,
                "bOverrideExposure": True,
            },
            "TagComponent": {"Tag": "Post Processing"},
            "TransformComponent": transform_component(),
        },
    )
    scene.add(
        "Core/Camera",
        {
            "CameraComponent": {
                "Camera": {
                    "mAspectRatio": 1.777778,
                    "mOrthographicFar": 1.0,
                    "mOrthographicNear": -1.0,
                    "mOrthographicSize": 10.0,
                    "mPerspectiveFOV": 1.047198,
                    "mPerspectiveFar": 400.0,
                    "mPerspectiveNear": 0.1,
                    "mProjectionType": 0,
                },
                "Exposure": 0.8,
                "FixedAspectRatio": False,
                "Primary": True,
                "bOverrideExposure": False,
            },
            "FollowCameraComponent": {
                "InitialPitchDegrees": -20.0,
                "MaxPitchDegrees": 5.0,
                "MinPitchDegrees": -75.0,
                "Mode": 0,
                "MouseSensitivity": 0.0024,
                "TargetUUID": player_id,
                "TopDownDistance": 14.0,
                "TopDownPitchDegrees": -40.0,
                "TopDownYawDegrees": 0.0,
                "bAllowPitchInput": True,
                "bAllowYawInput": True,
                "bFollowTargetRotation": False,
                "bHasTarget": True,
                "bLockToWorldUp": True,
                "bRequireHoldToRotate": True,
            },
            "SpringArmComponent": {
                "ArmLength": 12.5,
                "CollisionRecoverSpeed": 8.0,
                "CollisionSnapSpeed": 20.0,
                "LagSpeed": 10.0,
                "MinArmLength": 0.8,
                "ProbeRadius": 0.2,
                "SocketOffset": [0.0, 0.25, 0.0],
                "TargetOffset": [0.0, 1.5, 0.0],
                "bEnableCollision": True,
                "bEnableLag": True,
                "bEnableTopDownCollision": False,
            },
            "TagComponent": {"Tag": "Camera"},
            "TransformComponent": transform_component((0.0, 7.5, -10.0), (-0.52, 0.0, 0.0)),
        },
    )
    scene.add(
        "Core/Environment",
        {
            "EnvironmentLightComponent": {
                "Exposure": 0.52,
                "HdrTexturePath": HDR_ASSET_PATH,
                "bCloudsEnabled": False,
                "CloudBottom": 90.0,
                "CloudThickness": 95.0,
                "CloudCoverage": 0.42,
                "CloudSeed": 7301,
                "CloudMaxDistance": 5000.0,
                "CloudDensity": 0.035,
                "CloudScale": 260.0,
                "CloudRoundness": 0.75,
                "CloudErosion": 0.12,
                "CloudWindAngle": 25.0,
                "CloudWindSpeed": 1.8,
                "CloudEvolutionSpeed": 0.015,
                "CloudLitColor": [1.0, 0.97, 0.9],
                "CloudShadowColor": [0.56, 0.66, 0.87],
                "CloudAmbient": 0.65,
                "CloudSilverLining": 0.3,
                "IBLIntensity": 0.72,
            },
            "TagComponent": {"Tag": "Environment Light"},
            "TransformComponent": transform_component(),
        },
    )
    scene.add(
        "Core/DirectionalLight",
        {
            "DirectionalLightComponent": {
                "CascadeCount": 3,
                "CascadeLambda": 0.72,
                "Color": [1.0, 0.92, 0.78],
                "DepthBias": 0.0009,
                "Intensity": 1.18,
                "NormalBias": 0.03,
                "PCFRadius": 1.1,
                "ShadowDistance": 108.0,
                "ShadowMapSize": 2048,
                "ShadowStrength": 0.88,
                "bCastShadows": True,
                "bUsePCF": True,
            },
            "TagComponent": {"Tag": "Directional Light"},
            "TransformComponent": transform_component((8.0, 16.0, 9.0), (-2.55, 0.75, 0.20)),
        },
    )
    scene.add(
        "Lights/StarGlow",
        {
            "PointLightComponent": {
                "FalloffExponent": 2.0,
                "Intensity": 0.72,
                "LightColor": [0.78, 0.91, 1.0],
                "Radius": 18.0,
            },
            "TagComponent": {"Tag": "Star Glow"},
            "TransformComponent": transform_component((0.0, 2.0, 0.0)),
        },
    )

    for plate in TERRAIN_PLATES:
        scene.add_mesh(
            f"Terrain/Plate/{plate.name}",
            f"Terrain Plate {plate.name}",
            f"TerrainPlate_{plate.name}",
            (0.0, 0.0, 0.0),
            collider_shape=3,
        )

    for ramp_spec in RAMP_SPECS:
        scene.add_mesh(
            f"Terrain/Ramp/{ramp_spec.name}",
            f"Terrain Ramp {ramp_spec.name}",
            f"TerrainRamp_{ramp_spec.name}",
            (0.0, 0.0, 0.0),
            collider_shape=3,
        )

    scene.add_mesh("Terrain/Paths", "Dirt Path Network", "DirtPaths", (0.0, 0.0, 0.0))
    scene.add_mesh("Landmark/CentralStar", "Central Starbloom Plinth", "StarPlinth", (0.0, 0.04, 0.0))

    event_marker_meshes = {
        "EventAnchor_WestShrine": "EventRing_West",
        "EventAnchor_NorthRift": "EventRing_North",
        "EventAnchor_EastBasin": "EventRing_East",
        "EventAnchor_SouthWetland": "EventRing_South",
    }
    region_visuals_by_anchor = {
        visual.anchor_name: visual for visual in REGION_VISUALS
    }
    for anchor in EVENT_ANCHORS:
        scene.add(
            f"Events/{anchor.name}",
            {
                "TagComponent": {"Tag": anchor.name},
                "TransformComponent": transform_component(anchor.position),
            },
        )
        scene.add_mesh(
            f"Events/Marker/{anchor.name}",
            f"{anchor.name} Ground Marker",
            event_marker_meshes[anchor.name],
            (
                anchor.position[0],
                anchor.position[1] + anchor.marker_vertical_offset,
                anchor.position[2],
            ),
            rotation=(0.0, 0.0, 0.0),
            scale=(anchor.clear_radius, 1.0, anchor.clear_radius),
        )
        visual = region_visuals_by_anchor[anchor.name]
        barrier_position = (
            anchor.position[0],
            anchor.position[1] + anchor.marker_vertical_offset,
            anchor.position[2],
        )
        scene.add_mesh(
            f"Events/Barrier/{anchor.name}",
            f"{anchor.name} Barrier Dome",
            "BarrierDome_" + visual.region_id.title(),
            barrier_position,
            scale=(
                anchor.clear_radius,
                anchor.clear_radius * 0.72,
                anchor.clear_radius,
            ),
        )

    for visual in REGION_VISUALS:
        x, z = visual.landmark_position
        surface_height = terrain_surface_height(x, z)
        if surface_height is None:
            raise ValueError(
                f"{visual.region_id} landmark has no authored terrain surface"
            )
        scene.add_mesh(
            f"Landmark/Region/{visual.region_id.title()}",
            "Region Landmark " + visual.region_id.title(),
            visual.landmark_mesh,
            (x, surface_height + 0.01, z),
            rotation=(0.0, visual.landmark_yaw, 0.0),
        )

    for group in EVENT_SPAWN_GROUPS:
        for index in range(len(group.offsets)):
            spawn_x, spawn_z = event_spawn_xz(group, index)
            surface_height = terrain_surface_height(spawn_x, spawn_z)
            if surface_height is None:
                raise ValueError(
                    f"{group.tag_prefix}{index:02d} has no authored terrain surface"
                )
            tag = f"{group.tag_prefix}{index:02d}"
            scene.add(
                f"Events/Spawn/{tag}",
                {
                    "TagComponent": {"Tag": tag},
                    "TransformComponent": transform_component((
                        spawn_x,
                        surface_height + EVENT_SPAWN_SURFACE_OFFSET,
                        spawn_z,
                    )),
                },
            )

    wall_half_height = BOUNDARY_WALL_HEIGHT * 0.5
    wall_length = PLAYABLE_HALF_EXTENT * 2.0 + BOUNDARY_WALL_THICKNESS
    for name, position, scale in (
        ("North", (0.0, wall_half_height, PLAYABLE_HALF_EXTENT), (wall_length, BOUNDARY_WALL_HEIGHT, BOUNDARY_WALL_THICKNESS)),
        ("East", (PLAYABLE_HALF_EXTENT, wall_half_height, 0.0), (BOUNDARY_WALL_THICKNESS, BOUNDARY_WALL_HEIGHT, wall_length)),
        ("South", (0.0, wall_half_height, -PLAYABLE_HALF_EXTENT), (wall_length, BOUNDARY_WALL_HEIGHT, BOUNDARY_WALL_THICKNESS)),
        ("West", (-PLAYABLE_HALF_EXTENT, wall_half_height, 0.0), (BOUNDARY_WALL_THICKNESS, BOUNDARY_WALL_HEIGHT, wall_length)),
    ):
        scene.add_box_collider(
            f"Boundary/Wall/{name}",
            f"Forest Boundary {name}",
            position,
            scale,
        )

    for index, (position, rotation, scale) in enumerate(WETLAND_WATER_SPECS):
        scene.add_mesh(
            f"Water/Wetland/{index:02d}",
            f"South Wetland Water {index:02d}",
            "WaterPlane",
            position,
            rotation=rotation,
            scale=scale,
        )

    for index in range(12):
        angle = math.tau * index / 12.0 + rng.uniform(-0.075, 0.075)
        radius = rng.uniform(112.0, 136.0)
        variant = index % 3 + 1
        horizontal_scale = rng.uniform(12.0, 19.0)
        scene.add_mesh(
            f"Backdrop/Mountain/{index:02d}",
            f"Distant Mountain {index:02d}",
            f"DistantMountain_{variant:02d}",
            (math.cos(angle) * radius, rng.uniform(-7.0, -3.5), math.sin(angle) * radius),
            rotation=(0.0, rng.uniform(0.0, math.tau), 0.0),
            scale=(horizontal_scale, rng.uniform(23.0, 35.0), horizontal_scale * rng.uniform(0.78, 1.15)),
        )

    boundary_tree_meshes = ("PineTree", "DeciduousTree", "PineTree", "BlossomTree")
    for side_index, (side, index, x, y, z) in enumerate(boundary_tree_positions(rng)):
        tree_mesh = boundary_tree_meshes[side_index % len(boundary_tree_meshes)]
        scale = rng.uniform(1.62, 2.18)
        scene.add_mesh(
            f"Boundary/Tree/{side}/{index:03d}",
            f"Boundary {tree_mesh} {side} {index:03d}",
            tree_mesh,
            (x, y, z),
            rotation=(0.0, rng.uniform(0.0, math.tau), 0.0),
            scale=(scale, scale * rng.uniform(0.95, 1.12), scale),
        )

    occupied_large: list[tuple[float, float]] = []
    tree_positions = clustered_positions(rng, TREE_CLUSTERS, True, 3.1, occupied_large)
    tree_meshes = ("DeciduousTree", "DeciduousTree", "PineTree", "BlossomTree")
    for index, (x, y, z, cluster_name) in enumerate(tree_positions):
        bUseExternal = index % 7 == 0
        tree_mesh = EXTERNAL_MESH_PATHS["NatureTree"] if bUseExternal else tree_meshes[index % len(tree_meshes)]
        if "Shrine" in cluster_name:
            tree_mesh = "BlossomTree"
        scale = rng.uniform(0.76, 1.18)
        if bUseExternal:
            scale *= 0.90
        scene.add_mesh(
            f"Vegetation/Tree/{index:03d}",
            f"Cluster Tree {cluster_name} {index:03d}",
            tree_mesh,
            (x, y, z),
            rotation=(0.0, rng.uniform(0.0, math.tau), 0.0),
            scale=(scale, scale * rng.uniform(0.94, 1.12), scale),
        )

    rock_clusters = (
        ClusterSpec("WestRampRocks", (-35.0, -18.0), (11.0, 7.0), 5),
        ClusterSpec("NorthCliffRocks", (-26.0, 53.0), (7.0, 14.0), 6),
        ClusterSpec("EastBasinRocks", (72.0, 4.0), (6.0, 18.0), 6),
        ClusterSpec("WetlandRocks", (2.0, -78.0), (27.0, 6.0), 7),
    )
    rock_positions = clustered_positions(rng, rock_clusters, True, 1.8, occupied_large)
    for index, (x, y, z, cluster_name) in enumerate(rock_positions):
        scale = rng.uniform(0.48, 1.32)
        scene.add_mesh(
            f"Props/Rock/{index:03d}",
            f"Rock {cluster_name} {index:03d}",
            "Rock",
            (x, y, z),
            rotation=(rng.uniform(-0.15, 0.15), rng.uniform(0.0, math.tau), rng.uniform(-0.12, 0.12)),
            scale=(scale * rng.uniform(0.75, 1.35), scale, scale * rng.uniform(0.78, 1.30)),
        )

    crystal_points = (
        (-18.0, 59.0), (-13.0, 75.0), (13.0, 73.0), (17.0, 61.0),
        (-24.0, 47.0), (23.0, 48.0), (-2.0, 81.0),
        (43.0, -14.0), (55.0, 27.0), (69.0, 23.0), (76.0, 5.0),
        (69.0, -19.0), (45.0, -23.0), (78.0, -9.0),
    )
    for index, (x, z) in enumerate(crystal_points):
        y = terrain_surface_height(x, z)
        if y is None:
            raise ValueError(f"Crystal landmark is outside terrain at {(x, z)}")
        scale = rng.uniform(0.72, 1.36)
        scene.add_mesh(
            f"Props/Crystal/{index:03d}",
            f"Crystal Cluster {index:03d}",
            "Crystal",
            (x, y, z),
            rotation=(0.0, rng.uniform(0.0, math.tau), 0.0),
            scale=(scale, scale, scale),
        )

    small_positions = clustered_positions(rng, SMALL_PROP_CLUSTERS, False, 0.55, [])
    for index, (x, y, z, cluster_name) in enumerate(small_positions):
        placement_y = y + 0.01
        if "WetlandMushrooms" in cluster_name:
            category, mesh_name, scale = "Mushroom", "Mushroom", rng.uniform(0.68, 1.28)
        elif "WetlandReeds" in cluster_name:
            category, mesh_name, scale = "Reeds", "Reeds", rng.uniform(0.72, 1.22)
        elif "Flowers" in cluster_name or "Shrine" in cluster_name:
            category, mesh_name, scale = "Flower", "Flower", rng.uniform(0.70, 1.20)
        elif index % 9 == 0:
            category, mesh_name, scale = "BushFlowers", EXTERNAL_MESH_PATHS["NatureBushFlowers"], rng.uniform(0.80, 1.00)
            # This source mesh's pivot sits in the crown instead of at ground level.
            placement_y += 0.822 * scale
        else:
            category, mesh_name, scale = "Grass", "GrassTuft", rng.uniform(0.72, 1.30)
        scene.add_mesh(
            f"Vegetation/{category}/{index:03d}",
            f"{category} {cluster_name} {index:03d}",
            mesh_name,
            (x, placement_y, z),
            rotation=(0.0, rng.uniform(0.0, math.tau), 0.0),
            scale=(scale, scale, scale),
        )

    for index, (position, rotation, scale) in enumerate((
        ((-74.0, 4.0, 6.0), (0.0, math.pi * 0.5, 0.0), (1.35, 1.35, 1.35)),
        ((-64.0, 4.0, -8.5), (0.0, 0.28, 0.0), (1.0, 1.0, 1.0)),
        ((-64.0, 4.0, 20.0), (0.0, -0.22, 0.0), (0.92, 0.92, 0.92)),
    )):
        scene.add_mesh(
            f"Landmark/WestShrineGate/{index:02d}",
            f"West Shrine Gate {index:02d}",
            "ShrineGate",
            position,
            rotation=rotation,
            scale=scale,
        )
        for part_name, local_center, local_size in (
            ("Left Post", (-1.25, 2.05, 0.0), (0.34, 4.10, 0.44)),
            ("Right Post", (1.25, 2.05, 0.0), (0.34, 4.10, 0.44)),
            ("Lintel", (0.0, 3.65, 0.0), (3.45, 0.38, 0.62)),
        ):
            scene.add_local_box_collider(
                f"Collision/WestShrineGate/{index:02d}/{part_name}",
                f"Architecture Collision West Shrine Gate {index:02d} {part_name}",
                position,
                rotation,
                scale,
                local_center,
                local_size,
            )

    for index, (mesh_path, position, rotation, scale) in enumerate((
        (EXTERNAL_MESH_PATHS["RuinsArch"], (-60.0, 4.0, 22.5), (0.0, math.pi, 0.0), (1.25, 1.25, 1.25)),
        (EXTERNAL_MESH_PATHS["RuinsColumn"], (-72.0, 4.0, -7.0), (0.0, 0.12, -0.18), (1.60, 1.55, 1.60)),
        (EXTERNAL_MESH_PATHS["RuinsArch"], (-3.0, 5.8, 79.0), (0.0, 0.0, 0.0), (1.20, 1.20, 1.20)),
        (EXTERNAL_MESH_PATHS["RuinsColumn"], (-16.0, 5.8, 70.0), (0.0, 0.42, -0.24), (1.65, 1.55, 1.65)),
        (EXTERNAL_MESH_PATHS["RuinsColumn"], (14.0, 5.8, 72.0), (0.0, -0.38, 0.20), (1.55, 1.70, 1.55)),
    )):
        bIsSolidColumn = mesh_path == EXTERNAL_MESH_PATHS["RuinsColumn"]
        scene.add_mesh(
            f"Landmark/Ruins/{index:02d}",
            f"Broken Ruin Landmark {index:02d}",
            mesh_path,
            position,
            rotation=rotation,
            scale=scale,
            collider_shape=3 if bIsSolidColumn else None,
        )
        if not bIsSolidColumn:
            for part_name, local_center, local_size in (
                ("Left Pier", (-1.30, 0.982, -0.12), (0.50, 1.964, 0.50)),
                ("Right Pier", (1.30, 0.982, -0.12), (0.50, 1.964, 0.50)),
                ("Arch", (0.0, 2.748, -0.12), (3.10, 1.568, 0.50)),
            ):
                scene.add_local_box_collider(
                    f"Collision/Ruins/{index:02d}/{part_name}",
                    f"Architecture Collision Broken Ruin {index:02d} {part_name}",
                    position,
                    rotation,
                    scale,
                    local_center,
                    local_size,
                )

    for index, (position, rotation, scale) in enumerate((
        ((-24.0, 3.0, 60.0), (0.0, -0.25, 0.18), (1.0, 1.4, 1.0)),
        ((22.0, 3.0, 58.0), (0.0, 0.34, -0.15), (0.9, 1.1, 0.9)),
        ((-11.0, 5.8, 77.0), (0.0, 0.18, 0.12), (1.15, 1.45, 1.15)),
        ((11.0, 5.8, 77.0), (0.0, -0.20, -0.10), (0.95, 1.25, 0.95)),
        ((44.0, 1.4, 26.0), (0.0, 0.42, 0.10), (0.82, 1.05, 0.82)),
    )):
        scene.add_mesh(
            f"Landmark/Obelisk/{index:02d}",
            f"Broken Crystal Obelisk {index:02d}",
            "BrokenObelisk",
            position,
            rotation=rotation,
            scale=scale,
        )

    for index, (x, y, z, scale) in enumerate((
        (-13.0, 10.2, 69.0, 0.85),
        (9.0, 9.5, 72.0, 0.65),
        (-1.0, 12.0, 77.0, 0.52),
        (51.0, 5.4, 18.0, 0.46),
    )):
        scene.add_mesh(
            f"Landmark/FloatingRock/{index:02d}",
            f"Floating Rift Rock {index:02d}",
            "Rock",
            (x, y, z),
            rotation=(rng.uniform(-0.3, 0.3), rng.uniform(0.0, math.tau), rng.uniform(-0.25, 0.25)),
            scale=(scale, scale * 0.75, scale),
        )

    for index, (x, z) in enumerate(((-25.0, -64.0), (28.0, -61.0), (-22.0, -77.0))):
        y = terrain_surface_height(x, z)
        if y is None:
            raise ValueError(f"Wetland dead tree is outside terrain at {(x, z)}")
        scale = rng.uniform(0.88, 1.12)
        scene.add_mesh(
            f"Landmark/WetlandDeadTree/{index:02d}",
            f"Wetland Dead Tree {index:02d}",
            EXTERNAL_MESH_PATHS["NatureDeadTree"],
            (x, y, z),
            rotation=(0.0, rng.uniform(0.0, math.tau), 0.0),
            scale=(scale, scale, scale),
        )

    validate_scene(scene, meshes, player_id)
    return scene


def validate_scene(scene: SceneBuilder, meshes: dict[str, MeshBuilder], player_id: str) -> None:
    mesh_entity_count = sum(
        1 for components in scene.entities.values() if "MeshComponent" in components
    )
    if not 280 <= mesh_entity_count <= 410:
        raise ValueError(f"Expected 280-410 mesh entities, got {mesh_entity_count}")

    generated_mesh_paths = {
        f"{ASSET_MODEL_ROOT}/{mesh_name}.hmesh" for mesh_name in meshes
    }
    valid_mesh_paths = generated_mesh_paths | {PLAYER_MESH_PATH} | set(EXTERNAL_MESH_PATHS.values())
    for components in scene.entities.values():
        mesh_component = components.get("MeshComponent")
        if isinstance(mesh_component, dict) and mesh_component.get("Path") not in valid_mesh_paths:
            raise ValueError(f"Unknown mesh path in scene: {mesh_component.get('Path')}")

    by_tag = {
        components.get("TagComponent", {}).get("Tag"): components
        for components in scene.entities.values()
    }
    player = by_tag.get("Player")
    director = by_tag.get("GameDirector")
    camera = by_tag.get("Camera")
    post_process = by_tag.get("Post Processing")
    if not isinstance(player, dict) or "PythonScriptComponent" in player:
        raise ValueError("Player must exist without a PythonScriptComponent")
    audio_listener = player.get("AudioListenerComponent", {}) if isinstance(player, dict) else {}
    if not audio_listener.get("bActive") or not audio_listener.get("bUsePrimaryCameraOrientation"):
        raise ValueError("Player must retain the active camera-oriented audio listener")
    if not isinstance(director, dict) or director.get("PythonScriptComponent", {}).get("Path") != "Scripts.SurvivorGame.py":
        raise ValueError("GameDirector must own Scripts.SurvivorGame.py")
    if not isinstance(post_process, dict):
        raise ValueError("The generated scene must own global post processing")
    post_process_settings = post_process.get("PostProcessingComponent", {})
    if not post_process_settings.get("bEnabled") or not post_process_settings.get("bGlobal"):
        raise ValueError("Post processing must remain enabled and global")
    if not post_process_settings.get("bOverrideExposure"):
        raise ValueError("Global post processing must explicitly override exposure")
    if post_process_settings.get("bLocalVolumeEnabled"):
        raise ValueError("Global post processing must not opt into local-volume evaluation")
    if float(post_process_settings.get("BlendWeight", 0.0)) != 1.0:
        raise ValueError("Global post processing must retain full blend weight")
    camera_settings = camera.get("CameraComponent", {}) if isinstance(camera, dict) else {}
    if camera_settings.get("bOverrideExposure"):
        raise ValueError("Main camera must inherit the scene post-process exposure")
    follow_camera = camera.get("FollowCameraComponent", {}) if isinstance(camera, dict) else {}
    spring_arm = camera.get("SpringArmComponent", {}) if isinstance(camera, dict) else {}
    if follow_camera.get("TargetUUID") != player_id:
        raise ValueError("Third-person camera must target Player")
    if follow_camera.get("Mode") != 0:
        raise ValueError("Main camera must use ThirdPerson mode")
    if not follow_camera.get("bAllowYawInput") or not follow_camera.get("bAllowPitchInput"):
        raise ValueError("Third-person camera must allow yaw and pitch input")
    min_pitch = float(follow_camera.get("MinPitchDegrees", 0.0))
    max_pitch = float(follow_camera.get("MaxPitchDegrees", 0.0))
    if min_pitch > -70.0 or max_pitch < 0.0 or max_pitch - min_pitch < 70.0:
        raise ValueError("Third-person camera must retain a wide up/down pitch range")
    initial_pitch = float(follow_camera.get("InitialPitchDegrees", 0.0))
    if not min_pitch <= initial_pitch <= max_pitch:
        raise ValueError("Third-person camera initial pitch must stay inside its pitch range")
    environment = by_tag.get("Environment Light", {}).get("EnvironmentLightComponent", {})
    if environment.get("bCloudsEnabled") is not False or environment.get("CloudSeed") != 7301:
        raise ValueError("Verdant Rift must default to clouds disabled and retain its deterministic preset")
    if not (environment.get("CloudBottom", 0) >= 60 and
            environment.get("CloudThickness", 0) > 0 and
            0 < environment.get("CloudCoverage", 0) < 0.75):
        raise ValueError("Cloud layer must stay above combat with open sky gaps")
    if initial_pitch != -20.0:
        raise ValueError("Default camera must preserve the validated combat/sky composition")
    if not spring_arm.get("bEnableCollision") or float(spring_arm.get("ArmLength", 0.0)) < 10.0:
        raise ValueError("Third-person camera must use a collision-enabled long spring arm")

    terrain_rigidbody_count = 0
    ramp_rigidbody_count = 0
    boundary_wall_count = 0
    architecture_box_collider_count = 0
    architecture_convex_hull_count = 0
    boundary_tree_count = 0
    point_light_count = 0
    event_anchors_found: dict[str, dict[str, object]] = {}
    event_markers_found: dict[str, dict[str, object]] = {}
    barrier_domes_found: dict[str, dict[str, object]] = {}
    region_landmarks_found: dict[str, dict[str, object]] = {}
    event_spawns_found: dict[str, dict[str, dict[str, object]]] = {
        group.tag_prefix: {} for group in EVENT_SPAWN_GROUPS
    }
    surface_tag_prefixes = (
        "Boundary ",
        "Cluster Tree ",
        "Rock ",
        "Crystal Cluster ",
        "Grass ",
        "Flower ",
        "Mushroom ",
        "Reeds ",
        "BushFlowers ",
        "Wetland Dead Tree ",
        "Region Landmark ",
    )
    for components in scene.entities.values():
        tag = str(components.get("TagComponent", {}).get("Tag", ""))
        rigidbody = components.get("Rigidbody3DComponent")
        if "PointLightComponent" in components:
            point_light_count += 1
        if tag.startswith("Terrain Ramp"):
            if not isinstance(rigidbody, dict) or rigidbody.get("Shape") != 3:
                raise ValueError(f"{tag} must use a ConvexHull rigidbody")
            ramp_rigidbody_count += 1
        elif tag.startswith("Terrain Plate"):
            if not isinstance(rigidbody, dict) or rigidbody.get("Shape") != 3:
                raise ValueError(f"{tag} must use a ConvexHull rigidbody")
            terrain_rigidbody_count += 1
        elif tag.startswith("Forest Boundary "):
            if not isinstance(rigidbody, dict) or rigidbody.get("Shape") != 1:
                raise ValueError(f"{tag} must use a Box rigidbody")
            if "MeshComponent" in components:
                raise ValueError(f"{tag} must remain an invisible collider")
            boundary_wall_count += 1
        elif tag.startswith("Architecture Collision "):
            if not isinstance(rigidbody, dict) or rigidbody.get("Shape") != 1:
                raise ValueError(f"{tag} must use a simple Box rigidbody")
            if "MeshComponent" in components:
                raise ValueError(f"{tag} must remain an invisible collider")
            architecture_box_collider_count += 1
        elif tag in {
            "Broken Ruin Landmark 01",
            "Broken Ruin Landmark 03",
            "Broken Ruin Landmark 04",
        }:
            if not isinstance(rigidbody, dict) or rigidbody.get("Shape") != 3:
                raise ValueError(f"{tag} must use a ConvexHull rigidbody")
            if "MeshComponent" not in components:
                raise ValueError(f"{tag} must retain its visible mesh")
            architecture_convex_hull_count += 1
        elif rigidbody is not None:
            raise ValueError(f"Non-terrain decoration unexpectedly has a rigidbody: {tag}")

        if tag.startswith("Boundary ") and "Tree" in tag:
            boundary_tree_count += 1
        if tag.startswith("EventAnchor_") and tag.endswith(" Barrier Dome"):
            barrier_domes_found[tag[:-len(" Barrier Dome")]] = components
        elif tag.startswith("EventAnchor_") and "Ground Marker" not in tag:
            event_anchors_found[tag] = components
        elif tag.startswith("EventAnchor_") and tag.endswith(" Ground Marker"):
            event_markers_found[tag[:-len(" Ground Marker")]] = components
        elif tag.startswith("Region Landmark "):
            region_landmarks_found[tag] = components
        for group in EVENT_SPAWN_GROUPS:
            if tag.startswith(group.tag_prefix):
                event_spawns_found[group.tag_prefix][tag] = components
                break

        if tag.startswith(surface_tag_prefixes) and not tag.startswith("Rock Floating"):
            transform = components.get("TransformComponent", {})
            translation = transform.get("Translation", [])
            if len(translation) != 3:
                raise ValueError(f"{tag} must have a complete Translation")
            surface_height = terrain_surface_height(float(translation[0]), float(translation[2]))
            pivot_offset = 0.0
            if tag.startswith("BushFlowers "):
                scale = transform.get("Scale", [])
                if len(scale) != 3:
                    raise ValueError(f"{tag} must have a complete Scale")
                pivot_offset = 0.822 * float(scale[1]) + 0.01
            if surface_height is None or abs(float(translation[1]) - surface_height - pivot_offset) > 0.02:
                raise ValueError(f"{tag} is not placed on a terrain surface")

    if terrain_rigidbody_count != len(TERRAIN_PLATES):
        raise ValueError(
            f"Expected {len(TERRAIN_PLATES)} terrain ConvexHull rigidbodies, got {terrain_rigidbody_count}"
        )
    if ramp_rigidbody_count != len(RAMP_SPECS):
        raise ValueError(
            f"Expected {len(RAMP_SPECS)} ramp rigidbodies, got {ramp_rigidbody_count}"
        )
    if boundary_wall_count != 4:
        raise ValueError(f"Expected 4 invisible boundary walls, got {boundary_wall_count}")
    if architecture_box_collider_count != EXPECTED_ARCHITECTURE_BOX_COLLIDER_COUNT:
        raise ValueError(
            "Expected "
            f"{EXPECTED_ARCHITECTURE_BOX_COLLIDER_COUNT} architecture Box rigidbodies, "
            f"got {architecture_box_collider_count}"
        )
    if architecture_convex_hull_count != EXPECTED_ARCHITECTURE_CONVEX_HULL_COUNT:
        raise ValueError(
            "Expected "
            f"{EXPECTED_ARCHITECTURE_CONVEX_HULL_COUNT} solid architecture ConvexHull rigidbodies, "
            f"got {architecture_convex_hull_count}"
        )
    if point_light_count > 1:
        raise ValueError("The forward scene path currently supports only one point light")
    expected_boundary_trees = BOUNDARY_TREE_COUNT_PER_SIDE * 4
    if boundary_tree_count != expected_boundary_trees:
        raise ValueError(
            f"Expected {expected_boundary_trees} boundary trees, got {boundary_tree_count}"
        )
    expected_anchor_names = {anchor.name for anchor in EVENT_ANCHORS}
    if set(event_anchors_found) != expected_anchor_names:
        raise ValueError(
            f"Event anchors mismatch: {sorted(set(event_anchors_found) ^ expected_anchor_names)}"
        )
    if set(event_markers_found) != expected_anchor_names:
        raise ValueError(
            f"Event markers mismatch: {sorted(set(event_markers_found) ^ expected_anchor_names)}"
        )
    if set(barrier_domes_found) != expected_anchor_names:
        raise ValueError(
            "Event barrier domes mismatch: "
            f"{sorted(set(barrier_domes_found) ^ expected_anchor_names)}"
        )
    expected_landmark_tags = {
        "Region Landmark " + visual.region_id.title()
        for visual in REGION_VISUALS
    }
    if set(region_landmarks_found) != expected_landmark_tags:
        raise ValueError(
            "Region landmarks mismatch: "
            f"{sorted(set(region_landmarks_found) ^ expected_landmark_tags)}"
        )
    visuals_by_anchor = {
        visual.anchor_name: visual for visual in REGION_VISUALS
    }
    for anchor in EVENT_ANCHORS:
        components = event_anchors_found[anchor.name]
        if "MeshComponent" in components or "Rigidbody3DComponent" in components:
            raise ValueError(f"{anchor.name} must remain a transform-only gameplay anchor")
        translation = components.get("TransformComponent", {}).get("Translation", [])
        if translation != vec3(anchor.position):
            raise ValueError(f"{anchor.name} moved away from its authored position")
        anchor_surface_height = terrain_surface_height(anchor.position[0], anchor.position[2])
        if anchor_surface_height is None or abs(anchor.position[1] - anchor_surface_height - 0.04) > 0.02:
            raise ValueError(f"{anchor.name} is not aligned to its combat surface")
        marker_components = event_markers_found[anchor.name]
        if "Rigidbody3DComponent" in marker_components:
            raise ValueError(f"{anchor.name} Ground Marker must remain visual-only")
        marker_transform = marker_components.get("TransformComponent", {})
        expected_marker_translation = vec3((
            anchor.position[0],
            anchor.position[1] + anchor.marker_vertical_offset,
            anchor.position[2],
        ))
        if marker_transform.get("Translation") != expected_marker_translation:
            raise ValueError(f"{anchor.name} Ground Marker moved away from its authored height")
        if marker_transform.get("Scale") != vec3((anchor.clear_radius, 1.0, anchor.clear_radius)):
            raise ValueError(f"{anchor.name} Ground Marker no longer matches its clear radius")
        barrier_components = barrier_domes_found[anchor.name]
        if "Rigidbody3DComponent" in barrier_components:
            raise ValueError(f"{anchor.name} Barrier Dome must remain visual-only")
        visual = visuals_by_anchor[anchor.name]
        expected_barrier_mesh = (
            f"{ASSET_MODEL_ROOT}/BarrierDome_{visual.region_id.title()}.hmesh"
        )
        if barrier_components.get("MeshComponent", {}).get("Path") != expected_barrier_mesh:
            raise ValueError(f"{anchor.name} Barrier Dome uses the wrong themed mesh")
        barrier_transform = barrier_components.get("TransformComponent", {})
        expected_barrier_translation = vec3((
            anchor.position[0],
            anchor.position[1] + anchor.marker_vertical_offset,
            anchor.position[2],
        ))
        if barrier_transform.get("Translation") != expected_barrier_translation:
            raise ValueError(f"{anchor.name} Barrier Dome moved away from its anchor")
        expected_barrier_scale = vec3((
            anchor.clear_radius,
            anchor.clear_radius * 0.72,
            anchor.clear_radius,
        ))
        if barrier_transform.get("Scale") != expected_barrier_scale:
            raise ValueError(f"{anchor.name} Barrier Dome no longer covers its clear radius")
        if anchor.name == "EventAnchor_SouthWetland":
            highest_water_surface = max(position[1] for position, _, _ in WETLAND_WATER_SPECS)
            if expected_marker_translation[1] - highest_water_surface < 0.05:
                raise ValueError("South wetland marker must clear every wetland water plane")
        sample_radius = math.ceil(anchor.clear_radius)
        for offset_x in range(-sample_radius, sample_radius + 1):
            for offset_z in range(-sample_radius, sample_radius + 1):
                if offset_x * offset_x + offset_z * offset_z > anchor.clear_radius ** 2:
                    continue
                sampled_height = terrain_surface_height(
                    anchor.position[0] + offset_x,
                    anchor.position[2] + offset_z,
                )
                if sampled_height is None or abs(sampled_height - anchor_surface_height) > 0.12:
                    raise ValueError(f"{anchor.name} combat disc is not flat and continuous")
        for other_components in scene.entities.values():
            other_tag = str(other_components.get("TagComponent", {}).get("Tag", ""))
            if other_tag.startswith("Terrain ") or other_tag.startswith("Dirt Path"):
                continue
            if other_tag in (
                anchor.name,
                f"{anchor.name} Ground Marker",
                f"{anchor.name} Barrier Dome",
            ):
                continue
            translation = other_components.get("TransformComponent", {}).get("Translation", [])
            if len(translation) != 3:
                continue
            distance_squared = (
                (float(translation[0]) - anchor.position[0]) ** 2
                + (float(translation[2]) - anchor.position[2]) ** 2
            )
            if distance_squared < anchor.clear_radius ** 2:
                raise ValueError(f"{other_tag} intrudes into {anchor.name}'s clear combat disc")

    for visual in REGION_VISUALS:
        tag = "Region Landmark " + visual.region_id.title()
        components = region_landmarks_found[tag]
        if "Rigidbody3DComponent" in components:
            raise ValueError(f"{tag} must remain a collision-free silhouette landmark")
        expected_mesh_path = f"{ASSET_MODEL_ROOT}/{visual.landmark_mesh}.hmesh"
        if components.get("MeshComponent", {}).get("Path") != expected_mesh_path:
            raise ValueError(f"{tag} uses the wrong themed mesh")
        transform = components.get("TransformComponent", {})
        x, z = visual.landmark_position
        surface_height = terrain_surface_height(x, z)
        if surface_height is None:
            raise ValueError(f"{tag} has no authored terrain surface")
        supported_height = terrain_surface_height(x, z, 1.0)
        if supported_height is None or abs(supported_height - surface_height) > 0.02:
            raise ValueError(f"{tag} base is too close to a terrain edge or step")
        if transform.get("Translation") != vec3((x, surface_height + 0.01, z)):
            raise ValueError(f"{tag} moved away from its authored position")
        if transform.get("Rotation") != vec3((0.0, visual.landmark_yaw, 0.0)):
            raise ValueError(f"{tag} moved away from its authored orientation")
        if (
            abs(x) + visual.footprint_radius + 0.75 > PLAYABLE_HALF_EXTENT
            or abs(z) + visual.footprint_radius + 0.75 > PLAYABLE_HALF_EXTENT
        ):
            raise ValueError(f"{tag} footprint is too close to a boundary wall")
        for ramp_spec in RAMP_SPECS:
            minimum_distance = (
                ramp_spec.width * 0.5 + visual.footprint_radius + 0.75
            )
            if point_segment_distance_squared(
                visual.landmark_position,
                ramp_spec.low_center,
                ramp_spec.high_center,
            ) < minimum_distance ** 2:
                raise ValueError(f"{tag} footprint obstructs ramp {ramp_spec.name}")
        for centers, width, closed, _vertical_offset in authored_path_specs():
            segment_count = len(centers) if closed else len(centers) - 1
            minimum_distance = width * 0.5 + visual.footprint_radius + 0.50
            if any(
                point_segment_distance_squared(
                    visual.landmark_position,
                    centers[index],
                    centers[(index + 1) % len(centers)],
                ) < minimum_distance ** 2
                for index in range(segment_count)
            ):
                raise ValueError(f"{tag} footprint obstructs an authored path")
        for anchor in EVENT_ANCHORS:
            minimum_distance = (
                anchor.clear_radius + visual.footprint_radius + 0.75
            )
            distance_squared = (
                (x - anchor.position[0]) ** 2
                + (z - anchor.position[2]) ** 2
            )
            if distance_squared < minimum_distance ** 2:
                raise ValueError(f"{tag} footprint intrudes into {anchor.name}")

    all_spawn_positions: list[tuple[str, float, float]] = []
    landmark_footprints_by_tag = {
        "Region Landmark " + visual.region_id.title(): visual.footprint_radius
        for visual in REGION_VISUALS
    }
    anchors_by_name = {anchor.name: anchor for anchor in EVENT_ANCHORS}
    for group in EVENT_SPAWN_GROUPS:
        if len(group.offsets) != 10:
            raise ValueError(f"{group.tag_prefix} must author exactly 10 spawn sockets")
        expected_tags = {
            f"{group.tag_prefix}{index:02d}" for index in range(len(group.offsets))
        }
        found = event_spawns_found[group.tag_prefix]
        if set(found) != expected_tags:
            raise ValueError(
                f"{group.tag_prefix} spawn sockets mismatch: "
                f"{sorted(set(found) ^ expected_tags)}"
            )

        anchor = anchors_by_name[group.anchor_name]
        direction_bins: set[int] = set()
        for index, tag in enumerate(sorted(expected_tags)):
            components = found[tag]
            if "MeshComponent" in components or "Rigidbody3DComponent" in components:
                raise ValueError(f"{tag} must remain a transform-only spawn socket")
            transform = components.get("TransformComponent", {})
            translation = transform.get("Translation", [])
            if len(translation) != 3:
                raise ValueError(f"{tag} must have a complete Translation")
            spawn_x, spawn_z = event_spawn_xz(group, index)
            surface_height = terrain_surface_height(spawn_x, spawn_z)
            safe_surface_height = terrain_surface_height(spawn_x, spawn_z, 0.65)
            if (
                surface_height is None
                or safe_surface_height is None
                or abs(surface_height - safe_surface_height) > 0.02
            ):
                raise ValueError(f"{tag} is too close to a terrain edge or cliff")
            expected_translation = vec3((
                spawn_x,
                surface_height + EVENT_SPAWN_SURFACE_OFFSET,
                spawn_z,
            ))
            if translation != expected_translation:
                raise ValueError(f"{tag} moved away from its authored terrain position")

            anchor_distance_squared = (
                (spawn_x - anchor.position[0]) ** 2
                + (spawn_z - anchor.position[2]) ** 2
            )
            if anchor_distance_squared < (anchor.clear_radius + 0.75) ** 2:
                raise ValueError(f"{tag} overlaps its region's clear light disc")
            if spawn_x * spawn_x + spawn_z * spawn_z < 24.0 ** 2:
                raise ValueError(f"{tag} is too close to the player start")
            if (
                abs(spawn_x) > PLAYABLE_HALF_EXTENT - 3.0
                or abs(spawn_z) > PLAYABLE_HALF_EXTENT - 3.0
            ):
                raise ValueError(f"{tag} is too close to a boundary wall")

            water_height = wetland_water_surface_height(spawn_x, spawn_z)
            if water_height is not None and surface_height < water_height + 0.03:
                raise ValueError(f"{tag} is below a wetland water surface")

            neighborhood_heights = []
            for sample_index in range(8):
                angle = math.tau * sample_index / 8.0
                sample_height = terrain_surface_height(
                    spawn_x + math.cos(angle) * 0.70,
                    spawn_z + math.sin(angle) * 0.70,
                    0.15,
                )
                if sample_height is None:
                    raise ValueError(f"{tag} has unsupported ground in its spawn footprint")
                neighborhood_heights.append(sample_height)
            if max(neighborhood_heights) - min(neighborhood_heights) > 0.12:
                raise ValueError(f"{tag} crosses a discontinuous terrain step")

            angle = math.atan2(
                spawn_z - anchor.position[2],
                spawn_x - anchor.position[0],
            )
            direction_bins.add(int(((angle + math.tau) % math.tau) / (math.pi * 0.5)))
            all_spawn_positions.append((tag, spawn_x, spawn_z))

        if len(direction_bins) < 2:
            raise ValueError(f"{group.tag_prefix} needs at least two attack directions")

    for index, (tag, spawn_x, spawn_z) in enumerate(all_spawn_positions):
        for other_tag, other_x, other_z in all_spawn_positions[index + 1:]:
            if (spawn_x - other_x) ** 2 + (spawn_z - other_z) ** 2 < 2.5 ** 2:
                raise ValueError(f"Spawn sockets overlap: {tag} and {other_tag}")

        for other_components in scene.entities.values():
            other_tag = str(other_components.get("TagComponent", {}).get("Tag", ""))
            if (
                not other_tag
                or other_tag == tag
                or other_tag.startswith("EventAnchor_")
                or other_tag.startswith("EventSpawn_")
                or other_tag.startswith("Terrain ")
                or other_tag.startswith("Dirt Path")
                or other_tag.startswith("South Wetland Water")
            ):
                continue
            other_translation = other_components.get(
                "TransformComponent", {}
            ).get("Translation", [])
            if len(other_translation) != 3:
                continue
            distance_squared = (
                (spawn_x - float(other_translation[0])) ** 2
                + (spawn_z - float(other_translation[2])) ** 2
            )
            landmark_footprint = landmark_footprints_by_tag.get(other_tag)
            if (
                landmark_footprint is not None
                and distance_squared < (landmark_footprint + 0.75) ** 2
            ):
                raise ValueError(f"{tag} overlaps themed landmark {other_tag}")
            large_prop = other_tag.startswith((
                "Boundary ",
                "Cluster Tree ",
                "West Shrine Gate ",
                "Broken Ruin Landmark ",
                "Broken Crystal Obelisk ",
                "Rock ",
                "Crystal Cluster ",
                "Wetland Dead Tree ",
                "BushFlowers ",
                "Region Landmark ",
            ))
            if large_prop and distance_squared < 1.75 ** 2:
                raise ValueError(f"{tag} overlaps large prop {other_tag}")

            if other_tag.startswith(("Forest Boundary ", "Architecture Collision ")):
                other_transform = other_components.get("TransformComponent", {})
                scale = other_transform.get("Scale", [])
                rotation = other_transform.get("Rotation", [])
                if len(scale) != 3 or len(rotation) != 3:
                    raise ValueError(f"{other_tag} has incomplete collider transform data")
                delta_x = spawn_x - float(other_translation[0])
                delta_z = spawn_z - float(other_translation[2])
                cosine = math.cos(float(rotation[1]))
                sine = math.sin(float(rotation[1]))
                local_x = cosine * delta_x - sine * delta_z
                local_z = sine * delta_x + cosine * delta_z
                if (
                    abs(local_x) <= float(scale[0]) * 0.5 + 1.0
                    and abs(local_z) <= float(scale[2]) * 0.5 + 1.0
                ):
                    raise ValueError(f"{tag} overlaps collider {other_tag}")

    def plate_height_at(point: Vec2) -> float | None:
        heights = [
            plate.top_y for plate in TERRAIN_PLATES
            if point_in_polygon(point[0], point[1], plate.outline)
        ]
        return max(heights) if heights else None

    entrance_counts: Counter[str] = Counter()
    for ramp_spec in RAMP_SPECS:
        if ramp_spec.width < 7.0:
            raise ValueError(f"{ramp_spec.name} is narrower than the 7 m combat minimum")
        slope_degrees = math.degrees(math.atan2(
            ramp_spec.high_y - ramp_spec.low_y,
            ramp_spec.length,
        ))
        minimum_slope = 4.5 if ramp_spec.region == "SouthWetland" else 14.0
        if not minimum_slope <= slope_degrees <= 21.0:
            raise ValueError(
                f"{ramp_spec.name} slope {slope_degrees:.2f} is outside its authored range"
            )
        low_height = plate_height_at(ramp_spec.low_center)
        high_height = plate_height_at(ramp_spec.high_center)
        if low_height is None or abs(low_height - ramp_spec.low_y) > 0.12:
            raise ValueError(f"{ramp_spec.name} low seam is disconnected")
        if high_height is None or abs(high_height - ramp_spec.high_y) > 0.12:
            raise ValueError(f"{ramp_spec.name} high seam is disconnected")
        delta_x = ramp_spec.high_center[0] - ramp_spec.low_center[0]
        delta_z = ramp_spec.high_center[1] - ramp_spec.low_center[1]
        direction_x = delta_x / ramp_spec.length
        direction_z = delta_z / ramp_spec.length
        right_x = direction_z
        right_z = -direction_x
        for lateral_index in range(5):
            lateral = (lateral_index / 4.0 - 0.5) * ramp_spec.width
            for center, expected_height, seam_name in (
                (ramp_spec.low_center, ramp_spec.low_y, "low"),
                (ramp_spec.high_center, ramp_spec.high_y, "high"),
            ):
                seam_point = (
                    center[0] + right_x * lateral,
                    center[1] + right_z * lateral,
                )
                seam_height = plate_height_at(seam_point)
                if seam_height is None or abs(seam_height - expected_height) > 0.05:
                    raise ValueError(
                        f"{ramp_spec.name} {seam_name} seam is not connected across its full width"
                    )
        for progress_index in range(101):
            progress = progress_index / 100.0
            expected_height = ramp_spec.low_y + (ramp_spec.high_y - ramp_spec.low_y) * progress
            for lateral_index in range(5):
                lateral = (lateral_index / 4.0 - 0.5) * ramp_spec.width
                sample_x = ramp_spec.low_center[0] + delta_x * progress + right_x * lateral
                sample_z = ramp_spec.low_center[1] + delta_z * progress + right_z * lateral
                visible_height = terrain_surface_height(sample_x, sample_z)
                if visible_height is None or visible_height - expected_height > 0.05:
                    raise ValueError(f"{ramp_spec.name} is hidden by an overlapping terrain plate")
        entrance_counts[ramp_spec.region] += 1
    for region in ("WestShrine", "NorthRidgeLower", "NorthRidgeUpper", "EastBasin", "SouthWetland"):
        if entrance_counts[region] < 2:
            raise ValueError(f"{region} must have at least two wide entrances")

    for plate in TERRAIN_PLATES:
        winding_sign = 0
        for index in range(len(plate.outline)):
            a = plate.outline[index]
            b = plate.outline[(index + 1) % len(plate.outline)]
            c = plate.outline[(index + 2) % len(plate.outline)]
            turn = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if abs(turn) <= 1.0e-6:
                continue
            current_sign = 1 if turn > 0.0 else -1
            if winding_sign and current_sign != winding_sign:
                raise ValueError(f"Terrain plate {plate.name} is concave and unsafe for one ConvexHull")
            winding_sign = current_sign

    plates_by_name = {plate.name: plate for plate in TERRAIN_PLATES}
    terrace_pairs = (
        ("WestShrine", "WestShrineShoulder"),
        ("WestShrineShoulder", "WestLowland"),
        ("NorthRidgeUpper", "NorthRidgeMid"),
        ("NorthRidgeMid", "NorthRidgeLower"),
        ("NorthRidgeLower", "NorthRidgeShoulder"),
        ("NorthRidgeShoulder", "NorthLowland"),
    )
    for inner_name, outer_name in terrace_pairs:
        inner_plate = plates_by_name[inner_name]
        outer_plate = plates_by_name[outer_name]
        if inner_plate.top_y - outer_plate.top_y > 2.25:
            raise ValueError(f"Terrace step {outer_name} -> {inner_name} exceeds combat vertical range")
        for edge_index, start in enumerate(inner_plate.outline):
            end = inner_plate.outline[(edge_index + 1) % len(inner_plate.outline)]
            for sample_index in range(21):
                progress = sample_index / 20.0
                sample = (
                    start[0] + (end[0] - start[0]) * progress,
                    start[1] + (end[1] - start[1]) * progress,
                )
                if not point_in_polygon(sample[0], sample[1], outer_plate.outline):
                    raise ValueError(f"{inner_name} escapes its protective {outer_name} terrace")

    foundation = TERRAIN_PLATES[0]
    floor_half_x = max(abs(point[0]) for point in foundation.outline)
    floor_half_z = max(abs(point[1]) for point in foundation.outline)
    if abs(floor_half_x - ARENA_FLOOR_HALF_EXTENT) > 0.001 or abs(floor_half_z - ARENA_FLOOR_HALF_EXTENT) > 0.001:
        raise ValueError("Arena floor extent no longer matches the configured safety floor")
    required_floor_margin = PLAYABLE_HALF_EXTENT + BOUNDARY_WALL_THICKNESS * 0.5
    if floor_half_x < required_floor_margin or floor_half_z < required_floor_margin:
        raise ValueError("Arena floor must extend beyond every boundary wall")
    if PLAYABLE_HALF_EXTENT * 2.0 < 166.0 or PLAYABLE_HALF_EXTENT * 2.0 > 184.0:
        raise ValueError("Playable arena diameter must remain inside the 166-184 m target")
    if abs(terrain_surface_height(0.0, 0.0) - 0.02) > 0.001:
        raise ValueError("The central reset point must remain on the open meadow floor")
    if min(plate.top_y for plate in TERRAIN_PLATES) < -1.2:
        raise ValueError("Playable terrain is below the safe wetland depth")
    if max(plate.top_y for plate in TERRAIN_PLATES) > 6.0:
        raise ValueError("Playable terrain exceeds the direct-chase ground probe budget")

    path_offsets = [specification[3] for specification in authored_path_specs()]
    if len(set(path_offsets)) != len(path_offsets):
        raise ValueError("Authored path strips must use unique offsets at intersections")
    path_positions = meshes["DirtPaths"].positions
    for position in path_positions:
        surface_height = terrain_surface_height(position[0], position[2])
        if surface_height is None:
            raise ValueError("Dirt path vertex has no supporting terrain")
        surface_offset = position[1] - surface_height
        if not 0.025 <= surface_offset <= 0.07:
            raise ValueError("Dirt path vertex is floating above or buried below terrain")
    for triangle_index in range(0, len(path_positions), 3):
        triangle = path_positions[triangle_index:triangle_index + 3]
        for weights in ((1.0 / 3.0,) * 3, (0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6)):
            sample = tuple(
                sum(triangle[vertex_index][axis] * weights[vertex_index] for vertex_index in range(3))
                for axis in range(3)
            )
            surface_height = terrain_surface_height(sample[0], sample[2])
            if surface_height is None or not -0.05 <= sample[1] - surface_height <= 0.12:
                raise ValueError("Dirt path triangle crosses an unsupported terrain step")

    for external_path in EXTERNAL_MESH_PATHS.values():
        if scene.mesh_usage[external_path] <= 0:
            raise ValueError(f"Selected external asset is not used: {external_path}")


def rgbe_pixel(red: float, green: float, blue: float) -> bytes:
    brightest = max(red, green, blue)
    if brightest < 1.0e-32:
        return b"\x00\x00\x00\x00"
    mantissa, exponent = math.frexp(brightest)
    scale = mantissa * 256.0 / brightest
    return bytes((
        min(255, int(red * scale)),
        min(255, int(green * scale)),
        min(255, int(blue * scale)),
        min(255, exponent + 128),
    ))


def radiance_literal_channel(channel: bytes) -> bytes:
    encoded = bytearray()
    for start in range(0, len(channel), 128):
        chunk = channel[start:start + 128]
        encoded.append(len(chunk))
        encoded.extend(chunk)
    return bytes(encoded)


def build_hdr(width: int = 256, height: int = 128) -> bytes:
    output = bytearray(
        f"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {height} +X {width}\n".encode("ascii")
    )
    top = (0.20, 0.48, 0.92)
    horizon = (1.18, 0.72, 0.42)
    lower = (0.16, 0.25, 0.24)
    for y in range(height):
        v = y / (height - 1)
        scanline = bytearray()
        for x in range(width):
            u = x / (width - 1)
            if v < 0.60:
                blend = (v / 0.60) ** 1.35
                color = tuple(top[index] * (1.0 - blend) + horizon[index] * blend for index in range(3))
            else:
                blend = ((v - 0.60) / 0.40) ** 0.70
                color = tuple(horizon[index] * (1.0 - blend) + lower[index] * blend for index in range(3))
            du = min(abs(u - 0.74), 1.0 - abs(u - 0.74))
            dv = v - 0.27
            sun = 15.0 * math.exp(-(du * du + dv * dv) / 0.00055)
            scanline.extend(rgbe_pixel(color[0] + sun, color[1] + sun * 0.82, color[2] + sun * 0.55))
        output.extend((2, 2, width >> 8, width & 0xFF))
        for channel_index in range(4):
            output.extend(radiance_literal_channel(scanline[channel_index::4]))
    return bytes(output)


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def build_rgba_png(
    width: int,
    height: int,
    pixel_at,
) -> bytes:
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        for x in range(width):
            red, green, blue, alpha = pixel_at(x, y)
            scanlines.extend((red, green, blue, alpha))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(bytes(scanlines), 9))
        + png_chunk(b"IEND", b"")
    )


def build_detail_textures() -> dict[str, bytes]:
    """Generate a restrained 4x4-block macro pattern shared by large surfaces."""
    albedo_palette = (
        (250, 252, 246, 255),
        (238, 246, 235, 255),
        (246, 241, 229, 255),
        (232, 240, 231, 255),
    )
    normal_palette = (
        (128, 128, 255, 255),
        (133, 126, 254, 255),
        (124, 132, 254, 255),
        (130, 134, 254, 255),
    )
    ao_palette = (255, 246, 251, 239)
    roughness_palette = (248, 236, 244, 229)

    def palette_index(x: int, y: int) -> int:
        return ((x // 4) + (y // 4) * 3) % 4

    return {
        DETAIL_ALBEDO_PATH: build_rgba_png(
            16,
            16,
            lambda x, y: albedo_palette[palette_index(x, y)],
        ),
        DETAIL_NORMAL_PATH: build_rgba_png(
            16,
            16,
            lambda x, y: normal_palette[palette_index(x, y)],
        ),
        DETAIL_AO_PATH: build_rgba_png(
            16,
            16,
            lambda x, y: (ao_palette[palette_index(x, y)],) * 3 + (255,),
        ),
        DETAIL_MR_PATH: build_rgba_png(
            16,
            16,
            lambda x, y: (255, roughness_palette[palette_index(x, y)], 0, 255),
        ),
    }


def json_bytes(value: object) -> bytes:
    # Generated JSON is checked in with the repository's Windows text format.
    # Serialize explicitly so --verify-generated is independent of Python's host
    # newline translation.
    text = json.dumps(value, indent=4, ensure_ascii=False) + "\n"
    return text.replace("\n", "\r\n").encode("utf-8")


def assert_forward_slashes(value: object, location: str = "root") -> None:
    if isinstance(value, str):
        if "\\" in value:
            raise ValueError(f"Backslash found in serialized string at {location}: {value}")
    elif isinstance(value, dict):
        for key, child in value.items():
            assert_forward_slashes(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_forward_slashes(child, f"{location}[{index}]")


def validate_external_assets(project_root: Path) -> None:
    expected_paths = {
        *EXTERNAL_MESH_PATHS.values(),
        *(Path(path).with_suffix(".bin").as_posix() for path in EXTERNAL_MESH_PATHS.values()),
    }
    if set(EXTERNAL_ASSET_SHA256) != expected_paths:
        raise RuntimeError("External asset hash manifest does not match the selected mesh set")
    allowed_materials = {material_path(name) for name in build_materials()}
    for asset_path, expected_hash in EXTERNAL_ASSET_SHA256.items():
        payload = (project_root / asset_path).read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest().upper()
        if actual_hash != expected_hash:
            raise RuntimeError(f"External asset hash mismatch: {asset_path}")
    for mesh_asset_path in EXTERNAL_MESH_PATHS.values():
        mesh_resource = json.loads((project_root / mesh_asset_path).read_text(encoding="utf-8"))
        assert_forward_slashes(mesh_resource, f"external-mesh:{mesh_asset_path}")
        buffer_asset_path = Path(mesh_asset_path).with_suffix(".bin").as_posix()
        buffers = mesh_resource.get("bufferVec", [])
        if len(buffers) != 1 or buffers[0].get("uri") != buffer_asset_path:
            raise RuntimeError(f"External mesh buffer URI mismatch: {mesh_asset_path}")
        if int(buffers[0].get("byteLength", -1)) != (project_root / buffer_asset_path).stat().st_size:
            raise RuntimeError(f"External mesh buffer length mismatch: {mesh_asset_path}")
        referenced_materials = {
            primitive.get("materialResPath", "")
            for primitive in mesh_resource.get("primitives", [])
        }
        if not referenced_materials or not referenced_materials <= allowed_materials:
            raise RuntimeError(f"External mesh material mapping is invalid: {mesh_asset_path}")


def validate_roots() -> tuple[Path, Path]:
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    repo_root = project_root.parent
    required = (
        repo_root / "CMakeLists.txt",
        repo_root / "Engine" / "CMakeLists.txt",
        project_root / "Config" / "BaseEngine.json",
        project_root / "Assets",
        project_root / "Scripts" / "SurvivorGame.py",
        project_root / "Scripts" / "SurvivorWorld.py",
        project_root / PLAYER_MESH_PATH,
        project_root / f"{CAT_ROOT}/Cat.bin",
        project_root / f"{CAT_ROOT}/Atlas.hmat",
        project_root / f"{CAT_ROOT}/Atlas_Monsters.png",
        project_root / f"{CAT_ROOT}/Cat_Skeleton.hskel",
        project_root / PLAYER_ANIMATION_PATH,
        project_root / f"{CAT_ROOT}/CharacterArmature_Walk.hanim",
        project_root / f"{CAT_ROOT}/CharacterArmature_Jump.hanim",
        project_root / PLAYER_CONTROLLER_PATH,
        *(project_root / path for path in EXTERNAL_MESH_PATHS.values()),
        *(project_root / Path(path).with_suffix(".bin") for path in EXTERNAL_MESH_PATHS.values()),
        project_root / "SourceAssets" / "Quaternius" / "UltimateStylizedNature" / "README.md",
        project_root / "SourceAssets" / "Quaternius" / "UltimateStylizedNature" / "License.txt",
        project_root / "SourceAssets" / "Quaternius" / "UltimateModularRuins" / "README.md",
        project_root / "SourceAssets" / "Quaternius" / "UltimateModularRuins" / "License.txt",
    )
    if project_root.name != "Project":
        raise RuntimeError(f"Expected the tool below a Project directory, got: {project_root}")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Repository validation failed; missing:\n  " + "\n  ".join(missing))
    validate_external_assets(project_root)
    return repo_root, project_root


def safe_clean_owned_directory(
    project_root: Path,
    asset_path: str,
    expected_parent_asset_path: str,
    expected_name: str,
) -> Path:
    assets_root = (project_root / "Assets").resolve()
    target = project_root / asset_path
    attributes = getattr(target.lstat(), "st_file_attributes", 0) if target.exists() else 0
    if target.is_symlink() or attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise RuntimeError(f"Refusing to replace symlinked output directory: {target}")
    resolved_target = target.resolve()
    expected_parent = (project_root / expected_parent_asset_path).resolve()
    if not path_is_relative_to(expected_parent, assets_root):
        raise RuntimeError(f"Owned output parent is outside Assets: {expected_parent}")
    if resolved_target.parent != expected_parent or resolved_target.name != expected_name:
        raise RuntimeError(f"Refusing to clean unexpected output directory: {resolved_target}")
    if target.exists():
        for current_root, directory_names, file_names in os.walk(target, followlinks=False):
            for name in (*directory_names, *file_names):
                candidate = Path(current_root) / name
                candidate_attributes = getattr(candidate.lstat(), "st_file_attributes", 0)
                if candidate.is_symlink() or candidate_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise RuntimeError(f"Refusing to traverse reparse point in owned output: {candidate}")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)
    return target


def safe_clean_owned_model_root(project_root: Path) -> Path:
    return safe_clean_owned_directory(
        project_root,
        ASSET_MODEL_ROOT,
        "Assets/Models",
        "VerdantRift",
    )


def safe_clean_owned_detail_root(project_root: Path) -> Path:
    return safe_clean_owned_directory(
        project_root,
        DETAIL_TEXTURE_ROOT,
        "Assets/Textures",
        "VerdantRift",
    )


def build_payloads(project_root: Path) -> tuple[dict[Path, bytes], dict[str, object]]:
    rng = random.Random(SEED)
    materials = build_materials()
    meshes = build_meshes()
    scene = build_scene(meshes, rng)
    hdr_width, hdr_height = 256, 128

    required_meshes = {
        *(f"TerrainPlate_{plate.name}" for plate in TERRAIN_PLATES),
        *(f"TerrainRamp_{ramp_spec.name}" for ramp_spec in RAMP_SPECS),
        "DirtPaths",
        "StarPlinth",
        "EventRing_West",
        "EventRing_North",
        "EventRing_East",
        "EventRing_South",
        "RegionLandmark_Star",
        "RegionLandmark_Thunder",
        "RegionLandmark_Water",
        "RegionLandmark_Wind",
        "BarrierDome_Star",
        "BarrierDome_Thunder",
        "BarrierDome_Water",
        "BarrierDome_Wind",
        "DeciduousTree",
        "BlossomTree",
        "PineTree",
        "Rock",
        "GrassTuft",
        "Flower",
        "Mushroom",
        "Reeds",
        "ShrineGate",
        "Crystal",
        "DistantMountain_01",
        "DistantMountain_02",
        "DistantMountain_03",
        "ExperienceCrystal",
        "WaterPlane",
        "BrokenObelisk",
    }
    if set(meshes) != required_meshes:
        raise ValueError(f"Unexpected mesh set: {sorted(set(meshes) ^ required_meshes)}")
    referenced_materials = {
        material
        for mesh in meshes.values()
        for material in mesh.primitive_indices
    }
    if not referenced_materials <= set(materials):
        raise ValueError(
            f"Meshes reference missing materials: {sorted(referenced_materials - set(materials))}"
        )
    if not 8 <= len(materials) <= 20:
        raise ValueError(f"Verdant Rift palette budget exceeded: {len(materials)} materials")
    if EVENT_MARKER_SEGMENTS < 64:
        raise ValueError("Region marker rings require at least 64 radial segments")
    barrier_materials = {
        "Star": "BarrierStar",
        "Thunder": "BarrierThunder",
        "Water": "BarrierWater",
        "Wind": "BarrierWind",
    }
    for region_name, material_name in barrier_materials.items():
        material = materials.get(material_name)
        if (
            material is None
            or material.alpha_mode != "BLEND"
            or not material.double_sided
            or not 0.0 < material.color[3] <= 0.16
        ):
            raise ValueError(
                f"{region_name} barrier material must remain a subtle double-sided blend"
            )
        dome = meshes[f"BarrierDome_{region_name}"]
        if set(dome.primitive_indices) != {material_name}:
            raise ValueError(f"{region_name} barrier dome uses unexpected materials")
        if (
            min(position[1] for position in dome.positions) < -1.0e-6
            or max(position[1] for position in dome.positions) < 0.999
            or max(math.sqrt(position[0] ** 2 + position[2] ** 2)
                   for position in dome.positions) < 0.999
        ):
            raise ValueError(f"{region_name} barrier dome is not a unit upper hemisphere")

    payloads: dict[Path, bytes] = {}
    for name, specification in materials.items():
        material = material_json(name, specification)
        assert_forward_slashes(material, f"material:{name}")
        payloads[project_root / material_path(name)] = json_bytes(material)

    for texture_path, texture_payload in build_detail_textures().items():
        payloads[project_root / texture_path] = texture_payload

    total_vertices = 0
    total_triangles = 0
    for mesh_name, mesh in meshes.items():
        mesh_resource, binary = mesh_payload(mesh)
        assert_forward_slashes(mesh_resource, f"mesh:{mesh_name}")
        payloads[project_root / f"{ASSET_MODEL_ROOT}/{mesh_name}.hmesh"] = json_bytes(mesh_resource)
        payloads[project_root / f"{ASSET_MODEL_ROOT}/{mesh_name}.bin"] = binary
        total_vertices += len(mesh.positions)
        total_triangles += mesh.triangle_count

    assert_forward_slashes(scene.entities, "scene")
    payloads[project_root / SCENE_ASSET_PATH] = json_bytes(scene.entities)
    payloads[project_root / HDR_ASSET_PATH] = build_hdr(hdr_width, hdr_height)

    payload_digest = hashlib.sha256()
    for output_path, payload in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
        payload_digest.update(output_path.relative_to(project_root).as_posix().encode("utf-8"))
        payload_digest.update(b"\0")
        payload_digest.update(payload)
    external_dependency_digest = hashlib.sha256()
    for asset_path in sorted(EXTERNAL_ASSET_SHA256):
        external_dependency_digest.update(asset_path.encode("utf-8"))
        external_dependency_digest.update(b"\0")
        external_dependency_digest.update((project_root / asset_path).read_bytes())
    generation_fingerprint = hashlib.sha256(
        payload_digest.digest() + external_dependency_digest.digest()
    )

    mesh_entity_count = sum(
        1 for components in scene.entities.values() if "MeshComponent" in components
    )
    rigidbody_shapes = Counter(
        components["Rigidbody3DComponent"]["Shape"]
        for components in scene.entities.values()
        if "Rigidbody3DComponent" in components
    )
    suffix_counts = Counter(path.suffix for path in payloads)
    statistics: dict[str, object] = {
        "seed": SEED,
        "generated_file_count": len(payloads),
        "generated_payload_sha256": payload_digest.hexdigest().upper(),
        "external_dependency_sha256": external_dependency_digest.hexdigest().upper(),
        "generation_fingerprint_sha256": generation_fingerprint.hexdigest().upper(),
        "file_counts": dict(sorted(suffix_counts.items())),
        "material_count": len(materials),
        "mesh_asset_count": len(meshes),
        "mesh_vertex_count": total_vertices,
        "mesh_triangle_count": total_triangles,
        "scene_entity_count": len(scene.entities),
        "scene_mesh_entity_count": mesh_entity_count,
        "scene_static_box_rigidbody_count": rigidbody_shapes[1],
        "scene_static_convex_hull_rigidbody_count": rigidbody_shapes[3],
        "scene_mesh_asset_usage": dict(sorted(scene.mesh_usage.items())),
        "hdr_resolution": [hdr_width, hdr_height],
        "detail_texture_resolution": [16, 16],
        "playable_diameter": rounded(PLAYABLE_HALF_EXTENT * 2.0),
        "event_anchor_count": len(EVENT_ANCHORS),
        "event_marker_segments": EVENT_MARKER_SEGMENTS,
        "region_landmark_count": len(REGION_VISUALS),
        "barrier_dome_count": len(REGION_VISUALS),
        "barrier_dome_tessellation": [
            BARRIER_DOME_RADIAL_SEGMENTS,
            BARRIER_DOME_HEIGHT_SEGMENTS,
        ],
        "event_spawn_socket_count": sum(
            len(group.offsets) for group in EVENT_SPAWN_GROUPS
        ),
        "event_spawn_socket_groups": {
            group.tag_prefix: len(group.offsets) for group in EVENT_SPAWN_GROUPS
        },
        "model_output": ASSET_MODEL_ROOT,
        "hdr_output": HDR_ASSET_PATH,
        "scene_output": SCENE_ASSET_PATH,
    }
    return payloads, statistics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="build and validate every payload in memory without writing files",
    )
    mode.add_argument(
        "--verify-generated",
        action="store_true",
        help="verify that every generated file matches the deterministic payload",
    )
    arguments = parser.parse_args()

    _, project_root = validate_roots()
    payloads, statistics = build_payloads(project_root)

    if arguments.check:
        statistics["mode"] = "check"
        statistics["result"] = "PASS"
        print(json.dumps(statistics, indent=4, ensure_ascii=False))
        return

    if arguments.verify_generated:
        mismatches = []
        for output_path, expected_payload in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
            if not output_path.is_file():
                mismatches.append(f"missing: {output_path.relative_to(project_root).as_posix()}")
                continue
            if output_path.read_bytes() != expected_payload:
                mismatches.append(f"different: {output_path.relative_to(project_root).as_posix()}")
        for owned_asset_root in (ASSET_MODEL_ROOT, DETAIL_TEXTURE_ROOT):
            owned_root = (project_root / owned_asset_root).resolve()
            expected_owned_files = {
                path.resolve() for path in payloads
                if path_is_relative_to(path.resolve(), owned_root)
            }
            if owned_root.is_dir():
                extra_owned_files = sorted(
                    path for path in owned_root.rglob("*")
                    if path.is_file() and path.resolve() not in expected_owned_files
                )
                mismatches.extend(
                    f"unexpected: {path.relative_to(project_root).as_posix()}"
                    for path in extra_owned_files
                )
        if mismatches:
            raise RuntimeError("Generated output verification failed:\n  " + "\n  ".join(mismatches))
        statistics["mode"] = "verify-generated"
        statistics["result"] = "PASS"
        print(json.dumps(statistics, indent=4, ensure_ascii=False))
        return

    model_root = safe_clean_owned_model_root(project_root)
    safe_clean_owned_detail_root(project_root)
    hdr_root = (project_root / HDR_ASSET_PATH).parent
    scene_root = (project_root / SCENE_ASSET_PATH).parent
    (model_root / "Materials").mkdir(parents=True, exist_ok=True)
    hdr_root.mkdir(parents=True, exist_ok=True)
    scene_root.mkdir(parents=True, exist_ok=True)

    for output_path, payload in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)

    statistics["mode"] = "generate"
    statistics["result"] = "PASS"
    print(json.dumps(statistics, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
