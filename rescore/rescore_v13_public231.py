#!/usr/bin/env python3
"""Rescore the EXISTING public-231 native-readout run under JevBench v1.3.

NO NEW RUN. NO CARD. NO SERVER CONTACT.

Inputs are the artefacts of the run that produced 68.41, exactly as they sit:

    tmp/jev-survey/shim/native231d-results.jsonl        (231 rows, raw harness output)
    tmp/jev-survey/shim/score-native-d/per-item.jsonl   (231 scored rows)
    tmp/jev-survey/shim/score-native-d/summary.json     (the v1.2 axis computation)

The v1.2 axis values are RECOMPUTED here from per-item.jsonl and checked against
summary.json; the only thing that changes for v1.3 is Intelligence, which becomes
accuracy above the item-specific uniform-guessing baseline, plus the near-chance
penalty on the composite. Calibration, Speed and Cost are unchanged by v1.3.

Scoring code is the board's own: jevbench.composite_v13 / jevbench.metrics at tag
v1.3.0, extracted verbatim from the board checkout into tmp/rescore13/.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tmp" / "rescore13"))

import jevbench.composite_v13 as C13  # noqa: E402
import jevbench.metrics as M  # noqa: E402
from jevbench.composite_v13 import (  # noqa: E402
    calibration as v13_calibration,
    cost as v13_cost,
    intelligence as v13_intelligence,
    jevbench_score as v13_score,
    speed as v13_speed,
)

SHIM = ROOT / "tmp" / "jev-survey" / "shim"
PER_ITEM = SHIM / "score-native-d" / "per-item.jsonl"
SUMMARY = SHIM / "score-native-d" / "summary.json"
RESULTS = SHIM / "native231d-results.jsonl"
OUT = Path(__file__).resolve().parent / "RESCORE-v1.3-PUBLIC-231.json"

# The assumed Cost of the 68.41 row: the same-weights OpenRouter list price of
# Qwen/Qwen3.8-Flash-Next ($0.15/M input) x our measured input tokens, output
# free because the readout generates nothing. It is an ASSUMPTION, not a tariff
# the operator has accepted -- the board's cost() would raise on our own null.
ASSUMED_PRICE_IN_PER_M = 0.15


def load_jsonl(p: Path):
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def tier_accuracy(rows, tier):
    sub = [r for r in rows if r["tier"] == tier]
    n = len(sub)
    correct = sum(1 for r in sub if r.get("correct"))
    return correct, n, (correct / n if n else None)


def main() -> int:
    rows = load_jsonl(PER_ITEM)
    raw = load_jsonl(RESULTS)
    v12 = json.loads(SUMMARY.read_text())
    print(f"per-item rows: {len(rows)}   raw results rows: {len(raw)}")

    tiers = {}
    tier_detail = {}
    for t in ("easy", "standard", "hard"):
        correct, n, acc = tier_accuracy(rows, t)
        tiers[t] = acc
        tier_detail[t] = {"n_correct": correct, "n_public": n, "accuracy": acc}

    # ---- Intelligence, v1.2 rule (plain weighted accuracy) and v1.3 rule -----
    v12_int = None
    sw = sum(C13.TIER_WEIGHTS[t] for t in tiers if tiers[t] is not None)
    if sw:
        v12_int = sum(C13.TIER_WEIGHTS[t] * 100 * tiers[t]
                      for t in tiers if tiers[t] is not None) / sw
    v13_int = v13_intelligence(tiers)
    chances = {t: C13.TIER_CHANCES[t] for t in tiers}
    chance_corrected = {
        t: C13.chance_corrected_accuracy(tiers[t], C13.TIER_CHANCES[t]) for t in tiers
    }

    # ---- Calibration: v1.3 leaves this formula alone. Recompute it anyway. ---
    valid = [r for r in rows if r["tier"] == "hard" and r.get("valid") and r.get("probs")]
    pairs = [(max(r["probs"].values()), bool(r.get("correct"))) for r in valid]
    ece = M.ece_top_label(pairs)
    prob_items = [r for r in rows if r.get("gold_probs") and r.get("probs")]
    tvds = []
    for r in prob_items:
        labels = sorted(set(r["probs"]) | set(r["gold_probs"]))
        tvds.append(C13.tvd(r["probs"], r["gold_probs"], labels))
    mean_tvd = sum(tvds) / len(tvds) if tvds else None
    cal_v13 = v13_calibration(ece["ece"], mean_tvd)

    # ---- Speed: v1.3 leaves this formula alone. ------------------------------
    # The board's Speed axis is the serial standard+judge run. The judge tier is
    # 0 % public, so the closest available population is standard-only, which is
    # the block summary.json reports and the block the 68.41 row used.
    std = [r for r in rows if r["tier"] == "standard" and r.get("latency_s") is not None]
    lat = [r["latency_s"] for r in std]

    # the board's own percentile: jevbench.metrics.percentile (linear interpolation)
    p50_raw, p95_raw = M.percentile(lat, 0.50), M.percentile(lat, 0.95)
    spd = v13_speed(p50_raw, p95_raw, "gpu")

    # ---- Cost: the ASSUMED basis, restated exactly. --------------------------
    usage = [r.get("usage") or {} for r in raw]
    ptok = [u.get("prompt_tokens") for u in usage if u.get("prompt_tokens")]
    ctok = [u.get("completion_tokens") for u in usage if u.get("completion_tokens") is not None]
    mean_in = sum(ptok) / len(ptok) if ptok else None
    mean_out = sum(ctok) / len(ctok) if ctok else None
    usd_per_1000 = (mean_in or 0.0) * ASSUMED_PRICE_IN_PER_M / 1e6 * 1000
    cost_axis = v13_cost(usd_per_1000) if usd_per_1000 > 0 else None
    # the number the 68.41 row actually used, kept for continuity
    COST_681 = 39.29

    axes_v13 = {"intelligence": v13_int, "calibration": cal_v13,
                "speed": spd, "cost": COST_681}
    score_v13 = v13_score(axes_v13)
    axes_v12 = {"intelligence": v12_int, "calibration": v12["calibration"]["value"],
                "speed": v12["speed"]["axis_used"], "cost": COST_681}
    score_v12 = math.exp(sum(0.25 * math.log(max(axes_v12[a], 1.0)) for a in C13.AXES))

    # sensitivity: chance computed from the PUBLIC items alone instead of the
    # board's published full-tier histograms
    pub_chance = {}
    for t in ("easy", "standard", "hard"):
        sub = [r for r in rows if r["tier"] == t]
        pub_chance[t] = sum(1.0 / r["n_labels"] for r in sub) / len(sub)
    int_pubchance = v13_intelligence(tiers, tier_chances=pub_chance)
    score_pubchance = v13_score({**axes_v13, "intelligence": int_pubchance})

    report = {
        "what": "JevBench v1.3 rescore of the EXISTING public-231 native-readout run",
        "no_new_run": True,
        "source_artefacts": {
            "per_item": str(PER_ITEM.relative_to(ROOT)),
            "summary_v12": str(SUMMARY.relative_to(ROOT)),
            "results": str(RESULTS.relative_to(ROOT)),
        },
        "board_scoring_code": "jevbench/composite_v13.py + jevbench/metrics.py at tag v1.3.0",
        "population": {"n_public_items": len(rows), "tiers_present": ["easy", "standard", "hard"],
                       "tiers_absent": ["judge"], "judge_weight_renormalised": 0.28},
        "tiers": tier_detail,
        "tier_chances_full_frozen_tier": chances,
        "tier_chances_public_only": pub_chance,
        "intelligence": {
            "v12_rule_plain_weighted_accuracy": v12_int,
            "v13_rule_chance_corrected": v13_int,
            "per_tier_chance_corrected": chance_corrected,
        },
        "cross_check_against_v12_summary": {
            "intelligence_v12_recomputed": v12_int,
            "intelligence_v12_in_summary": v12["intelligence"]["value"],
            "intelligence_delta": None if v12_int is None else v12_int - v12["intelligence"]["value"],
            "calibration_recomputed": cal_v13,
            "calibration_in_summary": v12["calibration"]["value"],
            "calibration_delta": cal_v13 - v12["calibration"]["value"],
            "ece_recomputed": ece["ece"],
            "ece_in_summary": v12["calibration"]["ece_hard"],
            "mean_tvd_recomputed": mean_tvd,
            "mean_tvd_in_summary": v12["calibration"]["mean_tvd"],
            "speed_recomputed_standard72_gpu": spd,
            "speed_in_summary": v12["speed"]["axis_used"],
            "speed_delta": spd - v12["speed"]["axis_used"],
        },
        "speed_block": {"population": "standard (original) 72 public items",
                        "p50_s_raw": p50_raw, "p95_s_raw": p95_raw,
                        "adjusted": "x2 + 0.15 s (non-production, our own server)",
                        "note": "board Speed is the standard+judge 242-decision run; judge is 0 % public"},
        "cost": {
            "value_used": COST_681,
            "status": "ASSUMED, not measured",
            "basis": (f"${ASSUMED_PRICE_IN_PER_M:.2f}/M input tokens, $0 output; the readout generates "
                      "nothing, so output tokens are free by construction"),
            "measured_mean_input_tokens_per_decision": mean_in,
            "measured_mean_output_tokens_per_decision": mean_out,
            "usd_per_1000_from_measured_tokens": usd_per_1000,
            "cost_axis_from_measured_tokens": cost_axis,
            "why_not_used": ("the operator sets the tariff (B-04); 39.29 is our analyst estimate and is "
                             "carried unchanged so the v1.2 and v1.3 rows are comparable"),
        },
        "axes_v12_formula": axes_v12,
        "axes_v13_formula": axes_v13,
        "jevbench_score_v12_formula_with_assumed_cost": score_v12,
        "jevbench_score_v13": score_v13,
        "near_chance_penalty_applied": C13.near_chance_multiplier(v13_int) != 1.0,
        "sensitivity_public_only_chance": {
            "intelligence": int_pubchance,
            "jevbench_score_v13": score_pubchance,
        },
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")

    print()
    print("=== JevBench v1.3 rescore of the EXISTING public-231 run ===")
    print(f"tiers: easy {tier_detail['easy']['n_correct']}/{tier_detail['easy']['n_public']}"
          f"  standard {tier_detail['standard']['n_correct']}/{tier_detail['standard']['n_public']}"
          f"  hard {tier_detail['hard']['n_correct']}/{tier_detail['hard']['n_public']}")
    print(f"chance (full frozen tier): " + "  ".join(f"{t} {c:.6f}" for t, c in chances.items()))
    print(f"Intelligence  v1.2 rule {v12_int:.4f}   v1.3 rule {v13_int:.4f}")
    print(f"Calibration   {cal_v13:.4f}  (summary {v12["calibration"]['value']:.4f})")
    print(f"Speed         {spd:.4f}  (summary {v12["speed"]['axis_used']:.4f})")
    print(f"Cost          {COST_681}  ASSUMED")
    print(f"COMPOSITE     v1.2 formula {score_v12:.4f}   ->   v1.3 formula {score_v13:.4f}")
    print(f"near-chance penalty applied: {C13.near_chance_multiplier(v13_int) != 1.0}")
    print(f"sensitivity (public-only chance): Int {int_pubchance:.4f} -> score {score_pubchance:.4f}")
    print(f"written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
