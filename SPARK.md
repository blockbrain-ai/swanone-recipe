# Running swanOne on a DGX Spark

swanOne's filed run — 67.39 on JevBench's 231 public items — was measured on one NVIDIA DGX Spark. This
page is the Spark route. MiaAI Lab's single-Spark recipe serves the model, and the shim in this repository
answers each typed decision from one forward pass.

**Don't use the filing's serve command on a Spark.** JevBench issue #23, §4.2, was written for the
benchmark's x86 H100: it pins the amd64 build of the image, H100 memory settings and no packed PLE table,
so it will not start on a Spark as written. Use this page instead.

## What you need

- **One DGX Spark** (GB10, 128 GB unified memory). The model takes most of it. Our Spark run used
  72.86 GiB for weights and runtime, 1.67 GiB of peak activation and 21.11 GiB of KV cache, so nothing
  else large can run beside it.
- **Docker with the NVIDIA container runtime**, and permission to run it (your user in the `docker`
  group). DGX OS ships both.
- **Other GPU work stopped.** The recipe's memory reserve assumes about 7 GiB of other use on the Spark;
  `start.sh` prints the live figure and warns above 9.
- **About 150 GB of free disk:** the 99 GiB checkpoint, the 28.8 GB packed PLE table the recipe builds on
  its first start, and the image.
- **Python 3** for the shim. It uses the standard library only.

## 1. Serve the model with MiaAI Lab's recipe

**Read the recipe's "Safety rules" before the first start.** On a Spark, running out of unified memory
can hang the machine with no out-of-memory message. The recipe's `start.sh` budgets memory to prevent
that, and its watchdog stops the container if memory runs low.

```bash
git clone https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark
cd Qwen3.8-Flash-Next-Single-DGX-Spark
git checkout 6b50864              # the commit whose patch output is in our patches/
cp .env.sample .env
mkdir -p logs/archive && touch logs/archive/00000000T000000-container.log   # see the first note below
./download.sh                     # the ~99 GiB checkpoint; resumable
BIND=127.0.0.1 ./start.sh         # about 13 min to /health, then serves on 127.0.0.1:8888
```

- **The placeholder log file is needed on a fresh clone.** At `6b50864`, `start.sh` prunes old archived
  logs at the start of its launch step. With none there yet, that line fails under `set -euo pipefail`, and
  the script stops right after printing "Step 6: Launch", before any container starts, with nothing in its
  output naming the cause. The placeholder gives it something to list. A separate message earlier on,
  `start.sh: line 916: 09: value too great for base`, appears on every start and does not stop it.
- **The recipe is MiaAI Lab's**, licensed AGPL-3.0-or-later, and you run it under their terms. It builds
  the packed PLE table on its first start.
- **`BIND=127.0.0.1`** keeps the model off your network. By default the recipe binds every interface with
  no API key, and the shim sends none, so loopback is the setting that is both safe and compatible.
- **Port 8888:** `start.sh` refuses it while `comfy-h3.service` is running, if your Spark has it. Disable
  that service, or set another `PORT` and use the same port in step 2.
- **Reasoning** is on by default in the recipe's server. The shim switches it off in each request, so
  there is nothing to change.
- **The exact image (optional):** the recipe's `.env` names the image by tag, and a tag can move. Our run
  used the arm64 build `sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`, which
  the tag's multi-arch digest points to today. To pin it, set
  `IMAGE="vllm/vllm-openai@sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8"` in
  `.env`; Docker picks the arm64 build from it.
- **More concurrent decisions:** the recipe's default is four sequences, which is plenty for requests sent
  one at a time, as the benchmark sends them. For eight, the recipe's `.env.sample` requires
  `HOST_RESERVE_GIB=28` alongside: `BIND=127.0.0.1 MAX_NUM_SEQS=8 HOST_RESERVE_GIB=28 ./start.sh`.

**The weights.** `download.sh` fetches the checkpoint's current `main`. Our run used revision
`925d7be6c14c6c9442ef83e8f05b5a3c39304f69`, which was still `main` on 2026-09-23. To check before you
download:

