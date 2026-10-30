# RealmForge remote GPU connection
No Desktop Commander required. Choose a Gradio-hosted model worker you own or are authorized to use, including a compatible Hugging Face Space. The API schema varies by worker, so discover the correct endpoint and argument contract before rendering.

```bash
python -m pip install -r realmforge/ai-worker/requirements-remote.txt
export REALMFORGE_GRADIO_ENDPOINT='owner/space-name'
python realmforge/ai-worker/check_remote_worker.py
export REALMFORGE_GRADIO_API_NAME='/predict'
python realmforge/ai-worker/remote_worker.py --prompt 'Cinematic storm over a ruined citadel'
```

The example '/predict' is a placeholder, not a verified endpoint. Some video Spaces require parameters other than a single prompt and need an adapter matching their actual API schema. ZeroGPU has daily quotas, and not all Spaces allow API access or run Wan 2.2. Never commit HF_TOKEN to Git. Do not assume model weights are installed or an MP4 was generated until output is downloaded and inspected.
