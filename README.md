# swanOne bench-request submission package

Everything needed to run the filing. Companion document: `../SUBMISSION-DRAFT-swanOne.md`.

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

Nothing here requires credentials. If you would rather have a tarball or a `git diff`, open an issue on the
benchmark repository and ask — we will put it wherever is easiest for you.
