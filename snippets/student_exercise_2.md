
::: {.cell .markdown}

## Exercise 2: Persist guard metadata as MinIO object tags

When gourmetgram uploads an image, the orchestrator response includes full guard decisions. Your task is to surface those decisions as additional MinIO object tags so each stored image carries a traceable audit trail.

You will clone gourmetgram, make four edits to `app.py`, and rebuild the container.

:::

::: {.cell .markdown}

### Step 1: Clone gourmetgram onto the VM

:::

::: {.cell .code}
```bash
# runs on node-safeguard-{username}
cd ~
git clone -b production https://github.com/teaching-on-testbeds/gourmetgram
```
:::

::: {.cell .markdown}

### Step 2: Edit `app.py`

Open `gourmetgram/app.py`. Make the following four edits.

---

#### Edit A — return guard data from `request_fastapi`

Find the block near the end of `request_fastapi` that extracts `predicted_class` and `probability` from the response:

```python
        result = response.json()
        predicted_class = result.get("prediction")
        probability = result.get("probability")

        return predicted_class, probability
```

Replace it with:

```python
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
```

Also update the `except` block's return at the bottom of `request_fastapi`:

```python
        return None, None, {}
```

---

#### Edit B — unpack the new return value in the `/predict` route

Find these two lines inside `upload()`:

```python
        preds, probs = request_fastapi(img_path)
        if preds:
            executor.submit(upload_production_bucket, img_path, preds, probs, prediction_id) # New! upload production image to MinIO bucket
```

Replace them with:

```python
        preds, probs, guard_data = request_fastapi(img_path)
        if preds:
            executor.submit(upload_production_bucket, img_path, preds, probs, prediction_id, guard_data) # New! upload production image to MinIO bucket
```

---

#### Edit C — unpack the new return value in the `/test` route

Find:

```python
    preds, probs = request_fastapi(img_path)
```

Replace with:

```python
    preds, probs, guard_data = request_fastapi(img_path)
```

---

#### Edit D — add guard tags in `upload_production_bucket`

Update the function signature to accept `guard_data`:

```python
def upload_production_bucket(img_path, preds, confidence, prediction_id, guard_data=None):
```

Then find the existing `put_object_tagging` call:

```python
    s3.put_object_tagging(
        Bucket=bucket_name,
        Key=s3_key,
        Tagging={
            'TagSet': [
                {'Key': 'predicted_class', 'Value': preds},
                {'Key': 'confidence', 'Value': f"{confidence:.3f}"},
                {'Key': 'timestamp', 'Value': timestamp}
            ]
        }
    )
```

Replace it with:

```python
    gd = guard_data or {}
    s3.put_object_tagging(
        Bucket=bucket_name,
        Key=s3_key,
        Tagging={
            'TagSet': [
                {'Key': 'predicted_class', 'Value': preds},
                {'Key': 'confidence', 'Value': f"{confidence:.3f}"},
                {'Key': 'timestamp', 'Value': timestamp},
                {'Key': 'final_decision', 'Value': gd.get('final_decision', '')},
                {'Key': 'food_boundary_decision', 'Value': gd.get('food_boundary_decision', '')},
                {'Key': 'food_boundary_reason', 'Value': gd.get('food_boundary_reason', '')},
                {'Key': 'food_boundary_confidence', 'Value': gd.get('food_boundary_confidence', '')},
                {'Key': 'harmful_content_decision', 'Value': gd.get('harmful_content_decision', '')},
                {'Key': 'harmful_content_reason', 'Value': gd.get('harmful_content_reason', '')},
                {'Key': 'harmful_content_confidence', 'Value': gd.get('harmful_content_confidence', '')},
            ]
        }
    )
```

:::

::: {.cell .markdown}

### Step 3: Point docker-compose.yaml at your local clone

:::

::: {.cell .code}
```bash
# runs on node-safeguard-{username}
cd /home/cc/safeguard-chi/docker
nano docker-compose.yaml
```
:::

::: {.cell .markdown}

Find the line:

```
context: https://github.com/teaching-on-testbeds/gourmetgram.git#production
```

Change it to:

```
context: /home/cc/gourmetgram
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

:::

::: {.cell .markdown}

### Step 4: Rebuild and restart gourmetgram

:::

::: {.cell .code}
```bash
# runs on node-safeguard-{username}
docker compose -f /home/cc/safeguard-chi/docker/docker-compose.yaml up --build -d gourmetgram
```
:::

::: {.cell .markdown}

### Verify

Upload a food image using the gourmetgram UI at `http://<FLOATING_IP>:5000`. Then open the MinIO web console at `http://<FLOATING_IP>:9001` and inspect the uploaded object's tags. You should see ten tags: the original three (`predicted_class`, `confidence`, `timestamp`) plus seven guard fields (`final_decision`, `food_boundary_decision`, `food_boundary_reason`, `food_boundary_confidence`, `harmful_content_decision`, `harmful_content_reason`, `harmful_content_confidence`).

:::
