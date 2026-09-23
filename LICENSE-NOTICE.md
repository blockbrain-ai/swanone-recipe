# Licensing

## Summary — read this first

This repository is **not** offered under a single licence. The vLLM *engine* is Apache-2.0. The
**patch set that makes it serve this model derives in part from an AGPL-3.0 project** and is therefore
**not** ours to license as Apache-2.0.

An earlier version of this file stated that all nine patched files were published under Apache-2.0
"with attribution". That was wrong, and this file corrects it.

## `patches/` — mixed authorship

The nine files are modifications of **vLLM** (Apache-2.0). They retain vLLM's own headers.
`patches/*.orig` and `patches/orig/` are the unmodified upstream files, included so the diff is
reproducible.

They also derive from **MiaAI Lab's single-Spark recipe**,
[`MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark`](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark),
which is licensed **AGPL-3.0**. That repository predates this one, and a substantial part of the patch
logic here — including the `ple_offload` machinery, the MTP draft-vocabulary index and the
packed-PLE-table path — originates there and not in vLLM. MiaAI Lab's own patch generators are in its
`files/` directory; ours ship the patched output.

Consequences, stated plainly:

- **The patch set as a whole cannot be offered under Apache-2.0**, because AGPL-3.0 code cannot be
  relicensed by us.
- **`shim/typesafe_native_shim.py` is unaffected.** It is original to this repository.
- The precise per-file split between MiaAI Lab's work, vLLM's, and ours **has not yet been measured**.
  Until it is, no file here should be described as Apache-2.0 on our authority alone.

We are resolving this. The options are to relicense the affected files, to reimplement the derived
logic against MiaAI Lab's published description rather than its code, or to accept AGPL-3.0 for the
set. Details and the evidence are in `CREDITS.md`.

## Model weights

The weights are **not** in this repository. They are
[`Mia-AiLab/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/Mia-AiLab/Qwen3.8-Flash-Next-NVFP4),
which is **Apache-2.0**, and are fetched from Hugging Face at run time.

That checkpoint is itself derived from
[`Qwen/Qwen3.8-Flash-Next`](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) (Qwen licence, not
Apache-2.0) and quantized with NVIDIA's Model Optimizer. Serving it means accepting those upstream
terms as well.

## Full credits

See [`CREDITS.md`](CREDITS.md).
