#!/usr/bin/env python3
"""Doshie 4D Turntable Video Renderer (Blender Cycles + NVIDIA OptiX).

Renders a 360-degree rotating cinematic camera orbit loop of any 3D model
into a pristine H.264 MP4 video.

Usage:
    blender -b -P doshie_turntable_4d.py -- --input <model_path> --output <output_video.mp4> [--frames 90] [--fps 30] [--res 4k]
"""

import sys
import os
import math
from pathlib import Path

try:
    import bpy
    import mathutils
except ImportError:
    print("Error: Must be run via blender -b -P doshie_turntable_4d.py -- ...")
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


def setup_optix():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for c_type in ["OPTIX", "CUDA"]:
        try:
            prefs.compute_device_type = c_type
            prefs.get_devices()
            devices = [d for d in prefs.devices if d.type == c_type]
            if devices:
                for d in devices:
                    d.use = True
                print(f"[4D Turntable] Cycles GPU enabled: {[d.name for d in devices]}")
                break
        except Exception:
            pass
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPTIX"
    except Exception:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)


def import_model(filepath: str):
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
        raise ValueError(f"Unsupported format: {ext}")

    imported = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    if not imported:
        imported = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    return imported


def center_model(objects):
    if not objects:
        return 1.0
    min_c = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_c = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in objects:
        for v in obj.bound_box:
            world_v = obj.matrix_world @ mathutils.Vector(v)
            min_c.x = min(min_c.x, world_v.x)
            min_c.y = min(min_c.y, world_v.y)
            min_c.z = min(min_c.z, world_v.z)
            max_c.x = max(max_c.x, world_v.x)
            max_c.y = max(max_c.y, world_v.y)
            max_c.z = max(max_c.z, world_v.z)

    center = (min_c + max_c) / 2.0
    dims = max_c - min_c
    max_dim = max(dims.x, dims.y, dims.z) or 1.0

    for obj in objects:
        obj.location -= center
    return max_dim


def setup_lighting(model_size: float):
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("TurntableWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.04, 0.04, 0.05, 1.0)
        bg.inputs["Strength"].default_value = 0.6

    dist = model_size * 2.5
    # Key
    k_data = bpy.data.lights.new(name="KeyLight", type="AREA")
    k_data.energy = 400.0 * (model_size ** 2)
    k_data.color = (1.0, 0.96, 0.9)
    k_data.size = model_size * 1.5
    k_obj = bpy.data.objects.new("KeyLight", k_data)
    bpy.context.collection.objects.link(k_obj)
    k_obj.location = (dist * 0.7, -dist * 0.7, dist * 0.8)
    _point_at(k_obj, (0, 0, 0))

    # Fill
    f_data = bpy.data.lights.new(name="FillLight", type="AREA")
    f_data.energy = 160.0 * (model_size ** 2)
    f_data.color = (0.85, 0.9, 1.0)
    f_data.size = model_size * 2.0
    f_obj = bpy.data.objects.new("FillLight", f_data)
    bpy.context.collection.objects.link(f_obj)
    f_obj.location = (-dist * 0.8, -dist * 0.5, dist * 0.3)
    _point_at(f_obj, (0, 0, 0))

    # Rim
    r_data = bpy.data.lights.new(name="RimLight", type="AREA")
    r_data.energy = 500.0 * (model_size ** 2)
    r_data.color = (0.9, 0.8, 1.0)
    r_data.size = model_size * 1.0
    r_obj = bpy.data.objects.new("RimLight", r_data)
    bpy.context.collection.objects.link(r_obj)
    r_obj.location = (0, dist, dist * 0.6)
    _point_at(r_obj, (0, 0, 0))


def _point_at(obj, target):
    direction = mathutils.Vector(target) - obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = rot_quat.to_euler()


def animate_turntable(model_size: float, total_frames: int):
    """Animate a circular orbit camera around the subject."""
    cam_data = bpy.data.cameras.new("TurntableCam")
    cam_data.lens = 70.0
    cam = bpy.data.objects.new("TurntableCam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    dist = model_size * 2.8
    elevation = model_size * 0.25

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames

    for f in range(1, total_frames + 1):
        angle = (2.0 * math.pi * (f - 1)) / total_frames
        # Orbit in counter-clockwise circle around Z-axis
        x = dist * math.sin(angle)
        y = -dist * math.cos(angle)
        z = elevation

        cam.location = (x, y, z)
        _point_at(cam, (0, 0, 0))

        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)

    # Set interpolation to linear for smooth continuous loop
    if cam.animation_data and cam.animation_data.action:
        for fcurve in cam.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = "LINEAR"


def main():
    args = parse_args()
    input_file = args.get("input")
    output_file = args.get("output")
    total_frames = int(args.get("frames") or 72)  # default 72 frames (~2.4s at 30fps)
    fps = int(args.get("fps") or 30)
    samples = int(args.get("samples") or 32)  # 32 samples + OptiX denoiser renders fast per frame
    res_mode = str(args.get("res") or "4k").lower()

    if res_mode == "4k":
        res_x, res_y = 3840, 2160
    elif res_mode == "1080p":
        res_x, res_y = 1920, 1080
    else:
        res_x, res_y = 1920, 1080

    if not input_file or not Path(input_file).is_file():
        print(f"[4D Turntable] Input 3D file not found: {input_file}")
        sys.exit(1)

    if not output_file:
        output_file = str(Path(input_file).with_suffix(".mp4"))

    print(f"[4D Turntable] Staging 4D turntable animation for: {input_file}")
    clear_scene()
    setup_optix()

    mesh_objects = import_model(input_file)
    model_size = center_model(mesh_objects)
    setup_lighting(model_size)
    animate_turntable(model_size, total_frames)

    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.cycles.samples = samples

    # Video output configuration (H.264 MP4)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    scene.render.filepath = os.path.abspath(output_file)

    print(f"[4D Turntable] Rendering {total_frames} frames ({res_x}x{res_y} @ {fps}fps) with OptiX Cycles...")
    bpy.ops.render.render(animation=True)
    print(f"[4D Turntable] Successfully saved 4D video to: {output_file}")


if __name__ == "__main__":
    main()
