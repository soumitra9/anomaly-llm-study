"""Exp 6 — two-stage classical->LLM triage/rerank.

Takes a cheap classical detector's top-K candidates, re-scores with the best LLM/mode, and
compares Recall@1%FPR / Precision@top-N of the two-stage system vs classical-alone and
LLM-alone at matched cost. Reuses already-computed prompted scores. (Built in M4.)
"""
