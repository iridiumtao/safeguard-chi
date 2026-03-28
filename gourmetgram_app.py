# Backup: complete app.py for gourmetgram production branch with guard metadata tags.
# Drop this file into your local gourmetgram clone as app.py if you run into trouble
# applying the manual edits in Exercise 2:
#
#   cp /home/cc/safeguard-chi/gourmetgram_app.py /home/cc/gourmetgram/app.py
#
# Then rebuild:
#   docker compose -f /home/cc/safeguard-chi/docker/docker-compose.yaml up --build -d gourmetgram

import numpy as np
import requests
from flask import Flask, redirect, url_for, request, render_template
from werkzeug.utils import secure_filename
import os
import base64
from mimetypes import guess_type
from datetime import datetime
import boto3
import uuid
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["MINIO_URL"],
    aws_access_key_id=os.environ["MINIO_USER"],
    aws_secret_access_key=os.environ["MINIO_PASSWORD"],
    region_name="us-east-1",
)

app = Flask(__name__)

os.makedirs(os.path.join(app.instance_path, "uploads"), exist_ok=True)

FASTAPI_SERVER_URL = os.environ["FASTAPI_SERVER_URL"]


def upload_production_bucket(
    img_path, preds, confidence, prediction_id, guard_data=None
):
    classes = np.array(
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
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    pred_index = np.where(classes == preds)[0][0]
    class_dir = f"class_{pred_index:02d}"

    bucket_name = "production"
    root, ext = os.path.splitext(img_path)
    content_type = guess_type(img_path)[0] or "application/octet-stream"
    s3_key = f"{class_dir}/{prediction_id}{ext}"

    with open(img_path, "rb") as f:
        s3.upload_fileobj(
            f, bucket_name, s3_key, ExtraArgs={"ContentType": content_type}
        )

    gd = guard_data or {}
    s3.put_object_tagging(
        Bucket=bucket_name,
        Key=s3_key,
        Tagging={
            "TagSet": [
                {"Key": "predicted_class", "Value": preds},
                {"Key": "confidence", "Value": f"{confidence:.3f}"},
                {"Key": "timestamp", "Value": timestamp},
                {"Key": "final_decision", "Value": gd.get("final_decision", "")},
                {
                    "Key": "food_boundary_decision",
                    "Value": gd.get("food_boundary_decision", ""),
                },
                {
                    "Key": "food_boundary_reason",
                    "Value": gd.get("food_boundary_reason", ""),
                },
                {
                    "Key": "food_boundary_confidence",
                    "Value": gd.get("food_boundary_confidence", ""),
                },
                {
                    "Key": "harmful_content_decision",
                    "Value": gd.get("harmful_content_decision", ""),
                },
                {
                    "Key": "harmful_content_reason",
                    "Value": gd.get("harmful_content_reason", ""),
                },
                {
                    "Key": "harmful_content_confidence",
                    "Value": gd.get("harmful_content_confidence", ""),
                },
            ]
        },
    )


def request_fastapi(image_path):
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        encoded_str = base64.b64encode(image_bytes).decode("utf-8")
        payload = {"image": encoded_str}

        response = requests.post(f"{FASTAPI_SERVER_URL}/predict", json=payload)
        response.raise_for_status()

        result = response.json()
        predicted_class = result.get("prediction")
        probability = result.get("probability")

        fbg = result.get("food_boundary_guard") or {}
        hcg = result.get("harmful_content_guard") or {}
        guard_data = {
            "final_decision": result.get("final_decision", ""),
            "food_boundary_decision": fbg.get("decision", ""),
            "food_boundary_reason": fbg.get("reason", ""),
            "food_boundary_confidence": f"{fbg.get('confidence', 0):.4f}",
            "harmful_content_decision": hcg.get("decision", ""),
            "harmful_content_reason": hcg.get("reason", ""),
            "harmful_content_confidence": f"{hcg.get('confidence', 0):.4f}",
        }
        return predicted_class, probability, guard_data

    except Exception as e:
        print(f"Error during inference: {e}")
        return None, None, {}


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/predict", methods=["GET", "POST"])
def upload():
    preds = None
    if request.method == "POST":
        f = request.files["file"]
        f.save(os.path.join(app.instance_path, "uploads", secure_filename(f.filename)))
        img_path = os.path.join(
            app.instance_path, "uploads", secure_filename(f.filename)
        )

        prediction_id = str(uuid.uuid4())

        preds, probs, guard_data = request_fastapi(img_path)
        if preds:
            executor.submit(
                upload_production_bucket,
                img_path,
                preds,
                probs,
                prediction_id,
                guard_data,
            )
            return f'<button type="button" class="btn btn-info btn-sm">{preds}</button>'

    return '<a href="#" class="badge badge-warning">Warning</a>'


@app.route("/test", methods=["GET"])
def test():
    img_path = os.path.join(app.instance_path, "uploads", "test_image.jpeg")
    preds, probs, guard_data = request_fastapi(img_path)
    return str(preds)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
