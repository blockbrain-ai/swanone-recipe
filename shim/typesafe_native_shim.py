#!/usr/bin/env python3
"""Native-readout TypeSafe shim over a stock vLLM server.

WHY THIS EXISTS
    We serve Qwen3.8-Flash-Next through the board's `openai_compat` adapter, which makes the model
    WRITE the distribution as JSON — ~50 generated tokens per decision. NInfer runs the same
    checkpoint and reads the option logits in one forward pass, and scores ~9 composite points
    higher for it (see `THE-READOUT-IS-WORTH-9-POINTS.md`). This shim does the same thing with
    vLLM instead of a bespoke engine.

WHAT IT DOES
    POST /v1/systemone  (the board's `typesafe` adapter wire format)
      -> present the same state, the same instructions and the same label set as lettered options
      -> ONE vLLM request: max_tokens=1, top_logprobs=N
      -> read the option-letter distribution at the answer slot
      -> softmax over the letters, map back to the original label names
      -> return TypeSafe's {"answers": {"decision": {...}}} shape

WHAT IT DOES NOT DO
    It does not generate an answer, does not verbalise, and does not touch the weights. It is a
    readout, which is why the board prices it input-only.

DISCLOSURE (must appear in any filing that uses this)
    The options are PRESENTED as letters (A., B., ...) although the benchmark's label set is
    unchanged and every label is shown with its own criteria text verbatim. This is the same
    presentation the board already accepted for `open-alternative-jev` ("the author's own option
    order (A. yes, B. no)") and for reflex ("averages two option orders"). It is a presentation
    choice, and the option order it imposes is ours, so it must be declared.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VLLM = os.environ.get("SHIM_VLLM", "http://127.0.0.1:8890/v1/chat/completions")
MODEL = os.environ.get("SHIM_MODEL", "qwen3.8-flash-next")
PORT = int(os.environ.get("SHIM_PORT", "8009"))
TOP_LOGPROBS = int(os.environ.get("SHIM_TOP_LOGPROBS", "20"))
TIMEOUT = float(os.environ.get("SHIM_TIMEOUT", "180"))
# Thinking stays off: this is a readout, and a reasoning trace before an answer slot is not one.
CHAT_TEMPLATE_KWARGS = {"enable_thinking": False}

LETTERS = "ABCDEFGHIJ"

# THE SCAFFOLDING IS THE FIX. The board's `openai_compat` adapter gives the model a system prompt
# (`jevbench/adapters/openai_compat.py:20-24`): "You are a calibration engine. You never answer in
# prose. You output only a JSON object ...". Our verbalised path gets that; the first version of this
# shim got nothing, and on the 231 public items it lost 10.21 Intelligence — the model was answering
# a bare "Answer:" slot and continuing in prose ("The", "To", "**"). Measured on the non-board dev
# set built from our own fixed generators: bare prompt 0.596 accuracy.
SYSTEM = (
    "You are a calibration engine. You never answer in prose. You are given a state, a question and "
    "a numbered set of options, and you choose exactly one option. You reply with that option's "
    "LETTER and nothing else — a single character, no words, no punctuation, no explanation."
)


def options_from(criteria, qtype):
    """Ordered [(letter, response_label, description)].

    choice: criteria is {label: description}; the LABEL NAME is what the response must be keyed by.
    score : criteria is a list of level descriptions; label names are "0".."n-1" per the task's
            `labels` field, which is always the stringified index.
    noul  : criteria is {"true": ..., "false": ...} and the adapter wants P(yes). We read the
            true/false letters and hand back P(true), which the adapter maps onto {"yes","no"}.
    """
    if qtype == "choice":
        if not isinstance(criteria, dict):
            raise ValueError("choice without a criteria mapping")
        return [(LETTERS[i], k, v) for i, (k, v) in enumerate(criteria.items())]
    if qtype == "score":
        if not isinstance(criteria, (list, tuple)):
            raise ValueError("score without a criteria list")
        return [(LETTERS[i], str(i), v) for i, v in enumerate(criteria)]
    if qtype == "noul":
        if not isinstance(criteria, dict):
            raise ValueError("noul without a criteria mapping")
        # keep the record's own order, but remember which letter means "true"
        out = []
        for i, (k, v) in enumerate(criteria.items()):
            out.append((LETTERS[i], k, v))
        return out
    raise ValueError(f"unsupported question type {qtype!r}")


def build_prompt(state, instructions, opts):
    # STATE CAN BE A DICT. Some hard tasks ship structured state (alias_directory, amendment,
    # archive, ...). The board's own `openai_compat` adapter serialises it --
    # `state_text = task.state if isinstance(task.state, str) else json.dumps(task.state,
    # ensure_ascii=False)` (jevbench/adapters/openai_compat.py:64-67) -- and we match that exactly,
    # because rendering the state differently from the reference adapter would make the comparison
    # between our two runs meaningless. Calling .rstrip() on a dict is what stopped the first
    # complete run at 183/231 with three consecutive 500s.
    state_text = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False, indent=1)
    if not isinstance(instructions, str):
        instructions = json.dumps(instructions, ensure_ascii=False)
    lines = [state_text.rstrip(), "", instructions.rstrip(), "", "Options:"]
    for letter, _lab, desc in opts:
        lines.append(f"{letter}. {desc}")
    lines += ["", "Answer with the letter of exactly one option, and nothing else:"]
    return "\n".join(lines)


_TOK_LETTER = re.compile(r"^[\s(\[{'\"]*([A-Ja-j])[\s.,:)\]}'\"]*$")


def letter_probs(top_logprobs, n_letters):
    """Sum probability mass per option letter from vLLM's top_logprobs for the first token.

    A letter can appear as several surface tokens ("A", " A", "A."), so mass is SUMMED per letter
    rather than taking only the exact match.

    Returns None only if NO letter appeared at all. Under the guided-choice constraint a missing
    letter means the model gave it ~0 mass, which is a legitimate value and not a failure — the
    earlier `len(acc) < 2` guard turned ordinary low-probability options into a run-killing 502.
    """
    acc = {}
    for tok, lp in top_logprobs.items():
        m = _TOK_LETTER.match(tok)
        if not m:
            continue
        idx = LETTERS.index(m.group(1).upper())
        if idx >= n_letters:
            continue
        acc[idx] = acc.get(idx, 0.0) + math.exp(lp)
    if not acc:
        return None
    total = sum(acc.values())
    if total <= 0:
        return None
    return {i: acc.get(i, 0.0) / total for i in range(n_letters)}


def call_vllm(prompt_text, allowed_letters):
    """One forward pass, one token, constrained to the option letters.

    THE CONSTRAINT IS THE POINT, and it took a failure to find. Without it the model answers the
    "Answer:" slot in PROSE — measured on `easy-tool_selection-07`, the top-20 logprobs were
    `The -0.07, To -3.07, A -4.94, ** -4.94, ...` and only ONE option letter appeared, so no
    distribution over the options could be recovered at all. 11 of 129 requests failed that way and
    the board's "three consecutive infrastructure errors ends the run" rule stopped the run.

    `structured_outputs: {"choice": [...]}` masks the logits to the allowed letters. Measured on the
    same item afterwards: all five letters present with real logprobs
    (`A -0.01, B -5.08, C -5.51, E -6.39, D -6.76`) and the disallowed tokens pinned at -9999.

    This is a readout of P(option | state) restricted to the options — which is exactly what a
    Jev-class decision model returns natively, and what kev, reflex and NInfer read. It is not a
    repair of a malformed distribution: nothing is invented, and the relative mass between options
    is the model's own.
    """
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt_text}],
        "max_tokens": 1,
        "temperature": 1.0,
        "logprobs": True,
        "top_logprobs": TOP_LOGPROBS,
        "chat_template_kwargs": CHAT_TEMPLATE_KWARGS,
        "structured_outputs": {"choice": allowed_letters},
    }).encode()
    req = urllib.request.Request(VLLM, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def answer_for(task_state, decision):
    qtype = decision.get("type")
    instructions = decision.get("instructions") or ""
    criteria = decision.get("criteria")
    opts = options_from(criteria, qtype)
    if len(opts) > len(LETTERS):
        raise ValueError(f"{len(opts)} options exceeds the letter alphabet")
    if len(opts) > TOP_LOGPROBS:
        raise ValueError(f"{len(opts)} options exceeds TOP_LOGPROBS={TOP_LOGPROBS}; "
                         f"letters would be dropped from the readout")

    resp = call_vllm(build_prompt(task_state, instructions, opts),
                     [letter for letter, _l, _d in opts])
    usage = resp.get("usage") or {}
    try:
        lp = resp["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
        top = {d["token"]: d["logprob"] for d in lp}
    except (KeyError, IndexError, TypeError):
        return None, usage, "vLLM returned no top_logprobs at the answer slot"

    probs = letter_probs(top, len(opts))
    if probs is None:
        return None, usage, "could not recover an option-letter distribution from the answer slot"

    if qtype == "noul":
        # criteria order is the record's; find which letter carried "true"
        true_letter = next((i for i, (_l, lab, _d) in enumerate(opts) if str(lab).lower() == "true"), None)
        if true_letter is None:
            return None, usage, "noul criteria had no 'true' key"
        p_yes = probs.get(true_letter, 0.0)
        return {"type": "noul", "noul": p_yes}, usage, None

    dist = {lab: probs.get(i, 0.0) for i, (_l, lab, _d) in enumerate(opts)}
    total = sum(dist.values())
    if total <= 0:
        return None, usage, "empty distribution"
    dist = {k: v / total for k, v in dist.items()}
    best = max(dist, key=dist.get)
    return {"type": qtype, "choice": best, "probabilities": dist}, usage, None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):          # keep the log to one line per request
        sys.stderr.write("shim %s\n" % (fmt % args))

    def _send(self, code, obj):
        payload = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            self._send(200, {"models": [{"id": MODEL, "aliases": ["jev-latest"],
                                         "readout": "native option-logit over vLLM"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/v1/systemone"):
            self._send(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            self._send(400, {"error": f"bad request body: {e}"})
            return
        try:
            state = body.get("state") or ""
            decision = ((body.get("questions") or {}).get("decision")) or {}
            ans, usage, err = answer_for(state, decision)
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})
            return
        if err:
            self._send(502, {"error": err})
            return
        self._send(200, {
            "model": MODEL,
            "answers": {"decision": ans},
            # KEY NAMES MATTER: the harness reads usage.prompt_tokens / usage.completion_tokens.
            # Returning input_tokens/output_tokens (as the first version did) silently loses the
            # token accounting the board prices from.
            "usage": {"prompt_tokens": usage.get("prompt_tokens"),
                      "completion_tokens": usage.get("completion_tokens"),
                      "total_tokens": usage.get("total_tokens")},
        })


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"native-readout shim on 127.0.0.1:{PORT} -> {VLLM} (model {MODEL})", flush=True)
    srv.serve_forever()
