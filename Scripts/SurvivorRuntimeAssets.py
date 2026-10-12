"""Strict runtime view of the cooked Survivor asset-set manifest."""

import json
import os


MANIFEST_PROJECT_PATH = "Config/SurvivorRuntimeAssets.json"
_ROOT_FIELDS = frozenset(("Schema", "SchemaVersion", "Assets"))
_ASSET_FIELDS = frozenset(("Key", "Path", "Kind", "Reason"))
_ALLOWED_PREFIXES = ("Assets/", "Config/", "Scripts/", "Shaders/")
_ALLOWED_KEY_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyz0123456789/_-"
)


class RuntimeAssetManifestError(ValueError):
    pass


try:
    import HEngine as _HEngine
except ImportError:
    _HEngine = None


def _manifest_full_path():
    if _HEngine is not None:
        get_full_path = getattr(_HEngine, "GetFullPath", None)
        if get_full_path is None:
            raise RuntimeAssetManifestError(
                "HEngine.GetFullPath is unavailable for the runtime asset manifest"
            )
        return get_full_path(MANIFEST_PROJECT_PATH)
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "..",
        *MANIFEST_PROJECT_PATH.split("/"),
    ))


def _validate_key(key, index):
    if not isinstance(key, str) or not key:
        raise RuntimeAssetManifestError(
            "Runtime asset Assets[" + str(index) + "].Key must be non-empty"
        )
    if (key != key.lower() or key.startswith("/") or key.endswith("/") or
            "//" in key):
        raise RuntimeAssetManifestError("Invalid runtime asset key: " + repr(key))
    if any(character not in _ALLOWED_KEY_CHARACTERS for character in key):
        raise RuntimeAssetManifestError("Invalid runtime asset key: " + repr(key))


def _validate_path(path, index):
    if not isinstance(path, str) or not path:
        raise RuntimeAssetManifestError(
            "Runtime asset Assets[" + str(index) + "].Path must be non-empty"
        )
    if "\\" in path or ":" in path or not path.startswith(_ALLOWED_PREFIXES):
        raise RuntimeAssetManifestError("Unsafe runtime asset path: " + repr(path))
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise RuntimeAssetManifestError("Unsafe runtime asset path: " + repr(path))


def _load_manifest():
    manifest_path = _manifest_full_path()
    try:
        with open(manifest_path, "r", encoding="utf-8") as manifest_file:
            root = json.load(manifest_file)
    except (OSError, UnicodeError, ValueError) as error:
        raise RuntimeAssetManifestError(
            "Cannot load runtime asset manifest " + str(manifest_path) + ": " + str(error)
        ) from error

    if not isinstance(root, dict) or frozenset(root) != _ROOT_FIELDS:
        raise RuntimeAssetManifestError(
            "Runtime asset manifest root fields must be Schema, SchemaVersion, Assets"
        )
    if root["Schema"] != "hengine.runtime-asset-set":
        raise RuntimeAssetManifestError("Unsupported runtime asset manifest Schema")
    if type(root["SchemaVersion"]) is not int or root["SchemaVersion"] != 1:
        raise RuntimeAssetManifestError("Unsupported runtime asset manifest SchemaVersion")
    assets = root["Assets"]
    if not isinstance(assets, list) or not assets:
        raise RuntimeAssetManifestError("Runtime asset manifest Assets must be non-empty")

    paths = {}
    entries = []
    sort_keys = []
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict) or frozenset(asset) != _ASSET_FIELDS:
            raise RuntimeAssetManifestError(
                "Runtime asset Assets[" + str(index) + "] has invalid fields"
            )
        key = asset["Key"]
        path = asset["Path"]
        _validate_key(key, index)
        _validate_path(path, index)
        if asset["Kind"] != "HardRuntime":
            raise RuntimeAssetManifestError(
                "Runtime asset " + key + " must use Kind HardRuntime"
            )
        if not isinstance(asset["Reason"], str) or not asset["Reason"].strip():
            raise RuntimeAssetManifestError(
                "Runtime asset " + key + " must have a non-empty Reason"
            )
        if key in paths:
            raise RuntimeAssetManifestError("Duplicate runtime asset key: " + key)
        paths[key] = path
        entries.append(dict(asset))
        sort_keys.append((key.encode("utf-8"), path.encode("utf-8")))

    if sort_keys != sorted(sort_keys):
        raise RuntimeAssetManifestError(
            "Runtime asset manifest Assets must be sorted by Key then Path"
        )
    return paths, tuple(entries)


_ASSET_PATHS, _ASSET_ENTRIES = _load_manifest()


def asset_path(key):
    try:
        return _ASSET_PATHS[key]
    except KeyError as error:
        raise RuntimeAssetManifestError("Missing runtime asset key: " + str(key)) from error


def asset_keys():
    return tuple(_ASSET_PATHS)


def asset_entries():
    return _ASSET_ENTRIES
