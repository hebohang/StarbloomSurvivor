"""Generate eight deterministic native low-poly Survivor weapon cores."""

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
from typing import Callable, Iterable


OUTPUT_PROJECT_ROOT = Path("Project/Assets/Models/SurvivorWeapons/ExpansionGenerated")
OUTPUT_ASSET_ROOT = "Assets/Models/SurvivorWeapons/ExpansionGenerated"
PREFAB_PROJECT_ROOT = Path("Project/Assets/Prefabs")
CORE_NAMES = (
    "HoneyNeedleCore",
    "SporecapCore",
    "PhantomBellCore",
    "CoralAnchorCore",
    "PrismCore",
    "AcornCore",
    "FrostOrbCore",
    "GravityYoyoCore",
)


@dataclass(frozen=True)
class MaterialDefinition:
    color: tuple[float, float, float, float]
    metallic: float
    roughness: float
    emissive: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class CoreDefinition:
    name: str
    materials: tuple[tuple[str, MaterialDefinition], ...]
    build: Callable[[ModuleType, object], None]


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
        "he_survivor_expansion_mesh_helpers",
    )
    validation = load_module(
        repo_root / "Tools/VFX/generate_survivor_projectile_meshes.py",
        "he_survivor_expansion_mesh_validation",
    )
    helpers.ASSET_MODEL_ROOT = OUTPUT_ASSET_ROOT
    validation.OUTPUT_ASSET_ROOT = OUTPUT_ASSET_ROOT
    return helpers, validation


def material_key(model_name: str, material_name: str) -> str:
    return f"{model_name}_{material_name}"


def add_bipyramid_x(
    mesh: object,
    center: tuple[float, float, float],
    length: float,
    radius: float,
    material: str,
    segments: int = 6,
) -> None:
    left = (center[0] - length * 0.5, center[1], center[2])
    right = (center[0] + length * 0.5, center[1], center[2])
    ring = tuple(
        (
            center[0],
            center[1] + math.cos(math.tau * index / segments) * radius,
            center[2] + math.sin(math.tau * index / segments) * radius,
        )
        for index in range(segments)
    )
    for index, current in enumerate(ring):
        following = ring[(index + 1) % len(ring)]
        mesh.triangle(material, right, current, following)
        mesh.triangle(material, left, following, current)


def add_frustum_y(
    mesh: object,
    center: tuple[float, float, float],
    bottom_y: float,
    top_y: float,
    bottom_radius: float,
    top_radius: float,
    material: str,
    segments: int = 8,
) -> None:
    bottom_center = (center[0], bottom_y, center[2])
    top_center = (center[0], top_y, center[2])
    for index in range(segments):
        angle0 = math.tau * index / segments
        angle1 = math.tau * (index + 1) / segments
        bottom0 = (
            center[0] + math.cos(angle0) * bottom_radius,
            bottom_y,
            center[2] + math.sin(angle0) * bottom_radius,
        )
        bottom1 = (
            center[0] + math.cos(angle1) * bottom_radius,
            bottom_y,
            center[2] + math.sin(angle1) * bottom_radius,
        )
        top0 = (
            center[0] + math.cos(angle0) * top_radius,
            top_y,
            center[2] + math.sin(angle0) * top_radius,
        )
        top1 = (
            center[0] + math.cos(angle1) * top_radius,
            top_y,
            center[2] + math.sin(angle1) * top_radius,
        )
        mesh.quad(material, bottom0, top0, top1, bottom1)
        mesh.triangle(material, top_center, top1, top0)
        mesh.triangle(material, bottom_center, bottom0, bottom1)


def build_honey_needle(helpers: ModuleType, mesh: object) -> None:
    gold = material_key(mesh.name, "Gold")
    dark = material_key(mesh.name, "Dark")
    spark = material_key(mesh.name, "Spark")
    add_bipyramid_x(mesh, (0.0, 0.0, 0.0), 1.90, 0.22, gold, 6)
    add_bipyramid_x(mesh, (-0.08, 0.0, 0.0), 0.42, 0.31, dark, 6)
    helpers.add_octahedron(mesh, (-0.16, 0.34, 0.0), 0.22, 0.42, spark)
    helpers.add_octahedron(mesh, (-0.16, -0.34, 0.0), 0.22, 0.42, spark)


