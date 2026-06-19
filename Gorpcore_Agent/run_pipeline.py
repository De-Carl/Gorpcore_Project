"""
Pipeline orchestrator — chains the full curation Agent end to end.

Course bonus item #1 asks for a *complete* Agent that automates the repetitive
work (collect -> validate -> record -> label) while keeping human oversight. The
individual nodes already exist as standalone scripts; this orchestrator runs them
in the correct order, stops on the first failure, writes a single run log, and
pauses at the human-review gate so a person owns the final curation decision.

Flow (collect -> validate -> record -> label, per the course brief):

    [COLLECT]  ->  data_loader  ->  Node A  ->  Node B  ->  Node C  --> [HUMAN GATE] --> Node D
    (scrapers)     (index)          (quality)   (vision)    (cross-check)                (consolidate)

Collection is opt-in (`--collect`): the scrapers use Playwright and need a
browser, network, and a logged-in session (human-supervised), so by default the
pipeline reuses the existing Dataset v0 — the normal reproducible path. When
`--collect` is set, each platform scraper runs first; one platform failing
(e.g. JD is anti-scraped) does not abort the others.

Usage:
    python run_pipeline.py                 # use existing Dataset v0; pause for manual review
    python run_pipeline.py --collect       # ALSO run the scrapers first (browser + login)
    python run_pipeline.py --auto-review   # auto-fill review decisions (complete_human_review.py)
    python run_pipeline.py --skip-vision   # skip Node B (no Qwen-VL-Max API key)
    python run_pipeline.py --limit 20      # annotate only first 20 images in Node B
    python run_pipeline.py --fuse          # also run evidence fusion + figures afterwards

Each node still runs as its own process (same as running the scripts by hand),
so node state stays isolated and any node can also be run on its own.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_ROOT.parent
DATASET_ROOT = PROJECT_ROOT / "Dataset"
RUN_LOG = AGENT_ROOT / "output" / "pipeline_run_log.json"

# Stage 0 — collection. Each platform scraper is (script, label). They use
# Playwright and a logged-in session, so this stage is human-supervised.
SCRAPERS = [
    (DATASET_ROOT / "xhs" / "xhs.py", "Collect — Xiaohongshu"),
    (DATASET_ROOT / "bilibili" / "bilibili_scraper.py", "Collect — Bilibili"),
    (DATASET_ROOT / "taobao" / "taobao_review_scraper.py", "Collect — Taobao"),
    (DATASET_ROOT / "jd" / "jd_review_scraper.py", "Collect — JD"),
]


def run_step(name: str, script: Path, args: list[str], cwd: Path) -> dict:
    """Run one pipeline step as a subprocess; return a log entry. Raise on failure."""
    cmd = [sys.executable, str(script), *args]
    print(f"\n{'=' * 70}\n▶ {name}\n  {' '.join(cmd)}\n{'=' * 70}")
    started = datetime.now()
    result = subprocess.run(cmd, cwd=str(cwd))
    finished = datetime.now()
    entry = {
        "step": name,
        "script": str(script.relative_to(PROJECT_ROOT)),
        "args": args,
        "returncode": result.returncode,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "duration_sec": round((finished - started).total_seconds(), 1),
    }
    if result.returncode != 0:
        print(f"\n✗ Step '{name}' failed (exit {result.returncode}). Stopping pipeline.")
        raise SystemExit(result.returncode)
    print(f"✓ {name} done in {entry['duration_sec']}s")
    return entry


def run_collection() -> list[dict]:
    """Stage 0 — run each platform scraper. Tolerant: one platform failing
    (e.g. JD blocked) is logged but does not abort the rest."""
    print(f"\n{'#' * 70}\n# STAGE 0 — COLLECTION (browser + logged-in session required)\n{'#' * 70}")
    entries: list[dict] = []
    for script, label in SCRAPERS:
        if not script.exists():
            print(f"⏭  {label}: scraper not found ({script.name}), skipping.")
            entries.append({"step": label, "skipped": True, "reason": "scraper not found"})
            continue
        cmd = [sys.executable, str(script)]
        print(f"\n{'=' * 70}\n▶ {label}\n  {' '.join(cmd)}\n{'=' * 70}")
        started = datetime.now()
        result = subprocess.run(cmd, cwd=str(script.parent))
        ok = result.returncode == 0
        entries.append({
            "step": label,
            "script": str(script.relative_to(PROJECT_ROOT)),
            "returncode": result.returncode,
            "ok": ok,
            "started_at": started.isoformat(timespec="seconds"),
        })
        print(f"{'✓' if ok else '✗'} {label} (exit {result.returncode})"
              + ("" if ok else " — continuing with other platforms"))
    return entries


def human_review_gate(auto_review: bool) -> dict:
    """The human-in-the-loop checkpoint between Node C and Node D."""
    review_pool = AGENT_ROOT / "output" / "review_pool.csv"
    if auto_review:
        return run_step(
            "Human review (scripted, auditable)",
            AGENT_ROOT / "complete_human_review.py",
            [],
            AGENT_ROOT,
        )
    print(f"\n{'=' * 70}\n■ HUMAN REVIEW GATE\n{'=' * 70}")
    print(
        f"Node C has written the review pool:\n  {review_pool}\n\n"
        "Open it and fill the manual columns (Manual_Decision, Manual_Category,\n"
        "Manual_Notes, Corrected_*, Reviewer, Reviewed_At), then return here.\n"
        "(Or re-run with --auto-review to apply the scripted review decisions.)"
    )
    try:
        input("\nPress Enter once review_pool.csv is filled, to continue to Node D… ")
    except EOFError:
        print("Non-interactive session: skipping pause, continuing to Node D.")
    return {"step": "Human review (manual)", "review_pool": str(review_pool.relative_to(PROJECT_ROOT))}


def main() -> None:
    p = argparse.ArgumentParser(description="Run the full Gorpcore curation pipeline.")
    p.add_argument("--collect", action="store_true", help="Run the platform scrapers first (browser + login).")
    p.add_argument("--skip-vision", action="store_true", help="Skip Node B (no API key).")
    p.add_argument("--limit", type=int, default=None, help="Limit Node B to first N images.")
    p.add_argument("--auto-review", action="store_true", help="Auto-fill review decisions.")
    p.add_argument("--fuse", action="store_true", help="Also run evidence fusion + figures.")
    args = p.parse_args()

    log: list[dict] = []
    if args.collect:
        log.extend(run_collection())
    else:
        print("\n⏭  Skipping collection — using existing Dataset v0 (pass --collect to re-scrape).")
    log.append(run_step("Data loader (image index)", AGENT_ROOT / "data_loader.py", [], AGENT_ROOT))
    log.append(run_step("Node A — Quality gatekeeper", AGENT_ROOT / "node_a_quality_gatekeeper.py", [], AGENT_ROOT))

    if args.skip_vision:
        print("\n⏭  Skipping Node B (vision annotation) — using existing labels / text heuristics.")
        log.append({"step": "Node B — Vision annotator", "skipped": True})
    else:
        b_args = ["--limit", str(args.limit)] if args.limit is not None else []
        log.append(run_step("Node B — Vision annotator", AGENT_ROOT / "node_b_vision_annotator.py", b_args, AGENT_ROOT))

    log.append(run_step("Node C — Semantic cross-check", AGENT_ROOT / "node_c_semantic_cross_checker.py", [], AGENT_ROOT))
    log.append(human_review_gate(args.auto_review))
    log.append(run_step("Node D — Human review consolidation", AGENT_ROOT / "node_d_human_reviewer.py", [], AGENT_ROOT))

    if args.fuse:
        fusion = PROJECT_ROOT / "Evidence_fusion_visual_dispalys" / "member_e_feature_builder.py"
        log.append(run_step("Evidence fusion + feature database", fusion, [], fusion.parent))

    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    RUN_LOG.write_text(
        json.dumps({"run_at": datetime.now().isoformat(timespec="seconds"), "steps": log},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n{'=' * 70}\n✓ Pipeline complete. Run log → {RUN_LOG.relative_to(PROJECT_ROOT)}\n{'=' * 70}")


if __name__ == "__main__":
    main()
