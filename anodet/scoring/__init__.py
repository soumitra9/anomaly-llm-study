"""Scoring modes.

- mode A (likelihood): fine-tune the instruct checkpoint with LoRA, then NLL-score over r
  column permutations — wraps the AnoLLM fork (added in M2; needs transformers).
- mode B (prompted): the same instruct weights, frozen; expected-value over verbalizer-token
  logprobs. The engine-free numeric helpers live in `prompted_score` (M0, unit-tested); the
  transformers-backed runner is added in M2.
"""
