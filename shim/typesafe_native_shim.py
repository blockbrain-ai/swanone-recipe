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
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VLLM = os.environ.get("SHIM_VLLM", "http://127.0.0.1:8890/v1/chat/completions")
MODEL = os.environ.get("SHIM_MODEL", "qwen3.8-flash-next")
PORT = int(os.environ.get("SHIM_PORT", "8009"))
TOP_LOGPROBS = int(os.environ.get("SHIM_TOP_LOGPROBS", "20"))
TIMEOUT = float(os.environ.get("SHIM_TIMEOUT", "180"))
MIN_CONTEXT = int(os.environ.get("SHIM_MIN_CONTEXT", "4096"))
# Thinking stays off: this is a readout, and a reasoning trace before an answer slot is not one.
CHAT_TEMPLATE_KWARGS = {"enable_thinking": False}

# One letter per option, so up to 26 options. vLLM returns at most TOP_LOGPROBS (20) candidates, so on a
# decision with 21-26 options the 20 most probable letters carry the distribution and the rest get 0.
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# vLLM's wording when a prompt does not fit --max-model-len (it has changed between releases).
_CONTEXT_ERROR = re.compile(r"maximum context length|maximum model length|max_model_len|too long and exceeds", re.I)


class Unprocessable(ValueError):
    """An input this system cannot answer: over the server's context or size limit, more than 26 options, a
    question type it does not know, or options in the wrong form for their type.

    THE STATUS CODE IS THE CONTRACT. The benchmark's runner stops a run after three consecutive failed items
    unless the failure is an HTTP 422, which it scores as one wrong answer and moves on
    (`jevbench/runner.py`, "a 422 is the system refusing this input (e.g. over its context limit), not an
    outage"). Answering these with a 500, as this shim used to, lets three long items in a row end the run.
    """


class UpstreamError(RuntimeError):
    """vLLM failed or could not be reached: a 502, so a dead server still stops the run. vLLM's own 401, 403
    and 429 pass through unchanged, because the runner stops at once on those."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


# A SERVER STARTED WITH A SMALL --max-model-len WOULD MAKE EVERY LONGER ITEM A 422, and a run of 422s
# completes quietly with all of them wrong. So before answering, the shim reads the served model's limit, and
# answers 503 if it is below SHIM_MIN_CONTEXT, or if the server does not list SHIM_MODEL or report a limit.
# A 503 counts toward the runner's stop rule. 4096 is the smallest cap this package was validated at, and the
# longest public prompt is 3,946 tokens.
_server_context = None
_context_lock = threading.Lock()


def server_context():
    """The served model's max_model_len, read once from vLLM's /v1/models.

    Raises UpstreamError: 502 if the server cannot be read (vLLM's own 401, 403 and 429 pass through), 503 if it
    does not list SHIM_MODEL or reports no integer limit. A failure is not cached, so a server that comes up
    later is read on the next request.
    """
    global _server_context
    with _context_lock:
        if _server_context is None:
            url = VLLM.split("/v1/", 1)[0] + "/v1/models"
            try:
                with urllib.request.urlopen(url, timeout=10) as r:
                    models = json.loads(r.read()).get("data") or []
                entry = next((m for m in models if isinstance(m, dict) and m.get("id") == MODEL), None)
            except urllib.error.HTTPError as e:
                raise UpstreamError(f"{url}: HTTP {e.code}", e.code if e.code in (401, 403, 429) else 502) from e
            except (OSError, ValueError, AttributeError, TypeError) as e:
                raise UpstreamError(f"cannot read {url}: {type(e).__name__}: {e}") from e
            if entry is None:
                raise UpstreamError(f"{url} does not list {MODEL!r}; set SHIM_MODEL to the served model name", 503)
            if not isinstance(entry.get("max_model_len"), int) or isinstance(entry.get("max_model_len"), bool):
                raise UpstreamError(f"{url} reports no max_model_len for {MODEL!r}", 503)
            _server_context = entry["max_model_len"]
            sys.stderr.write(f"shim: the server's max_model_len is {_server_context}\n")
    return _server_context


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
    if qtype not in ("choice", "score", "noul"):
        raise Unprocessable(f"unsupported question type {qtype!r}")
    if qtype == "score":
        if not isinstance(criteria, (list, tuple)):
            raise Unprocessable("score without a criteria list")
        items = [(str(i), v) for i, v in enumerate(criteria)]
    else:
        if not isinstance(criteria, dict):
            raise Unprocessable(f"{qtype} without a criteria mapping")
        # noul keeps the record's own order; answer_for finds which letter means "true"
        if qtype == "noul" and not any(str(k).lower() == "true" for k in criteria):
            raise Unprocessable("noul criteria had no 'true' key")
        items = list(criteria.items())
    if not items:
        raise Unprocessable("no options")
    if len(items) > len(LETTERS):
        raise Unprocessable(f"{len(items)} options exceeds the {len(LETTERS)}-letter alphabet")
    return [(LETTERS[i], k, v) for i, (k, v) in enumerate(items)]


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


_TOK_LETTER = re.compile(r"^[\s(\[{'\"]*([A-Za-z])[\s.,:)\]}'\"]*$")


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
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        if e.code == 400 and _CONTEXT_ERROR.search(detail):
            raise Unprocessable(f"over the server's context limit: {detail}") from e
        if e.code == 413:
            raise Unprocessable(f"over the server's request size limit: {detail}") from e
        raise UpstreamError(f"vLLM HTTP {e.code}: {detail}", e.code if e.code in (401, 403, 429) else 502) from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise UpstreamError(f"vLLM unreachable or unreadable: {type(e).__name__}: {e}") from e


def answer_for(task_state, decision):
    qtype = decision.get("type")
    instructions = decision.get("instructions") or ""
    criteria = decision.get("criteria")
    opts = options_from(criteria, qtype)

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
        true_letter = next(i for i, (_l, lab, _d) in enumerate(opts) if str(lab).lower() == "true")
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
            questions = body.get("questions") if isinstance(body, dict) else None
            decision = questions.get("decision") if isinstance(questions, dict) else None
            if not isinstance(decision, dict):
                raise ValueError("expected a JSON object with questions.decision")
        except Exception as e:
            self._send(400, {"error": f"bad request body: {e}"})
            return
        try:
            context = server_context()
            if context < MIN_CONTEXT:
                raise UpstreamError(f"the server's max_model_len is {context}, below SHIM_MIN_CONTEXT={MIN_CONTEXT};"
                                    f" restart vLLM with a larger --max-model-len", 503)
            ans, usage, err = answer_for(body.get("state") or "", decision)
        except Unprocessable as e:
            sys.stderr.write(f"shim 422 {e}\n")
            self._send(422, {"error": str(e)})
            return
        except UpstreamError as e:
            self._send(e.status, {"error": str(e)})
            return
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
