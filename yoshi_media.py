import json
import os
import re
import secrets
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path("/srv/diyoshi-data")
DATA_READY = DATA_ROOT.is_dir() and os.path.ismount(DATA_ROOT)
ROOT = Path(os.environ.get(
    "YOSHI_MEDIA_ROOT",
    DATA_ROOT / "generated-media" if DATA_READY else PROJECT_ROOT / "generated-media",
)).expanduser().resolve()
LOCAL_MEDIA = Path(os.environ.get(
    "YOSHI_LOCAL_MEDIA_HOME", PROJECT_ROOT / "local-media"
)).expanduser().resolve()
LOCAL_PYTHON = LOCAL_MEDIA / "venv" / "bin" / "python"
LOCAL_WORKER = LOCAL_MEDIA / "generate.py"
HQ_PYTHON = DATA_ROOT / "runtime" / "optimum-intel" / "bin" / "python"
HQ_WORKER = LOCAL_MEDIA / "generate_optimum.py"
DATA_MODEL = DATA_ROOT / "models" / "Juggernaut-XL-v9-int8-ov"
FALLBACK_MODEL = LOCAL_MEDIA / "models" / "LCM_Dreamshaper_v7-int8-ov"
LOCAL_MODEL = Path(os.environ.get(
    "YOSHI_LOCAL_IMAGE_MODEL",
    DATA_MODEL if DATA_READY and DATA_MODEL.is_dir() else FALLBACK_MODEL,
)).expanduser().resolve()
ALLOWED_IMAGE_SIZES = {"512x512", "768x512", "512x768", "768x768"}
ALLOWED_QUALITIES = {"low", "medium", "high"}
QUALITY_STEPS = {"low": 4, "medium": 6, "high": 20}
QUALITY_SUFFIX = (
    "polished professional composition, coherent shapes, clean silhouette, "
    "detailed materials, balanced lighting, sharp focus, high visual quality"
)


class MediaError(RuntimeError):
    pass


def _local_ready():
    return (
        LOCAL_PYTHON.is_file()
        and LOCAL_WORKER.is_file()
        and LOCAL_MODEL.is_dir()
        and LOCAL_MODEL.joinpath("model_index.json").is_file()
    )


def _high_quality_ready():
    return HQ_PYTHON.is_file() and HQ_WORKER.is_file() and DATA_MODEL.is_dir()


def status():
    ready = _local_ready()
    high_quality = _high_quality_ready()
    return {
        "mode": "local",
        "portable": True,
        "image": {
            "connected": ready,
            "provider": (
                f"Local Optimum/OpenVINO · {LOCAL_MODEL.name} · Intel GPU"
                if high_quality else
                f"Local OpenVINO · {LOCAL_MODEL.name} · Intel GPU/CPU"
                if ready else "Local model missing"
            ),
        },
        "video": {
            "connected": False,
            "provider": "Local video is not enabled on this hardware",
        },
        "openai_credentials_present": False,
        "message": (
            "Private local image generation is ready. No subscription or API key is used."
            if ready else
            "The private local image runtime is not fully installed."
        ),
    }


def configure_key(_key):
    raise MediaError("Cloud media access was removed. DiYoshi now uses local generation.")


def remove_key():
    return status()


def _profile_directory(profile):
    clean = re.sub(r"[^a-z0-9_-]+", "-", str(profile or "").casefold()).strip("-")
    if not clean:
        raise MediaError("A profile is required.")
    directory = ROOT.joinpath(clean).resolve()
    if directory.parent != ROOT:
        raise MediaError("Invalid media profile.")
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    return directory


def _clean_prompt(prompt):
    value = " ".join(str(prompt or "").split()).strip()
    if not value or len(value) > 4000:
        raise MediaError("Describe the image in 1 to 4,000 characters.")
    return value


def _enhance_prompt(prompt):
    base = prompt
    normalized = prompt.casefold().strip()
    if normalized in {"yoshi", "diyoshi"}:
        base = (
            "full-body portrait of a friendly green dinosaur AI mascot named DiYoshi, "
            "warm expressive face, confident pose, original character design, centered"
        )
    elif len(prompt.split()) < 6:
        base = f"{prompt}, clearly defined main subject, centered composition"
    return f"{base}, {QUALITY_SUFFIX}"


def generate_image(profile, prompt, size="512x512", quality="medium"):
    prompt = _clean_prompt(prompt)
    if not _local_ready():
        raise MediaError("The private local image model is not ready.")
    if size not in ALLOWED_IMAGE_SIZES or quality not in ALLOWED_QUALITIES:
        raise MediaError("Unsupported local image size or quality.")
    width, height = (int(value) for value in size.split("x"))
    filename = f"{secrets.token_hex(12)}.png"
    target = _profile_directory(profile) / filename
    enhanced_prompt = _enhance_prompt(prompt)
    seed = secrets.randbelow(2_147_483_647)
    high_quality = quality == "high" and _high_quality_ready()
    runtime = HQ_PYTHON if high_quality else LOCAL_PYTHON
    worker = HQ_WORKER if high_quality else LOCAL_WORKER
    command = [
        str(runtime), str(worker),
        "--prompt", enhanced_prompt,
        "--output", str(target),
        "--width", str(width),
        "--height", str(height),
        "--steps", str(QUALITY_STEPS[quality]),
        "--seed", str(seed),
    ]
    environment = os.environ.copy()
    environment["YOSHI_LOCAL_IMAGE_MODEL"] = str(LOCAL_MODEL)
    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            env=environment,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        target.unlink(missing_ok=True)
        raise MediaError("Local image generation timed out safely.") from error
    if result.returncode != 0 or not target.is_file():
        target.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "Local image generation failed.").strip()
        raise MediaError(detail[-1000:])
    os.chmod(target, 0o600)
    try:
        metadata = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        metadata = {}
    return {
        "kind": "image",
        "filename": filename,
        "prompt": prompt,
        "provider": "Local Optimum/OpenVINO" if high_quality else "Local OpenVINO",
        "quality": "max" if high_quality else quality,
        "device": metadata.get("device", "AUTO"),
        "seconds": metadata.get("seconds"),
    }


def start_video(_prompt, size="1280x720", seconds=8):
    del size, seconds
    raise MediaError(
        "Local AI video is not enabled on this Tecra. "
        "Image generation is fully local and ready."
    )


def poll_video(_profile, _job_id):
    raise MediaError("There is no local video job to poll.")


def media_path(profile, filename):
    if not re.fullmatch(r"[0-9a-f]{24}\.(?:png|mp4)", str(filename or "")):
        raise MediaError("Invalid media filename.")
    directory = _profile_directory(profile)
    target = directory.joinpath(filename).resolve()
    if target.parent != directory or not target.is_file():
        raise MediaError("Media file not found.")
    return target
