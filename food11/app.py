import os
import base64
import io
from contextlib import asynccontextmanager

import numpy as np
import torch
import torch.nn.functional as F
from torchvision import models
from PIL import Image
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from preprocess import INFERENCE_TRANSFORM

MODEL_PATH = os.getenv("MODEL_PATH", "/app/food11.pth")

CLASSES = np.array(
    [
        "Bread",
        "Dairy product",
        "Dessert",
        "Egg",
        "Fried food",
        "Meat",
        "Noodles/Pasta",
        "Rice",
        "Seafood",
        "Soup",
        "Vegetable/Fruit",
    ]
)

# Mutable state dict populated during lifespan startup
model_state: dict = {"ready": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    m = models.mobilenet_v2(weights=None)
    num_ftrs = m.last_channel
    # Dropout(0.5) matches training — different from guard services which use 0.2
    m.classifier = torch.nn.Sequential(
        torch.nn.Dropout(0.5), torch.nn.Linear(num_ftrs, 11)
    )
    state = torch.load(MODEL_PATH, map_location=torch.device("cpu"))
    m.load_state_dict(state)
    m.eval()

    model_state["model"] = m
    model_state["ready"] = True
    yield
    # Shutdown — release model reference
    model_state.clear()


app = FastAPI(lifespan=lifespan)


class PredictRequest(BaseModel):
    image: str  # base64-encoded


class PredictResponse(BaseModel):
    prediction: str
    probability: float


@app.get("/health")
def health():
    # Returns 503 until model is loaded and ready
    if model_state.get("ready"):
        return {"status": "ok"}
    return JSONResponse(status_code=503, content={"status": "loading"})


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    img_bytes = base64.b64decode(req.image)
    # convert("RGB") handles RGBA/palette PNGs
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    tensor = INFERENCE_TRANSFORM(img).unsqueeze(0)

    with torch.no_grad():  # skip gradient tracking at inference
        output = model_state["model"](tensor)
        probabilities = F.softmax(output, dim=1)
        predicted_class = torch.argmax(probabilities, 1).item()
        confidence = probabilities[0, predicted_class].item()

    return PredictResponse(
        prediction=CLASSES[predicted_class],
        probability=round(confidence, 6),
    )
