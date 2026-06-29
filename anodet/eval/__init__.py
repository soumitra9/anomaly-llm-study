"""Experiment runners (Exp 1-6) + the Cartesian-loop grid runner.

The runner expands `configs/` axis-lists into (model, mode, dataset, seed) cells, skips
already-complete cells (resumable), and writes per-cell JSON via `src.utils.run_metadata`.
The completion manifest reconciles actual vs expected before any aggregation.
"""
