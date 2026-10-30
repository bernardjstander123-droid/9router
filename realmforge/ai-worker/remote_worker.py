"""RealmForge remote Gradio inference adapter.
Requires a real, user-authorized Gradio endpoint and matching API name.
Never treats an unconfigured endpoint as operational.
"""
import os
from pathlib import Path
from gradio_client import Client, handle_file

def generate(prompt: str, endpoint: str | None = None, api_name: str | None = None):
    endpoint = endpoint or os.getenv("REALMFORGE_GRADIO_ENDPOINT")
    api_name = api_name or os.getenv("REALMFORGE_GRADIO_API_NAME")
    if not endpoint or not api_name:
        raise RuntimeError("Set REALMFORGE_GRADIO_ENDPOINT and REALMFORGE_GRADIO_API_NAME")
    token = os.getenv("HF_TOKEN")
    client = Client(endpoint, token=token if token else None)
    result = client.predict(prompt, api_name=api_name)
    return result

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--prompt",required=True)
    args=parser.parse_args()
    print(generate(args.prompt))
