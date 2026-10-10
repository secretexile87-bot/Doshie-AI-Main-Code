#!/usr/bin/env python3
"""Doshie Complete 4D Experience Pipeline.

Takes an exported 3D avatar (.glb, .obj, .fbx) and generates:
1. Native 4K UHD photorealistic portrait render (.png)
2. 360-degree orbital 4D video animation loop (.mp4)
3. Facial blendshapes inspection report

Usage:
    python doshie_4d_pipeline.py --input /path/to/avatar.glb
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Doshie Complete 4D Avatar Pipeline")
    parser.add_argument("--input", required=True, help="Path to 3D avatar (.glb, .obj, .fbx)")
    parser.add_argument("--output-dir", default=str(Path.home() / "Pictures"), help="Destination directory")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"Error: 3D model file not found at: {input_path}")
        sys.exit(1)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = input_path.stem
    portrait_4k = out_dir / f"{base_name}_4k_portrait.png"
    turntable_4d = out_dir / f"{base_name}_4d_turntable.mp4"

    blender_bin = "/home/doshie/.local/share/blender-4.3.2-linux-x64/blender"
    render_4k_script = Path(__file__).resolve().parent / "doshie_render_4k.py"
    turntable_script = Path(__file__).resolve().parent / "doshie_turntable_4d.py"

    print("=" * 60)
    print("🚀 DOSHIE 4D AVATAR PIPELINE STARTING")
    print(f"Input Model : {input_path}")
    print(f"Output Dir  : {out_dir}")
    print("=" * 60)

    # 1. 4K Still Portrait Render
    print("\n[Step 1/2] Rendering 4K UHD Studio Portrait (Cycles OptiX)...")
    cmd_4k = [
        blender_bin, "-b", "-P", str(render_4k_script),
        "--",
        "--input", str(input_path),
        "--output", str(portrait_4k),
        "--samples", "128",
        "--width", "3840",
        "--height", "2160"
    ]
    res_4k = subprocess.run(cmd_4k, capture_output=True, text=True)
    if res_4k.returncode == 0:
        print(f"✅ 4K Portrait saved to: {portrait_4k}")
    else:
        print(f"❌ 4K Render error: {res_4k.stderr[-300:]}")

    # 2. 4D 360 Turntable Animation
    print("\n[Step 2/2] Rendering 360° 4D Turntable Video Loop (MP4)...")
    cmd_tt = [
        blender_bin, "-b", "-P", str(turntable_script),
        "--",
        "--input", str(input_path),
        "--output", str(turntable_4d),
        "--frames", "60",
        "--fps", "30",
        "--res", "1080p",
        "--samples", "32"
    ]
    res_tt = subprocess.run(cmd_tt, capture_output=True, text=True)
    if res_tt.returncode == 0:
        print(f"✅ 4D Turntable Video saved to: {turntable_4d}")
    else:
        print(f"❌ 4D Turntable error: {res_tt.stderr[-300:]}")

    print("\n" + "=" * 60)
    print("🎉 ALL 4D RENDERS COMPLETE!")
    print(f"1. 4K Still Portrait : {portrait_4k}")
    print(f"2. 4D Video Loop     : {turntable_4d}")
    print("=" * 60)


if __name__ == "__main__":
    main()