def build_sporecap(helpers: ModuleType, mesh: object) -> None:
    cap = material_key(mesh.name, "Cap")
    stem = material_key(mesh.name, "Stem")
    spots = material_key(mesh.name, "Spots")
    helpers.add_ellipsoid(mesh, (0.0, 0.30, 0.0), (0.72, 0.38, 0.72), cap, 4, 9)
    helpers.add_cylinder(mesh, (0.0, -0.62, 0.0), 0.24, 0.80, stem, 8)
    for center, radius in (
        ((-0.28, 0.62, -0.14), 0.13),
        ((0.26, 0.61, 0.12), 0.11),
        ((0.07, 0.66, -0.32), 0.09),
    ):
        helpers.add_octahedron(mesh, center, radius, radius * 1.25, spots)


def build_phantom_bell(helpers: ModuleType, mesh: object) -> None:
    shell = material_key(mesh.name, "Shell")
    ivory = material_key(mesh.name, "Ivory")
    glow = material_key(mesh.name, "Glow")
    add_frustum_y(mesh, (0.0, 0.0, 0.0), -0.48, 0.55, 0.64, 0.22, shell, 9)
    helpers.add_cylinder(mesh, (0.0, -0.58, 0.0), 0.69, 0.17, ivory, 9)
    helpers.add_octahedron(mesh, (0.0, 0.72, 0.0), 0.20, 0.34, glow)
    helpers.add_ellipsoid(mesh, (0.0, -0.68, 0.0), (0.18, 0.24, 0.18), glow, 3, 7)


def build_coral_anchor(helpers: ModuleType, mesh: object) -> None:
    coral = material_key(mesh.name, "Coral")
    tide = material_key(mesh.name, "Tide")
    gold = material_key(mesh.name, "Gold")
    helpers.add_box(mesh, (0.0, 0.05, 0.0), (0.18, 1.45, 0.20), coral)
    helpers.add_box(mesh, (0.0, 0.43, 0.0), (1.05, 0.16, 0.22), tide)
    helpers.add_box(mesh, (0.0, -0.53, 0.0), (1.10, 0.17, 0.25), coral)
    helpers.add_cone(mesh, (-0.50, -0.65, 0.0), 0.25, 0.58, coral, 6)
    helpers.add_cone(mesh, (0.50, -0.65, 0.0), 0.25, 0.58, coral, 6)
    helpers.add_octahedron(mesh, (0.0, 0.84, 0.0), 0.27, 0.35, gold)
    helpers.add_box(mesh, (0.33, 0.18, 0.0), (0.12, 0.50, 0.16), tide)


def build_prism(helpers: ModuleType, mesh: object) -> None:
    cyan = material_key(mesh.name, "Cyan")
    violet = material_key(mesh.name, "Violet")
    star = material_key(mesh.name, "Star")
    top = (0.0, 0.82, 0.0)
    bottom = (0.0, -0.82, 0.0)
    ring = ((0.58, 0.0, 0.0), (0.0, 0.0, 0.58),
            (-0.58, 0.0, 0.0), (0.0, 0.0, -0.58))
    for index, current in enumerate(ring):
        following = ring[(index + 1) % len(ring)]
        material = cyan if index % 2 == 0 else violet
        mesh.triangle(material, top, following, current)
        mesh.triangle(material, bottom, current, following)
    helpers.add_octahedron(mesh, (0.0, 0.0, 0.0), 0.20, 0.58, star)


def build_acorn(helpers: ModuleType, mesh: object) -> None:
    nut = material_key(mesh.name, "Nut")
    cap = material_key(mesh.name, "Cap")
    stem = material_key(mesh.name, "Stem")
    helpers.add_ellipsoid(mesh, (0.0, -0.12, 0.0), (0.52, 0.65, 0.52), nut, 5, 8)
    helpers.add_ellipsoid(mesh, (0.0, 0.38, 0.0), (0.59, 0.24, 0.59), cap, 3, 8)
    helpers.add_cylinder(mesh, (0.0, 0.53, 0.0), 0.10, 0.38, stem, 6)


