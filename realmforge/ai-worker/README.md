# RealmForge Wan 2.2 5B AI Video Worker
This is a **real generative model installation script**, not the model weights themselves.

## GPU machine install
Install ComfyUI on a supported GPU machine first. Use Python 3.10+ and the correct PyTorch build for its accelerator.

```bash
python -m pip install -U huggingface_hub
python realmforge/ai-worker/install_wan22_5b.py --comfyui /path/to/ComfyUI
python realmforge/ai-worker/verify_wan22_5b.py --comfyui /path/to/ComfyUI
```

The script downloads the 5B diffusion model, FP8 UMT5 text encoder and Wan 2.2 VAE from Comfy-Org/Wan-2.2. Large downloads need substantial free disk space and network connectivity. This does not install weights on an Android phone.

Open ComfyUI, use the Wan 2.2 5B Video Generation template and verify a short generation. Documentation: https://comfyanonymous.github.io/ComfyUI_examples/wan22/

Status: Installer and file-presence verification scripts committed. **No weights downloaded or inference run verified** in the GitHub repository. The Android application still needs a worker API bridge to request renders.
