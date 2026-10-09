# Final Pipeline API

Self-contained FastAPI service containing the instance-segmentation detector cascade, five-fold dual-head classifier ensemble, species configuration, and safety gate. It does not import code or load artifacts from `../final_pipeline` at runtime.

## Run locally

From this `backend` directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:API_KEY = "replace-with-a-long-random-secret"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

The detector cascade exactly follows the final pipeline: `seg_model_s_2` runs at confidence 0.25 and image size 512, retries at confidence 0.10 and image size 768, then uses `seg_model_n_3` at those retry settings. Every stage uses the predicted instance mask to create the contextual ROI; the returned bounding box is ROI metadata, not a box-detector crop. The response's `detector_stage` identifies the successful cascade stage.

The classifier defaults select the five bundled MobileViT ArcFace+Focal fold checkpoints. CUDA is used when available and automatically falls back to CPU. Configuration variables are documented in `.env.example`; export them in the shell or provide them through the deployment environment.

The bundle uses the pipeline's built-in conservative thresholds and reports `thresholds_source: "defaults"`. A calibrated threshold JSON can optionally be placed at `pipeline/config/gate_thresholds.json` or supplied through `THRESHOLDS_PATH`.

## Endpoints

- `GET /api/v1/health` — process liveness.
- `GET /api/v1/predictions/status` — model readiness, selected device, and threshold source.
- `POST /api/v1/predictions` — multipart upload using the `file` field.

Every `/api/v1` endpoint, including health and model status, requires the static key in the `X-API-Key` header. The service fails closed with HTTP 503 when `API_KEY` is not configured and returns HTTP 401 for a missing or invalid key. Swagger remains viewable at `/docs`; use its **Authorize** button to enter the key.

Requests are rate-limited per client IP in each running process. The defaults allow 60 requests per 60 seconds and can be changed with `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`. Responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`; rejected requests return HTTP 429 with `Retry-After`. For multi-worker or multi-instance deployment, replace the in-memory limiter with a shared Redis-backed limiter.

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/predictions -H "X-API-Key: replace-with-a-long-random-secret" -F "file=@snake.jpg"
```

Request the detector visualization and classifier ROI with query arguments:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/predictions?include_mask_overlay=true&include_roi_crop=true&include_gradcam=true" -H "X-API-Key: replace-with-a-long-random-secret" -F "file=@snake.jpg"
```

The optional `mask_overlay`, `roi_crop`, and `gradcam_overlay` response objects contain `media_type: "image/jpeg"` and base64-encoded JPEG bytes in `data`. They are omitted by default to keep responses small. The mask overlay shows the raw mask produced by the successful instance-segmentation cascade stage; the ROI is the healed, context-expanded crop actually passed to the classifier; and the Grad-CAM overlay is the normalized average of the five fold-specific maps for the ensemble-predicted species.

`processing_ms` measures only the core detector cascade, ROI extraction, classifier ensemble, and safety-gate execution. Optional image drawing, JPEG encoding, and Grad-CAM generation occur after this value is fixed and therefore never increase it. When at least one optional artifact is requested, `artifact_processing_ms` reports that additional work separately.

Every successful detection also returns `pixel_reduction`. It reports the exact original and ROI dimensions, total pixel counts, removed pixel count, retained percentage, and reduction percentage. Percentages describe spatial image area before the classifier resizes its input; they do not describe file-size compression.

An image with no detected snake returns a successful response with `decision: "WITHHOLD"`; malformed uploads and unavailable model artifacts return appropriate HTTP errors.

This model is decision support for a research demonstration. It is not a substitute for emergency medical assessment or qualified identification.

## Docker

Build from the `backend` directory so the build context contains the bundled models:

```powershell
docker build -t snake-pipeline-api .
```

Run the CPU image with the required API key:

```powershell
docker run --rm `
  --name snake-pipeline-api `
  -p 8000:8000 `
  -e API_KEY="replace-with-a-long-random-secret" `
  -e RATE_LIMIT_REQUESTS=60 `
  -e RATE_LIMIT_WINDOW_SECONDS=60 `
  snake-pipeline-api
```

The image runs as a non-root user, preloads the models, and uses one Uvicorn worker to avoid duplicating model memory. Its health check calls the protected `/api/v1/health` endpoint with `API_KEY`. The default build installs CPU-only PyTorch; `MODEL_DEVICE=cpu` is set explicitly in the runtime image.

The first build is large because it downloads PyTorch and the ML dependencies. Docker caches the dependency stage as long as `requirements.txt` does not change.

The builder explicitly removes Ultralytics' GUI-enabled `opencv-python` dependency and reinstalls `opencv-python-headless`. This prevents X11 runtime errors such as a missing `libxcb.so.1` while keeping the final image free of desktop libraries.
