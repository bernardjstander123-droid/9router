import gradio as gr
import spaces
import torch

@spaces.GPU(duration=60)
def verify_gpu():
    if not torch.cuda.is_available():
        raise gr.Error("CUDA GPU unavailable; worker NOT verified")
    device = torch.device("cuda")
    a = torch.randn((512, 512), device=device)
    b = torch.randn((512, 512), device=device)
    c = a @ b
    torch.cuda.synchronize()
    return {"gpu_verified": True, "device": torch.cuda.get_device_name(0),
            "torch_cuda": torch.version.cuda,
            "matrix_checksum": round(float(c.sum().item()), 4)}

with gr.Blocks(title="RealmForge GPU Worker") as demo:
    gr.Markdown("# RealmForge GPU Worker\nPress Verify to run a real CUDA matrix multiplication.")
    output=gr.JSON(label="GPU verification")
    gr.Button("Verify GPU").click(fn=verify_gpu, inputs=[], outputs=output, api_name="verify_gpu")
demo.queue().launch()
