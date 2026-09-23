# Deploying IPTT on OpenShift — Airgapped Cluster (IPv6)

For the UI refresh and separate PostgreSQL lab, see
[Killercoda → OpenShift test guide](docs/UI-POSTGRES-LAB.md).

Your cluster has no internet access, so the app is **not** built on the cluster.
Instead:

```
build machine ──build──▶ image ──push──▶ JFrog Artifactory ──pull──▶ OpenShift (IPv6)
```

Everything here was smoke-tested (clean install, DB seed, full login flow, IPv6 bind).

---

## 0. What was changed in the repo for this

| Change | Why |
|---|---|
| `requirements.txt` rewritten (pinned, Linux-compatible) | Old file was a Windows conda export (`file:///C:/...`) — cannot install |
| `Dockerfile` added | No build entrypoint existed; now builds `uvicorn main:app` on port 8080, random-UID compatible (OpenShift) |
| **`uvicorn --host "::"`** (default in image) | **Critical on IPv6 clusters** — binding `0.0.0.0` only opens an IPv4 socket and pods become unreachable. `"::"` serves IPv6 (and IPv4-mapped) clients — verified |
| `DATABASE_URL` env var (`database.py`) | Puts the SQLite file on a PVC instead of ephemeral container storage |
| `SESSION_SECRET` env var (`main.py`) | Injected from an OpenShift Secret instead of hardcoded |
| `seed_admin.py` made idempotent + creates tables | It crashed on a fresh DB ("no such table: user") |
| `openshift/iptt-airgap.yaml` | PVC + Deployment (with `imagePullSecrets`) + Service + Route — no BuildConfig needed |

---

## 1. Prerequisites

- A build machine (laptop / CI runner / jump host) with `podman` or `docker` that can
  reach PyPI + Docker Hub — **or** JFrog Artifactory proxying both (very common in
  airgapped orgs: a *docker-remote* repo and a *pypi-remote* repo).
- `oc` CLI logged in to the IPv6 cluster (`oc login https://api.<cluster>:6443`).
- Names in this guide to replace with yours:
  - `artifactory.example.com` → your JFrog hostname
  - `docker-local` → your JFrog Docker repo key (local repo for pushes)
  - `docker-remote` / `pypi-remote` → JFrog remote repos proxying Docker Hub / PyPI
  - `iptt` → OpenShift project name

---

## 2. Build the image and push to JFrog

### 2a. Build

**If the build machine has direct internet:**

```bash
cd iptt
podman build -t artifactory.example.com/docker-local/iptt:1.0.0 .
```

**If the build machine only reaches JFrog** (base image + PyPI proxied through Artifactory):

```bash
podman build \
  --build-arg BASE_IMAGE=artifactory.example.com/docker-remote/python:3.12-slim \
  --build-arg PIP_INDEX_URL="https://artifactory.example.com/artifactory/api/pypi/pypi-remote/simple/" \
  -t artifactory.example.com/docker-local/iptt:1.0.0 .
```

> If JFrog doesn't proxy Docker Hub yet, mirror the base image once with skopeo:
> `skopeo copy docker://docker.io/library/python:3.12-slim docker://artifactory.example.com/docker-local/python:3.12-slim`
> and use that as `BASE_IMAGE`.

> **Architecture:** build for your cluster's node arch (`--platform linux/amd64` or
> `linux/arm64`). If nodes are mixed, build+push a multi-arch manifest list.

### 2b. Verify locally (optional but recommended)

```bash
podman run --rm -p 8080:8080 artifactory.example.com/docker-local/iptt:1.0.0
curl http://[::1]:8080/login        # expect the IPTT login HTML
```

### 2c. Push

```bash
podman login artifactory.example.com            # user + API key / identity token
podman push artifactory.example.com/docker-local/iptt:1.0.0
```

JFrog path styles — both work, use whatever your Artifactory is configured for:

- Path method:  `artifactory.example.com/<repo-key>/iptt:1.0.0`
- Subdomain:    `<repo-key>.artifactory.example.com/iptt:1.0.0`

---

## 3. One-time cluster setup

```bash
oc new-project iptt
```

### 3a. Make nodes trust the JFrog certificate (usually already done in airgaps)

If JFrog TLS is signed by your corporate CA, the cluster must trust it. This needs
**cluster-admin** (ask your platform team if image pulls fail with x509 errors):

```bash
oc create configmap jfrog-ca -n openshift-config \
    --from-file=artifactory.example.com=/path/to/corporate-ca.crt
oc patch image.config.openshift.io/cluster --type=merge \
    -p '{"spec":{"additionalTrustedCA":{"name":"jfrog-ca"}}}'
```

### 3b. Pull secret for JFrog

```bash
oc create secret docker-registry jfrog-pull-secret \
    --docker-server=artifactory.example.com \
    --docker-username=<user> \
    --docker-password=<api-key-or-password> \
    --docker-email=unused@example.com

oc secrets link default jfrog-pull-secret --for=pull
```

