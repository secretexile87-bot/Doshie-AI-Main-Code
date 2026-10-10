#!/usr/bin/env python3
"""Doshie 4K 3D Studio Renderer (Blender Cycles + NVIDIA OptiX).

Usage inside Blender:
    blender -b -P doshie_render_4k.py -- --input <model_path> --output <output_image_path> [--samples 128]
"""

import sys
import os
from pathlib import Path

try:
    import bpy
    import mathutils
except ImportError:
    print("Error: This script must be executed by Blender via: blender -b -P doshie_render_4k.py -- ...")
    sys.exit(1)


def parse_args():
    argv = sys.argv
    if "--" not in argv:
        return {}
    args = argv[argv.index("--") + 1:]
    parsed = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                parsed[key] = args[i + 1]
                i += 2
            else:
                parsed[key] = True
                i += 1
        else:
            i += 1
    return parsed


def setup_optix_gpu():
    """Configure Blender Cycles to use NVIDIA RTX 5070 OptiX ray tracing & AI denoising."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"

    preferences = bpy.context.preferences
    cycles_prefs = preferences.addons["cycles"].preferences

    # Prioritize OptiX, fallback to CUDA if OptiX not found
    for compute_type in ["OPTIX", "CUDA"]:
        try:
            cycles_prefs.compute_device_type = compute_type
            cycles_prefs.get_devices()
            devices = [d for d in cycles_prefs.devices if d.type == compute_type]
            if devices:
                for d in devices:
                    d.use = True
                print(f"[Doshie Render] Enabled {compute_type} GPU: {[d.name for d in devices]}")
                break
        except Exception as err:
            print(f"[Doshie Render] Could not configure {compute_type}: {err}")

    # Enable hardware AI denoising
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPTIX"
    except Exception:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"


def clear_scene():
    """Remove default startup objects (cube, camera, light)."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)


def import_model(filepath: str):
    """Import 3D model supporting glTF/GLB, OBJ, FBX, and PLY."""
    ext = Path(filepath).suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == ".obj":
        try:
            bpy.ops.wm.obj_import(filepath=filepath)
        except Exception:
            bpy.ops.import_scene.obj(filepath=filepath)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == ".ply":
        bpy.ops.import_mesh.ply(filepath=filepath)
    else:
        raise ValueError(f"Unsupported 3D format: {ext}")

    imported_objects = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not imported_objects:
        imported_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    return imported_objects


def frame_and_center_model(objects):
    """Compute bounding box, center model at origin, and normalize size."""
    if not objects:
        return 1.0

    min_coord = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_coord = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in objects:
        for v in obj.bound_box:
            world_v = obj.matrix_world @ mathutils.Vector(v)
            min_coord.x = min(min_coord.x, world_v.x)
            min_coord.y = min(min_coord.y, world_v.y)
            min_coord.z = min(min_coord.z, world_v.z)
            max_coord.x = max(max_coord.x, world_v.x)
            max_coord.y = max(max_coord.y, world_v.y)
            max_coord.z = max(max_coord.z, world_v.z)

    center = (min_coord + max_coord) / 2.0
    dims = max_coord - min_coord
    max_dim = max(dims.x, dims.y, dims.z) or 1.0

    # Center all objects
    for obj in objects:
        obj.location -= center

    return max_dim


def setup_studio_lighting(model_size: float):
    """Create a high-end 3-point studio portrait lighting setup."""
    # World background (sleek dark studio vignette)
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("StudioWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.05, 0.05, 0.06, 1.0)
        bg_node.inputs["Strength"].default_value = 0.5

    dist = model_size * 2.5

    # 1. Key Light (Warm, 45 deg right, high)
    key_light_data = bpy.data.lights.new(name="KeyLight", type="AREA")
    key_light_data.energy = 350.0 * (model_size ** 2)
    key_light_data.color = (1.0, 0.95, 0.88)
    key_light_data.size = model_size * 1.2
    key_light = bpy.data.objects.new(name="KeyLight", object_data=key_light_data)
    bpy.context.collection.objects.link(key_light)
    key_light.location = (dist * 0.7, -dist * 0.7, dist * 0.8)
    _point_at(key_light, (0, 0, 0))

    # 2. Fill Light (Cool, 45 deg left, softer)
    fill_light_data = bpy.data.lights.new(name="FillLight", type="AREA")
    fill_light_data.energy = 140.0 * (model_size ** 2)
    fill_light_data.color = (0.85, 0.92, 1.0)
    fill_light_data.size = model_size * 2.0
    fill_light = bpy.data.objects.new(name="FillLight", object_data=fill_light_data)
    bpy.context.collection.objects.link(fill_light)
    fill_light.location = (-dist * 0.8, -dist * 0.5, dist * 0.3)
    _point_at(fill_light, (0, 0, 0))

    # 3. Rim / Hair Light (Crisp back light for edge separation)
    rim_light_data = bpy.data.lights.new(name="RimLight", type="AREA")
    rim_light_data.energy = 450.0 * (model_size ** 2)
    rim_light_data.color = (1.0, 1.0, 1.0)
    rim_light_data.size = model_size * 0.8
    rim_light = bpy.data.objects.new(name="RimLight", object_data=rim_light_data)
    bpy.context.collection.objects.link(rim_light)
    rim_light.location = (-dist * 0.4, dist * 0.8, dist * 0.9)
    _point_at(rim_light, (0, 0, 0))


def setup_camera(model_size: float, focal_length: float = 85.0):
    """Set up 85mm portrait camera aimed at model."""
    cam_data = bpy.data.cameras.new(name="PortraitCamera")
    cam_data.lens = focal_length
    cam_data.sensor_width = 36.0  # Full-frame sensor
    cam = bpy.data.objects.new(name="PortraitCamera", object_data=cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    dist = model_size * 2.8
    cam.location = (0, -dist, model_size * 0.15)
    _point_at(cam, (0, 0, 0))


def _point_at(obj, target):
    """Orient an object towards a target coordinate."""
    loc = obj.location
    direction = mathutils.Vector(target) - loc
    rot_quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = rot_quat.to_euler()


def main():
    args = parse_args()
    input_file = args.get("input")
    output_file = args.get("output")
    samples = int(args.get("samples") or 128)
    res_x = int(args.get("width") or 3840)   # 4K UHD
    res_y = int(args.get("height") or 2160)  # 4K UHD

    if not input_file or not Path(input_file).is_file():
        print(f"[Doshie Render] Input 3D file does not exist: {input_file}")
        sys.exit(1)

    if not output_file:
        output_file = str(Path(input_file).with_suffix(".png"))

    print(f"[Doshie Render] Preparing 4K render for: {input_file}")
    clear_scene()
    setup_optix_gpu()

    # Import and stage model
    mesh_objects = import_model(input_file)
    model_size = frame_and_center_model(mesh_objects)
    print(f"[Doshie Render] Model framed. Bounding size: {model_size:.2f}")

    setup_studio_lighting(model_size)
    setup_camera(model_size, focal_length=85.0)

    # 4K Render Resolution & Quality Settings
    scene = bpy.context.scene
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.cycles.samples = samples
    scene.cycles.adaptive_threshold = 0.01  # Noise threshold

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"  # 16-bit high dynamic range PNG
    scene.render.filepath = os.path.abspath(output_file)

    print(f"[Doshie Render] Starting 4K Cycles OptiX render ({res_x}x{res_y}, {samples} samples)...")
    bpy.ops.render.render(write_still=True)
    print(f"[Doshie Render] Render successfully saved to: {output_file}")


if __name__ == "__main__":
    main()
