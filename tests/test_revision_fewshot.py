"""RV2 few-shot: exemplar block + fleet cell construction (no model download)."""
import numpy as np
import pandas as pd

import scripts.revision_fewshot as rv2
from anodet.scoring.prompted import _build_prompt, _normal_exemplar_block


class _Tok:
    chat_template = None


def test_normal_exemplar_block_deterministic():
    X = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    y = np.array([0, 0, 1])
    b1 = _normal_exemplar_block(X, y, k=2, seed=0)
    b2 = _normal_exemplar_block(X, y, k=2, seed=0)
    assert b1 == b2
    assert "Example normal record 1:" in b1
    assert "Example normal record 2:" in b2
    assert "a is 3" not in b1  # anomaly row never used


def test_build_prompt_zero_shot_unchanged():
    tok = _Tok()
    p0 = _build_prompt(tok, "col is 1", 10, 0, "")
    assert "Record: col is 1" in p0
    assert "Example normal" not in p0


def test_build_prompt_with_exemplars():
    tok = _Tok()
    block = "Example normal record 1: x is 1"
    p = _build_prompt(tok, "y is 2", 10, 0, block)
    assert block in p
    assert "Record: y is 2" in p


def test_rv2_build_cells():
    cells = rv2.build_cells(["breastw"], [0, 1])
    assert len(cells) == 2
    assert all(c["mode"] == "prompted-fewshot" for c in cells)