def build_frost_orb(helpers: ModuleType, mesh: object) -> None:
    ice = material_key(mesh.name, "Ice")
    snow = material_key(mesh.name, "Snow")
    glint = material_key(mesh.name, "Glint")
    helpers.add_ellipsoid(mesh, (0.0, 0.0, 0.0), (0.62, 0.62, 0.62), ice, 5, 9)
    helpers.add_box(mesh, (0.0, 0.0, 0.0), (1.48, 0.10, 0.10), snow)
    helpers.add_box(mesh, (0.0, 0.0, 0.0), (0.10, 1.48, 0.10), snow)
    helpers.add_box(mesh, (0.0, 0.0, 0.0), (0.10, 0.10, 1.48), snow)
    helpers.add_octahedron(mesh, (0.0, 0.0, 0.0), 0.27, 0.62, glint)


def build_gravity_yoyo(helpers: ModuleType, mesh: object) -> None:
    violet = material_key(mesh.name, "Violet")
    gold = material_key(mesh.name, "Gold")
    glow = material_key(mesh.name, "Glow")
    helpers.add_cylinder(mesh, (0.0, -0.30, 0.0), 0.69, 0.22, violet, 10)
    helpers.add_cylinder(mesh, (0.0, 0.08, 0.0), 0.69, 0.22, violet, 10)
    helpers.add_cylinder(mesh, (0.0, -0.10, 0.0), 0.31, 0.42, gold, 8)
    helpers.add_octahedron(mesh, (0.0, 0.0, 0.0), 0.20, 0.38, glow)


def material(
    color: tuple[float, float, float],
    metallic: float,
    roughness: float,
    emissive: tuple[float, float, float] | None = None,
) -> MaterialDefinition:
    emissive_rgba = (*emissive, 1.0) if emissive is not None else None
    return MaterialDefinition((*color, 1.0), metallic, roughness, emissive_rgba)


CORE_DEFINITIONS = (
    CoreDefinition("HoneyNeedleCore", (
        ("Gold", material((1.00, 0.67, 0.16), 0.10, 0.55, (0.10, 0.05, 0.00))),
        ("Dark", material((0.09, 0.07, 0.12), 0.02, 0.76)),
        ("Spark", material((1.00, 0.91, 0.42), 0.04, 0.42, (0.16, 0.10, 0.01))),
    ), build_honey_needle),
    CoreDefinition("SporecapCore", (
        ("Cap", material((0.63, 0.27, 0.74), 0.00, 0.80)),
        ("Stem", material((0.46, 0.78, 0.35), 0.00, 0.88)),
        ("Spots", material((0.88, 0.95, 0.56), 0.00, 0.70, (0.05, 0.08, 0.01))),
    ), build_sporecap),
    CoreDefinition("PhantomBellCore", (
        ("Shell", material((0.23, 0.52, 0.90), 0.06, 0.55, (0.01, 0.03, 0.08))),
        ("Ivory", material((0.94, 0.97, 1.00), 0.02, 0.62)),
        ("Glow", material((0.44, 0.91, 1.00), 0.04, 0.36, (0.08, 0.22, 0.30))),
    ), build_phantom_bell),
    CoreDefinition("CoralAnchorCore", (
        ("Coral", material((0.96, 0.31, 0.28), 0.02, 0.72)),
        ("Tide", material((0.22, 0.76, 0.78), 0.02, 0.60, (0.01, 0.08, 0.09))),
        ("Gold", material((1.00, 0.70, 0.22), 0.12, 0.50)),
    ), build_coral_anchor),
    CoreDefinition("PrismCore", (
        ("Cyan", material((0.31, 0.86, 0.82), 0.08, 0.42, (0.04, 0.17, 0.17))),
        ("Violet", material((0.55, 0.36, 0.88), 0.08, 0.46, (0.09, 0.04, 0.18))),
        ("Star", material((1.00, 0.80, 0.25), 0.10, 0.38, (0.18, 0.10, 0.01))),
    ), build_prism),
    CoreDefinition("AcornCore", (
        ("Nut", material((0.48, 0.23, 0.11), 0.00, 0.88)),
        ("Cap", material((0.88, 0.55, 0.16), 0.04, 0.68)),
        ("Stem", material((0.23, 0.12, 0.08), 0.00, 0.92)),
    ), build_acorn),
    CoreDefinition("FrostOrbCore", (
        ("Ice", material((0.36, 0.76, 0.96), 0.04, 0.40, (0.03, 0.11, 0.18))),
        ("Snow", material((0.94, 0.99, 1.00), 0.00, 0.58)),
        ("Glint", material((0.62, 0.94, 1.00), 0.06, 0.32, (0.10, 0.28, 0.36))),
    ), build_frost_orb),
    CoreDefinition("GravityYoyoCore", (
        ("Violet", material((0.37, 0.20, 0.70), 0.08, 0.52)),
        ("Gold", material((1.00, 0.68, 0.18), 0.12, 0.48)),
        ("Glow", material((0.88, 0.48, 0.96), 0.04, 0.35, (0.16, 0.05, 0.22))),
    ), build_gravity_yoyo),
)


