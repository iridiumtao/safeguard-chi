

::: {.cell .markdown}

## Launch containers

Inside the SSH session on your `node-safeguard-{username}` VM, build and start the full safeguard stack:

:::

::: {.cell .code}
```bash
# runs on node-safeguard-{username}
cd safeguard-chi
docker compose -f docker/docker-compose.yaml up --build -d
```
:::

::: {.cell .markdown}

Once the build completes, check that all services are up and healthy:

:::

::: {.cell .code}
```bash
# runs on node-safeguard-{username}
docker compose -f /home/cc/safeguard-chi/docker/docker-compose.yaml ps
```
:::

::: {.cell .markdown}

All services should show **`Up`** status. The ML services (food-boundary-guard, harmful-content-guard, food11) take up to 60 seconds to load their models; wait until their health checks pass before proceeding.

:::

::: {.cell .markdown}

Open the gourmetgram web interface in your browser:

```
http://<FLOATING_IP>:5000
```

Replace `<FLOATING_IP>` with the floating IP address you noted earlier. You should see the GourmetGram food upload page.

:::

::: {.cell .markdown}

### Observe: upload without the guard pipeline

The stack is currently configured to send images **directly to the Food-11 classifier**, bypassing the guard pipeline. Try uploading the following:

- A photo of **non-food** (e.g. a person, a landscape, a car)
- A photo containing a **weapon** (e.g. a knife, a gun)

Notice that both images are accepted and classified — the app has no way to reject them yet. In the next exercise you will wire in the guard pipeline and repeat these uploads to see the difference.

:::
