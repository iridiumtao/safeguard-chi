
::: {.cell .markdown}

## Exercise 1: Wire in the guard pipeline

Right now gourmetgram is pointed at the Food-11 classifier directly (`http://food11:8000`), so images reach the model without any guard check. You will update one environment variable to route traffic through the orchestrator instead, which runs both guard models before passing accepted images to Food-11.

**Port reference — do not mix these up:**

| Port | Service | Role |
|------|---------|------|
| **8080** | orchestrator | Guard pipeline entry point — this is the correct target |
| **8000** | food11 | Food-11 classifier — currently set, but bypasses the guards |

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
