#!/usr/bin/env python3
"""Generate the deterministic camera-facing Starbloom menu backdrop mesh."""

import argparse
import json
import os
import struct


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIRECTORY = os.path.join(PROJECT_ROOT, "Assets", "Models", "StarbloomMenu")
MESH_PATH = os.path.join(ASSET_DIRECTORY, "StarbloomMenuBackdrop.hmesh")
MATERIAL_PATH = os.path.join(ASSET_DIRECTORY, "StarbloomMenuBackdrop.hmat")
BINARY_PATH = os.path.join(ASSET_DIRECTORY, "StarbloomMenuBackdrop.bin")
TEXTURE_PATH = "Assets/UI/Backgrounds/StarbloomMenuGarden.png"
MATERIAL_ASSET_PATH = "Assets/Models/StarbloomMenu/StarbloomMenuBackdrop.hmat"
BINARY_ASSET_PATH = "Assets/Models/StarbloomMenu/StarbloomMenuBackdrop.bin"


def _pack_vectors(values):
    flat = [component for value in values for component in value]
    return struct.pack("<" + "f" * len(flat), *flat)


def _assets():
    aspect = 1672.0 / 941.0
    positions = (
        (-aspect, -1.0, 0.0),
        (aspect, -1.0, 0.0),
        (aspect, 1.0, 0.0),
        (-aspect, 1.0, 0.0),
    )
    normals = ((0.0, 0.0, -1.0),) * 4
    texcoords = ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))
    indices = (0, 1, 2, 0, 2, 3)

    position_bytes = _pack_vectors(positions)
    normal_bytes = _pack_vectors(normals)
    texcoord_bytes = _pack_vectors(texcoords)
    index_bytes = struct.pack("<" + "I" * len(indices), *indices)
    binary = position_bytes + normal_bytes + texcoord_bytes + index_bytes

    views = []
    accessors = []

    def add_attribute(data, component_count, value_type, values):
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

    position_accessor = add_attribute(position_bytes, 3, "VEC3", positions)
    normal_accessor = add_attribute(normal_bytes, 3, "VEC3", normals)
    texcoord_accessor = add_attribute(texcoord_bytes, 2, "VEC2", texcoords)
    index_view = len(views)
    views.append({
        "bufferIndex": 0,
        "byteLength": len(index_bytes),
        "byteOffset": len(position_bytes) + len(normal_bytes) + len(texcoord_bytes),
        "byteStride": 0,
        "name": "",
        "target": 34963,
    })
    index_accessor = len(accessors)
    accessors.append({
        "bufferViewIndex": index_view,
        "byteOffset": 0,
        "componentType": 5125,
        "count": len(indices),
        "max": [max(indices)],
        "min": [min(indices)],
        "name": "",
        "normalized": False,
        "type": "SCALAR",
    })

    mesh = {
        "accessorVec": accessors,
        "bufferVec": [{
            "byteLength": len(binary),
            "data": [],
            "name": "",
            "uri": BINARY_ASSET_PATH,
        }],
        "bufferViewVec": views,
        "name": "StarbloomMenuBackdrop",
        "primitives": [{
            "attributes": {
                "POSITION": position_accessor,
                "NORMAL": normal_accessor,
                "TEXCOORD_0": texcoord_accessor,
            },
            "indices": index_accessor,
            "materialResPath": MATERIAL_ASSET_PATH,
            "mode": 4,
            "targets": [],
        }],
        "skeletonPath": "",
        "version": 1,
        "weights": [],
    }
    sampler = {
        "magFilter": 9729,
        "minFilter": 9729,
        "wrapS": 33071,
        "wrapT": 33071,
    }
    texture_resource = {
        "sampler": sampler,
        "textureSourcePath": TEXTURE_PATH,
    }
    material = {
        "Properties": {
            "ExposedProperties": {
                "g_AlbedoMap": TEXTURE_PATH,
                "g_AoMap": "white",
                "g_MetallicRoughnessMap": "white",
                "g_NormalMap": "normal",
            },
            "alphaCutoff": 0.5,
            "alphaMode": "OPAQUE",
            "bUseAlbedoMap": True,
            "bUseAoMap": False,
            "bUseEmissiveMap": True,
            "bUseMetallicRoughnessMap": False,
            "bUseNormalMap": False,
            "doubleSided": True,
            "emissiveFactor": [1.0, 1.0, 1.0],
            "emissiveTexture": {
                "texCoord": 0,
                "textureRes": texture_resource,
            },
            "name": "StarbloomMenuBackdrop",
            "normalTexture": {
                "scale": 1.0,
                "texCoord": 0,
                "textureRes": {"sampler": sampler, "textureSourcePath": ""},
            },
            "occlusionTexture": {
                "strength": 1.0,
                "texCoord": 0,
                "textureRes": {"sampler": sampler, "textureSourcePath": ""},
            },
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                "baseColorTexture": {
                    "texCoord": 0,
                    "textureRes": texture_resource,
                },
                "metallicFactor": 0.0,
                "metallicRoughnessTexture": {
                    "texCoord": 0,
                    "textureRes": {"sampler": sampler, "textureSourcePath": ""},
                },
                "roughnessFactor": 1.0,
            },
        },
        "ShaderPath": "Shaders\\BasePBR.hlsl",
        "Type": "Default",
    }
    return mesh, material, binary


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mesh, material, binary = _assets()
    expected = {
        MESH_PATH: _json_bytes(mesh),
        MATERIAL_PATH: _json_bytes(material),
        BINARY_PATH: binary,
    }
    if args.check:
        stale = [path for path, data in expected.items()
                 if not os.path.isfile(path) or open(path, "rb").read() != data]
        if stale:
            raise SystemExit("stale menu backdrop assets: " + ", ".join(stale))
        print("Starbloom menu backdrop assets: PASS")
        return
    os.makedirs(ASSET_DIRECTORY, exist_ok=True)
    for path, data in expected.items():
        with open(path, "wb") as output:
            output.write(data)
    print("Generated Starbloom menu backdrop assets")


if __name__ == "__main__":
    main()
