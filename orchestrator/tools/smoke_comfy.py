"""Direct smoke test of ComfyUI workflow."""
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://singing-fur-chemicals-when.trycloudflare.com"
workflow_path = Path(__file__).resolve().parents[2] / "config" / "comfy" / "workflows" / "sdxl_ip_adapter_api.json"
workflow = json.loads(workflow_path.read_text(encoding="utf-8"))

# Patch the workflow for a simple smoke test
# Node 2 is CLIPTextEncode (positive prompt)
workflow["2"]["inputs"]["text"] = "a simple river stone on a sandy riverbank, cinematic lighting, 4k"
# Node 3 is CLIPTextEncode (negative prompt)
workflow["3"]["inputs"]["text"] = "watermark, text, distorted, ugly, blurry"
# Node 5 is KSampler - set seed
workflow["5"]["inputs"]["seed"] = 42
# Node 7 is SaveImage
workflow["7"]["inputs"]["filename_prefix"] = "smoke_test"

print("Posting prompt to ComfyUI...")
payload = json.dumps({"prompt": workflow}).encode("utf-8")
request = Request(
    f"{BASE}/prompt",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urlopen(request, timeout=120) as response:
        body = response.read()
        result = json.loads(body)
    prompt_id = result.get("prompt_id")
    print(f"Prompt queued! ID: {prompt_id}")
except Exception as e:
    print(f"ERROR posting prompt: {e}")
    if hasattr(e, 'read'):
        body = e.read().decode('utf-8', errors='replace')
        print(f"Response body: {body[:1000]}")
    sys.exit(1)

# Poll for the result
import time
deadline = time.monotonic() + 300
print("Polling for completion...")
while time.monotonic() < deadline:
    try:
        with urlopen(f"{BASE}/history/{prompt_id}", timeout=30) as response:
            history = json.loads(response.read())
    except Exception as e:
        print(f"Poll error: {e}")
        time.sleep(2)
        continue

    outputs = history.get(prompt_id, {}).get("outputs", {})
    if outputs:
        print(f"History received with {len(outputs)} outputs")
        for node_id, output in outputs.items():
            images = output.get("images", [])
            for img in images:
                print(f"  Image: {img['filename']} ({img.get('type', 'output')})")
        print("SMOKE TEST PASSED")
        sys.exit(0)
    status = history.get(prompt_id, {}).get("status", {})
    if status.get("completed") is False:
        print("   prompt still queued/processing...")
    time.sleep(3)

print(f"Timed out waiting for prompt {prompt_id}")
sys.exit(1)
