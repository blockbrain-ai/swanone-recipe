# Baselines: the same model, writing its answer out

These two runs are the comparison for the one-token readout. They use the same served model as the
filed run in `../rescore/` (`qwen3.8-flash-next`, the checkpoint and patched server in this package), on
JevBench's public items, but answer through the benchmark's `openai_compat` adapter, which asks the model
to *write* its probability for each option as JSON. The readout instead reads those probabilities
from one forward pass and generates a single token.

| file | how the model answered | decisions | sha256 |
|---|---|---:|---|
| `A-board-protocol-173.jsonl` | reasoning on (the chat template's default), answer written out | 173 attempted: 160 answered, 13 stopped at the 4,096-token cap before writing an answer | `aa3ebefa03e8fbf343cffd75f4a24620dcbbb988fd4c5fe007652dbc129eb911` |
| `C-thinking-off-231.jsonl` | reasoning off (`enable_thinking: false`), answer written as JSON | 231 of 231 answered | `4f937703647f0015fc663c8337984149c93ba9d42fbbd715f7620f61893f09b6` |

Each row is one decision: the task id, tier and family, the returned distribution, the scored result,
the latency, and the token counts the server reported in `usage`.

## Re-derive the comparison

```bash
python3 baselines/tokens.py
```

```
reasoning on, answer written out          decisions 173  mean  714.3  at the 4096-token cap 13
reasoning off, answer written as JSON     decisions 231  mean   49.9  at the 4096-token cap 0
one-token readout (the filed run)         decisions 231  mean    1.0  at the 4096-token cap 0
```

## What these runs are not

- **Not the filed figure.** The filed composite is the readout run in `../rescore/`.
- **Not a controlled accuracy comparison.** The two paths use different prompts (the adapter's own and
  the shim's), and run A covers 173 of the 231 items, so compare their token counts, not their scores.
- **Public items only**, one run each.
