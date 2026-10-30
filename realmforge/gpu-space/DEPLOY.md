# Deploy and confirm
1. Create a Hugging Face Space with the Gradio SDK and ZeroGPU hardware (subject to account eligibility).
2. Upload README.md, app.py, requirements.txt from this directory into the Space root.
3. Wait for the Space build to finish and show Running.
4. Invoke the 'Verify GPU' button or the /verify_gpu API.
5. Confirm gpu_verified=true, a nonempty device name and numeric matrix_checksum.
6. Set REALMFORGE_GRADIO_ENDPOINT to your actual owner/space identifier in RealmForge.
A running Space status alone does not verify GPU execution. This code does not perform Wan video inference.
