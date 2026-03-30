FROM public.ecr.aws/lambda/python:3.13

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
COPY pyproject.toml uv.lock ${LAMBDA_TASK_ROOT}/
ENV UV_PROJECT_ENVIRONMENT=/var/lang
RUN uv sync --no-dev --frozen --no-cache --inexact

# Copy application code
COPY app.py ${LAMBDA_TASK_ROOT}/

# Set Lambda handler
CMD ["app.lambda_handler"]
