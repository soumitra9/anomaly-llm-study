"""M1 local smoke test — mode A (likelihood) end-to-end on the Mac, single-process, CPU.

Drives the AnoLLM *class* directly (bypassing the CUDA/DDP-only train_anollm.py): load -> bin ->
split -> fine-tune (few steps, fp32, CPU) -> NLL-score over permutations -> AUROC. Goal is to prove
the pipeline runs and produces sane numbers locally before any GPU spend — NOT to hit the gate.

Run:  uv run python scripts/smoke_exp1.py
(The script chdir's into third_party/AnoLLM so the fork's `anollm` and `src.data_utils` resolve;
AUROC uses sklearn inline to avoid the `src` package-name clash with our own src/ — that import
architecture is resolved properly in M2.)
"""
import os
import sys
import tempfile
import types
import warnings

warnings.filterwarnings("ignore")
# adbench drags in TensorFlow 2.21 + Keras 3, which breaks transformers' lazy TF integration
# (it wants tf-keras). We only use the torch path, so tell transformers to ignore TF entirely.
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["WANDB_DISABLED"] = "true"
# AnoLLMTrainer.get_train_dataloader is DDP-hardwired (DistributedSampler + LOCAL_RANK). Run it
# single-process by faking a 1-rank world (gloo group, CPU-friendly). The gate on Kaggle uses 1 GPU
# the same way; full multi-GPU DDP is not needed for our scale.
os.environ.setdefault("LOCAL_RANK", "0")
os.environ.setdefault("RANK", "0")
os.environ.setdefault("WORLD_SIZE", "1")
os.environ.setdefault("MASTER_ADDR", "127.0.0.1")
os.environ.setdefault("MASTER_PORT", "29500")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(REPO, "third_party", "AnoLLM")
os.chdir(SUB)
sys.path.insert(0, SUB)  # fork's `src` + `anollm` (our package is NOT on path here)


class Args(types.SimpleNamespace):
    """load_data() needs both attribute access (args.x) and membership ('x' in args)."""

    def __contains__(self, k):
        return k in self.__dict__


def main():
    import numpy as np
    import torch.distributed as dist
    from sklearn.metrics import average_precision_score, roc_auc_score

    if not dist.is_initialized():
        dist.init_process_group(backend="gloo", rank=0, world_size=1)

    from anollm import AnoLLM
    from src.data_utils import get_max_length_dict, get_text_columns, load_data

    dataset = "breastw"
    args = Args(
        dataset=dataset, setting="semi_supervised", data_dir="data",
        n_splits=5, split_idx=0, train_ratio=0.5, seed=42,
        binning="standard", n_buckets=10, remove_feature_name=False,
    )
    X_train, X_test, y_train, y_test = load_data(args)
    print(f"[data] {dataset}: train(normals)={X_train.shape} test={X_test.shape} "
          f"test_anomaly_rate={float(np.mean(y_test)):.3f} cols={list(X_train.columns)}")

    model = AnoLLM(
        "HuggingFaceTB/SmolLM-135M",
        experiment_dir=tempfile.mkdtemp(prefix="anollm_smoke_"),
        batch_size=8,
        efficient_finetuning="",          # full FT (faithful Exp-1 recipe on the tiny model)
        max_length_dict=get_max_length_dict(dataset),
        textual_columns=get_text_columns(dataset),
        # train_kwargs -> TrainingArguments:
        max_steps=20,                     # SMOKE ONLY (gate uses 2000)
        learning_rate=5e-5,
        bf16=False, fp16=False, use_cpu=True,  # CPU + fp32 for a safe local smoke
        report_to=[],
    )
    model.model = model.model.float()     # bf16 checkpoint -> fp32 for CPU

    with tempfile.TemporaryDirectory() as dtmp:
        model.fit(X_train, X_train.columns.to_list(), use_wandb=False, processed_data_dir=dtmp)
        scores = model.decision_function(X_test, n_permutations=4, batch_size=8, device="cpu")

    agg = scores.mean(axis=1)             # mean NLL over permutations (higher = more anomalous)
    auroc = roc_auc_score(y_test, agg)
    auprc = average_precision_score(y_test, agg)
    print(f"[result] {dataset} SmolLM-135M (20 steps, CPU, r=4): "
          f"AUROC={auroc:.3f} AUPRC={auprc:.3f} (no-skill={float(np.mean(y_test)):.3f})")
    print("[smoke] mode-A pipeline ran end-to-end on Mac ✓ "
          "(numbers are not the gate — 20 steps only)")


if __name__ == "__main__":
    main()
