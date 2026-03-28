import os
import json
import uuid
import base64
import io
from contextlib import asynccontextmanager
from typing import Optional

import torch
from torchvision import models
from PIL import Image
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from preprocess import INFERENCE_TRANSFORM

MODEL_PATH = os.getenv("MODEL_PATH", "/app/food_boundary_guard.pth")
METRICS_PATH = os.getenv("METRICS_PATH", "/app/food_boundary_guard_metrics.json")

# Mutable state dict populated during lifespan startup
model_state: dict = {"ready": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load threshold from metrics file
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    threshold = metrics["best_threshold"]

    # MobileNetV2 with single-neuron head to match training architecture
    m = models.mobilenet_v2(weights=None)
    num_ftrs = m.last_channel
    m.classifier = torch.nn.Sequential(
        torch.nn.Dropout(0.2), torch.nn.Linear(num_ftrs, 1)
    )
    state = torch.load(MODEL_PATH, map_location=torch.device("cpu"))
    m.load_state_dict(state)
    m.eval()

    model_state["model"] = m
    model_state["threshold"] = threshold
    model_state["ready"] = True
    yield
    # Shutdown — release model reference
    model_state.clear()


app = FastAPI(lifespan=lifespan)


class PredictRequest(BaseModel):
    image: str  # base64-encoded image bytes
    request_id: Optional[str] = None


class PredictResponse(BaseModel):
    request_id: str
    guard_model: str
    guard_version: str
    confidence: float
    decision: str  # "accepted" | "rejected"
    reason: str  # "food" | "non-food"


@app.get("/health")
def health():
    # Returns 503 until model is loaded and ready
    if model_state.get("ready"):
        return {"status": "ok"}
    return JSONResponse(status_code=503, content={"status": "loading"})


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    req_id = req.request_id or str(uuid.uuid4())

    img_bytes = base64.b64decode(req.image)
    # convert("RGB") handles RGBA/palette PNGs
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    tensor = INFERENCE_TRANSFORM(img).unsqueeze(0)

    with torch.no_grad():  # skip gradient tracking at inference
        logit = model_state["model"](tensor)
        confidence = torch.sigmoid(logit).item()

    threshold = model_state["threshold"]
    if confidence >= threshold:
        decision, reason = "accepted", "food"
    else:
        decision, reason = "rejected", "non-food"

    return PredictResponse(
        request_id=req_id,
        guard_model="food_boundary_guard",
        guard_version="v1.0.0",
        confidence=round(confidence, 6),
        decision=decision,
        reason=reason,
    )
