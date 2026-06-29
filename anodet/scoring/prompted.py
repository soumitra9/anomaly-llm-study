"""Mode B (prompted) — production runner.

A FROZEN instruct model scores each serialized row by the **expected value** over a small set of
"anomaly level" digit tokens: `score = Σ_k p(k)·k` (PLAN §4b). This is continuous and tie-free from a
single forward pass — no generation loop, no parse failures. A parsed-integer fallback is also provided
(for the ceiling/elicitation-sensitivity comparison) and reports a parse-failure rate.

Same row serialization as mode A (binned "col is value , ..."), so the A/B differs only in scoring.
Engine-free numerics live in `prompted_score` (unit-tested); this module adds the transformers I/O.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from anodet import _fork
from anodet.scoring.prompted_score import expected_score, parse_failure_rate, parse_int_score

# Instruct aliases (mode B needs instruction-followers; base SmolLM is poor at this — use -Instruct)
INSTRUCT_ALIASES = {
    "smol-instruct": "HuggingFaceTB/SmolLM-135M-Instruct",
    "smol-360-instruct": "HuggingFaceTB/SmolLM-360M-Instruct",
    "qwen3-4b-instruct": "Qwen/Qwen2.5-3B-Instruct",  # placeholder; verify exact Qwen3 tag at run time
}

_SYSTEM = "You are a security anomaly detector."


def serialize_rows(df: pd.DataFrame) -> list[str]:
    """AnoLLM-style 'col is value , ...' per row (binning already applied upstream)."""
    cols = list(df.columns)
    return [" , ".join(f"{c} is {row[c]}" for c in cols) for _, row in df.iterrows()]


def _build_prompt(tok, row_text: str, n_levels: int, paraphrase: int = 0) -> str:
    asks = [
        f"Record: {row_text}\nHow anomalous is this record on a scale of 0 (normal) to "
        f"{n_levels-1} (highly anomalous)? Answer with a single digit.",
        f"Given the record: {row_text}\nRate its anomalousness from 0 (perfectly normal) to "
        f"{n_levels-1} (extremely suspicious). Reply with one digit only.",
        f"{row_text}\nOn a 0-{n_levels-1} scale, how suspicious is this record? One digit.",
    ]
    msg = [{"role": "system", "content": _SYSTEM},
           {"role": "user", "content": asks[paraphrase % len(asks)]}]
    if tok.chat_template:
        return tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
    return _SYSTEM + "\n" + asks[paraphrase % len(asks)] + "\nAnswer: "


def run_prompted(
    model: str,
    X_test: pd.DataFrame,
    *,
    n_levels: int = 10,
    batch_size: int = 16,
    device: Optional[str] = None,
    paraphrase: int = 0,
    also_parse_integer: bool = False,
) -> dict:
    """Expected-value prompted scores. Returns {'scores','distinct_levels','device',
    optional 'parsed_scores','parse_failure_rate'}."""
    _fork.setup_env()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    name = INSTRUCT_ALIASES.get(model, model)
    device = _fork.pick_device(device)
    tok = AutoTokenizer.from_pretrained(name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"  # causal LM: keep the real last token at the end for next-token logits
    dtype = torch.bfloat16 if device == "cuda" else torch.float32
    lm = AutoModelForCausalLM.from_pretrained(name, torch_dtype=dtype).to(device).eval()

    # first-token id for each level digit (single-token for 0..9 in these tokenizers)
    digit_ids = [tok.encode(str(d), add_special_tokens=False)[0] for d in range(n_levels)]
    levels = np.arange(n_levels)

    prompts = [_build_prompt(tok, r, n_levels, paraphrase) for r in serialize_rows(X_test)]
    scores, parsed = [], []
    with torch.no_grad():
        for i in range(0, len(prompts), batch_size):
            enc = tok(prompts[i:i + batch_size], return_tensors="pt", padding=True).to(device)
            logits = lm(**enc).logits[:, -1, :]  # left-padded -> last col is the next-token position
            for b in range(logits.shape[0]):
                lp = logits[b, digit_ids].float().cpu().numpy()
                scores.append(expected_score(levels, lp))
            if also_parse_integer:
                gen = lm.generate(**enc, max_new_tokens=4, do_sample=False,
                                  pad_token_id=tok.pad_token_id)
                for b in range(gen.shape[0]):
                    txt = tok.decode(gen[b, enc["input_ids"].shape[1]:], skip_special_tokens=True)
                    parsed.append(parse_int_score(txt, 0, n_levels - 1))

    s = np.asarray(scores)
    out = {"scores": s, "distinct_levels": int(np.unique(np.round(s, 6)).size), "device": device}
    if also_parse_integer:
        out["parsed_scores"] = parsed
        out["parse_failure_rate"] = parse_failure_rate(parsed)
    return out
