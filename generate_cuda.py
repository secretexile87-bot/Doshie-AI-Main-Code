import argparse
from pathlib import Path
import torch
from diffusers import StableDiffusionXLPipeline

MODEL_ID = "/home/doshie/Doshie/models/sdxl-base-1.0"
parser = argparse.ArgumentParser()
parser.add_argument("--prompt", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--width", type=int, default=512)
parser.add_argument("--height", type=int, default=512)
parser.add_argument("--steps", type=int, default=20)
parser.add_argument("--seed", type=int, default=0)
args = parser.parse_args()
if not torch.cuda.is_available():
    raise RuntimeError("CUDA/NVIDIA GPU is unavailable")
device = "cuda"
dtype = torch.float16
pipe = StableDiffusionXLPipeline.from_pretrained(
    MODEL_ID, torch_dtype=dtype, use_safetensors=True
)
pipe.to(device)
pipe.vae.enable_slicing()
generator = torch.Generator(device=device).manual_seed(args.seed)
image = pipe(
    prompt=args.prompt,
    width=args.width,
    height=args.height,
    num_inference_steps=args.steps,
    guidance_scale=7.0,
    generator=generator,
).images[0]
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
image.save(args.output)
print('{"device":"cuda","gpu":"NVIDIA RTX 5070","model":"SDXL 1.0"}')
