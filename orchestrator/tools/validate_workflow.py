"""Validate the ComfyUI workflow JSON and its map YAML."""
import json
import sys
from pathlib import Path

import yaml

from kuba.providers.comfyui import validate_workflow_map

repo = Path(__file__).resolve().parents[1].parent
wf_path = repo / "config" / "comfy" / "workflows" / "sdxl_ip_adapter_api.json"
map_path = repo / "config" / "comfy" / "workflows" / "sdxl_ip_adapter_api.map.yaml"

print(f"=== Workflow: {wf_path}")
wf = json.loads(wf_path.read_text(encoding="utf-8"))
print(f"Nodes: {len(wf)}")
for nid, node in sorted(wf.items(), key=lambda x: int(x[0])):
    print(f"  Node {nid}: {node['class_type']}")

print(f"\n=== Map: {map_path}")
mapping = yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
for k, v in mapping.items():
    print(f"  {k}: {v}")

print("\n=== Cross-validation")
errors = validate_workflow_map(wf, mapping)
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("Map validates against workflow OK")
