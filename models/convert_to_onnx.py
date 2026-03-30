import argparse
import sys
from pathlib import Path

import torch
from torchvision.models import convnext_small  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert ConvNeXt Small (.pth) to ONNX")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "onnx" / "convnext_small_pretrained_best.pth",
        help="Path to input .pth file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "onnx" / "weight.onnx",
        help="Path to output .onnx file",
    )
    parser.add_argument("--num-classes", type=int, default=2, help="Number of classification classes")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found")
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # 1. Create model and load weights
    print("1. Creating ConvNeXt Small model and loading weights...")
    model = convnext_small(num_classes=args.num_classes)
    state_dict = torch.load(args.input, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    # 2. Export to ONNX
    print("2. Exporting to ONNX...")
    dummy_input = torch.randn(1, 3, 224, 224)

    with torch.no_grad():
        torch.onnx.export(  # type: ignore
            model,
            (dummy_input,),
            str(args.output),
            export_params=True,
            opset_version=18,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={
                "input": {0: "batch_size"},
                "output": {0: "batch_size"},
            },
            external_data=False,
        )

    size_mb = args.output.stat().st_size / (1024 * 1024)
    print(f"\nConversion complete: {args.output} ({size_mb:.1f} MB)")
    print(f"Output classes: {args.num_classes}")
    print("To upload to S3:")
    print(f"  aws s3 cp {args.output} s3://<ModelBucketName>/models/weight.onnx")


if __name__ == "__main__":
    main()