### 3c. App session secret

```bash
oc create secret generic iptt-secret \
    --from-literal=SESSION_SECRET="$(openssl rand -hex 32)"
```

---

## 4. Deploy

```bash
# Edit the image: line in openshift/iptt-airgap.yaml -> your real JFrog ref/tag
sed -i 's#image: artifactory.example.com/docker-local/iptt:1.0.0#image: <your-real-ref>#' \
    openshift/iptt-airgap.yaml

oc apply -f openshift/iptt-airgap.yaml
oc rollout status deploy/iptt

# First time only: create DB tables + seed users (admin/Manoj_PM/Manoj_Viewer)
oc exec deploy/iptt -- python seed_admin.py

oc get route iptt          # your https URL
```

Open the route URL and log in with **admin / admin123**.

---

## 5. Releasing updates

```bash
# build machine
podman build -t artifactory.example.com/docker-local/iptt:1.0.1 .
podman push artifactory.example.com/docker-local/iptt:1.0.1

# cluster
oc set image deploy/iptt iptt=artifactory.example.com/docker-local/iptt:1.0.1
oc rollout status deploy/iptt
```

Tips:
- Prefer a **new tag per release** (what's running is always obvious).
- If you reuse `:latest`, set `imagePullPolicy: Always` and run
  `oc rollout restart deploy/iptt` after each push.
- For maximal reproducibility deploy by digest:
  `artifactory.example.com/docker-local/iptt@sha256:<digest>`
  (get it via `skopeo inspect docker://<ref>` or JFrog UI).

---

## 6. IPv6 notes (single-stack cluster)

- The app binds `::` — done in the image, no action needed. `HOST` env can override it.
- Nothing in the manifests hardcodes IPv4: the Service has no `ipFamilies` (cluster
  defaults apply — it will get an IPv6 ClusterIP), probes target the pod IP
  (IPv6) automatically, and Routes are IPv6-native.
- Use **hostnames** (not literal IPs) for JFrog in pull secrets and image refs —
  avoids IPv6-literal-in-URL issues.
- External clients reach the app through the OpenShift Router (HAProxy) regardless
  of their family, as long as DNS/Ingress for the cluster is published (A and/or AAAA).

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ImagePullBackOff`, event: `x509: certificate signed by unknown authority` | Nodes don't trust JFrog's CA → §3a |
| `ImagePullBackOff`, event: `401 Unauthorized` | Pull secret wrong/missing → §3b; check `oc get secret jfrog-pull-secret -o jsonpath='{.data.\.dockerconfigjson}' \| base64 -d` |
| `ImagePullBackOff`, event: `manifest unknown` | Wrong repo path or tag; verify with `skopeo inspect docker://<ref>` from the build machine |
| Pods Ready but timeouts via route | Almost always an app bound to `0.0.0.0` on IPv6 — verify: `oc exec deploy/iptt -- sh -c 'netstat -lnt 2>/dev/null \|\| ss -lnt'` should show `[::]:8080` |
| `CrashLoopBackOff` | `oc logs deploy/iptt` — usually missing `iptt-secret` (§3c) |
| Login works but sessions drop on restart | `SESSION_SECRET` not coming from the Secret (fallback value changes nothing, but fix it anyway per §3c) |
| DB empty after pod reschedule | PVC not mounted; the manifest mounts `iptt-data` at `/app/data` and sets `DATABASE_URL` accordingly — both must be present |
| 2+ replicas → lock/corruption errors | SQLite = single writer. Keep `replicas: 1`; move to PostgreSQL for HA |

Handy commands:

```bash
oc get pods -l app=iptt
oc describe pod -l app=iptt        # pull events / probe failures
oc logs -f deploy/iptt
oc exec deploy/iptt -- ls -ld /app/data    # PVC perms (fsGroup should make it group-writable)
```

---

## 8. Before calling it production

1. **Change default passwords** (`admin123` / `pm123` / `viewer123`):
   `oc exec deploy/iptt -- sh -c 'SEED_ADMIN_PASSWORD=<strong> python seed_admin.py'`
   won't change existing users — update passwords in the UI after first login.
2. **PostgreSQL for HA** (enables >1 replica): deploy `postgresql` from the
   airgapped catalog/mirrored image, then
   `oc set env deploy/iptt DATABASE_URL="postgresql+psycopg2://user:pass@postgresql:5432/iptt"`
   and add `psycopg2-binary` to `requirements.txt` (rebuild image).
3. **Backups**: snapshot the `iptt-data` PVC via your storage class tooling.
4. Email (`email_utils.py`) is disabled by default; if enabled, inject SMTP
   credentials via the `iptt-secret` Secret — never bake them into the image.
5. Tune resource requests/limits from `oc adm top pod` observations.
