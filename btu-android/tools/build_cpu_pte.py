"""Export BTU's small CPU decoder to ExecuTorch.

This is an inference/export smoke-test model, NOT a trained image generator.
Install compatible PyTorch and ExecuTorch versions in a Python environment.
"""
import argparse
from pathlib import Path

import torch
from torch import nn
from executorch.exir import to_edge_transform_and_lower
from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner


class BTUDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(16, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 3, 3, padding=1)

    def forward(self, x):
        return torch.sigmoid(self.conv2(torch.relu(self.conv1(x))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, help="Trusted BTUDecoder state_dict checkpoint")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("btu_cinema_inference.pte"))
    args = parser.parse_args()

    torch.manual_seed(42)
    model = BTUDecoder().eval()
    if args.weights:
        state = torch.load(args.weights, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)
    else:
        print("WARNING: Random weights; this is NOT photorealistic image generation.")

    example = (torch.randn(1, 16, 64, 64),)
    with torch.inference_mode():
        output = model(*example)
    if tuple(output.shape) != (1, 3, 64, 64):
        raise RuntimeError(f"Unexpected output shape: {tuple(output.shape)}")
    if not torch.isfinite(output).all().item():
        raise RuntimeError("Decoder output contains NaN or infinity")

    exported = torch.export.export(model, example)
    program = to_edge_transform_and_lower(
        exported, partitioner=[XnnpackPartitioner()]
    ).to_executorch()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(program.buffer)
    if args.output.stat().st_size == 0:
        raise RuntimeError("Export produced an empty .pte file")
    print(f"Exported {args.output} ({args.output.stat().st_size} bytes), shape={tuple(output.shape)}")
    print("NOTE: Android ExecuTorch runtime execution still requires separate verification.")


if __name__ == "__main__":
    main()
