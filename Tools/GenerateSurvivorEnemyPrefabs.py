"""Generate the 12 enemy and 5 Boss prefabs required by SurvivorCatalogWorld."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


EXPECTED_ENEMY_COUNT = 12
EXPECTED_BOSS_COUNT = 5
OUTPUT_ASSET_ROOT = "Assets/Prefabs/SurvivorEnemies"


def project_root_from_script():
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    if project_root.name != "Project":
        raise RuntimeError("Generator must live under Project/Tools")
    required = (
        project_root / "Assets",
        project_root / "Config" / "BaseEngine.json",
        project_root / "Scripts" / "SurvivorCatalogWorld.py",
    )
    missing = [path.as_posix() for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Missing generator prerequisite(s):\n  " + "\n  ".join(missing))
    return project_root


def load_catalog(project_root):
    scripts_path = str(project_root / "Scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    import SurvivorCatalogWorld as world

    enemies = list(world.ENEMIES)
    bosses = list(world.BOSSES)
    if len(enemies) != EXPECTED_ENEMY_COUNT:
        raise ValueError(
            "Catalog contains %d enemies; expected %d"
            % (len(enemies), EXPECTED_ENEMY_COUNT)
        )
    if len(bosses) != EXPECTED_BOSS_COUNT:
        raise ValueError(
            "Catalog contains %d Bosses; expected %d"
            % (len(bosses), EXPECTED_BOSS_COUNT)
        )
    return enemies, bosses


def path_is_relative_to(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def asset_file(project_root, asset_path):
    if not isinstance(asset_path, str) or not asset_path.startswith("Assets/"):
        raise ValueError("Expected an Assets-relative path, got: " + repr(asset_path))
    if "\\" in asset_path:
        raise ValueError("Asset path contains a backslash: " + asset_path)
    candidate = (project_root / Path(asset_path)).resolve()
    assets_root = (project_root / "Assets").resolve()
    if not path_is_relative_to(candidate, assets_root):
        raise ValueError("Asset path escapes Project/Assets: " + asset_path)
    return candidate


def assert_forward_slashes(value, location="root"):
    if isinstance(value, str):
        if "\\" in value:
            raise ValueError("Backslash at %s: %s" % (location, value))
    elif isinstance(value, dict):
        for key, child in value.items():
            assert_forward_slashes(child, "%s.%s" % (location, key))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_forward_slashes(child, "%s[%d]" % (location, index))


def collect_asset_references(value):
    references = set()
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if normalized.startswith("Assets/"):
            references.add(normalized)
    elif isinstance(value, dict):
        for child in value.values():
            references.update(collect_asset_references(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            references.update(collect_asset_references(child))
    return references


def load_json_resource(project_root, asset_path):
    resource_path = asset_file(project_root, asset_path)
    if not resource_path.is_file():
        raise FileNotFoundError("Missing Catalog resource: " + asset_path)
    resource = json.loads(resource_path.read_text(encoding="utf-8"))
    return resource


def validate_resource_references(project_root, resource, location):
    missing = []
    for reference in sorted(collect_asset_references(resource)):
        if not asset_file(project_root, reference).is_file():
            missing.append(reference)
    if missing:
        raise FileNotFoundError(
            "%s contains missing reference(s):\n  %s"
            % (location, "\n  ".join(missing))
        )


def first_valid_controller_clip(project_root, controller_path):
    controller = load_json_resource(project_root, controller_path)
    validate_resource_references(project_root, controller, controller_path)
    missing_candidates = []
    for node in controller.get("nodes", []):
        if node.get("type") != "State":
            continue
        clip_path = node.get("clipPath")
        if not isinstance(clip_path, str) or not clip_path:
            continue
        clip_file = asset_file(project_root, clip_path)
        if clip_file.is_file():
            return clip_path
        missing_candidates.append(clip_path)
    suffix = ""
    if missing_candidates:
        suffix = " Missing candidates: " + ", ".join(missing_candidates)
    raise ValueError(
        "Controller has no valid State clip: %s.%s" % (controller_path, suffix)
    )


def prefab_for_entry(project_root, entry):
    required_fields = ("id", "prefab", "mesh", "controller", "scale")
    missing_fields = [field for field in required_fields if field not in entry]
    if missing_fields:
        raise ValueError(
            "Catalog entry is missing fields %s: %s"
            % (missing_fields, entry.get("id"))
        )
    entry_id = entry["id"]
    expected_prefab_path = "%s/%s.hprefab" % (OUTPUT_ASSET_ROOT, entry_id)
    if entry["prefab"] != expected_prefab_path:
        raise ValueError(
            "%s prefab path mismatch: expected %s, got %s"
            % (entry_id, expected_prefab_path, entry["prefab"])
        )
    mesh = load_json_resource(project_root, entry["mesh"])
    validate_resource_references(project_root, mesh, entry["mesh"])
    clip_path = first_valid_controller_clip(project_root, entry["controller"])
    scale = float(entry["scale"])
    if not 0.0001 <= scale <= 1.0:
        raise ValueError("Invalid prefab scale for %s: %s" % (entry_id, scale))

    prefab = {
        "AnimatorComponent": {
            "animResPath": clip_path,
            "bEnableRootMotion": False,
            "bLockRootMotionXZ": True,
            "bLoop": True,
            "bPlay": True,
            "controllerPath": entry["controller"],
            "currentClipIndex": 0,
            "playSpeed": 1.0,
        },
        "MeshComponent": {
            "Path": entry["mesh"],
            "meshResPath": "",
        },
        "TagComponent": {
            "Tag": "SurvivorMonster",
        },
        "TransformComponent": {
            "ParentUuid": "",
            "Rotation": [0.0, 0.0, 0.0],
            "Scale": [scale, scale, scale],
            "Translation": [0.0, 0.08, 0.0],
        },
    }
    assert_forward_slashes(prefab, "prefab:" + entry_id)
    validate_resource_references(project_root, prefab, "prefab:" + entry_id)
    return prefab


def json_payload(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_payloads(project_root):
    enemies, bosses = load_catalog(project_root)
    entries = enemies + bosses
    ids = [entry["id"] for entry in entries]
    prefab_paths = [entry["prefab"] for entry in entries]
    if len(ids) != EXPECTED_ENEMY_COUNT + EXPECTED_BOSS_COUNT:
        raise ValueError("Unexpected combined enemy/Boss count")
    if len(set(ids)) != len(ids):
        raise ValueError("Enemy and Boss IDs must be unique")
    if len(set(prefab_paths)) != len(prefab_paths):
        raise ValueError("Enemy and Boss prefab paths must be unique")

    payloads = {}
    entry_metadata = []
    payload_hashes = set()
    for entry in entries:
        prefab = prefab_for_entry(project_root, entry)
        payload = json_payload(prefab)
        output_path = project_root / entry["prefab"]
        digest = hashlib.sha256(payload).hexdigest()
        if digest in payload_hashes:
            raise ValueError(
                "Behavior-specific prefabs generated identical bytes: " + entry["id"]
            )
        payload_hashes.add(digest)
        payloads[output_path] = payload
        entry_metadata.append({
            "id": entry["id"],
            "boss": bool(entry.get("boss", False)),
            "path": entry["prefab"],
            "mesh": entry["mesh"],
            "controller": entry["controller"],
            "clip": prefab["AnimatorComponent"]["animResPath"],
            "scale": float(entry["scale"]),
            "sha256": digest,
        })

    aggregate = hashlib.sha256()
    for output_path, payload in sorted(
            payloads.items(), key=lambda item: item[0].as_posix()):
        aggregate.update(output_path.relative_to(project_root).as_posix().encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(payload)
    return payloads, entry_metadata, aggregate.hexdigest()


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(str(temporary), str(path))


def verify_payload(path, expected_payload, project_root):
    relative_path = path.relative_to(project_root).as_posix()
    if not path.is_file():
        return "missing: " + relative_path
    actual_payload = path.read_bytes()
    if actual_payload != expected_payload:
        return "different: " + relative_path
    prefab = json.loads(actual_payload.decode("utf-8"))
    assert_forward_slashes(prefab, relative_path)
    if prefab.get("TagComponent", {}).get("Tag") != "SurvivorMonster":
        return "invalid TagComponent: " + relative_path
    validate_resource_references(project_root, prefab, relative_path)
    return None


def check_generated(project_root, payloads):
    mismatches = []
    for output_path, expected_payload in sorted(
            payloads.items(), key=lambda item: item[0].as_posix()):
        mismatch = verify_payload(output_path, expected_payload, project_root)
        if mismatch:
            mismatches.append(mismatch)

    output_root = project_root / OUTPUT_ASSET_ROOT
    expected_files = set(path.resolve() for path in payloads)
    if output_root.is_dir():
        extras = sorted(
            path for path in output_root.glob("*.hprefab")
            if path.resolve() not in expected_files
        )
        mismatches.extend(
            "unexpected: " + path.relative_to(project_root).as_posix()
            for path in extras
        )
    if mismatches:
        raise RuntimeError(
            "Generated enemy prefab verification failed:\n  "
            + "\n  ".join(mismatches)
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild every prefab in memory and verify exact generated files",
    )
    arguments = parser.parse_args()

    project_root = project_root_from_script()
    payloads, entries, aggregate_sha256 = build_payloads(project_root)
    if arguments.check:
        check_generated(project_root, payloads)
        mode = "check"
    else:
        for output_path, payload in sorted(
                payloads.items(), key=lambda item: item[0].as_posix()):
            atomic_write(output_path, payload)
        check_generated(project_root, payloads)
        mode = "generate"

    print(json.dumps({
        "mode": mode,
        "result": "PASS",
        "enemy_count": EXPECTED_ENEMY_COUNT,
        "boss_count": EXPECTED_BOSS_COUNT,
        "generated_file_count": len(payloads),
        "aggregate_sha256": aggregate_sha256,
        "entries": entries,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
