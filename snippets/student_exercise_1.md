
::: {.cell .markdown}

## Exercise 1: Wire in the guard pipeline

Right now gourmetgram is pointed at the Food-11 classifier directly (`http://food11:8000`), so images reach the model without any guard check. Your task is to update one environment variable to route traffic through the orchestrator instead — the orchestrator runs both guard models before passing accepted images to Food-11.

**Port reference — make sure you change to the right one:**

| Port | Service | Role |
|------|---------|------|
| **8080** | orchestrator | Runs both guard models before Food-11 — **change to this** |
| **8000** | food11 | Food-11 classifier only, no guards — currently set |

:::

::: {.cell .markdown}

### Step 1: Edit docker-compose.yaml

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
FASTAPI_SERVER_URL=http://food11:8000
```

Change it to:

```
FASTAPI_SERVER_URL=http://orchestrator:8080
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

:::

::: {.cell .markdown}

### Step 2: Restart gourmetgram

:::

::: {.cell .code}
```bash
# runs on node-safeguard-{username}
cd /home/cc/safeguard-chi
docker compose -f docker/docker-compose.yaml up -d gourmetgram
```
:::

::: {.cell .markdown}

### Verify

Upload the same non-food and weapon images you tried earlier. This time the app should reject them — the guard pipeline is now active.

:::
