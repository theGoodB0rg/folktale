"""Test ComfyUI reachability and available nodes."""
import json
import sys
from urllib.request import urlopen

BASE = "https://singing-fur-chemicals-when.trycloudflare.com"

print("=== 1. System Stats ===")
try:
    with urlopen(f"{BASE}/system_stats", timeout=15) as r:
        stats = json.loads(r.read())
    devices = stats.get("devices", [])
    for d in devices:
        print(f"  Device: {d['name']}, VRAM: {d['vram_total']/1e9:.1f}GB")
    print(f"  ComfyUI version: {stats['system']['comfyui_version']}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

print("\n=== 2. Available Node Classes (first 30) ===")
try:
    with urlopen(f"{BASE}/object_info", timeout=30) as r:
        obj_info = json.loads(r.read())
    for i, (cls_name, info) in enumerate(sorted(obj_info.items())):
        if i >= 30:
            break
        required = list(info.get("input", {}).get("required", {}).keys())
        print(f"  {cls_name}: {required[:4]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== 3. Check our workflow node classes exist ===")
required_nodes = ["CheckpointLoaderSimple", "CLIPTextEncode", "CLIPVisionLoader",
                  "LoadImage", "IPAdapterModelLoader", "IPAdapter",
                  "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage"]
for node in required_nodes:
    if node in obj_info:
        print(f"  {node}: FOUND")
    else:
        print(f"  {node}: MISSING!")

print("\n=== 4. Available models ===")
for folder in ["checkpoints", "clip_vision", "ipadapter"]:
    try:
        with urlopen(f"{BASE}/view?format=json&folder={folder}", timeout=15) as r:
            data = json.loads(r.read())
        models = data.get("files", []) or data
        print(f"  {folder}: {len(models)} files")
        for m in models[:5]:
            print(f"    {m}")
    except Exception as e:
        print(f"  {folder}: ERROR {e}")
