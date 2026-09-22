# Licensing

The nine patched files under `patches/` are modifications of **vLLM** source, which is
**Apache-2.0**. They retain vLLM's own headers and are published here as patches under the same
licence, with attribution. `patches/*.orig` and `patches/orig/` are the unmodified upstream files,
included so the diff is reproducible.

`shim/typesafe_native_shim.py` is original to this repository, Apache-2.0.

The model weights are **not** here. They are `Mia-AiLab/Qwen3.8-Flash-Next-NVFP4` (Apache-2.0) and
`Mia-AiLab/Qwen3.8-Flash-Next-NVFP4` is fetched from Hugging Face at run time.
