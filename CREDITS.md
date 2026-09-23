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
reimplement it — **all nine files under `patches/` are your patch output**, and we verified that
byte-for-byte: your five generators (`files/patch_*.py`) reproduce every one of our nine files exactly
from the same pre-patch originals, with every anchor matching exactly once. There is no part of the
patch code here that is ours. What is ours is the packaging and the shim, nothing more.

That is the honest accounting, and it is also why the licence sentence below matters so much more than
a footnote.

**We got the licence wrong, and we are sorry about it.** We first published these files as
Apache-2.0. Your recipe is **AGPL-3.0-or-later**, and we cannot relicense it. `patches/` is now
distributed under **AGPL-3.0-or-later** with the full text in `LICENSE-AGPL-3.0`, and
`LICENSE-NOTICE.md` states the position. The correction is the least we owe, and it is later than it
should have been.

We would also like to thank you for the *manner* of the work, which taught us something. Every claim in
that repository is measured on named hardware and reported with its failures attached —
`NV_ERR_NO_MEMORY` counts, peak driver memory against budget, the reserve cells that did not work. And
when you took an idea from someone else you said so precisely: the FP8-KV approach is credited to
[`lancelind/qwen3.8-Flash-DGX`](https://github.com/lancelind/qwen3.8-Flash-DGX) as *"reimplemented here
against this image's own sources. That credit applies to this one patch; nothing else in this
repository derives from that project."* That sentence is the standard we are now trying to meet.
[`oscarmenendezgarcia`](https://github.com/oscarmenendezgarcia) is credited by name for the
Spanish-extended draft vocabulary and the audit gate. We noticed, and we have copied the habit.

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

- **The native-readout shim** (`shim/typesafe_native_shim.py`) — original to this repository, Apache-2.0.
- **The scoring and rescoring** (`rescore/`) — our harness invocation and per-item output.
- **The packaging** — `patches/MANIFEST.md` (per-file sha256 against the published image),
  `swanOne-vllm-patch.diff`, and the verification that applying it reproduces all nine files
  byte-for-byte.

**None of the patch code is ours.** MiaAI Lab's generators reproduce all nine files exactly. An earlier
draft of this file said "mixed authorship" and listed vLLM's retained headers and the packaging as
evidence of our own work on the patches; that was wrong. Retained headers are what a rewriting generator
produces, and packaging is not authorship of the code.

## Licence compatibility

Some lines that MiaAI Lab's recipe patches are **Apache-2.0 vLLM** work, in open pull requests #53899,
#53908, #53960, #54070 and #54129. Apache-2.0 code may be combined into an AGPL work, so the set as a
whole is **AGPL-3.0-or-later**. The reverse would not have been possible.

AGPL §13 binds whoever runs the modified version for remote users. Our own endpoint is not public, so
that duty is not ours today; if you run this as a network service, it is yours. The corresponding source
is this repository, so the offer is satisfied by pointing here.
