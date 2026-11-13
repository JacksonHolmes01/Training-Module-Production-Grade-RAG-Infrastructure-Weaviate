# Lesson 5: Layer 1: Non-Root Users

By default, the main process in most containers runs as **root** (user ID 0). Root inside a container is not the same as root on your computer. Docker isolates it. But it is still the most powerful user in that container, and every container escape vulnerability ever found has been far easier to exploit from root.

The fix is simple to describe: run each service as an ordinary user.

---

## Read the layer

Open `hardening/01-non-root.yml`.

```yaml
  weaviate:
    user: "10001:10001"
    depends_on:
      weaviate-perms:
        condition: service_completed_successfully
```

Weaviate's official image starts as root, but Weaviate itself does not need root at all. It runs fine as an ordinary user. There is one catch. In Part 3, Weaviate ran as root, so everything in its data volume belongs to root, and user 10001 cannot write to it.

```yaml
  weaviate-perms:
    image: cr.weaviate.io/semitechnologies/weaviate:1.40.4
    user: "0:0"
    entrypoint: ["sh", "-c", "chown -R 10001:10001 /var/lib/weaviate && ..."]
    cap_drop: [ALL]
    cap_add: [CHOWN, DAC_READ_SEARCH, FOWNER]
    network_mode: none
```

`weaviate-perms` is a one-shot container that hands the data folder to user 10001, then exits. It is the only thing in the lab that still runs as root, so it is boxed in as tightly as possible: every capability is dropped except the three it needs to change file ownership, and it has **no network at all**. Weaviate waits for it to finish before starting.

```yaml
  weaviate-init:
    user: "10001:10001"
```

The setup container that creates the collection runs as an ordinary user too. It only makes HTTPS calls; it never needed root.

```yaml
  ingestion-api:
    user: "10001:10001"
  gradio-ui:
    user: "10001:10001"
    environment:
      HOME: /tmp
```

The two Python services run as user 10001, a number with no special meaning that does not exist on most host systems, so it maps to nobody important. Gradio expects a home folder to write a few small files to; `HOME: /tmp` gives it one.

```yaml
  ollama:
    user: "10001:10001"
    environment:
      HOME: /tmp
      OLLAMA_MODELS: /ollama/models
    volumes: !override
      - ollama_data:/ollama:ro
```

Ollama gets a bonus: the models are now mounted **read-only** (`:ro`). Nothing running inside the Ollama container can replace or alter a model file. A swapped model is a quiet and powerful supply chain attack, and this closes it. (This is why you downloaded the models in Lesson 2, before hardening.)

`!override` tells Docker Compose to **replace** the volume list from `docker-compose.yml` instead of adding to it.

```yaml
  nginx:
    image: nginxinc/nginx-unprivileged:1.28.2-alpine
```

The official NGINX image starts as root so it can use ports below 1024. NGINX publishes an `unprivileged` variant that never runs as root. This lab uses port 8088, so it needs no special port.

> **In your own Dockerfiles**, the better place for this is a `USER` line, so the image is safe no matter how it is run. A `user:` setting in compose works for images you do not control, like the third-party images here.

---

## Apply it

```bash
bin/harden.sh 1
```

```
Active layers:
  docker-compose.yml
  hardening/01-non-root.yml
Applying (containers that changed are recreated)...
Stack is up.
```

Confirm every container's user:

```bash
for c in rag-api rag-nginx rag-ollama rag-ui rag-weaviate; do
  printf "%-14s uid=%s\n" "$c" "$(docker exec $c id -u)"
done
```

```
rag-api        uid=10001
rag-nginx      uid=101
rag-ollama     uid=10001
rag-ui         uid=10001
rag-weaviate   uid=10001
```

## Test it still works

```bash
bin/smoke_test.sh
```

All six checks should pass. Always test after a change.

## Audit

```bash
python3 bin/audit.py
```

`non-root` now passes for all five containers: **18 of 45 (40%)**.

## Attack again

```bash
bin/attacker_demo.sh
```

```
  run as root?                                 no   uid 10001
  plant a backdoor in the app's code?          no   cannot create /app/app/main.py: Permission denied
  drop a tool in /var/tmp and run it?          YES  tool ran
  run a program from /tmp?                     YES  tool ran
  install packages (apt-get)?                  no
  change file ownership (CAP_CHOWN)?           no   Operation not permitted
  open raw network sockets (CAP_NET_RAW)?      no   Operation not permitted
  read the API key from the environment?       YES  EDGE_API_KEY=wIyrm6...
```

One setting turned five `YES` answers into `no`. The application's files belong to root, so user 10001 cannot change them, cannot install software, and gets no privileges.

Three `YES` answers remain. Some folders, like `/var/tmp` and `/tmp`, are writable by **every** user by design, so an attacker can still bring and run their own tools. And the key is still in the environment. The next layers deal with these.

Next: [Layer 2: Capabilities, Escalation, and Limits](06-capabilities.md)
