import argparse
import sys
from pathlib import Path

import boto3  # type: ignore
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "onnx" / "weight.onnx"


def get_bucket_name_from_stack() -> str | None:
    """Get the model bucket name from the CloudFormation stack outputs."""
    cf = boto3.client("cloudformation")  # type: ignore
    try:
        response = cf.describe_stacks(StackName="sam-image-classifier")  # type: ignore
        outputs = response["Stacks"][0]["Outputs"]  # type: ignore
        for output in outputs:  # type: ignore
            if output["OutputKey"] == "ModelBucketName":
                return output["OutputValue"]  # type: ignore
    except Exception as e:
        logger.error(f"Failed to get bucket name from stack: {e}")
    return None


def upload_to_s3(file_path: Path, bucket_name: str, s3_key: str) -> None:
    """Upload a model file to S3."""
    size_mb = file_path.stat().st_size / (1024 * 1024)
    logger.info(f"Uploading: {file_path.name} ({size_mb:.1f} MB) -> s3://{bucket_name}/{s3_key}")
    s3 = boto3.client("s3")  # type: ignore
    s3.upload_file(str(file_path), bucket_name, s3_key)  # type: ignore
    logger.success("Upload complete!")


def main():
    parser = argparse.ArgumentParser(description="Upload an ONNX model to S3")
    parser.add_argument("--file", type=Path, default=DEFAULT_MODEL_PATH, help="Path to the .onnx file to upload")
    parser.add_argument("--bucket", help="S3 bucket name (auto-detected from stack if omitted)")
    parser.add_argument("--key", default="models/weights.onnx", help="S3 key to upload to")
    args = parser.parse_args()

    if not args.file.exists():
        logger.error(f"File not found: {args.file}")
        sys.exit(1)

    bucket_name = args.bucket or get_bucket_name_from_stack()
    if not bucket_name:
        logger.error("Please specify a bucket name (--bucket) or deploy the stack first (sam deploy)")
        sys.exit(1)

    upload_to_s3(args.file, bucket_name, args.key)
    logger.success(f"Model accessible at: s3://{bucket_name}/{args.key}")


if __name__ == "__main__":
    main()
