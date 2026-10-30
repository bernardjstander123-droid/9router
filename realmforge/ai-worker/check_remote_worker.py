"""Check remote Gradio endpoint metadata without submitting paid inference."""
import os
from gradio_client import Client
endpoint=os.getenv("REALMFORGE_GRADIO_ENDPOINT")
if not endpoint: raise SystemExit("UNCONFIGURED: REALMFORGE_GRADIO_ENDPOINT is missing")
client=Client(endpoint,token=os.getenv("HF_TOKEN") or None)
print(client.view_api(print_info=False))
print("REMOTE API METADATA ACCESSIBLE; generation not yet verified")
