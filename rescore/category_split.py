#!/usr/bin/env python3
"""Line the filed run up, item for item, against every system JevBench publishes per-item results for.

    git clone https://github.com/fstandhartinger/jevbench && git -C jevbench checkout fd51755
    python3 rescore/category_split.py jevbench/results/v1.2/jevbench-v1.2-per-task.json

Accuracy on the 231 public items, by tier and by category (the board's "topic"). For each slice it
prints our count, how many published systems answered more, how many answered the same, and the best
count among them (max). Outcome code "c" is correct; "w", "f" and "n" all count as not correct, as in the
board's own tier accuracies. The rows named in LEFT_OUT are not part of this comparison, and nor are
systems without an outcome for every public item; the header says how many were compared. Standard
library only.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LEFT_OUT = {"jev-1.13.0", "classifier-dev-fast"}
board = json.load(open(sys.argv[1]))
tasks = {t["id"]: t for t in board["tasks"]}
ours = {r["task_id"]: bool(r["correct"])
        for r in (json.loads(line) for line in (HERE / "per-item.jsonl").open() if line.strip())}
if set(ours) != set(tasks):
    sys.exit("the task ids in per-item.jsonl do not match the board file's public items")
others = [{tid: s["public_tasks"][tid][0] == "c" for tid in tasks}
          for key, s in board["systems"].items()
          if key not in LEFT_OUT and set(s["public_tasks"]) == set(tasks)]


def line(label: str, ids: list[str]) -> None:
    mine = sum(ours[t] for t in ids)
    counts = [sum(o[t] for t in ids) for o in others]
    ahead = sum(c > mine for c in counts)
    tied = sum(c == mine for c in counts)
    print(f"{label:18} {len(ids):5} {mine:5} {ahead:6} {tied:5} {max(counts):5}")


print(f"{len(others)} published systems, {len(tasks)} public items, board revision {board['revision']}")
print(f"{'slice':18} {'items':>5} {'ours':>5} {'ahead':>6} {'tied':>5} {'max':>5}")
line("all public items", list(tasks))
for tier in ("easy", "standard", "hard"):
    line(tier, [t for t in tasks if tasks[t]["tier"] == tier])
for topic in sorted({t["topic"] for t in tasks.values()}):
    line(topic, [t for t in tasks if tasks[t]["topic"] == topic])
