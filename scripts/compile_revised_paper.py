#!/usr/bin/env python3
"""Regenerate paper figures, sync to draft_v1_revised, compile PDF, verify.

Usage:
    uv run python scripts/compile_revised_paper.py [--max-iter 5]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper" / "draft_v1_revised"
FIG_SYNC = {
    "exp2_cd_diagram.png": "fig_cd.png",
    "exp3_security_bars.png": "fig_security.png",
    "exp4_ordering.png": "fig_ordering.png",
    "exp5_pareto.png": "fig_pareto.png",
}


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"[compile] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def regenerate_figures() -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    for script in ("scripts/exp5_pareto.py", "scripts/m6_figures.py", "scripts/make_figures.py"):
        subprocess.run([sys.executable, script], cwd=ROOT, env=env, check=True)


def sync_figures() -> None:
    src_dir = ROOT / "results" / "figures"
    dst_dir = PAPER / "figures"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in FIG_SYNC.items():
        src = src_dir / src_name
        if not src.exists():
            raise FileNotFoundError(f"missing figure source: {src}")
        shutil.copy2(src, dst_dir / dst_name)
        print(f"[compile] synced {src_name} -> figures/{dst_name}")


def compile_pdf() -> Path:
    tex = "main_independent.tex"
    log = PAPER / "main_independent.log"
    for pass_i, cmd in enumerate(
        [
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex],
            ["bibtex", "main_independent"],
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex],
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex],
        ],
        start=1,
    ):
        print(f"[compile] pdflatex/bibtex pass {pass_i}")
        _run(cmd, cwd=PAPER)
    return log


def verify(log: Path, pdf: Path, *, max_pages: int) -> list[str]:
    issues: list[str] = []
    text = log.read_text(encoding="utf-8", errors="replace")
    if "LaTeX Error" in text:
        issues.append("LaTeX errors in log")
    if re.search(r"(Citation|Reference).*undefined", text):
        issues.append("undefined citations/references")
    overfull = len(re.findall(r"Overfull \\hbox", text))
    if overfull:
        issues.append(f"{overfull} overfull hbox warnings")

    if not pdf.exists():
        issues.append(f"missing PDF: {pdf}")
        return issues

    proc = subprocess.run(
        ["pdfinfo", str(pdf)],
        capture_output=True,
        text=True,
        check=False,
    )
    m = re.search(r"Pages:\s+(\d+)", proc.stdout)
    pages = int(m.group(1)) if m else -1
    print(f"[compile] PDF pages={pages}")
    if pages < 1:
        issues.append("could not read page count")
    elif pages > max_pages:
        issues.append(f"page count {pages} exceeds limit {max_pages}")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile revised independent paper with checks")
    ap.add_argument("--max-iter", type=int, default=5)
    ap.add_argument("--max-pages", type=int, default=8)
    args = ap.parse_args()

    pdf = PAPER / "main_independent.pdf"
    for iteration in range(1, args.max_iter + 1):
        print(f"========== iteration {iteration} ==========")
        regenerate_figures()
        sync_figures()
        log = compile_pdf()
        issues = verify(log, pdf, max_pages=args.max_pages)
        if not issues:
            print(f"[compile] PASS (iteration {iteration})")
            return 0
        print(f"[compile] issues: {', '.join(issues)}")
    print(f"[compile] FAIL after {args.max_iter} iterations")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
