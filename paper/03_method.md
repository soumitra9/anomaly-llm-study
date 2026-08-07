# Method (draft — framing only)

## Row serialization
Each row is rendered to text as `col is value , ...` (AnoLLM-style). Numerical columns use AnoLLM's "standard"
binning (rescale + round); textual columns are kept verbatim. **The same serialization is shared across both
scoring modes**, so a mode A/B comparison varies only the scoring mechanism, not the input text. Column order is
held fixed within a comparison and varied only in the dedicated ordering ablation (RQ5).

## Two scoring modes (same model family and size)
- **Mode A — likelihood.** The *base* backbone (e.g., SmolLM-360M, Qwen2.5-3B) is fine-tuned with LoRA on
  the normal training rows; a row's anomaly score is the **mean negative log-likelihood over `r` random column
  permutations** (AnoLLM Eqn 5), with per-column length normalization for textual fields and column-name
  tokens excluded. We cache the full per-permutation NLL matrix, so the r-sensitivity curve (r = 5/10/21) is
  recovered post hoc for free. Checkpoint kind: `base+LoRA`.
- **Mode B — prompted (expected value).** The *frozen instruction-tuned* sibling of the same model family
  (e.g., SmolLM-360M-Instruct, Qwen2.5-3B-Instruct) reads the serialized row and a short schema; we compute
  a continuous score as the **expected value over anomaly-level digit tokens**, `score = Σ_k p(k)·k`, from a
  single forward pass. This is continuous and tie-free. Checkpoint kind: `instruct (frozen)`.

  **Design note:** mode A and mode B differ in both scoring method *and* checkpoint (base+LoRA vs frozen
  instruct). They are the same model *family and size* — not identical weights. To bound this confound we run
  a dissolving arm: LoRA fine-tuning the instruct checkpoint and scoring by likelihood on a subset of ODDS
  (§dissolving-arm). If instruct-likelihood ≈ base-likelihood, the checkpoint difference does not explain the
  A/B gap. Engine is HF Transformers + PEFT throughout (no vLLM).

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

## Confound checks (M3.5, pre-registered in GATE_SPEC.md)

**DA1 — dissolving arm.** Fine-tuning the instruct checkpoint (Qwen2.5-3B-Instruct) instead of the base
yields mean |ΔAUROC| = 0.0054 across 8 ODDS datasets (seed=0, r=5), well below the pre-registered 0.02
tolerance (GATE_SPEC.md §DA1). The checkpoint difference does not explain the likelihood-vs-prompted gap.

**BA1 — binned serialization on credit-card.** Switching credit-card from raw float serialization (Exp 3
protocol) to ODDS-style standard binning changes mean classical AUROC by 0.0012 across four detectors
(iforest/knn/pca/ecod), well below the pre-registered 0.03 tolerance (GATE_SPEC.md §BA1). The serialization
format does not explain the cross-domain AUROC gap. (Note: KNN on the temporal split is evaluated after
dropping the `Time` feature, which encodes temporal order and confounds KNN distance metrics under temporal
splits; the corrected KNN AUROC is 0.932 vs the biased 0.178.)

**T3 — Time feature in temporal split.** The credit-card `Time` column (transaction timestamp) creates a
train/test distribution shift under temporal splits: KNN AUROC collapses from 0.932 (time excluded) to 0.178
(time included). Tree-based detectors (IForest, ECOD) and PCA are robust (|ΔAUROC| < 0.025). All reported
classical credit-card results use the time-excluded protocol (`exp3_security_notime`).
