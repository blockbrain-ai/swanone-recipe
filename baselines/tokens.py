#!/usr/bin/env python3
"""Re-derive the tokens generated per decision, for the three ways swanOne's model can answer.

    python3 baselines/tokens.py

Reads the two written-answer runs in this directory and the filed one-token readout run in
../rescore/. Every figure comes from the `usage.completion_tokens` the server reported for each
decision. Standard library only.
"""
from __future__ import annotations

import json
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
CAP = 4096
RUNS = [
    ("reasoning on, answer written out", HERE / "A-board-protocol-173.jsonl"),
    ("reasoning off, answer written as JSON", HERE / "C-thinking-off-231.jsonl"),
    ("one-token readout (the filed run)", HERE.parent / "rescore" / "native231d-results.jsonl"),
]

for label, path in RUNS:
    rows = [json.loads(line) for line in path.open() if line.strip()]
    tokens = [row["usage"]["completion_tokens"] for row in rows]
    at_cap = sum(t >= CAP for t in tokens)
    print(f"{label:40}  decisions {len(tokens):3}  mean {statistics.mean(tokens):6.1f}  at the {CAP}-token cap {at_cap}")