def projected_core_size(positions: Iterable[tuple[float, float, float]]) -> dict[str, float]:
    # Orthographic proxy for the fixed angled gameplay camera.  This catches a
    # core becoming sub-pixel relative to its peers without claiming a hardware
    # dependent screen-space pixel measurement.
    right = (0.70710678, 0.0, -0.70710678)
    up = (0.40824829, 0.81649658, 0.40824829)
    values = tuple(positions)
    horizontal = [sum(point[index] * right[index] for index in range(3)) for point in values]
    vertical = [sum(point[index] * up[index] for index in range(3)) for point in values]
    width = max(horizontal) - min(horizontal)
    height = max(vertical) - min(vertical)
    diameter = max(width, height)
    if not 0.80 <= diameter <= 2.40:
        raise ValueError(f"Projected core diameter is outside the readable band: {diameter}")
    if min(width, height) < 0.36 or width * height < 0.55:
        raise ValueError(f"Projected core silhouette is too thin: {width}x{height}")
    return {
        "projected_width": round(width, 6),
        "projected_height": round(height, 6),
        "relative_diameter": round(diameter, 6),
    }


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def prefab_resource(name: str) -> dict[str, object]:
    return {
        "MeshComponent": {
            "Path": f"{OUTPUT_ASSET_ROOT}/{name}.hmesh",
            "meshResPath": "",
        },
        "TagComponent": {"Tag": "ProjectileVisual"},
        "TransformComponent": {
            "ParentUuid": "",
            "Rotation": [0.0, 0.0, 0.0],
            "Scale": [0.0, 0.0, 0.0],
            "Translation": [0.0, -100.0, 0.0],
        },
    }


def collect_asset_references(value: object) -> set[str]:
    references: set[str] = set()
    if isinstance(value, str):
        if value.startswith("Assets/"):
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
) -> None:
    project_root = (repo_root / "Project").resolve()
    payload_paths = {path.resolve() for path in payloads}
    for path, payload in payloads.items():
        if path.suffix not in {".hmesh", ".hmat", ".hprefab"}:
            continue
        resource = json.loads(payload.decode("utf-8"))
        for reference in collect_asset_references(resource):
            reference_path = (project_root / Path(reference)).resolve()
            if reference_path not in payload_paths and not reference_path.is_file():
                raise FileNotFoundError(
                    f"{path.relative_to(repo_root).as_posix()} references missing {reference}"
                )


