

# Project Blueprint: Headless Folktale Automation Pipeline (`Kuba-Engine`)

## Master Instruction to Cursor Agent

> **CRITICAL GATEKEEPER:** Do NOT write, generate, or scaffold any implementation code, file trees, or boilerplate configurations yet. This is a discovery, architectural planning, and verification phase. Your immediate task is to digest this specification, conduct necessary background research on the specified APIs/tools, and output an **Architectural Proposal** followed by a structured **Q&A Session** targeting edge cases. Wait for explicit user sign-off on your plan before touched a single line of code.

---

## 1. Context & High-Level Vision

The objective is to build a highly automated, CLI-driven, local-first video generation pipeline tailored for producing 15-minute "African Folktale" style anthology videos.

Instead of manual timeline orchestration in a heavy video editing UI, the entire assembly, asset matching, and rendering will be handled programmatically via a code-driven composition engine.

### Content Architecture per Episode

* **Total Duration:** ~15 minutes (approx. 900 seconds).
* **Audio:** Continuous, natural-sounding African oral storyteller narration driven by local speech synthesis.
* **Visual Assets (Stills):** ~14 minutes of hyper-consistent character and environment still frames, utilizing panning, zooming (Ken Burns effects), and transitions to maintain pacing.
* **Visual Assets (Motion):** ~60 seconds of elite-tier, cinematic, silent text-to-video clips strategically interspersed during high-climax or action-oriented scenes.

---

## 2. Technical Stack & Core Infrastructure

The pipeline must be completely modular, interacting with local services and cloud APIs via lightweight orchestration scripts (Python or Node.js).

| Component | Technology | Execution Environment | Rationale / Integration Method |
| --- | --- | --- | --- |
| **Orchestrator** | Python or Node.js CLI | Local PC (Terminal) | Reads/writes the master `blueprint.json`, handles rate limits, async polling, and asset verification. |
| **Script & Prompting** | Google AI Studio (Gemini API) | Cloud (Free Tier) | Ingests themes/folktales and outputs structured JSON containing narration tokens, precise asset prompt layouts, and scene timings. |
| **Audio Generation** | Kokoro TTS (ONNX) | Local PC | Ultra-fast local synthesis. Must support custom voice profile embeddings (`.json` Float32 arrays) to achieve natural African narration cadences rather than standard US/UK accents. |
| **Image Generation** | ComfyUI API + IP-Adapter | Local PC (Headless Port) | Programmatic control over SDXL or Flux architectures. Uses an IP-Adapter node inside the JSON workflow payload to enforce strict character consistency across different scene environments. |
| **Video Generation** | Google AI Studio (Veo) / SiliconFlow | Cloud (Free / Asynchronous Tier) | Generates silent, high-fidelity 5-6 second clips for high-impact scenes. Must handle asynchronous polling loops via Operation IDs. |
| **Composition Engine** | Remotion (React) | Local PC (Headless Renderer) | programmatically imports the `blueprint.json`, maps assets to absolute frame timelines, applies dynamic CSS transforms (zooms/pans), and exports the final MP4 via CLI. |

---

## 3. Data Flow Architecture

The pipeline must run as an absolute state machine driven by a single file: `blueprint.json`.

```
[Phase 1: LLM Engine] ---> Outputs blueprint.json (Timestamps, Prompts, Voice Text)
                                 |
                                 v
[Phase 2: Asset Fan-out] -------> Batch Local Kokoro TTS (Generates .wav audio files)
                         -------> Batch Local ComfyUI API (Generates character-consistent .pngs)
                         -------> Batch Async Cloud Video API (Polls & downloads silent .mp4s)
                                 |
                                 v
[Phase 3: Validation] -----------> Verifies file integrity, durations, and matching indices
                                 |
                                 v
[Phase 4: Composition] ----------> Remotion reads blueprint.json + local assets -> FFMPEG compile

```

---

## 4. Architectural Constraints & Philosophy

* **No UI Babysitting:** The system must run entirely from shell commands. Standard output should provide clean, verbose log lines, progress bars for long-running operations (like API polling), and distinct error boundaries.
* **Failure Isolation:** If a cloud video API call fails or times out, the orchestrator must automatically fall back to generating a still image via the local ComfyUI instance for that specific timestamp, ensuring the entire 15-minute render sequence doesn't crash mid-run.
* **State Persistence & Idempotency:** If the script is interrupted during asset generation, restarting it must inspect the directory structure and the `blueprint.json` state, skipping assets that are already successfully generated/downloaded.

---

## 5. Your Task: Immediate Next Steps for Cursor

Before writing any implementation code or system configuration, analyze this document and reply with the following structural layout:

### Step 1: Research & Feasibility Analysis

Evaluate the current 2026 ecosystem for the following and highlight potential friction points:

1. **Kokoro TTS Custom Embeddings:** Detail the best programmatic vector injection method via Python/Node for custom voice profiles without retraining the model.
2. **ComfyUI Headless API:** Explain how you plan to manage the JSON payload schema for ComfyUI to handle the dynamic text prompt updates alongside a static IP-Adapter image path node.
3. **Google AI Studio (Veo Async Polling):** Confirm the design pattern for managing long-running operations (LRO) over a 60-second aggregate clip budget without hitting rate limits on the free tier.

### Step 2: System Architecture Proposal

Propose the exact directory layout, configuration structure (e.g., `.env` variable structures), and language choice (Python vs. TypeScript/Node) for the orchestrator layer, justifying why one will handle the async asset fetching and Remotion context binding better.

### Step 3: Deep-Dive Discovery Questions

Provide a targeted list of technical questions for me to answer regarding:

* Your local hardware specs (VRAM boundaries for running ComfyUI and Kokoro simultaneously).
* Your preference on the `blueprint.json` internal schema structure.
* The target frame rate and resolution profile for the Remotion build matrix.

***Do not output code. Await user feedback on your analysis and questions.***