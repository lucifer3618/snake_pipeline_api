# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS builder

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --upgrade pip setuptools wheel

COPY requirements.txt ./requirements.txt

# Install the selected PyTorch build first. The normal requirements install then
# sees torch/torchvision as satisfied instead of replacing them with other wheels.
# Ultralytics declares the GUI OpenCV distribution as a dependency. Remove it
# and reinstall the headless distribution last so it owns the cv2 extension.
RUN pip install --index-url "$TORCH_INDEX_URL" \
        torch==2.5.1 torchvision==0.20.1 \
    && pip install -r requirements.txt \
    && pip uninstall --yes opencv-python \
    && pip install --force-reinstall --no-deps "opencv-python-headless>=4.10"


FROM python:3.12-slim-bookworm AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DEVICE=cpu \
    PRELOAD_MODELS=true \
    PORT=8000

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "$APP_GID" app \
    && useradd --uid "$APP_UID" --gid "$APP_GID" --create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY --chown=app:app app ./app
COPY --chown=app:app pipeline ./pipeline

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/api/v1/health', headers={'X-API-Key': os.environ['API_KEY']}); urllib.request.urlopen(request, timeout=5).read()"]

# One worker prevents loading a separate copy of every model into memory and
# keeps the in-process rate limiter consistent within this container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
