# Method (draft — framing only)

## Row serialization
Each row is rendered to text as `col is value , ...` (AnoLLM-style). Numerical columns use AnoLLM's "standard"
binning (rescale + round); textual columns are kept verbatim. **The same serialization is shared across both
scoring modes**, so a mode A/B comparison varies only the scoring mechanism, not the input text. Column order is
held fixed within a comparison and varied only in the dedicated ordering ablation (RQ5).

## Two scoring modes (same model weights)
- **Mode A — likelihood.** The backbone is fine-tuned (LoRA) on the normal training rows; a row's anomaly
  score is the **mean negative log-likelihood over `r` random column permutations** (AnoLLM Eqn 5), with
  per-column length normalization for textual fields and column-name tokens excluded. We cache the full
  per-permutation NLL matrix, so the r-sensitivity curve (r = 5/10/21) is recovered post hoc for free.
- **Mode B — prompted (expected value).** The *frozen instruction-tuned* sibling of the same model reads the
  serialized row and a short schema, and we compute a continuous score as the **expected value over a set of
  anomaly-level digit tokens**, `score = Σ_k p(k)·k`, from a single forward pass. This is continuous and
  tie-free (no parse failures); a parsed-integer variant is recorded only for an elicitation-sensitivity
  comparison. Engine is HF Transformers + PEFT throughout (no vLLM), dissolving cross-engine logprob confounds;
  a device/dtype parity check gates any CUDA-vs-MPS comparison.

## Metrics
AUROC (tie-aware) for comparability; **AUPRC reported relative to the no-skill baseline (prevalence)** with
bootstrap CIs; **Precision@top-N** and **Recall@fixed-FPR** (Clopper–Pearson CIs) for the operational,
imbalance-aware view; runtime / VRAM / cost / parse-failure-rate for practicality. On security data, test-set
negatives are subsampled and **importance-reweighted** to recover the true-base-rate metrics.

## Statistics
ODDS (30 datasets): Friedman omnibus → Nemenyi critical-difference diagram; pre-registered pairwise claims via
Holm-corrected Wilcoxon signed-rank. Security (2–3 datasets): per-dataset bootstrap CIs and effect sizes (no
Friedman). One confirmatory test per research question under Holm–Bonferroni family-wise control; everything
else is labeled exploratory.
