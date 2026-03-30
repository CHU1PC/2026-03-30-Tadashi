"""
FastAPI app for SAM Image Classifier.

Proxies requests to SAM local (http://localhost:3000).

Usage:
  uv run fastapi dev
"""

import base64
import os

import httpx
from fastapi import FastAPI, File, UploadFile

app = FastAPI(title="SAM Image Classifier")

SAM_API_URL = os.environ.get("SAM_API_URL", "http://localhost:3000")


@app.post("/classify")
async def classify(file: UploadFile = File(...)):
    """
    Receive image, send to SAM local Lambda for classification.
    Lambda loads model weights from S3 and runs ONNX inference.
    """
    image_bytes = await file.read()
    image_b64 = base64.b64encode(image_bytes).decode()

    async with httpx.AsyncClient(timeout=300) as client:
        res = await client.post(
            f"{SAM_API_URL}/classify",
            json={"image": image_b64},
        )
        return res.json()
