"""Generate the deterministic native low-poly Survivor boss chest asset."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Iterable, Sequence, Tuple


OUTPUT_PROJECT_ROOT = Path("Project/Assets/Models/SurvivorBossChest")
OUTPUT_ASSET_ROOT = "Assets/Models/SurvivorBossChest"
PREFAB_PROJECT_PATH = Path("Project/Assets/Prefabs/SurvivorBossChest.hprefab")
MODEL_NAME = "BossChest"
MATERIAL_ORDER = ("Body", "GoldTrim", "StarClasp")
PREFAB_SCALE = 0.72
PREFAB_HEIGHT = 0.18

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]
Face = Tuple[int, int, int]


@dataclass(frozen=True)
class MaterialDefinition:
    color: tuple[float, float, float, float]
    metallic: float
    roughness: float
    emissive: tuple[float, float, float, float] | None = None


MATERIAL_DEFINITIONS = {
    "Body": MaterialDefinition((0.18, 0.08, 0.34, 1.0), 0.04, 0.68),
    "GoldTrim": MaterialDefinition((0.92, 0.52, 0.10, 1.0), 0.28, 0.46),
    "StarClasp": MaterialDefinition(
        (1.0, 0.86, 0.30, 1.0),
        0.14,
        0.36,
        (0.10, 0.045, 0.006, 1.0),
    ),
}


def load_module(path: Path, name: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Cannot load generator helper: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def load_helpers(repo_root: Path) -> tuple[ModuleType, ModuleType]:
    helpers = load_module(
        repo_root / "Project/Tools/GenerateVerdantRift.py",
        "he_survivor_boss_chest_mesh_helpers",
    )
    validation = load_module(
        repo_root / "Tools/VFX/generate_survivor_projectile_meshes.py",
        "he_survivor_boss_chest_mesh_validation",
    )
    helpers.ASSET_MODEL_ROOT = OUTPUT_ASSET_ROOT
    validation.OUTPUT_ASSET_ROOT = OUTPUT_ASSET_ROOT
    return helpers, validation


def json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def material_key(local_name: str) -> str:
    return f"{MODEL_NAME}_{local_name}"


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a: Vec3, b: Vec3) -> float:
    return sum(a[index] * b[index] for index in range(3))


def signed_area(outline: Sequence[Vec2]) -> float:
    return 0.5 * sum(
        outline[index][0] * outline[(index + 1) % len(outline)][1]
        - outline[(index + 1) % len(outline)][0] * outline[index][1]
        for index in range(len(outline))
    )


def validate_closed_shell(
    name: str,
    vertices: Sequence[Vec3],
    faces: Sequence[Face],
) -> dict[str, int]:
    if len(vertices) < 4 or len(faces) < 4:
        raise ValueError(f"Closed shell {name} is incomplete")

    used_vertices: set[int] = set()
    edge_counts: dict[tuple[int, int], int] = {}
    center = tuple(
        sum(vertex[axis] for vertex in vertices) / len(vertices)
        for axis in range(3)
    )
    signed_volume = 0.0
    for face in faces:
        if len(set(face)) != 3 or min(face) < 0 or max(face) >= len(vertices):
            raise ValueError(f"Closed shell {name} has an invalid triangle index")
        used_vertices.update(face)
        a, b, c = (vertices[index] for index in face)
        face_cross = cross(subtract(b, a), subtract(c, a))
        if not all(math.isfinite(value) for value in face_cross):
            raise ValueError(f"Closed shell {name} has a non-finite triangle")
        if dot(face_cross, face_cross) <= 1.0e-12:
            raise ValueError(f"Closed shell {name} has a degenerate triangle")
        centroid = tuple((a[axis] + b[axis] + c[axis]) / 3.0 for axis in range(3))
        if dot(face_cross, subtract(centroid, center)) <= 1.0e-9:
            raise ValueError(f"Closed shell {name} has an inward triangle")
        signed_volume += dot(a, cross(b, c)) / 6.0
        for index in range(3):
            edge = tuple(sorted((face[index], face[(index + 1) % 3])))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    if used_vertices != set(range(len(vertices))):
        raise ValueError(f"Closed shell {name} has unused vertices")
    if not edge_counts or any(count != 2 for count in edge_counts.values()):
        raise ValueError(f"Closed shell {name} is not a closed two-manifold")
    if signed_volume <= 1.0e-9:
        raise ValueError(f"Closed shell {name} has reversed winding")
    return {
        "vertices": len(vertices),
        "triangles": len(faces),
        "edges": len(edge_counts),
    }


def add_extruded_outline(
    mesh: object,
    shell_name: str,
    outline: Sequence[Vec2],
    back_z: float,
    front_z: float,
    material: str,
) -> dict[str, object]:
    if len(outline) < 3 or signed_area(outline) <= 1.0e-8:
        raise ValueError(f"Outline {shell_name} must be counter-clockwise")
    if back_z >= front_z:
        raise ValueError(f"Outline {shell_name} has invalid depth")

    vertex_count = len(outline)
    vertices: list[Vec3] = [
        (point[0], point[1], front_z) for point in outline
    ]
    vertices.extend((point[0], point[1], back_z) for point in outline)
    center_x = sum(point[0] for point in outline) / vertex_count
    center_y = sum(point[1] for point in outline) / vertex_count
    front_center = len(vertices)
    vertices.append((center_x, center_y, front_z))
    back_center = len(vertices)
    vertices.append((center_x, center_y, back_z))

    faces: list[Face] = []
    for index in range(vertex_count):
        following = (index + 1) % vertex_count
        back_index = vertex_count + index
        back_following = vertex_count + following
        faces.append((front_center, index, following))
        faces.append((back_center, back_following, back_index))
        faces.append((back_index, back_following, following))
        faces.append((back_index, following, index))

    topology = validate_closed_shell(shell_name, vertices, faces)
    for face in faces:
        mesh.triangle(material, *(vertices[index] for index in face))
    return {"name": shell_name, **topology}


def rounded_rectangle_outline(
    center_x: float,
    center_y: float,
    half_width: float,
    half_height: float,
    corner: float,
) -> tuple[Vec2, ...]:
    if not 0.0 < corner < min(half_width, half_height):
        raise ValueError("Rounded rectangle corner radius is invalid")
    return (
        (center_x - half_width + corner, center_y - half_height),
        (center_x + half_width - corner, center_y - half_height),
        (center_x + half_width, center_y - half_height + corner),
        (center_x + half_width, center_y + half_height - corner),
        (center_x + half_width - corner, center_y + half_height),
        (center_x - half_width + corner, center_y + half_height),
        (center_x - half_width, center_y + half_height - corner),
        (center_x - half_width, center_y - half_height + corner),
    )


def star_outline(
    center_x: float,
    center_y: float,
    outer_radius: float,
    inner_radius: float,
) -> tuple[Vec2, ...]:
    if not 0.0 < inner_radius < outer_radius:
        raise ValueError("Star radii are invalid")
    return tuple(
        (
            center_x
            + math.cos(math.pi * 0.5 + index * math.pi / 5.0)
            * (outer_radius if index % 2 == 0 else inner_radius),
            center_y
            + math.sin(math.pi * 0.5 + index * math.pi / 5.0)
            * (outer_radius if index % 2 == 0 else inner_radius),
        )
        for index in range(10)
    )


def build_mesh(helpers: ModuleType) -> tuple[object, list[dict[str, object]]]:
    mesh = helpers.MeshBuilder(MODEL_NAME)
    topology_reports: list[dict[str, object]] = []

    topology_reports.append(add_extruded_outline(
        mesh,
        "rounded_body",
        rounded_rectangle_outline(0.0, 0.35, 0.98, 0.43, 0.17),
        -0.60,
        0.60,
        material_key("Body"),
    ))
    topology_reports.append(add_extruded_outline(
        mesh,
        "arched_lid",
        (
            (-0.98, 0.68),
            (0.98, 0.68),
            (0.98, 1.12),
            (0.86, 1.31),
            (0.62, 1.40),
            (-0.62, 1.40),
            (-0.86, 1.31),
            (-0.98, 1.12),
        ),
        -0.60,
        0.60,
        material_key("Body"),
    ))

    topology_reports.append(add_extruded_outline(
        mesh,
        "gold_seam",
        rounded_rectangle_outline(0.0, 0.74, 1.03, 0.075, 0.035),
        -0.64,
        0.64,
        material_key("GoldTrim"),
    ))
    topology_reports.append(add_extruded_outline(
        mesh,
        "gold_lid_strap",
        rounded_rectangle_outline(0.0, 1.05, 0.095, 0.31, 0.035),
        -0.65,
        0.65,
        material_key("GoldTrim"),
    ))
    topology_reports.append(add_extruded_outline(
        mesh,
        "star_clasp",
        star_outline(0.0, 0.78, 0.29, 0.135),
        0.67,
        0.79,
        material_key("StarClasp"),
    ))

    expected_materials = tuple(material_key(name) for name in MATERIAL_ORDER)
    if tuple(mesh.primitive_indices) != expected_materials:
        raise ValueError(
            "Boss chest material/primitive order drifted: "
            f"{tuple(mesh.primitive_indices)}"
        )
    if not 80 <= mesh.triangle_count <= 240:
        raise ValueError("Boss chest is outside its low-poly triangle budget")
    if len(mesh.positions) != mesh.triangle_count * 3:
        raise ValueError("Boss chest expanded topology is invalid")
    if any(
        not indices or len(indices) % 3
        for indices in mesh.primitive_indices.values()
    ):
        raise ValueError("Boss chest primitive topology is invalid")
    return mesh, topology_reports


def validate_runtime_bounds(mesh: object) -> dict[str, list[float]]:
    minimum = [min(point[axis] for point in mesh.positions) for axis in range(3)]
    maximum = [max(point[axis] for point in mesh.positions) for axis in range(3)]
    local_size = [maximum[axis] - minimum[axis] for axis in range(3)]
    runtime_size = [value * PREFAB_SCALE for value in local_size]
    if not (
        1.20 <= runtime_size[0] <= 1.80
        and 0.80 <= runtime_size[1] <= 1.30
        and 0.75 <= runtime_size[2] <= 1.30
    ):
        raise ValueError(f"Boss chest runtime bounds are unreasonable: {runtime_size}")
    return {
        "local_min": [round(value, 6) for value in minimum],
        "local_max": [round(value, 6) for value in maximum],
        "runtime_size": [round(value, 6) for value in runtime_size],
    }


def prefab_resource() -> dict[str, object]:
    return {
        "MeshComponent": {
            "Path": f"{OUTPUT_ASSET_ROOT}/{MODEL_NAME}.hmesh",
            "meshResPath": "",
        },
        "TagComponent": {"Tag": "SurvivorBossChest"},
        "TransformComponent": {
            "ParentUuid": "",
            "Rotation": [0.0, 0.0, 0.0],
            "Scale": [PREFAB_SCALE, PREFAB_SCALE, PREFAB_SCALE],
            "Translation": [0.0, PREFAB_HEIGHT, 0.0],
        },
    }


def collect_asset_references(value: object) -> set[str]:
    references: set[str] = set()
    if isinstance(value, str) and value.startswith("Assets/"):
        references.add(value)
    elif isinstance(value, dict):
        for child in value.values():
            references.update(collect_asset_references(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            references.update(collect_asset_references(child))
    return references


def validate_payload_references(
    repo_root: Path,
    payloads: dict[Path, bytes],
) -> int:
    project_root = (repo_root / "Project").resolve()
    payload_paths = {path.resolve() for path in payloads}
    reference_count = 0
    for path, payload in payloads.items():
        if path.suffix not in {".hmesh", ".hmat", ".hprefab"}:
            continue
        resource = json.loads(payload.decode("utf-8"))
        for reference in collect_asset_references(resource):
            reference_count += 1
            reference_path = (project_root / Path(reference)).resolve()
            try:
                reference_path.relative_to(project_root)
            except ValueError as error:
                raise ValueError(f"Asset reference escapes Project: {reference}") from error
            if reference_path not in payload_paths and not reference_path.is_file():
                raise FileNotFoundError(
                    f"{path.relative_to(repo_root).as_posix()} references missing "
                    f"{reference}"
                )
    return reference_count


def validate_prefab(prefab: dict[str, object]) -> None:
    if prefab.get("TagComponent") != {"Tag": "SurvivorBossChest"}:
        raise ValueError("Boss chest prefab tag is invalid")
    transform = prefab.get("TransformComponent")
    if not isinstance(transform, dict):
        raise ValueError("Boss chest prefab requires TransformComponent")
    scale = transform.get("Scale")
    if not isinstance(scale, list) or len(scale) != 3 or min(scale) <= 0.0:
        raise ValueError("Boss chest prefab must be initially visible")


def weapon_binary_hashes(repo_root: Path) -> dict[str, str]:
    weapon_root = repo_root / "Project/Assets/Models/SurvivorWeapons"
    hashes: dict[str, str] = {}
    if not weapon_root.is_dir():
        return hashes
    for path in sorted(weapon_root.rglob("*.bin")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.setdefault(digest, path.relative_to(repo_root).as_posix())
    return hashes


def build_payloads(repo_root: Path) -> tuple[dict[Path, bytes], dict[str, object]]:
    helpers, validation = load_helpers(repo_root)
    mesh, topology_reports = build_mesh(helpers)
    validation.validate_mesh_normals(mesh)
    runtime_bounds = validate_runtime_bounds(mesh)

    mesh_resource, binary = helpers.mesh_payload(mesh)
    helpers.assert_forward_slashes(mesh_resource, "mesh:BossChest")
    validation.validate_mesh_resource(
        mesh_resource,
        binary,
        MODEL_NAME,
        MATERIAL_ORDER,
    )

    output_root = repo_root / OUTPUT_PROJECT_ROOT
    payloads: dict[Path, bytes] = {
        output_root / f"{MODEL_NAME}.hmesh": json_bytes(mesh_resource),
        output_root / f"{MODEL_NAME}.bin": binary,
    }
    material_hashes: set[str] = set()
    for local_name in MATERIAL_ORDER:
        definition = MATERIAL_DEFINITIONS[local_name]
        generated_name = material_key(local_name)
        specification = helpers.MaterialSpec(
            definition.color,
            definition.metallic,
            definition.roughness,
            definition.emissive,
            False,
            "OPAQUE",
        )
        resource = helpers.material_json(generated_name, specification)
        helpers.assert_forward_slashes(resource, f"material:{generated_name}")
        properties = resource.get("Properties", {})
        base_color = properties.get("pbrMetallicRoughness", {}).get(
            "baseColorFactor"
        )
        if (
            properties.get("alphaMode") != "OPAQUE"
            or properties.get("doubleSided") is not False
            or not isinstance(base_color, list)
            or len(base_color) != 4
            or base_color[3] != 1.0
        ):
            raise ValueError(f"Boss chest material is not opaque: {generated_name}")
        material_payload = json_bytes(resource)
        material_digest = hashlib.sha256(material_payload).hexdigest()
        if material_digest in material_hashes:
            raise ValueError("Boss chest materials must have unique payload hashes")
        material_hashes.add(material_digest)
        payloads[
            output_root / "Materials" / f"{generated_name}.hmat"
        ] = material_payload

    prefab = prefab_resource()
    validate_prefab(prefab)
    helpers.assert_forward_slashes(prefab, "prefab:SurvivorBossChest")
    payloads[repo_root / PREFAB_PROJECT_PATH] = json_bytes(prefab)
    reference_count = validate_payload_references(repo_root, payloads)

    binary_digest = hashlib.sha256(binary).hexdigest()
    existing_weapon_hashes = weapon_binary_hashes(repo_root)
    if binary_digest in existing_weapon_hashes:
        raise ValueError(
            "Boss chest duplicates an existing weapon core binary: "
            f"{existing_weapon_hashes[binary_digest]}"
        )

    payload_hashes = [hashlib.sha256(payload).hexdigest() for payload in payloads.values()]
    if len(set(payload_hashes)) != len(payload_hashes):
        raise ValueError("Boss chest generated payload hashes must be unique")
    aggregate = hashlib.sha256()
    for path, payload in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
        aggregate.update(path.relative_to(repo_root).as_posix().encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(payload)

    return payloads, {
        "aggregate_sha256": aggregate.hexdigest(),
        "binary_sha256": binary_digest,
        "generated_file_count": len(payloads),
        "material_count": len(MATERIAL_ORDER),
        "opaque_material_count": len(MATERIAL_ORDER),
        "prefab": PREFAB_PROJECT_PATH.relative_to("Project").as_posix(),
        "primitive_count": len(mesh.primitive_indices),
        "reference_count": reference_count,
        "runtime_bounds": runtime_bounds,
        "shell_count": len(topology_reports),
        "topology": topology_reports,
        "triangle_count": mesh.triangle_count,
        "unique_payload_hash_count": len(set(payload_hashes)),
        "vertex_count": len(mesh.positions),
        "weapon_binary_hashes_compared": len(existing_weapon_hashes),
    }


def validate_output_set(payloads: dict[Path, bytes], output_root: Path) -> None:
    expected = {
        path.resolve()
        for path in payloads
        if output_root.resolve() in path.resolve().parents
    }
    if not output_root.exists():
        return
    unexpected: list[Path] = []
    for path in output_root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"Refusing generated output symlink: {path}")
        if path.is_file() and path.resolve() not in expected:
            unexpected.append(path)
    if unexpected:
        raise RuntimeError(
            "Unexpected files in owned SurvivorBossChest output: "
            + str([path.relative_to(output_root).as_posix() for path in unexpected])
        )


def write_payloads(payloads: dict[Path, bytes], output_root: Path) -> None:
    validate_output_set(payloads, output_root)
    for path, payload in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        if temporary.exists():
            raise RuntimeError(f"Refusing stale generated temporary file: {temporary}")
        try:
            temporary.write_bytes(payload)
            os.replace(str(temporary), str(path))
        finally:
            if temporary.exists():
                temporary.unlink()


def check_payloads(payloads: dict[Path, bytes], output_root: Path) -> None:
    validate_output_set(payloads, output_root)
    missing = [path for path in payloads if not path.is_file()]
    changed = [
        path
        for path, payload in payloads.items()
        if path.is_file() and path.read_bytes() != payload
    ]
    if missing or changed:
        def names(paths: Iterable[Path]) -> list[str]:
            return [path.as_posix() for path in sorted(paths)]

        raise RuntimeError(
            f"Generated boss chest is stale; missing={names(missing)} "
            f"changed={names(changed)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the exact generated boss chest assets without writing files",
    )
    arguments = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    if not (repo_root / "Project/Project.heproject").is_file():
        raise RuntimeError(f"Not an HEngineDev repository root: {repo_root}")
    output_root = (repo_root / OUTPUT_PROJECT_ROOT).resolve()
    payloads, report = build_payloads(repo_root)
    if arguments.check:
        check_payloads(payloads, output_root)
        report["mode"] = "check"
    else:
        write_payloads(payloads, output_root)
        check_payloads(payloads, output_root)
        report["mode"] = "generate"
    report["result"] = "PASS"
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
