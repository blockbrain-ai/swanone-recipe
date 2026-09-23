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

This is derivation and not resemblance, and it is checkable: thirteen of MiaAI Lab's private helper
names appear in our patches, and six of them — `_mxfp8_use_vision_emulation`,
`_ple_prefetch_rows`, `_dequant_nvfp4_rows`, `_qsa_as_fp8`, `_attach_draft_vocab` and
`_ple_dtype_is_nvfp4` among them — exist nowhere in upstream vLLM. Three environment variables we
use (`VLLM_MTP_DRAFT_VOCAB`, `VLLM_PLE_OFFLOAD_STEP_TIMEOUT`, `VLLM_PLE_PACKED_TABLE_DIR`) are also
absent from upstream vLLM and present in their patches. Two comments in our own shipped files still
point at *their* filenames (`files/build_draft_vocab.py`, `files/build_ple_packed_table.py`), which
was the tell.

**We got the licence line wrong, and we are sorry about it.** We published these patches as
Apache-2.0. Mia's work is **AGPL-3.0**, and we cannot relicense it. `LICENSE-NOTICE.md` now says so,
and we are correcting the licensing. That correction is the least we owe, and it is later than it
should have been.

We would also like to thank Mia's team for the *manner* of the work, which taught us something. Every
claim in that repository is measured on named hardware and reported with its failures attached —
`NV_ERR_NO_MEMORY` counts, peak driver memory against budget, the cells that did not work. And when
they took an idea from someone else they said so precisely: the FP8-KV approach is credited to
[`lancelind/qwen3.8-Flash-DGX`](https://github.com/lancelind/qwen3.8-Flash-DGX) as *"reimplemented
here against this image's own sources. That credit applies to this one patch; nothing else in this
repository derives from that project."* That sentence is the standard we are now trying to meet.
[`oscarmenendezgarcia`](https://github.com/oscarmenendezgarcia) is credited by name for the
Spanish-extended draft vocabulary and the audit gate. We noticed, and we copied the habit.

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

To be exact about the part we can claim:

- **The native-readout shim** (`shim/typesafe_native_shim.py`) — original to this repository.
- **The scoring and rescoring** (`rescore/`) — our harness invocation and per-item output.
- **The packaging** — `patches/MANIFEST.md` (per-file sha256 against the pristine image),
  `swanOne-vllm-patch.diff`, and the verification that applying it reproduces all nine files
  byte-for-byte.

Everything else in `patches/` is vLLM's or MiaAI Lab's.

## A note on licence compatibility

Because MiaAI Lab's recipe is AGPL-3.0-or-later, and this server is offered over a network, AGPL
section 13 applies to the derived patches: users interacting with it over a network are entitled to
the corresponding source. That is part of why the correction above matters, and not only a matter of
manners.
