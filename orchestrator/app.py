import os
import uuid
import base64
import io
import requests
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

FOOD_BOUNDARY_GUARD_URL = os.getenv(
    "FOOD_BOUNDARY_GUARD_URL", "http://food-boundary-guard:8001"
)
HARMFUL_CONTENT_GUARD_URL = os.getenv(
    "HARMFUL_CONTENT_GUARD_URL", "http://harmful-content-guard:8002"
)
FOOD11_URL = os.getenv("FOOD11_URL", "http://food11:8000")

app = FastAPI()


class PredictRequest(BaseModel):
    image: str  # base64-encoded


@app.get("/health")
def health():
    # Orchestrator is stateless — no model to load, always ready
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    # UUID propagated to all downstream guard calls
    request_id = str(uuid.uuid4())
    payload = {"image": req.image, "request_id": request_id}

    # Stage 1: food boundary guard
    try:
        fbg_resp = requests.post(
            f"{FOOD_BOUNDARY_GUARD_URL}/predict", json=payload, timeout=30
        )
        fbg_resp.raise_for_status()
        fbg_data = fbg_resp.json()
    except Exception as e:
        return JSONResponse(
            content={
                "prediction": "error",
                "probability": 0.0,
                "final_decision": "error",
                "request_id": request_id,
                "food_boundary_guard": None,
                "harmful_content_guard": None,
                "error": str(e),
            }
        )

    # Flat subset of guard response (omit request_id/guard_model/guard_version)
    food_boundary_guard = {
        "decision": fbg_data["decision"],
        "reason": fbg_data["reason"],
        "confidence": fbg_data["confidence"],
    }

    # Short-circuit on rejection at food boundary stage
    if fbg_data["decision"] == "rejected":
        return JSONResponse(
            content={
                "prediction": "rejected",
                "probability": 0.0,
                "final_decision": "rejected",
                "request_id": request_id,
                "food_boundary_guard": food_boundary_guard,
                "harmful_content_guard": None,
            }
        )

    # Stage 2: harmful content guard
    try:
        hcg_resp = requests.post(
            f"{HARMFUL_CONTENT_GUARD_URL}/predict", json=payload, timeout=30
        )
        hcg_resp.raise_for_status()
        hcg_data = hcg_resp.json()
    except Exception as e:
        return JSONResponse(
            content={
                "prediction": "error",
                "probability": 0.0,
                "final_decision": "error",
                "request_id": request_id,
                "food_boundary_guard": food_boundary_guard,
                "harmful_content_guard": None,
                "error": str(e),
            }
        )

    harmful_content_guard = {
        "decision": hcg_data["decision"],
        "reason": hcg_data["reason"],
        "confidence": hcg_data["confidence"],
    }

    # Short-circuit on rejection at harmful content stage
    if hcg_data["decision"] == "rejected":
        return JSONResponse(
            content={
                "prediction": "rejected",
                "probability": 0.0,
                "final_decision": "rejected",
                "request_id": request_id,
                "food_boundary_guard": food_boundary_guard,
                "harmful_content_guard": harmful_content_guard,
            }
        )

    # Stage 3: food11 classification — only reached when both guards accept
    try:
        f11_resp = requests.post(
            f"{FOOD11_URL}/predict", json={"image": req.image}, timeout=30
        )
        f11_resp.raise_for_status()
        f11_data = f11_resp.json()
    except Exception as e:
        return JSONResponse(
            content={
                "prediction": "error",
                "probability": 0.0,
                "final_decision": "error",
                "request_id": request_id,
                "food_boundary_guard": food_boundary_guard,
                "harmful_content_guard": harmful_content_guard,
                "error": str(e),
            }
        )

    # Full approved response
    return JSONResponse(
        content={
            "prediction": f11_data["prediction"],
            "probability": f11_data["probability"],
            "final_decision": "approved",
            "request_id": request_id,
            "food_boundary_guard": food_boundary_guard,
            "harmful_content_guard": harmful_content_guard,
        }
    )
