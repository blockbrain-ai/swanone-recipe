# Licensing

**Summary: the repository is mixed. `shim/` is Apache-2.0. `patches/` is AGPL-3.0-or-later and is not
our work to license.**

An earlier version of this notice (2026-09-22) described the nine patched files as Apache-2.0
"modifications of vLLM source". That was incorrect, and this file replaces it.

## `patches/` — AGPL-3.0-or-later

The nine files under `patches/` incorporate code from MiaAI Lab's recipe
[`MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark`](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark),
which is licensed **AGPL-3.0-or-later**, and **they are distributed here under AGPL-3.0-or-later**. The
full licence text is in `LICENSE-AGPL-3.0`.

**They are MiaAI Lab's patch output, not our engineering.** Their recipe's own generators
(`files/patch_*.py`) reproduce all nine of these files **byte-for-byte** from the same pre-patch
originals this repository ships. We verified that, and it is the honest basis for the licence above:
there is no meaningful part of this patch code that is ours to license differently. What is ours is the
packaging — `patches/MANIFEST.md`, the sha256 verification against the published image, and
`swanOne-vllm-patch.diff`.

Some of the lines the recipe patches are themselves **Apache-2.0 vLLM** work, in open pull requests
#53899, #53908, #53960, #54070 and #54129. Apache-2.0 code may be combined into an AGPL work; the
reverse is not possible, which is why the set as a whole is AGPL.

`patches/*.orig` and `patches/orig/` are the unmodified files from the published image, included so the
diff is reproducible.

**The nine patched files are byte-identical to MiaAI Lab's generator output and are not edited here.** If
you need a change, change the generator upstream and re-run it.

## `shim/` — Apache-2.0

`shim/typesafe_native_shim.py` is original to this repository and remains **Apache-2.0**; see
`LICENSE-APACHE-2.0`. It talks to the server over HTTP, so it is a separate program and the AGPL above
does not reach it.

## Model weights

The weights are **not** in this repository. They are
[`Mia-AiLab/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/Mia-AiLab/Qwen3.8-Flash-Next-NVFP4)
(**Apache-2.0**), fetched from Hugging Face at run time. That checkpoint derives from
[`Qwen/Qwen3.8-Flash-Next`](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) (Qwen licence) and was
quantized with NVIDIA's Model Optimizer; serving it means accepting those terms too.

## If you are MiaAI Lab

This repository uses your recipe, and we got the licence wrong for a day. We would rather fix it the way
you would want. If you want the credit worded differently, want the patch files removed, or would prefer
to grant a permissive licence for the patch output, please open an issue and we will do it.

## Full credits

See [`CREDITS.md`](CREDITS.md).
