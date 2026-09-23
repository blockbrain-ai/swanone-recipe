# swanOne patch set — MANIFEST

Nine files, Apache-2.0. They are modified vLLM source and **MiaAI Lab's patch output** — their
generators reproduce all nine byte-for-byte. See `../LICENSE-NOTICE.md` and `../CREDITS.md`. Mount each
file over the target path inside `vllm/vllm-openai:qwen38-flash-next`. Line counts are
`git diff --no-index --numstat` against the pre-patch original; the in-image column is the sha256 of
the *unpatched* file inside the published image, verified with `docker run --rm` while preparing the
filing.

| # | file | target inside the image | changed lines | in-image sha256 (16) | patched sha256 (full) |
|---|---|---|---|---|---|
| 1 | `ple_layer_patched.py` | `/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py` | **544** | `a71144c1d36e06f2` | `f43070c8d43180abb8bdc4e22691ce6c7bc940e7a13b69b0b031e1995e6d9a6f` |
| 2 | `qsa_ops_patched.py` | `/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ops/qsa.py` | **73** | `c4ffe3674cafa0ce` | `0669d6334f58a624c89c15f3e46c90f28e59b0b913507101dec1c5765e3c3b12` |
| 3 | `qsa_nvidia_patched.py` | `/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/qsa.py` | **76** | `748addc85efaa8f7` | `ee5de40742ad48a6064ea24b99a285ff69c47d57bbb170f57c4eef71567a1df3` |
| 4 | `mtp_patched.py` | `/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/mtp.py` | **85** | `7735cee47d0d1e47` | `8da66d9f48bd93c935d74e2635c45483dc999c87b94bc4ce828e727eb1713349` |
| 5 | `modelopt_patched.py` | `/usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/quantization/modelopt.py` | **104** | `3f3ca743fd3c66d7` | `2ad524d557971518564cc3de8e4630b0a822199ad7c45a442ca9a5874c82c8fb` |
| 6 | `ple_offload/ple_offload_layer.py` | `/usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/ple_offload_layer.py` | **13** | `9c0ab215116d0e1b` | `8a0906467764b3fc9b88badedafdecb85880360f5380e314c1f3e6194bdd2df4` |
| 7 | `ple_offload/worker.py` | `/usr/local/lib/python3.12/dist-packages/vllm/v1/ple_offload/worker.py` | **114** | `f93a0a8c40ee3c53` | `b9919f4c42ede71ba0582f8fe40cd905d848547c9135bca7fdbb72c0cbf43cf0` |
| 8 | `ple_offload/connector.py` | `/usr/local/lib/python3.12/dist-packages/vllm/v1/ple_offload/connector.py` | **79** | `b911d00cf4a39556` | `9ca076235bb523128ea774215e2d6a42d1a6bfe45ffa3c91323b08dc99814979` |
| 9 | `ple_offload/protocol.py` | `/usr/local/lib/python3.12/dist-packages/vllm/v1/ple_offload/protocol.py` | **5** | `3e943753e6427c5b` | `cf64579ca3cf1daa9ff617a1a8c4690e0db2d1d7412a74e3b8b32629492a05da` |

**Total changed lines: 1093 across 9 files.**

## Pre-patch originals

The originals used to produce those diffs are shipped beside the patch so the diff can be reproduced:
`patches/*.orig` (5 files) and `patches/orig/` (the 4 `ple_offload` files). They are byte-identical to
the files inside the published image.

## Applying

```bash
docker run ... \
  -v <PATCHDIR>/ple_layer_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py \
  -v <PATCHDIR>/qsa_ops_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ops/qsa.py \
  -v <PATCHDIR>/qsa_nvidia_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/qsa.py \
  -v <PATCHDIR>/mtp_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/mtp.py \
  -v <PATCHDIR>/modelopt_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/quantization/modelopt.py \
  -v <PATCHDIR>/ple_offload/ple_offload_layer.py:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/layers/ple_offload_layer.py \
  -v <PATCHDIR>/ple_offload/worker.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/ple_offload/worker.py \
  -v <PATCHDIR>/ple_offload/connector.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/ple_offload/connector.py \
  -v <PATCHDIR>/ple_offload/protocol.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/ple_offload/protocol.py \
  vllm/vllm-openai:qwen38-flash-next@sha256:0aea3024...
```

`--gpu-memory-utilization` must be **0.90** on a 94 GB card (0.786 fails). See the filing, §4.3.


## Companion asset (not part of the patch)

`../assets/draft_vocab_en_code_47k.txt` — 47,172 tokens, 274,622 bytes, sha256
`ee819d2560b52ba1351acdd1c4a0244b77bb60694a7660c6363097a482b0afb5`. Mounted to `/root/draft_vocab.txt`
and read only by our patched `mtp.py` via `VLLM_MTP_DRAFT_VOCAB`. **Not in the image** (verified: the path
does not exist in a `docker run --rm` of the published image, and the unpatched image has no reference to
the variable). **Produced by** MiaAI Lab's `build_draft_vocab.py` (their script, AGPL-3.0, not
redistributed here) **from the public checkpoint's tokenizer** — the file itself is a list of 47,172
integer token ids and carries no copyrightable expression of theirs. **Required only if MTP speculative
decoding is kept** — see the filing §4.6 for how to drop it.

## The whole patch as one file

`../swanOne-vllm-patch.diff` — 1646 lines, a single unified diff of all nine files against the published
amd64 image. **Verified: applying it to pristine copies reproduces all nine patched files byte-for-byte
(9/9).**

```bash
patch -p1 -d / < swanOne-vllm-patch.diff
```
