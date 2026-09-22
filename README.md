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
