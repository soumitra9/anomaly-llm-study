# Response to Reviewers

We thank the reviewer for a careful and constructive review, and for the Weak Accept recommendation. Below we respond to each recommended change. Section and table references are to the revised manuscript. Two changes required new computation (a stronger few-shot prompted baseline, and the previously missing UNSW-NB15 likelihood arm); the rest are scoping and presentation changes. The revised paper remains within the page limit.

## 1. Strengthen the prompted baseline, or narrow the "likelihood dominates prompted" claim

Both. We added a stronger prompted baseline (normals-only few-shot, three exemplars) on eight ODDS datasets with Qwen2.5-3B-Instruct. Few-shot prompting raised mean AUROC from 0.468 (zero-shot) to 0.759, closing about 95% of the gap to likelihood scoring (0.773 on the same eight datasets). The residual 0.014 difference is not statistically significant (paired Wilcoxon on eight dataset means, p=0.64, n=8). We therefore narrowed the claim throughout: likelihood outperforms the *zero-shot expected-value* prompted baseline used in the main A/B, but is statistically indistinguishable from a few-shot prompted baseline on these datasets. See Section IV-B (Scoring Mode), the abstract, and the Mode B description in Section III.

## 2. Address the checkpoint confound (2x2, or expand DA1)

We rely on the pre-registered DA1 control rather than a new 2x2. DA1 LoRA-fine-tunes the *instruct* checkpoint and scores it by likelihood on eight ODDS datasets, isolating scoring mode from the base-vs-instruct difference; the effect is bounded at mean |dAUROC| = 0.0054 (Sections III and III-E). We state explicitly in the Limitations that this bounds but does not fully eliminate the confound.

## 3. Add the Qwen2.5-3B likelihood arm on UNSW-NB15

Done, and it changes the security narrative. Qwen2.5-3B likelihood scoring on UNSW-NB15 reaches recall@1%FPR 0.302 (mean over three seeds), exceeding every classical detector (KNN 0.189, IForest 0.188, ECOD 0.161, PCA 0.099) and the prompted baseline (0.151). This reverses the ordering seen on credit-card fraud, where classical detectors dominate. On the secondary AUPRC-gain view the UNSW ordering is mixed. We updated Table III (now reports the UNSW likelihood cell), the regime-summary table (Table I, split into per-dataset rows), the abstract, Section IV-E, and the Discussion. We frame this strictly per-dataset and draw no cross-dataset conclusion.

## 4. Expand the security panel beyond two datasets

We agree this is the right long-term step and have kept it as future work. We note that with only two datasets, and now with the two datasets pointing in opposite directions at fixed FPR, no cross-dataset statistic is possible; we make no generalization claim and say so in the Limitations and Future Work.

## 5. Increase seeds for the ablations, or label them exploratory

We label them exploratory. The semantic-name and serialization-order ablations use n=3 seed pairs (minimum achievable Wilcoxon p=0.25); the manuscript reports them as descriptive, exploratory evidence and draws no conclusion from them (Sections IV-D, IV-F, and Limitations).

## 6. Investigate the C3 failure

We now report the eleven out-of-band datasets (cardio, covertype, ecoli, letter, optdigits, pendigits, satellite, vowels, wbc, wine, yeast) and note that the deviations are bidirectional (our AUROC exceeds the reference on some, falls short on others), so the shortfall is not a uniform downward bias. We give two candidate explanations consistent with our controls: the released AnoLLM fork differing from the published configuration (a grad-accumulation / effective-batch test moved letter and satellite by only 0.02-0.03 AUROC, insufficient to close the gap), and LoRA fine-tuning instability on small tabular datasets. See Section IV-A.

## 7. State the scale caveat prominently; add a 7B point if feasible

We added a prominent scale-limitation sentence next to the scale claim (Section IV, Model Scale): the null on model scale is bounded to the 360M-3B range, and 7B+ models are untested, so the claim should not be extrapolated. A 7B-scale run was not feasible within the compute budget for this revision; we flag it as future work.

## 8. Test more than one domain ordering, or state the single-instance caveat

We added the caveat next to the ordering result (Section IV-F): a single hand-designed ordering per dataset cannot rule out that some other informed ordering helps; we tested one domain ordering, not the space of informed orderings.

## 9. Add a compute/cost table alongside Fig. 4

Added (Table IV, next to the Pareto figure). It reports approximate wall time per 1,000 test rows per method with an explicit provenance column: the ODDS likelihood and prompted timings are RUNLOG-level aggregate approximations (flat per-mode constants), while the triage timing is measured per cell. We were transparent that per-dataset per-mode wall clock is not available for the ODDS likelihood/prompted modes, consistent with the approximation disclosure already in Sections IV and V.

## 10. Define "regime-dependent"; surface the Table III footnote

We added a crisp definition of "regime-dependent" at first use in the Introduction: whether LLM scoring helps is determined jointly by the scoring mode, evaluation metric, and data regime (imbalance and alert budget), not by model family or size alone. The former Table III footnote (likelihood evaluated on credit-card only) is now moot because the UNSW likelihood arm has been added; the caption reflects that both datasets are covered.

---

We believe these changes address the substantive concerns while keeping every claim scoped to the datasets, metrics, and methods actually tested. We thank the reviewer again for feedback that materially improved the paper.
