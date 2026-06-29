"""M1 completion smoke — all THREE scoring paths on one dataset, into one traceable JSON.

Proves locally (Mac, CPU) that mode A (likelihood, fine-tuned) + mode B (prompted expected-value,
frozen instruct) + a classical baseline (IForest) all run on the same breastw split and that the
result is written through our `anodet` traceability core with full RunMetadata. Numbers are smoke
quality (tiny steps / few perms / subsampled), not the gate.

Run:  uv run python scripts/smoke_pipeline.py
"""
import os
import sys
import tempfile
import types
import warnings

warnings.filterwarnings("ignore")
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["WANDB_DISABLED"] = "true"
for k, v in {"LOCAL_RANK": "0", "RANK": "0", "WORLD_SIZE": "1",
             "MASTER_ADDR": "127.0.0.1", "MASTER_PORT": "29501"}.items():
    os.environ.setdefault(k, v)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(REPO, "third_party", "AnoLLM")
sys.path.insert(0, SUB)   # fork's `src` (data_utils) + `anollm`
sys.path.insert(0, REPO)  # our `anodet` (distinct name -> no clash)
os.chdir(SUB)             # data_utils + adbench expect cwd at the fork root


class Args(types.SimpleNamespace):
    def __contains__(self, k):
        return k in self.__dict__


def serialize_rows(df):
    """AnoLLM-style 'col is value , ...' per row (for the prompted mode B smoke)."""
    cols = list(df.columns)
    out = []
    for _, row in df.iterrows():
        out.append(" , ".join(f"{c} is {row[c]}" for c in cols))
    return out


def mode_b_expected_value(rows, n_levels=10, batch_size=16):
    """Frozen instruct model; expected value over single-digit anomaly-level tokens (0..n_levels-1)."""
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    name = "HuggingFaceTB/SmolLM-135M-Instruct"
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float32).eval()
    digit_ids = [tok.encode(str(d), add_special_tokens=False)[0] for d in range(n_levels)]
    levels = np.arange(n_levels)

    def build(r):
        msg = [
            {"role": "system", "content": "You are a security anomaly detector."},
            {"role": "user", "content": f"Record: {r}\nHow anomalous is this record on a scale of "
                                        f"0 (normal) to {n_levels-1} (highly anomalous)? Answer with a single digit."},
        ]
        return tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)

    prompts = [build(r) for r in rows]
    scores = []
    with torch.no_grad():
        for i in range(0, len(prompts), batch_size):
            chunk = prompts[i:i + batch_size]
            enc = tok(chunk, return_tensors="pt", padding=True)
            logits = model(**enc).logits
            # last non-pad position per row
            last = enc["attention_mask"].sum(1) - 1
            for b in range(len(chunk)):
                lp = logits[b, last[b]][digit_ids]  # logits over the 10 digit tokens
                p = torch.softmax(lp.float(), dim=-1).numpy()
                scores.append(float((p * levels).sum()))
    return np.asarray(scores)


def main():
    import time

    import numpy as np
    import torch.distributed as dist
    from pyod.models.iforest import IForest

    import anodet  # noqa: F401  (our package; proves no clash with fork's `src`)
    from anodet.metrics import auprc, auroc, recall_at_fpr
    from anodet.utils.io import atomic_write_json
    from anodet.utils.run_metadata import capture_env

    if not dist.is_initialized():
        dist.init_process_group(backend="gloo", rank=0, world_size=1)

    from anollm import AnoLLM
    from src.data_utils import get_max_length_dict, get_text_columns, load_data

    ds = "breastw"
    args = Args(dataset=ds, setting="semi_supervised", data_dir="data", n_splits=5, split_idx=0,
                train_ratio=0.5, seed=42, binning="standard", n_buckets=10, remove_feature_name=False)
    X_train, X_test, y_train, y_test = load_data(args)

    # smoke subsample of the test set (keeps mode-B CPU pass fast); fixed seed
    rs = np.random.RandomState(0)
    idx = rs.choice(len(X_test), size=min(120, len(X_test)), replace=False)
    Xte = X_test.reset_index(drop=True).loc[idx].reset_index(drop=True)
    yte = np.asarray(y_test)[idx]
    results = {}

    # --- classical baseline: IForest (pyod 2.0.1) ---
    clf = IForest().fit(X_train.values)
    s_if = clf.decision_function(Xte.values)
    results["iforest"] = {"auroc": auroc(yte, s_if), "auprc": auprc(yte, s_if),
                          "recall_at_1pct_fpr": recall_at_fpr(yte, s_if, 0.01)}

    # --- mode A: likelihood (fine-tune instruct base; smoke = tiny steps) ---
    t0 = time.time()
    m = AnoLLM("HuggingFaceTB/SmolLM-135M", experiment_dir=tempfile.mkdtemp(),
               batch_size=8, efficient_finetuning="", max_length_dict=get_max_length_dict(ds),
               textual_columns=get_text_columns(ds), max_steps=10, learning_rate=5e-5,
               bf16=False, fp16=False, use_cpu=True, report_to=[])
    m.model = m.model.float()
    with tempfile.TemporaryDirectory() as dtmp:
        m.fit(X_train, X_train.columns.to_list(), use_wandb=False, processed_data_dir=dtmp)
        s_a = m.decision_function(Xte, n_permutations=2, batch_size=8, device="cpu").mean(axis=1)
    results["mode_a_likelihood"] = {"auroc": auroc(yte, s_a), "auprc": auprc(yte, s_a),
                                    "r_permutations": 2, "max_steps": 10}
    mode_a_secs = time.time() - t0

    # --- mode B: prompted expected-value (frozen instruct) ---
    s_b = mode_b_expected_value(serialize_rows(Xte))
    results["mode_b_prompted"] = {"auroc": auroc(yte, s_b), "auprc": auprc(yte, s_b),
                                  "scorer": "expected_value_over_digits"}

    payload = {
        "key": "smoke__breastw__all-three-paths",
        "status": "complete",
        "dataset": ds, "n_test_scored": int(len(yte)), "test_anomaly_rate": float(yte.mean()),
        "metrics_by_path": results,
        "smoke": True,
        "timing": {"mode_a_secs": round(mode_a_secs, 1)},
        "run_metadata_env": capture_env(engine="hf"),
    }
    out = os.path.join(REPO, "results", "raw", "smoke", "breastw_all_three.json")
    atomic_write_json(out, payload)

    print("\n=== M1 pipeline smoke (breastw, subsample=%d, no-skill=%.3f) ===" % (len(yte), yte.mean()))
    for k, v in results.items():
        print(f"  {k:22s} AUROC={v['auroc']:.3f} AUPRC={v['auprc']:.3f}")
    print(f"  written -> {out}")
    print("  all three scoring paths ran + landed in one traceable JSON ✓")


if __name__ == "__main__":
    main()
