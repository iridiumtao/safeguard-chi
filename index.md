



## Launch and set up a VM instance- with python-chi

We will use the `python-chi` Python API to Chameleon to provision our VM server. 

We will execute the cells in this notebook inside the Chameleon Jupyter environment.

Run the following cell, and make sure the correct project is selected. 


```python
# runs on Chameleon Jupyter environment
from chi import server, context, lease, network
import chi, os, time, datetime

context.version = "1.0" 
context.choose_project()
context.choose_site(default="KVM@TACC")

username = os.getenv('USER') # all exp resources will have this prefix
```


We will reserve and bring up an `m1.medium` instance with the `CC-Ubuntu24.04` disk image. 

> **Note**: the following cells bring up a server only if you don't already have one with the same name! (Regardless of its error state.) If you have a lease or a server in ERROR state already, delete it first in the Horizon GUI before you run these cells.




First we will reserve the VM instance for 6 hours, starting now:



```python
# runs on Chameleon Jupyter environment
l = lease.Lease(f"lease-safeguard-{username}", duration=datetime.timedelta(hours=6))
l.add_flavor_reservation(id=chi.server.get_flavor_id("m1.medium"), amount=1)
l.submit(idempotent=True)
```


```python
# runs on Chameleon Jupyter environment
l.show()
```



Now we can launch an instance using that lease:


```python
# runs on Chameleon Jupyter environment
s = server.Server(
    f"node-safeguard-{username}", 
    image_name="CC-Ubuntu24.04",
    flavor_name=l.get_reserved_flavors()[0].name
)
s.submit(idempotent=True)
```


By default, all connections to VM resources are blocked, as a security measure.  We need to attach one or more "security groups" to our VM resource, to permit access over the Internet to specified ports.

The following security groups will be created (if they do not already exist in our project) and then added to our server:



```python
# runs on Chameleon Jupyter environment
security_groups = [
    {"name": "allow-ssh", "port": 22, "description": "Enable SSH traffic on TCP port 22"},
    {"name": "allow-5000", "port": 5000, "description": "Enable TCP port 5000 (gourmetgram Flask frontend)"},
    {"name": "allow-8080", "port": 8080, "description": "Enable TCP port 8080 (orchestrator guard pipeline)"},
    {"name": "allow-8000", "port": 8000, "description": "Enable TCP port 8000 (food11 FastAPI, used by benchmark notebook)"},
    {"name": "allow-9000", "port": 9000, "description": "Enable TCP port 9000 (MinIO object storage API)"},
    {"name": "allow-9001", "port": 9001, "description": "Enable TCP port 9001 (MinIO web console)"},
    {"name": "allow-8888", "port": 8888, "description": "Enable TCP port 8888 (Jupyter notebook server)"},
]
```


```python
# runs on Chameleon Jupyter environment
for sg in security_groups:
  secgroup = network.SecurityGroup({
      'name': sg['name'],
      'description': sg['description'],
  })
  secgroup.add_rule(direction='ingress', protocol='tcp', port=sg['port'])
  secgroup.submit(idempotent=True)
  s.add_security_group(sg['name'])

print(f"updated security groups: {[sg['name'] for sg in security_groups]}")
```



Then, we'll associate a floating IP with the instance:


```python
# runs on Chameleon Jupyter environment
s.associate_floating_ip()
```

```python
# runs on Chameleon Jupyter environment
s.refresh()
s.check_connectivity()
```


In the output below, make a note of the floating IP that has been assigned to your instance (in the "Addresses" row).


```python
# runs on Chameleon Jupyter environment
s.refresh()
s.show(type="widget")
```






### Retrieve code and notebooks on the instance

Now, we can use `python-chi` to execute commands on the instance, to set it up. We'll start by retrieving the code and other materials on the instance.


```python
# runs on Chameleon Jupyter environment
s.execute("git clone https://github.com/teaching-on-testbeds/safeguard-chi")
```



### Set up Docker

Here, we will set up the container framework.


```python
# runs on Chameleon Jupyter environment
s.execute("curl -sSL https://get.docker.com/ | sudo sh")
s.execute("sudo groupadd -f docker; sudo usermod -aG docker $USER")
```



## Open an SSH session

Finally, open an SSH sesson on your server. From your local terminal, run

```
ssh -i ~/.ssh/id_rsa_chameleon cc@A.B.C.D
```

where

* in place of `~/.ssh/id_rsa_chameleon`, substitute the path to your own key that you had uploaded to KVM@TACC
* in place of `A.B.C.D`, use the floating IP address you just associated to your instance.




## Launch containers

Inside the SSH session on your `node-safeguard-{username}` VM, build and start the full safeguard stack:

```bash
# runs on node-safeguard-{username}
cd safeguard-chi
docker compose -f docker/docker-compose.yaml up --build -d
```

This builds four custom services (orchestrator, food-boundary-guard, harmful-content-guard, food11) and pulls MinIO — allow 5–10 minutes on first run while PyTorch wheels download.



Once the build completes, check that all services are up and healthy:

```bash
# runs on node-safeguard-{username}
docker compose -f docker/docker-compose.yaml ps
```

All services should show **`Up`** status. The ML services (food-boundary-guard, harmful-content-guard, food11) take up to 60 seconds to load their models; wait until their health checks pass before proceeding.



Open the gourmetgram web interface in your browser:

```
http://<FLOATING_IP>:5000
```

Replace `<FLOATING_IP>` with the floating IP address you noted earlier. You should see the GourmetGram food upload page.



## Exercise 1: Configure the orchestrator endpoint

The gourmetgram frontend connects to the guard pipeline through the `FASTAPI_SERVER_URL` environment variable. You need to set this to the correct service and port.

