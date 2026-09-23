# Credits

This repository exists because other people published their work. Most of what follows is theirs.

## MiaAI Lab — the recipe this is built on

**The single greatest debt here is to [MiaAI Lab](https://x.com/MiaAI_lab)
([`MiaAI-Lab`](https://github.com/MiaAI-Lab)).** Serving a 99 GiB NVFP4
vision-language model from one DGX Spark's 121 GiB of unified memory is not something we worked out
from scratch — Mia and her team did, and published it as
[`Qwen3.8-Flash-Next-Single-DGX-Spark`](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark).

That repository is the reason this one can exist at all. From it we drew:

- **The PLE CPU-offload machinery**, including the diagnosis that GB10 cannot use stream-memory ops
  (`CU_DEVICE_ATTRIBUTE_CAN_USE_STREAM_MEM_OPS = 0`) and the host-side handshake that replaces them.
  The GPU worker hangs after graph capture without this; they found it and fixed it.
- **The memory-mapped packed PLE table** (`build_ple_packed_table.py`). On unified memory this is the
  difference between a model that fits and one that does not.
- **The MTP draft-vocabulary index** (`build_draft_vocab.py`) — slicing the drafter's LM head to a
  47k-token vocabulary, with the `VLLM_MTP_DRAFT_VOCAB` interface we still use.
- **The MXFP8 fallback for shapes FlashInfer's kernel rejects**, including the measured `N`/`K`
  divisibility limits on sm_121.
- **The FP8-KV cache path** for quantized attention caches.

**Thank you, Mia and team.** The recipe is the reason this repository exists. We did not adapt it or
reimplement it — **all nine files under `patches/` are your patch output**, verified byte-for-byte: your
five generators (`files/patch_*.py`) reproduce every one of our nine files exactly from the same
pre-patch originals, with every anchor matching exactly once. There is no part of the patch code here
that is ours. What is ours is the packaging and the shim.

**Licence:** `patches/` is distributed here as **Apache-2.0** — modified vLLM source, and an Apache-2.0
work by your own README, which licenses the *generators* under AGPL-3.0-or-later and states that the
files they generate "keep vLLM's own Apache-2.0 headers and remain Apache-2.0 works". **Your AGPL scripts
are not redistributed here at all.** If you read that differently, tell us and we will change it.

We would also like to thank you for the *manner* of the work. Every claim in that repository is measured
on named hardware and reported with its failures attached — `NV_ERR_NO_MEMORY` counts, peak driver memory
against budget, the reserve cells that did not work. And when you took an idea from someone else you said
so precisely: the FP8-KV approach is credited to
[`lancelind/qwen3.8-Flash-DGX`](https://github.com/lancelind/qwen3.8-Flash-DGX) as *"reimplemented here
against this image's own sources. That credit applies to this one patch; nothing else in this repository
derives from that project."* That sentence is the standard we are trying to meet.
[`oscarmenendezgarcia`](https://github.com/oscarmenendezgarcia) is credited by name for the
Spanish-extended draft vocabulary and the audit gate.

## NInfer — the one-token readout approach

The shim answers each decision by reading the model's own probabilities over the option letters from a
single forward pass, instead of asking it to write the answer out. **That approach is
[NInfer](https://github.com/igorls/ninfer)'s**: a single-GPU inference engine (Apache-2.0) whose
[JevBench entry](https://github.com/fstandhartinger/jevbench/issues/12) reads the option-letter
distribution this way, including on this same checkpoint. Our shim does the same thing on stock vLLM —
the code in `shim/` is ours; the idea it implements is theirs.

## Dustin, on our team — jobe

[`jobe`](https://github.com/MantisShrimpdev/jobe), by Dustin (MIT), is a one-pass decision readout over
Qwen's released Qwen3.5-4B checkpoint, with no training of its own; its README reports 0.805 on JevBench's
public set and 0.604 on the hard tier. It shaped our path to this submission in two ways. Reproducing its
published per-item results through our own pipeline, we landed within a point of them, which is how we
checked our readout pipeline. And reading Qwen's released checkpoint and its untrained base the same way
showed that the hard-tier advantage we had been chasing through training comes from Qwen's own
post-training: 61.3 % against 49.5 % on the public hard items.

## Models

- **Qwen / Alibaba** — [`Qwen/Qwen3.8-Flash-Next`](https://huggingface.co/Qwen/Qwen3.8-Flash-Next),
  the base model everything here derives from.
- **MiaAI Lab** — [`Mia-AiLab/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/Mia-AiLab/Qwen3.8-Flash-Next-NVFP4),
  the checkpoint this repository serves.
- **NVIDIA** — [`nvidia/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4)
  and Model Optimizer, whose quantized output the served checkpoint is built from.

## Software

- **vLLM** — Apache-2.0. The engine, and the code every patch in `patches/` modifies.
- **[`lancelind/qwen3.8-Flash-DGX`](https://github.com/lancelind/qwen3.8-Flash-DGX)** — Apache-2.0. The
  FP8-KV approach, via MiaAI Lab's reimplementation (see above).
- **`fstandhartinger/jevbench`** — the benchmark suite this entry was prepared for, and the source of
  the public 231-item set in `rescore/`.

## Our own contribution

To be exact about the part we can claim — and it is deliberately a short list:

- **The native-readout shim** (`shim/typesafe_native_shim.py`) — the code is original to this
  repository, MIT; the approach it implements is NInfer's (above).
- **The scoring and rescoring** (`rescore/`) — our harness invocation and per-item output.
- **The packaging** — `patches/MANIFEST.md` (per-file sha256 against the published image),
  `swanOne-vllm-patch.diff`, and the verification that applying it reproduces all nine files
  byte-for-byte.

**None of the patch code is ours.** MiaAI Lab's generators reproduce all nine files exactly.

## Licence compatibility

Some of the lines that MiaAI Lab's recipe patches are **Apache-2.0 vLLM** work, in open pull requests
#53899, #53908, #53960, #54070 and #54129 — so the output is an Apache-2.0 work on both sides of the
question, which is why we distribute it under Apache-2.0.

MiaAI Lab's recipe itself is AGPL-3.0-or-later. **We do not redistribute those scripts**, so that
licence does not reach this repository; if you rebuild the patch output yourself, you run their
generators from their repository and their terms apply to that.

AGPL §13 binds whoever runs a modified AGPL version for remote users. Even on the reading where the
output is AGPL, our own endpoint is not public, so that duty would fall to whoever serves it publicly.
The corresponding source is this repository either way.
