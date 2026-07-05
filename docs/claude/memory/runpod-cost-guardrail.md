---
name: runpod-cost-guardrail
description: NEVER invoke any cost-incurring RunPod action without asking the user to confirm TWICE
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 35bb7932-d37b-41f7-8f2b-bc3261e91022
---

User has a RunPod MCP set up for renting GPUs for the anomaly-detection project. **Hard rule (user instruction, 2026-06-29):** any RunPod action that incurs cost or changes infrastructure state — create-pod, start-pod, create-network-volume, create-endpoint, update-pod, and similar — must **NEVER be run without asking the user to confirm twice** (two explicit confirmations in-chat before invoking).

Read-only RunPod calls (list-pods, get-pod, list-endpoints, get-endpoint) are fine without double-confirm.

**Why:** GPU pods bill by the hour; an accidental spin-up (or a pod left running) burns real money. The user wants a deliberate, two-step human gate on all spend.

**How to apply:** before any state-changing RunPod call — (1) state exactly what will be created and the $/hr, ask "confirm?"; (2) after they confirm, ask once more "final confirm — provisioning now?"; only then invoke. Also remind the user to `stop-pod` when done (idle pods still bill; network volume bills even while pod stopped). Consider enforcing via settings.json deny/ask permission rule.

**RunPod MCP VERIFIED connected 2026-06-29. Tool classification:**
- COST, double-confirm: `create-pod`, `start-pod`, `update-pod`, `create-network-volume`, `update-network-volume`, `create-endpoint`, `update-endpoint`, `run-endpoint`, `runsync-endpoint`.
- DESTRUCTIVE/data-loss, double-confirm: `delete-pod` (this IS terminate — there is no separate terminate-pod), `delete-network-volume`, `delete-endpoint`, `delete-template`.
- Encouraged, single ack: `stop-pod` (saves money).
- Read-only, no confirm: `list-pods`, `get-pod`, `list-gpu-types`, `list-data-centers`, `list-templates`, `list/get-network-volume`, `list/get-endpoint`, `endpoint-health`, `get-job-status`.
Note: network volume is pinned to a `dataCenterId` — pod must launch in the same DC. See [[compute-constraint]] and [[kaggle-mcp]].