**Port reference — do not mix these up:**

| Port | Service | Role |
|------|---------|------|
| **8080** | orchestrator | Guard pipeline entry point — set `FASTAPI_SERVER_URL` to this |
| **8000** | food11 | Food-11 classifier — do **not** point gourmetgram here |

### Option A: Full stack on one Compose network (default)

When all services run together via `docker compose`, Docker's internal DNS resolves service names automatically. The gourmetgram container can reach the orchestrator by its service name `orchestrator` on port `8080`:

```
FASTAPI_SERVER_URL=http://orchestrator:8080
```

This value is already set in `docker/docker-compose.yaml`. No change needed if you launched the full stack together.

### Option B: TA-hosted orchestrator on a separate VM

If the orchestrator is running on a different VM (e.g., the TA hosts a shared orchestrator for the class), set `FASTAPI_SERVER_URL` to the TA's floating IP instead:

```
FASTAPI_SERVER_URL=http://<TA_FLOATING_IP>:8080
```

Replace `<TA_FLOATING_IP>` with the IP address provided by your TA. Port remains `8080`.

To apply this change, update the environment in `docker/docker-compose.yaml` and restart the gourmetgram service:

```bash
# runs on node-safeguard-{username}
docker compose -f docker/docker-compose.yaml up -d gourmetgram
```



### Verify

Upload a food image using the gourmetgram UI at `http://<FLOATING_IP>:5000`. After a successful upload the response should include `"final_decision": "approved"` and a food class prediction. A non-food image should return `"final_decision": "rejected"`.



## Exercise 2: Persist guard metadata as MinIO object tags

When gourmetgram uploads an image to the `production` bucket, the orchestrator response already contains guard outcomes. Your task is to extend `upload_production_bucket` to write those outcomes as **S3 object tags** so each stored image carries a traceable audit trail.

### Where to make the change

Edit `upload_production_bucket` in the gourmetgram `app.py` from the **`production`** branch of `teaching-on-testbeds/gourmetgram` (the same file the container builds from). The function receives the orchestrator JSON response and calls boto3-style S3 operations against MinIO.

### What the orchestrator returns

The orchestrator always returns HTTP 200 with a JSON body that includes:

- `final_decision` — `"approved"`, `"rejected"`, or `"error"` (top-level string)
- `food_boundary_guard` — nested object `{"decision": ..., "reason": ..., "confidence": ...}` (always present)
- `harmful_content_guard` — nested object with the same shape, **or `null`** when the food boundary guard rejected the image and the harmful content stage was never reached

Example approved response:

```json
{
  "prediction": "Pizza",
  "probability": 0.987,
  "final_decision": "approved",
  "food_boundary_guard": {"decision": "accepted", "reason": "food", "confidence": 0.9992},
  "harmful_content_guard": {"decision": "accepted", "reason": "safe", "confidence": 0.9831}
}
```

Example rejected response (short-circuit at food boundary):

```json
{
  "prediction": "rejected",
  "probability": 0.0,
  "final_decision": "rejected",
  "food_boundary_guard": {"decision": "rejected", "reason": "non-food", "confidence": 0.9754},
  "harmful_content_guard": null
}
```

### S3 tag value constraint

S3 (and MinIO) tag **values must be strings**. The nested guard objects must be serialized with `json.dumps(...)` before storing. When `harmful_content_guard` is `null`, Python receives `None` — use `json.dumps({})` (empty JSON object) to represent "stage not reached" without fabricating a decision.

### Implementation

Add the following after the `s3.put_object(...)` call inside `upload_production_bucket`:

```python
import json

fbg = resp.get("food_boundary_guard")
hcg = resp.get("harmful_content_guard")

tagging = {
    "TagSet": [
        {"Key": "final_decision", "Value": resp["final_decision"]},
        {
            "Key": "food_boundary_guard",
            "Value": json.dumps(fbg if fbg is not None else {}),
        },
        {
            "Key": "harmful_content_guard",
            "Value": json.dumps(hcg if hcg is not None else {}),
        },
    ]
}
s3.put_object_tagging(Bucket=bucket, Key=key, Tagging=tagging)
```

Where `bucket` and `key` match the values used in the preceding `s3.put_object` call, and `resp` is the orchestrator JSON response dict already available in `upload_production_bucket`.

> **Note:** MinIO's Python SDK exposes the same `put_object_tagging` method name and `Tagging` parameter shape as boto3, so the snippet works with either client.



### Verify

After rebuilding gourmetgram and uploading an image, inspect the object tags in the MinIO web console at `http://<FLOATING_IP>:9001` (login with the credentials from `docker/docker-compose.yaml`). The object should show three tags: `final_decision`, `food_boundary_guard`, and `harmful_content_guard`.



## Delete resources

When we are finished, we must delete the VM server instance to make the resources available to other users.

We will execute the cells in this notebook inside the Chameleon Jupyter environment.

Run the following cell, and make sure the correct project is selected.


```python
# runs on Chameleon Jupyter environment
from chi import server, context, lease
import chi, os, time, datetime

context.version = "1.0"
context.choose_project()
context.choose_site(default="KVM@TACC")
```


```python
# runs on Chameleon Jupyter environment
username = os.getenv('USER') # all exp resources will have this prefix
s = server.get_server(f"node-safeguard-{username}")
s.delete()
l = lease.get_lease(f"lease-safeguard-{username}")
l.delete()
```


<hr>

<small>Questions about this material? Contact Fraida Fund</small>

<hr>

<small>This material is based upon work supported by the National Science Foundation under Grant No. 2230079.</small>

<small>Any opinions, findings, and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the National Science Foundation.</small>
