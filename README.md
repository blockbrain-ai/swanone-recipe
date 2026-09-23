# swanOne bench-request submission package

Everything needed to run the filing. Companion document: `../SUBMISSION-DRAFT-swanOne.md`.

## Built on MiaAI Lab's recipe — please read

None of this would run without **[MiaAI Lab](https://x.com/MiaAI_lab)**'s
[`Qwen3.8-Flash-Next-Single-DGX-Spark`](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark).
Serving a 99 GiB NVFP4 model from one Spark's unified memory is their work: the PLE CPU-offload
machinery and the GB10 stream-memory diagnosis behind it, the memory-mapped packed PLE table, the MTP
draft-vocabulary index, the MXFP8 kernel fallbacks and the FP8-KV cache path. **Thank you, Mia and
team** — the measurements, the failure counts and the willingness to publish the cells that did not
work are what made this possible from the outside.

To be exact: **the nine files in `patches/` are their patch output, not our engineering.** Their
generators reproduce all nine of our files byte-for-byte. What is ours is the packaging and the shim.

Their recipe licenses its **generators** under AGPL-3.0-or-later, but it also states that the files they
generate "keep vLLM's own Apache-2.0 headers and remain Apache-2.0 works" — and our nine files are that
output. So `patches/` is **Apache-2.0**, and **none of their AGPL scripts are redistributed here**.
`shim/` is ours and is MIT. We have asked them to confirm that reading. `LICENSE-NOTICE.md` has the
detail and `CREDITS.md` names everyone whose work is here.

    patches/    the nine patched vLLM files, each mounted over an absolute path in the image,
                with the pre-patch originals so the diff is reproducible
                  patches/MANIFEST.md   targets, changed-line counts, sha256s, apply command
                  patches/*.orig        pre-patch originals for the 5 top-level files
                  patches/orig/         pre-patch originals for the 4 ple_offload files
    assets/     draft_vocab_en_code_47k.txt — 47,172-token MTP draft vocabulary (optional; see §4.6)
    shim/       typesafe_native_shim.py — implements /v1/systemone over vLLM logprobs

Order of operations: patches -> server (filing §4.2) -> shim (filing §3) -> harness (filing §5).

Nothing here needs credentials. Do not commit a HuggingFace token into this tree.

## How to use this repository

Everything lives under three directories, and the filing refers to them as placeholders you must
substitute before pasting any command. **A literal paste fails**, because `<` is a shell redirect.

| placeholder | set it to |
|---|---|
| `<PATCHDIR>` | `.../swanone-recipe/patches` |
| `<ASSETDIR>` | `.../swanone-recipe/assets` |
| `<HFCACHE>`  | a Hugging Face cache directory containing `Mia-AiLab/Qwen3.8-Flash-Next-NVFP4` |
| `<PLECACHE>` | a directory for the PLE table cache (may be empty) |

For example, with this repository cloned to `/srv/swanone-recipe`:

    export PATCHDIR=/srv/swanone-recipe/patches
    export ASSETDIR=/srv/swanone-recipe/assets

`patches/MANIFEST.md` lists, for each of the nine files, its mount target in the image, its changed-line
count, and its sha256 — and gives the apply command. The nine files are mounted **over** the image's own
copies; they are not baked in.

Order of operations: **patches -> server -> shim -> harness.** The server alone does not speak the
benchmark's wire format; `shim/typesafe_native_shim.py` is what serves `/v1/systemone`, and it listens on
**port 8009**.

## Step 4, written out in full — the filing's §5 was only a flag fragment

Filing §5 gives the harness flags but no invocation, which is our error. It is `jevbench`'s own CLI and
the dataset is yours to choose, so the complete command is:

    python3 -m jevbench.cli run \
      --tasks <YOUR>/datasets/public/easy.jsonl,<YOUR>/datasets/public/original.jsonl,<YOUR>/datasets/public/hard.jsonl \
      --adapter typesafe --endpoint http://127.0.0.1:8009 --key-env '' \
      --model swanone --cost-basis self_hosted_gpu --reserve-usd 0 \
      --results  <OUT>/results.jsonl \
      --raw-dir  <OUT>/raw \
      --ledger   <OUT>/ledger.jsonl \
      --manifest <OUT>/manifest.json \
      --run-label swanone --delay-s 0

`--endpoint` must match whatever `SHIM_PORT` the shim was started with (§3 uses 8009). Add
`--max-model-len`-style limits on your side as your harness requires; nothing in the shim depends on it.

**Two practical notes from running this ourselves on an H100 NVL:**

- **`git` is not installed in the published image; `patch` is.** So the §8.3 route
  (`patch -p1 -d / < swanOne-vllm-patch.diff`) works inside the container, while a `git clone` does not.
- **`--max-model-len 4096` is below this benchmark's documented hard tier**, which is described as
  *"long multi-condition policy documents (2–6k tokens)"*. The longest **public** prompt is 3,946 tokens,
  but the held-out items are not public, and the benchmark's own rule is that *"an input over a system's
  documented context limit"* counts **wrong**. If your card can take a larger context, prefer it — we were
  unable to start 8192 at `--gpu-memory-utilization 0.90` with `--max-num-seqs 6` on a 94 GB card, and the
  4096 in §4.2 is what we validated.

Nothing here requires credentials. If you would rather have a tarball or a `git diff`, open an issue on the
benchmark repository and ask — we will put it wherever is easiest for you.
