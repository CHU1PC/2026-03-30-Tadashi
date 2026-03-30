import base64
import io
import json
import os

import boto3  # type: ignore
import numpy as np
import onnxruntime as ort  # type: ignore
from PIL import Image

MODEL_BUCKET = os.environ["MODEL_BUCKET"]
MODEL_KEY = os.environ["MODEL_KEY"]

LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT") or None
s3 = boto3.client("s3", endpoint_url=LOCALSTACK_ENDPOINT)  # type: ignore

# Class labels (corresponding to model output indices)
CLASS_LABELS = ["bad", "good"]


def _load_model_from_s3() -> ort.InferenceSession:
    """
    Download ONNX model from S3 and create an inference session.

    /tmp is the only writable directory in Lambda (up to 10GB).
    Downloaded once on cold start and cached for warm starts.
    """
    local_model_path = "/tmp/model.onnx"

    if not os.path.exists(local_model_path):
        print(f"Downloading model from S3: s3://{MODEL_BUCKET}/{MODEL_KEY}")
        s3.download_file(MODEL_BUCKET, MODEL_KEY, local_model_path)  # type: ignore
        size_mb = os.path.getsize(local_model_path) / (1024 * 1024)
        print(f"Download complete: {size_mb:.1f} MB")

    return ort.InferenceSession(local_model_path)


# Load model on cold start
session = _load_model_from_s3()
input_name: str = session.get_inputs()[0].name  # type: ignore[no-untyped-call]


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Preprocess image for ConvNeXt Small input.

    Input spec:
      - Size: 224x224 pixels
      - Channels: RGB (3 channels)
      - Normalization: ImageNet mean/std
      - Shape: (1, 3, 224, 224) - batch x channels x height x width
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((224, 224))

    # Convert to numpy array (H, W, C) -> (C, H, W)
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = img_array.transpose(2, 0, 1)

    # ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
    img_array = (img_array - mean) / std

    # Add batch dimension: (3, 224, 224) -> (1, 3, 224, 224)
    return np.expand_dims(img_array, axis=0)


def softmax(x: np.ndarray) -> np.ndarray:
    """Softmax: convert outputs to per-class probabilities."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


def lambda_handler(event: dict[str, str], context: object) -> dict[str, int | str | dict[str, str]]:
    """Receive base64 image, classify with ONNX Runtime."""
    try:
        body = json.loads(event["body"])
    except (TypeError, json.JSONDecodeError):
        return _response(400, {"error": "Invalid request body"})

    image_b64 = body.get("image")
    if not image_b64:
        return _response(400, {"error": "image is required (base64 encoded)"})

    # Decode base64 image
    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        return _response(400, {"error": "Invalid base64 image"})

    # Preprocess and classify
    input_data = preprocess_image(image_bytes)
    raw_outputs: list[np.ndarray] = session.run(None, {input_name: input_data})  # type: ignore[reportUnknownMemberType]
    probabilities = softmax(raw_outputs[0][0])

    sorted_indices: list[int] = np.argsort(probabilities)[::-1].tolist()
    predictions: list[dict[str, str | float]] = [
        {
            "label": CLASS_LABELS[idx],
            "confidence": round(float(probabilities[idx]), 4),
        }
        for idx in sorted_indices
    ]

    return _response(200, {"predictions": predictions})


def _response(status_code: int, body: dict[str, object]) -> dict[str, int | str | dict[str, str]]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("CORS_ORIGIN", "*"),
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
