"""Data loaders + serialization.

Wraps the AnoLLM fork for ODDS load (.mat), numeric "standard" binning, and row->text
serialization + column permutation. New, backend-agnostic loaders for creditcard (Kaggle MCP,
v3) and UNSW-NB15 (nids-datasets Network-Flows subset) expose
`download() -> (path, version_id, content_hash)`. `odds_names` injects recovered UCI column
names onto pima/breastw for the Exp 3b semantic ablation. (Built from M2/M3.)
"""
