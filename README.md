# SAM Image Classifier

Serverless image classification app built with AWS SAM.
Loads ONNX model weights from S3 and classifies images using ONNX Runtime + ConvNeXt Small.

## Architecture

```text
FastAPI (Docker, :8000) -> SAM local (host, :3000) -> Lambda (Docker)
                                                        -> S3/LocalStack (load model weights)
                                                        -> ONNX Runtime (inference)
                                                        -> return result
```

### Key Points

- **Model weights (.onnx) stored in S3** - swap models without redeploying Lambda
- **Classify Lambda uses Docker container** - ML libraries are too large for ZIP (250MB limit vs 10GB for containers)
- **FastAPI in Docker** - local testing app that proxies to SAM local
- **LocalStack** - emulates S3 locally, no AWS account needed
- **Lambda /tmp caching** - model downloaded once on cold start, reused on warm starts

## Prerequisites

```bash
# AWS CLI (also needed for LocalStack commands)
brew install awscli

# SAM CLI
brew install aws-sam-cli

# Docker Desktop (required for everything: LocalStack, FastAPI, SAM local, Lambda containers)
# https://www.docker.com/products/docker-desktop/

# Python 3.13 + uv
brew install uv
```

## Setup

```bash
# Install dependencies
uv sync

# Convert model from .pth to .onnx (if not already done)
uv run python models/convert_to_onnx.py
```

## Local Development

### Step 1: Start LocalStack + FastAPI

```bash
docker compose up -d
```

This starts:

- **LocalStack** on `http://localhost:4566` (emulates S3)
- **FastAPI** on `http://localhost:8000` (proxies to SAM local)

### Step 2: Create local S3 bucket

```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://sam-image-classifier-models --region ap-northeast-1
```

### Step 3: Upload model to local S3

```bash
aws --endpoint-url=http://localhost:4566 s3 cp onnx/weight.onnx \
  s3://sam-image-classifier-models/models/weight.onnx --region ap-northeast-1
```

### Step 4: Build Lambda

```bash
sam build
```

This builds the Docker image for `ClassifyFunction` with ONNX Runtime and dependencies.

### Step 5: Start SAM local API

```bash
sam local start-api --env-vars env.local.json
```

The `--env-vars env.local.json` flag tells SAM to use LocalStack endpoints instead of real AWS.
SAM local API will be available at `http://localhost:3000`.

### Step 6: Test it

Open `http://0.0.0.0:8000/docs` to test the `/classify` endpoint via Swagger UI.

Or test with curl:

```bash
curl -X POST http://localhost:8000/classify \
  -F "file=@dataset/images/good/sample.jpg"
```

### Step 7: Stop and delete everything

```bash
docker compose down -v --rmi all
```

SAM local needs to be stopped separately with `Ctrl+C`.

## Deploy to AWS

If you want to deploy to real AWS (optional):

### Step 1: Configure AWS credentials

```bash
aws configure
# AWS Access Key ID: (your key)
# AWS Secret Access Key: (your secret)
# Default region: ap-northeast-1
# Output format: json
```

### Step 2: Deploy

```bash
sam build && sam deploy --guided
```

You will be prompted for:

| Prompt | Recommended Value |
| --- | --- |
| Stack Name | sam-image-classifier |
| AWS Region | ap-northeast-1 |
| Confirm changes before deploy | Yes |
| Allow SAM CLI IAM role creation | Yes |
| Save arguments to config file | Yes |

After the first deploy, subsequent deploys only need:

```bash
sam build && sam deploy
```

### Step 3: Upload model to S3

```bash
uv run python s3/upload_model.py
```

## Project Structure

```text
├── template.yaml          # SAM template (all resource definitions)
├── samconfig.toml          # Deploy configuration
├── pyproject.toml          # Python project config (uv) - conversion scripts
├── docker-compose.yml      # LocalStack + FastAPI containers
├── env.local.json          # Environment variables for sam local (LocalStack)
│
├── lambda/                 # Lambda function (Docker container)
│   ├── Dockerfile
│   ├── pyproject.toml      # ONNX Runtime, Pillow, numpy
│   ├── uv.lock
│   └── app.py              # Load model from S3, classify image, return result
│
├── app/                    # FastAPI app (Docker container)
│   ├── Dockerfile          # Multi-stage build
│   ├── pyproject.toml      # FastAPI, httpx
│   ├── uv.lock
│   └── main.py             # Proxies to SAM local API
│
├── models/                 # Model scripts
│   └── convert_to_onnx.py  # Convert .pth to .onnx
│
├── s3/                     # S3 utility scripts
│   └── upload_model.py     # Upload ONNX model to S3
│
└── onnx/                   # ONNX model files
    └── weight.onnx         # Converted model weights
```

## API Endpoint

| Method | Path | Description |
| --- | --- | --- |
| POST | /classify | Upload an image file and classify it |

## SAM Concepts Covered

- **template.yaml** structure (Parameters, Globals, Resources, Outputs)
- **PackageType: Image** - Deploy Docker containers as Lambda
- **SAM Policy Templates** - S3ReadPolicy
- **Intrinsic functions** - !Ref, !Sub
- **sam build / sam deploy / sam local** commands
- **Lambda /tmp directory** for model caching on cold start
- **LocalStack** for fully offline local development

## Cleanup

### Local

```bash
docker compose down -v   # Stop LocalStack + FastAPI and remove data
```

### AWS

```bash
# Empty S3 bucket first (buckets with content can't be deleted)
aws s3 rm s3://$(aws cloudformation describe-stacks \
  --stack-name sam-image-classifier \
  --query 'Stacks[0].Outputs[?OutputKey==`ModelBucketName`].OutputValue' \
  --output text) --recursive

# Delete the CloudFormation stack and all resources
sam delete
```
