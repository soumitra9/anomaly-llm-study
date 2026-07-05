---
name: compute-constraint
description: No local GPU — dictates a hosted-API + small-CPU-model design split for the two scoring modes
metadata: 
  node_type: memory
  type: project
  originSessionId: f0312d5f-9fe4-4ce2-a145-6b443f9d0b23
---

User has NO local GPU (confirmed 2026-06-28). All large-model inference must go through hosted APIs (OpenRouter/Together/Fireworks/DeepInfra). User named Qwen, GLM (~5.x), and Meta/Llama as candidate open models.

**Decision: model-generation axis recast around SCORING MODE (user's choice), which the no-GPU constraint reinforces:**

- **Prompted suspiciousness scoring (mode b)** = PRIMARY axis. Only needs text generation, so the FULL ladder of modern hosted open models is usable (e.g. Qwen3.5, GLM-5/5.1, Llama 4, plus small CPU-runnable ones). This is the axis AnoLLM never tested and the one that should scale with capability.

- **Likelihood scoring (mode a, AnoLLM's NLL)** = needs token log-probs over the SUPPLIED serialized row (cumulative prompt NLL), not just generated-token logprobs. Most hosted chat APIs expose logprobs only on GENERATED tokens; prompt/echo logprobs are rare. So mode (a) is restricted to: (i) small models run locally on CPU (SmolLM, Qwen3-0.6B/1.7B, Gemma3-4B, Phi-4-mini via transformers/llama.cpp — exact NLL, slow but controllable), and/or (ii) the subset of completion endpoints supporting echo+logprobs. Document this split explicitly per the brief's §8.2 step 2 — never silently substitute.

**Scale/cost watch:** credit-card fraud = 284k rows; r=21 permutations multiplies cost. Need a documented, principled TEST SUBSAMPLE (e.g. all anomalies + stratified normals preserving realistic-but-tractable imbalance) for API-scored runs. Permutation averaging (r) is a likelihood-mode trick; prompted mode uses few/single pass.

2026 model landscape (verify exact HF/provider tags at run time; naming moves fast): DeepSeek V4, GLM-5/5.1 (MIT), Qwen3.5 (Apache-2.0), Llama 4, Kimi K2.6. Small/CPU: Phi-4-mini 3.8B (fits 8GB, ~15-20 tok/s on M1 Air), Gemma 3 4B (4.2GB RAM), Qwen3 small, Mistral Small 3. project_idea.md §6's Tier-1/2 lists are now stale. See [[anollm-verified-facts]].
