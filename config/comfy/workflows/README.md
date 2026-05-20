# ComfyUI Workflow Files

Put ComfyUI workflows saved in API format in this directory.

The default docs use:

```text
sdxl_ip_adapter_api.json
sdxl_ip_adapter_api.map.yaml
```

`sdxl_ip_adapter_api.json` should be exported from ComfyUI with "Save (API Format)".

`sdxl_ip_adapter_api.map.yaml` maps Kuba provider fields to workflow input paths:

```yaml
positive_prompt: "6.inputs.text"
negative_prompt: "7.inputs.text"
seed: "3.inputs.seed"
save_prefix: "28.inputs.filename_prefix"
reference_image: "14.inputs.image"
```

Adjust the node IDs to match your workflow.