def build_payloads(repo_root: Path) -> tuple[dict[Path, bytes], dict[str, object]]:
    helpers, validation = load_helpers(repo_root)
    output_root = repo_root / OUTPUT_PROJECT_ROOT
    prefab_root = repo_root / PREFAB_PROJECT_ROOT
    payloads: dict[Path, bytes] = {}
    reports: list[dict[str, object]] = []
    binary_hashes: set[str] = set()
    model_hashes: set[str] = set()

    if tuple(definition.name for definition in CORE_DEFINITIONS) != CORE_NAMES:
        raise ValueError("Core definitions do not match the requested stable names")

    for definition in CORE_DEFINITIONS:
        mesh = helpers.MeshBuilder(definition.name)
        definition.build(helpers, mesh)
        expected_material_order = tuple(
            material_key(definition.name, local_name)
            for local_name, _ in definition.materials
        )
        if tuple(mesh.primitive_indices) != expected_material_order:
            raise ValueError(
                f"Material/primitive order drifted for {definition.name}: "
                f"{tuple(mesh.primitive_indices)}"
            )
        if not 12 <= mesh.triangle_count <= 400:
            raise ValueError(f"Low-poly triangle budget failed for {definition.name}")
        if len(mesh.positions) != mesh.triangle_count * 3:
            raise ValueError(f"Expanded topology is invalid for {definition.name}")
        if any(len(indices) == 0 or len(indices) % 3 for indices in mesh.primitive_indices.values()):
            raise ValueError(f"Primitive topology is invalid for {definition.name}")
        validation.validate_mesh_normals(mesh)
        screen_size = projected_core_size(mesh.positions)

        mesh_resource, binary = helpers.mesh_payload(mesh)
        helpers.assert_forward_slashes(mesh_resource, f"mesh:{definition.name}")
        local_material_order = tuple(local_name for local_name, _ in definition.materials)
        validation.validate_mesh_resource(
            mesh_resource,
            binary,
            definition.name,
            local_material_order,
        )
        binary_digest = hashlib.sha256(binary).hexdigest()
        if binary_digest in binary_hashes:
            raise ValueError(f"Core geometry is duplicated: {definition.name}")
        binary_hashes.add(binary_digest)
        payloads[output_root / f"{definition.name}.hmesh"] = json_bytes(mesh_resource)
        payloads[output_root / f"{definition.name}.bin"] = binary

        model_digest = hashlib.sha256(binary)
        for local_name, material_definition in definition.materials:
            generated_name = material_key(definition.name, local_name)
            specification = helpers.MaterialSpec(
                material_definition.color,
                material_definition.metallic,
                material_definition.roughness,
                material_definition.emissive,
                False,
                "OPAQUE",
            )
            material_resource = helpers.material_json(generated_name, specification)
            helpers.assert_forward_slashes(material_resource, f"material:{generated_name}")
            properties = material_resource["Properties"]
            base_color = properties["pbrMetallicRoughness"]["baseColorFactor"]
            if properties["alphaMode"] != "OPAQUE" or base_color[3] != 1.0:
                raise ValueError(f"Core material is not opaque: {generated_name}")
            if properties["doubleSided"]:
                raise ValueError(f"Closed core material must be single-sided: {generated_name}")
            material_payload = json_bytes(material_resource)
            model_digest.update(material_payload)
            payloads[
                output_root / "Materials" / f"{generated_name}.hmat"
            ] = material_payload

        model_fingerprint = model_digest.hexdigest()
        if model_fingerprint in model_hashes:
            raise ValueError(f"Core resource is duplicated: {definition.name}")
        model_hashes.add(model_fingerprint)
        prefab_path = prefab_root / f"Survivor{definition.name}.hprefab"
        prefab = prefab_resource(definition.name)
        helpers.assert_forward_slashes(prefab, f"prefab:{definition.name}")
        payloads[prefab_path] = json_bytes(prefab)
        reports.append({
            "name": definition.name,
            "prefab": prefab_path.relative_to(repo_root / "Project").as_posix(),
            "triangles": mesh.triangle_count,
            "primitives": len(mesh.primitive_indices),
            "materials": list(local_material_order),
            "binary_sha256": binary_digest,
            **screen_size,
        })

    validate_payload_references(repo_root, payloads)
    aggregate = hashlib.sha256()
    for path, payload in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
        aggregate.update(path.relative_to(repo_root).as_posix().encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(payload)
    return payloads, {
        "model_count": len(reports),
        "prefab_count": len(reports),
        "generated_file_count": len(payloads),
        "triangle_count": sum(int(report["triangles"]) for report in reports),
        "aggregate_sha256": aggregate.hexdigest(),
        "models": reports,
    }


def expected_model_files(payloads: dict[Path, bytes], output_root: Path) -> set[Path]:
    return {
        path.resolve() for path in payloads
        if output_root in path.resolve().parents
    }


def validate_output_set(payloads: dict[Path, bytes], output_root: Path) -> None:
    expected = expected_model_files(payloads, output_root)
    if not output_root.exists():
        return
    unexpected = []
    for path in output_root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"Refusing generated output symlink: {path}")
        if path.is_file() and path.resolve() not in expected:
            unexpected.append(path)
    if unexpected:
        raise RuntimeError(
            "Unexpected files in owned ExpansionGenerated output: "
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
        path for path, payload in payloads.items()
        if path.is_file() and path.read_bytes() != payload
    ]
    if missing or changed:
        def names(paths: Iterable[Path]) -> list[str]:
            return [path.as_posix() for path in sorted(paths)]
        raise RuntimeError(
            f"Generated expansion cores are stale; missing={names(missing)} "
            f"changed={names(changed)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the exact generated core assets without writing files",
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