```bash
curl -s https://huggingface.co/api/models/Mia-AiLab/Qwen3.8-Flash-Next-NVFP4 | grep -o '"sha":"[0-9a-f]*"'
```

If it prints a different sha, your weights differ from the ones our numbers describe.

**Our measured run's server settings** were a 262,144-token context, MTP with 3 speculative tokens, an fp8
KV cache, eight sequences, 2,048 batched tokens and a memory budget of 0.786 on a 121.69 GiB Spark. The
recipe's defaults are the same except for the sequence count, and 0.786 is the budget `start.sh` derives
on that Spark with its default 26 GiB reserve. Our server came up with eight sequences at that reserve;
the recipe's own measurement found that the combination can fail at launch, which is why step 1 follows
its advice instead. Our server listened on a different port; nothing depends on the port.

## 2. Start the shim

```bash
git clone https://github.com/blockbrain-ai/swanone-recipe
cd swanone-recipe
SHIM_VLLM=http://127.0.0.1:8888/v1/chat/completions \
SHIM_MODEL=qwen3.8-flash-next \
SHIM_PORT=8009 \
python3 shim/typesafe_native_shim.py
```

`SHIM_MODEL` must match the recipe's `SERVED_MODEL_NAME`, which is `qwen3.8-flash-next` unless you
changed it. The shim listens on `127.0.0.1` only, so call it from the Spark itself or through an SSH
tunnel.

## 3. Send a decision

The first request compiles kernels, so send one to warm up before you time anything.

```bash
curl -s http://127.0.0.1:8009/v1/systemone -H 'Content-Type: application/json' -d '{
  "state": "Customer message: the parcel arrived crushed and the glass inside is broken.",
  "questions": {"decision": {
    "type": "choice",
    "instructions": "Which team should handle this message?",
    "criteria": {
      "returns":  "damaged or wrong items, refunds and replacements",
      "billing":  "charges, invoices and payment problems",
      "delivery": "late or missing parcels and tracking"
    }
  }}
}'
```

The reply carries the answer and its token counts:

| field | what it holds |
|---|---|
| `answers.decision.choice` | the label with the highest probability |
| `answers.decision.probabilities` | one probability per label, summing to 1 |
| `usage.completion_tokens` | 1 — the decision is read, not written |

The other two decision types use the same request:

- **Yes or no:** `"type": "noul"`, with `"criteria": {"true": "…", "false": "…"}`. The reply is
  `{"type": "noul", "noul": <probability of true>}`.
- **A score:** `"type": "score"`, with `"criteria"` as a list of level descriptions. Labels come back
  as `"0"`, `"1"`, … by position, each with a probability.

A decision can have up to ten options, lettered A to J. `state` can be text or a JSON object.

## 4. Score it on JevBench's public items (optional)

Use the command under "Step 4" in the [README](README.md), with `--endpoint http://127.0.0.1:8009`.

## What has been checked

**This page was run end to end on 2026-09-23, on one DGX Spark:**

- A fresh clone of the recipe at `6b50864`. The server was healthy after 762 s.
- The shim answered all three decision types, each with one output token.
- JevBench's harness over the 231 public items: 206 correct (easy 48/48, standard 68/72, hard 90/111),
  with 1 output token on every item. Our filed run scored 204, and this run agrees with it on 221 of the
  231 items.

**Two things differed from a new Spark.** The checkpoint and the packed PLE table were already on the
machine, so `download.sh` verified the files by sha256 instead of downloading them, and `start.sh` did not
rebuild the table. The shim also ran on another port, because 8009 was already in use.

The settings under "Our measured run's server settings" in step 1 are the ones that produced the filed
run; step 1's default command differs from them only in the sequence count. The step 1 commands are
MiaAI Lab's, from their README and `.env.sample` at `6b50864`, plus the placeholder line. If a step fails
for you, open an issue here.

## The filing's docker command

JevBench issue #23, §4.2, mounts the nine files in `patches/` into a single `docker run`. It pins the amd64
build of the image (the arm64 build is `@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`)
and uses H100 memory settings with no packed PLE table. Adapting it to a Spark is not documented here;
step 1 is the Spark route.
