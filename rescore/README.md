# The v1.3 rescore of our public-231 run

Issue [#23](https://github.com/fstandhartinger/jevbench/issues/23) §6 says our composite is **67.39**, and
that this is the **v1.3** number — 1.02 *below* the 68.41 the v1.2 formula gives on the same run. We filed
the lower one because v1.3 is the formula the live board uses. This directory is the evidence for that
sentence, so you do not have to take it on trust.

| file | what it is |
|---|---|
| `RESCORE-v1.3-PUBLIC-231.json` | the result: every axis under **both** formulas, per tier |
| `rescore_v13_public231.py` | the script that produced it (unmodified) |
| `native231d-results.jsonl` | our raw harness output for the 231 public items — 231 rows |
| `per-item.jsonl` | the same run after scoring — 231 rows |
| `summary.json` | the v1.2 axis computation the rescore recomputes and checks against |
| `category_split.py` | lines this run up, item for item, against JevBench's published per-item outcomes for 40 systems (see the top-level README) |

**No new run is behind any of this** (`"no_new_run": true` in the JSON): it is a recomputation of one
existing public-tier run under a different composite. The scoring code is the board's own, at tag
`v1.3.0` (`jevbench/composite_v13.py` + `jevbench/metrics.py`).

## The check that matters

The rescore **recomputes the v1.2 axes from `per-item.jsonl` and compares them to `summary.json` before
applying v1.3**, and reports the difference. It comes out at **0.0** on every axis. So the only thing that
moves between the two numbers is Intelligence, which is exactly what v1.3 changed — chance-correction,
84.28 against the v1.2 rule's 89.54. Calibration and Speed are untouched by v1.3.

## Running it

The script was written inside our working tree and resolves its inputs relative to itself
(`ROOT = Path(__file__).resolve().parents[2]`, then `tmp/jev-survey/shim/...`). It is published
**unmodified**, so to re-run it, reproduce that layout:

```bash
mkdir -p tmp/jev-survey/shim/score-native-d
cp native231d-results.jsonl tmp/jev-survey/shim/
cp per-item.jsonl summary.json tmp/jev-survey/shim/score-native-d/
# place rescore_v13_public231.py at <root>/Planning/jev-survey/ and run it
python3 rescore_v13_public231.py
```

## What it does **not** cover

- **The judge tier is absent** (0 % public, 0.28 of Intelligence). The weight is renormalised, and the
  judge tier is stated as absent rather than estimated.
- **Cost is assumed, not measured** — the same-weights published tariff of `Qwen/Qwen3.8-Flash-Next`,
  which issue #23 §5 asks the operator to accept, replace, or refuse.
- **Speed is the standard-tier 72 public items alone**, not the board's standard + judge 242-decision
  population, which cannot be computed from public data. Issue #23 §6 carries the same warning.
