
::: {.cell .markdown}

## Benchmark: guard pipeline overhead

Compare inference latency and throughput between the direct Food-11 path and the full guard pipeline:

- **Direct path** — POST to Food-11 (`port 8000`): no guard check, classification only
- **Guarded path** — POST to orchestrator (`port 8080`): food boundary guard → harmful content guard → Food-11

This notebook runs from **Chameleon Trovi** (JupyterHub), not inside the Docker Compose stack. Port 8000 and port 8080 must be open in your Chameleon security groups — both are already included if you followed the `create_server` notebook.

:::

::: {.cell .markdown}

### Configure endpoints

Set the floating IP of your `node-safeguard-{username}` VM:

:::

::: {.cell .code}
```python
# runs on Chameleon Jupyter environment
import requests, base64, time, numpy as np, os, glob

FLOATING_IP = "<FLOATING_IP>"  # replace with your VM's floating IP

FOOD11_URL       = f"http://{FLOATING_IP}:8000"
ORCHESTRATOR_URL = f"http://{FLOATING_IP}:8080"
NUM_REQUESTS     = 100

print(f"Food11 URL:       {FOOD11_URL}")
print(f"Orchestrator URL: {ORCHESTRATOR_URL}")
```
:::

::: {.cell .markdown}

### Load a test image

A sample food image is included in the repo at `test_images/sushi_001.jpg` and used by default.

:::

::: {.cell .code}
```python
# runs on Chameleon Jupyter environment
IMAGE_PATH = "test_images/sushi_001.jpg"

with open(IMAGE_PATH, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

print(f"Image: {IMAGE_PATH}")
print(f"Payload size: {len(image_b64)} chars")
```
:::

::: {.cell .markdown}

### Run benchmark

:::

::: {.cell .code}
```python
# runs on Chameleon Jupyter environment
def benchmark(url, payload, num_requests=100):
    latencies = []
    requests.post(f"{url}/predict", json=payload)  # warmup, not counted
    for i in range(num_requests):
        start = time.time()
        resp = requests.post(f"{url}/predict", json=payload)
        latencies.append((time.time() - start) * 1000)
        assert resp.status_code == 200, f"Request {i} failed: {resp.status_code}"
    return np.array(latencies)

payload = {"image": image_b64}

print(f"Benchmarking Food11 direct — {NUM_REQUESTS} requests...")
food11_latencies = benchmark(FOOD11_URL, payload, NUM_REQUESTS)

print(f"Benchmarking orchestrator (guarded) — {NUM_REQUESTS} requests...")
orch_latencies = benchmark(ORCHESTRATOR_URL, payload, NUM_REQUESTS)

print("Done.")
```
:::

::: {.cell .markdown}

### Results

:::

::: {.cell .code}
```python
# runs on Chameleon Jupyter environment
def summarize(latencies, label):
    total_sec = latencies.sum() / 1000
    return {
        "path":            label,
        "median_ms":       round(np.median(latencies), 2),
        "p95_ms":          round(np.percentile(latencies, 95), 2),
        "p99_ms":          round(np.percentile(latencies, 99), 2),
        "throughput_rps":  round(len(latencies) / total_sec, 2),
    }

r1 = summarize(food11_latencies, "Food11 direct")
r2 = summarize(orch_latencies,   "Orchestrator (guarded)")

print(f"{'Metric':<22} {'Food11 direct':>15} {'Orchestrator':>15}")
print("-" * 54)
for key, label in [("median_ms", "Median (ms)"), ("p95_ms", "p95 (ms)"),
                   ("p99_ms", "p99 (ms)"), ("throughput_rps", "Throughput (req/s)")]:
    print(f"{label:<22} {r1[key]:>15} {r2[key]:>15}")
```
:::

::: {.cell .markdown}

### Interpretation

The guarded path adds two extra HTTP round-trips (food boundary guard + harmful content guard) on top of Food-11 inference. On a CPU-only Chameleon m1.medium VM, expect roughly 3× higher latency and correspondingly lower throughput for the orchestrator path compared to Food-11 direct — the cost of the guard pipeline for safety and auditability.

:::
