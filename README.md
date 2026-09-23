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
The shim's approach — reading the answer from the model's probabilities over the option letters in one
forward pass — is [NInfer](https://github.com/igorls/ninfer)'s; the code is ours.

Their recipe licenses its **generators** under AGPL-3.0-or-later, but it also states that the files they
generate "keep vLLM's own Apache-2.0 headers and remain Apache-2.0 works" — and our nine files are that
output. So `patches/` is **Apache-2.0**, and **none of their AGPL scripts are redistributed here**.
`shim/` is ours and is MIT. That reading is ours, from their README — we have not agreed it with them
directly. `LICENSE-NOTICE.md` has the detail and `CREDITS.md` names everyone whose work is here.

    patches/    the nine patched vLLM files, each mounted over an absolute path in the image,
                with the pre-patch originals so the diff is reproducible
                  patches/MANIFEST.md   targets, changed-line counts, sha256s, apply command
                  patches/*.orig        pre-patch originals for the 5 top-level files
                  patches/orig/         pre-patch originals for the 4 ple_offload files
    assets/     draft_vocab_en_code_47k.txt — 47,172-token MTP draft vocabulary (optional; see §4.6)
    shim/       typesafe_native_shim.py — implements /v1/systemone over vLLM logprobs
    rescore/    the filed run, per item, and its v1.3 rescore (see rescore/README.md)
    baselines/  the same model writing its answer out, reasoning on and off (see baselines/README.md)

Order of operations: patches -> server (filing §4.2) -> shim (filing §3) -> harness (filing §5).

Nothing here needs credentials. Do not commit a HuggingFace token into this tree.

## What one decision costs

Same model, JevBench's public items, tokens generated per decision:

| how the decision is answered | tokens generated per decision |
|---|---:|
| reasoning on, answer written out | 714.3 on average — 13 of 173 stopped at the 4,096-token cap |
| reasoning off, answer written as JSON | 49.9 on average |
| the one-token readout in `shim/` | 1 — 231 of 231 |

The prompt (about 700 tokens) is read in every case; the readout removes the generation. Re-derive all
three with `python3 baselines/tokens.py`.

## Where it landed, category by category

JevBench publishes per-item outcomes for the systems it has run on the same 231 public items. The filed
run is lined up against 40 of them, item for item:

| slice | items | ours | systems ahead | tied | max of the 40 |
|---|---:|---:|---:|---:|---:|
| all public items | 231 | 204 | 2 | 0 | 226 |
| easy | 48 | 48 | 0 | 28 | 48 |
| standard | 72 | 70 | 6 | 4 | 71 |
| hard | 111 | 86 | 2 | 0 | 107 |

| category | items | ours | systems ahead | tied | max of the 40 |
|---|---:|---:|---:|---:|---:|
| adequacy | 12 | 10 | 12 | 3 | 12 |
| adversarial | 6 | 6 | 0 | 14 | 6 |
| ambiguous | 7 | 6 | 5 | 3 | 7 |
| extraction | 24 | 24 | 0 | 23 | 24 |
| fact | 12 | 12 | 0 | 29 | 12 |
| intent | 24 | 24 | 0 | 16 | 24 |
| judge_hard | 17 | 12 | 14 | 1 | 16 |
| long_policy | 19 | 16 | 2 | 0 | 19 |
| multi_hop | 18 | 15 | 3 | 3 | 18 |
| ordinal | 12 | 12 | 0 | 24 | 12 |
| policy | 12 | 12 | 0 | 8 | 12 |
| probability | 10 | 8 | 4 | 2 | 10 |
| routing | 12 | 12 | 0 | 16 | 12 |
| routing_hard | 5 | 5 | 0 | 23 | 5 |
| temporal_numeric | 15 | 6 | 6 | 5 | 14 |
| tool_selection | 12 | 12 | 0 | 37 | 12 |
| tradeoff | 6 | 5 | 4 | 1 | 6 |
| trap | 8 | 7 | 16 | 6 | 8 |

The two systems ahead overall and on the hard tier are DeepSeek V4.1 Flash (226 of 231) and GPT-5.6 Luna
at low reasoning effort (225), both frontier API models, and both at 107 of 111 on the hard tier.

This is accuracy on the public items, not the board's Intelligence axis, which weights the tiers, corrects
for chance and includes the judge tier. We developed the readout on these same items, so our side of every
row is an upper bound; the 40 are JevBench's own runs. One item moves a small category by 4–20
points. Re-derive the tables with `python3 rescore/category_split.py
<jevbench>/results/v1.2/jevbench-v1.2-per-task.json`, from the board repository at `fd51755`.

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
