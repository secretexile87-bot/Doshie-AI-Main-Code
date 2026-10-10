#!/usr/bin/env python3
"""Doshie Native 2D-Photo to 3D Avatar & 4K/4D Rendering Engine.

Runs 100% locally on Doshie (Acer Nitro RTX 5070):
1. Takes a 2D portrait photo
2. Extracts 478 3D facial vertices and topology using Google MediaPipe
3. Projects high-resolution photo textures onto 3D coordinates
4. Exports native 3D avatar (.glb)
5. Renders native 4K UHD studio-lit portrait (.png) via OptiX Cycles GPU
6. Renders 360-degree 4D orbital video animation loop (.mp4)

Usage:
    python doshie_photo_to_3d.py [--image /path/to/selfie.jpg] [--output-dir ~/Pictures]
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image

BLENDER_PYTHON = "/home/doshie/.local/share/blender-4.3.2-linux-x64/4.3/python/bin/python3.11"
BLENDER_BIN = "/home/doshie/.local/share/blender-4.3.2-linux-x64/blender"
MODEL_TASK_PATH = "/home/doshie/.local/share/mediapipe/face_landmarker.task"

# Ensure we run under Python 3.11 with MediaPipe installed
if sys.executable != BLENDER_PYTHON and os.path.exists(BLENDER_PYTHON):
    try:
        import mediapipe
    except ImportError:
        os.execv(BLENDER_PYTHON, [BLENDER_PYTHON] + sys.argv)


def reconstruct_3d_mesh(image_path: Path, output_glb: Path):
    """Extract 3D facial geometry and textures from photo and export to GLB."""
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.vision import face_landmarker
    import trimesh

    print(f"🔍 [1/3] Detecting facial geometry from: {image_path}")
    base_options = python.BaseOptions(model_asset_path=MODEL_TASK_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        num_faces=1
    )
    detector = vision.FaceLandmarker.create_from_options(options)

    mp_image = mp.Image.create_from_file(str(image_path))
    results = detector.detect(mp_image)

    if not results.face_landmarks:
        raise ValueError("No face detected in the provided image.")

    landmarks = results.face_landmarks[0]
    conns = list(face_landmarker.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION)

    triangles = []
    for i in range(0, len(conns), 3):
        c1, c2, c3 = conns[i], conns[i+1], conns[i+2]
        pts = list({c1.start, c1.end, c2.start, c2.end, c3.start, c3.end})
        if len(pts) == 3:
            triangles.append(pts)

    img_pil = Image.open(image_path).convert("RGB")
    w, h = img_pil.size
    aspect = h / w

    vertices = []
    uvs = []
    for lm in landmarks:
        vx = (lm.x - 0.5) * 2.0
        vy = -(lm.y - 0.5) * 2.0 * aspect
        vz = -lm.z * 2.0
        vertices.append([vx, vy, vz])
        uvs.append([lm.x, 1.0 - lm.y])

    vertices = np.array(vertices, dtype=np.float32)
    triangles = np.array(triangles, dtype=np.int32)
    uvs = np.array(uvs, dtype=np.float32)

    mesh = trimesh.Trimesh(
        vertices=vertices[:468],
        faces=triangles,
        visual=trimesh.visual.TextureVisuals(
            uv=uvs[:468],
            image=img_pil
        ),
        process=False
    )

    mesh.export(str(output_glb))
    print(f"✅ [1/3] 3D Avatar Mesh exported: {output_glb} ({output_glb.stat().st_size // 1024} KB)")


def main():
    parser = argparse.ArgumentParser(description="Doshie Native 2D Photo to 3D/4D Avatar Generator")
    parser.add_argument("--image", default="/home/doshie/Pictures/doshie_selfie.jpg", help="Path to input photo")
    parser.add_argument("--output-dir", default=str(Path.home() / "Pictures"), help="Output directory")
    args = parser.parse_args()

    image_path = Path(args.image).resolve()
    if not image_path.is_file():
        print(f"Error: Input photo not found: {image_path}")
        sys.exit(1)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = image_path.stem
    output_glb = out_dir / f"{base_name}_3d_avatar.glb"
    output_4k = out_dir / f"{base_name}_4k_portrait.png"
    output_4d = out_dir / f"{base_name}_4d_turntable.mp4"

    script_dir = Path(__file__).resolve().parent
    render_4k_script = script_dir / "doshie_render_4k.py"
    turntable_script = script_dir / "doshie_turntable_4d.py"

    print("=" * 60)
    print("🤖 DOSHIE NATIVE 3D/4D ENGINE STARTING (100% LOCAL)")
    print(f"Input Photo : {image_path}")
    print(f"Target 3D   : {output_glb}")
    print("=" * 60)

    # 1. 3D Mesh Reconstruction
    reconstruct_3d_mesh(image_path, output_glb)

    # 2. 4K Studio Ray-Tracing (Blender Cycles OptiX)
    print("\n🎬 [2/3] Rendering 4K Studio Portrait (NVIDIA OptiX)...")
    cmd_4k = [
        BLENDER_BIN, "-b", "-P", str(render_4k_script),
        "--",
        "--input", str(output_glb),
        "--output", str(output_4k),
        "--samples", "64",
        "--width", "3840",
        "--height", "2160"
    ]
    subprocess.run(cmd_4k, check=True)
    print(f"✅ [2/3] 4K Portrait saved to: {output_4k}")

    # 3. 4D 360 Turntable Animation
    print("\n🎥 [3/3] Rendering 4D 360° Turntable Video (MP4)...")
    cmd_tt = [
        BLENDER_BIN, "-b", "-P", str(turntable_script),
        "--",
        "--input", str(output_glb),
        "--output", str(output_4d),
        "--frames", "45",
        "--fps", "30",
        "--res", "1080p",
        "--samples", "16"
    ]
    subprocess.run(cmd_tt, check=True)
    print(f"✅ [3/3] 4D Video Loop saved to: {output_4d}")

    print("\n" + "=" * 60)
    print("🎉 ALL NATIVE 3D & 4D ASSETS GENERATED LOCALLY!")
    print(f"1. 3D Model (.glb)    : {output_glb}")
    print(f"2. 4K Portrait (.png) : {output_4k}")
    print(f"3. 4D Video (.mp4)    : {output_4d}")
    print("=" * 60)


if __name__ == "__main__":
    main()
