# Licensing

## Summary

| what | licence | why |
|---|---|---|
| `patches/` (the nine generated files) | **Apache-2.0** | they are modified **vLLM** source, and MiaAI Lab's recipe states that its generated files "keep vLLM's own Apache-2.0 headers and remain Apache-2.0 works" |
| `shim/typesafe_native_shim.py` | **MIT** | original to this repository |
| `assets/draft_vocab_en_code_47k.txt` | data, no copyright claimed | 47,172 integer token ids produced by a tokenizer |
| **MiaAI Lab's scripts** | **AGPL-3.0-or-later** | we do **not** redistribute them |

**This notice has now been wrong in both directions, so here is what is actually true.** It first said
Apache-2.0 without crediting MiaAI Lab. It was then corrected to AGPL-3.0-or-later on the reasoning that
the patch code came from their **AGPL-3.0** generators. That was too pessimistic, on their own documented
terms — see below. The position above is the one we are distributing under, and we have asked MiaAI Lab to
confirm it.

## `patches/` — Apache-2.0, and MiaAI Lab's work

The nine files are modified **vLLM** source (Apache-2.0) and retain vLLM's own headers.
`patches/*.orig` and `patches/orig/` are the unmodified files from the published image, included so the
diff is reproducible.

**They are MiaAI Lab's patch output, not our engineering.** Their recipe's generators
([`MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark`](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark))
reproduce all nine of these files **byte-for-byte** from the same pre-patch originals. There is no
meaningful part of this patch code that is ours. What is ours is the packaging — `patches/MANIFEST.md`,
the sha256 verification, and `swanOne-vllm-patch.diff`.

**MiaAI Lab's recipe distinguishes its scripts from their output, and so do we:**

> It covers the files in this repository — the launcher, the patch generators, the packed-table builder
> and the watchdog. It does **not** relicense anything they operate on … The patch generators emit
> modified copies onto your machine only. Those generated files keep vLLM's own Apache-2.0 headers and
> remain Apache-2.0 works. — their README, "What the license does and does not cover"

So the generators are **AGPL-3.0-or-later**, and the files they generate are **Apache-2.0**. We
redistribute only the output, so we distribute it under Apache-2.0 as they describe. **Their AGPL scripts
are not in this repository at all** — if you rebuild the patch output yourself, you run their generators
from their repository, under their licence.

Some of the lines the recipe patches are themselves Apache-2.0 vLLM work, in open pull requests #53899,
#53908, #53960, #54070 and #54129.

**We have asked MiaAI Lab to confirm this reading.** If they would rather the output carried AGPL-3.0, or
want the wording changed, we will change it — see below.

## `shim/` — MIT

`shim/typesafe_native_shim.py` is original to this repository and licensed **MIT** (`LICENSE-MIT`). It
talks to the server over HTTP and is a separate program.

## Model weights

The weights are **not** in this repository. They are
[`Mia-AiLab/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/Mia-AiLab/Qwen3.8-Flash-Next-NVFP4)
(**Apache-2.0**), fetched from Hugging Face at run time. That checkpoint derives from
[`Qwen/Qwen3.8-Flash-Next`](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) (Qwen licence) and was
quantized with NVIDIA's Model Optimizer; serving it means accepting those terms too.

## If you are MiaAI Lab

This repository is built on your recipe and we got the credit wrong before we got it right. We currently
believe, from your README, that the patch output is an Apache-2.0 work and that we are distributing it on
those terms. **If you disagree, or want different wording, or want the patch files removed, please open an
issue and we will do exactly that.** We would also rather credit you the way you want to be credited.

## Full credits

See [`CREDITS.md`](CREDITS.md).
