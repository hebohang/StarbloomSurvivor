"""Export existing Survivor content for the C# Web host; no gameplay translation."""
import ast
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

import argparse
import os
parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--catalog-only', action='store_true')
parser.add_argument('--engine', default=os.environ.get('HE_ENGINE_ROOT', ''))
args = parser.parse_args()
PROJECT = Path(__file__).resolve().parents[1]
ROOT = Path(args.engine).resolve() if args.engine else PROJECT.parent
if not (ROOT / 'Tools/Build/SharedContent.py').is_file():
    raise RuntimeError('Set --engine or HE_ENGINE_ROOT to the HEngine installation.')
OUTPUT = Path(args.output).resolve()
sys.path.insert(0, str(PROJECT / "Scripts"))
import SurvivorCatalog as catalog
import SurvivorContent as content
import SurvivorMetaProgression as meta
import SurvivorProfile as profile
import SurvivorRegionObjectives as regions
from SurvivorRuntimeAssets import asset_path
sys.path.insert(0, str(PROJECT / "Tools"))
import GenerateVerdantRift as terrain
sys.path.insert(0, str(ROOT / "Tools/Build"))
from SharedContent import validate as validate_shared_content
from PortableContent import export_assets, copy_project_files, copy_licenses


def main():
    shared_content = validate_shared_content(PROJECT)
    catalog.validate_catalog()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = {key.lower(): getattr(catalog, key) for key in (
        "CHARACTERS", "WEAPONS", "TOMES", "TRINKETS", "EVOLUTIONS", "ENEMIES", "BOSSES",
        "WAVES", "DIFFICULTIES", "CHALLENGES", "QUESTS", "PRODUCTS", "POWER_UPS", "BOSS_EVENTS")}
    data.update(characterDefinitions=content.CHARACTER_DEFS,
                defaultProfile=profile.default_profile(), metaPowerUps=meta.META_POWER_UP_RULES,
                terrainPlates=[asdict(p) for p in terrain.TERRAIN_PLATES], terrainRamps=[asdict(p) for p in terrain.RAMP_SPECS],
                regions=regions._plain(regions.REGION_CONFIG), objective=regions._plain(regions.OBJECTIVE_CONFIG),
                encounterTiers=regions._plain(regions.ENCOUNTER_TIERS), domainPowers=regions._plain(regions.DOMAIN_POWER_CONFIG),
                globalThreatBands=regions._plain(regions.GLOBAL_THREAT_BANDS), encounterDifficulty=regions._plain(regions.DIFFICULTY_COUNT_MULTIPLIERS))
    shared_ui = json.loads((PROJECT / "Config/SharedUI.json").read_text(encoding="utf-8"))
    data["sharedUi"] = shared_ui["documents"]
    data["scenePath"] = shared_content["scenePath"]
    # Reuse the original desktop labels without importing engine-bound scripts.
    def literal(filename, variable):
        tree = ast.parse((PROJECT / "Scripts" / filename).read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in node.targets):
                return ast.literal_eval(node.value)
        raise ValueError(f"Missing UI localization table: {filename}:{variable}")
    strings = literal("SurvivorGame.py", "SURVIVOR_TEXT")
    bindings = literal("SurvivorPresentation.py", "static_text")
    data["nativeUiText"] = literal("SurvivorHub.py", "HUB_STATIC_TEXT")
    data["nativeHubText"] = literal("SurvivorHub.py", "HUB_TEXT")
    for group, prefix in (("difficulties", "difficulty"), ("challenges", "challenge")):
        data[group] = [dict(entry, name={
            language: labels[prefix + "_" + entry["id"]]
            for language, labels in data["nativeHubText"].items()
        }) for entry in data[group]]
    data["nativeCollectionRoles"] = literal("SurvivorHub.py", "COLLECTION_ROLE_TEXT")
    data["nativeWeaponVfx"] = {key: {name: value[name] for name in ("castVfx", "bodyVfx", "impactVfx", "projectilePrefab")} for key, value in content.WEAPON_DEFS.items()}
    data["nativeCommonVfx"] = {key: asset_path("vfx/common/" + key) for key in ("enemy-projectile-orange", "enemy-zone-telegraph", "boss-area-telegraph")}
    if args.catalog_only:
        dependencies = sorted({path for entry in data["nativeWeaponVfx"].values() for path in entry.values() if path} | set(data["nativeCommonVfx"].values()))
        (OUTPUT / "SurvivorNativeDependencies.cs").write_text(
            "// Generated from the existing weapon content. Do not edit.\nnamespace GameScripts;\n" +
            "\n".join("[HEngine.ScriptDependency(" + json.dumps(path) + ")]" for path in dependencies) +
            "\npublic sealed partial class SurvivorNativeGame {}\n", encoding="utf-8")
    for language, labels in data["nativeUiText"].items():
        for element, key in bindings.items():
            if key in strings[language]:
                labels.setdefault(element, strings[language][key])
    data["audio"] = {name: asset_path("audio/" + name.replace("_", "-")) for name in (
        "music_menu", "music_gameplay", "ui_click", "ui_confirm", "level_up", "xp_pickup", "boss_alert", "player_hit")}
    (OUTPUT / "catalog.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(PROJECT / "Config/PortableRendering.json", OUTPUT / "rendering.json")
    if args.catalog_only:
        return
    copied = export_assets(PROJECT, OUTPUT, data, {
        shared_content["scenePath"], "Assets/UI/Backgrounds/starbloom_title_bg.png",
        "Assets/UI/Backgrounds/starbloom_loading_bg.png",
    })
    copy_project_files(PROJECT, OUTPUT, "Web")
    # Keep asset attributions in every distribution, including browser and mini-game packages.
    package = json.loads((PROJECT / "Config/Package.json").read_text(encoding="utf-8"))
    copy_licenses(PROJECT, OUTPUT, package, copied)
    manifest = dict(schema=1, game="小树保卫者", gameplay="C#", sharedContent=shared_content, assets=copied)
    (OUTPUT / "content-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(copied)} original assets, {sum(item['bytes'] for item in copied.values()) / 1048576:.1f} MiB: {OUTPUT}")


if __name__ == "__main__": main()
