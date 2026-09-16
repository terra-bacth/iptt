# Deploying IPTT on OpenShift

This guide takes the IPTT FastAPI application from the repo and runs it on an
OpenShift cluster. It has been smoke-tested locally (install, DB seed, login flow).

---

## 0. What was changed to make the app cluster-ready

| Problem in the repo | Fix in this branch |
|---|---|
| `requirements.txt` was a Windows conda export (`file:///C:/...` paths) — uninstallable on Linux | Rewritten with pinned, Linux-compatible versions (validated by a clean install + app boot test) |
| No `Dockerfile` | Added `Dockerfile` (Python 3.12-slim, runs `uvicorn main:app` on port 8080, OpenShift random-UID compatible) |
| SQLite path hardcoded to `iptt.db` in the working dir | `database.py` now reads `DATABASE_URL` from the environment (defaults to the old local behavior) |
| Session secret hardcoded in `main.py` | Read from `SESSION_SECRET` env var (OpenShift Secret), old value kept as local fallback |
| `seed_admin.py` crashed on a fresh DB ("no such table: user") | It now creates tables first and is idempotent |

> No application logic was changed. Local dev (`uvicorn main:app --reload`) still works
> exactly as before.

---

## 1. Prerequisites

1. Access to an OpenShift cluster (4.x) and permission to create a project.
2. The `oc` CLI installed: https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html
3. Logged in:
   ```bash
   oc login https://api.<your-cluster>:6443
   ```

---

## 2. Push the deployment files to GitHub

OpenShift will build **from your Git repo**, so the new files must be pushed:

```bash
git add requirements.txt Dockerfile .dockerignore database.py seed_admin.py main.py openshift/ OPENSHIFT_DEPLOYMENT.md
git commit -m "Make IPTT deployable on OpenShift"
git push origin main
```

---

## 3. Deploy (CLI path — recommended)

```bash
# 3.1 Create a project (namespace)
oc new-project iptt

# 3.2 Apply BuildConfig, ImageStream, PVC, Deployment, Service, Route
oc apply -f openshift/iptt-all-in-one.yaml

# 3.3 Create the session secret (generated random, not stored in git)
oc create secret generic iptt-secret \
    --from-literal=SESSION_SECRET="$(openssl rand -hex 32)"

# 3.4 Build the image on the cluster and watch it
oc start-build iptt --follow

# 3.5 Wait for the rollout
oc rollout status deploy/iptt

# 3.6 First time only: create tables + seed default users
oc exec deploy/iptt -- python seed_admin.py

# 3.7 Get your URL (https, edge-TLS route is already configured)
oc get route iptt
```

Open `https://<route-host>` and log in with **admin / admin123**
(or the value of `SEED_ADMIN_PASSWORD` if you set one).

---

## 4. Alternative paths

### 4a. `oc new-app` (no YAML, uses the Dockerfile auto-detected in the repo)

```bash
oc new-project iptt
oc new-app https://github.com/spandey171294/iptt.git --name=iptt --strategy=docker
oc expose service iptt
oc create secret generic iptt-secret --from-literal=SESSION_SECRET="$(openssl rand -hex 32)"
oc set env deploy/iptt SESSION_SECRET value-from secret...   # see note below
```

> The CLI path in §3 is preferred: `oc new-app` alone does not create the PVC or wire
> the secret/env, which this app needs.

### 4b. Web console (no CLI)

1. **Developer** perspective → **+Add** → **Import from Git**.
2. Git URL: `https://github.com/spandey171294/iptt.git` → builder image **Dockerfile** is auto-detected.
3. Create the application, then:
   - **Storage**: add a PVC and mount it at `/app/data` on the deployment.
   - **Environment**: add `DATABASE_URL=sqlite:////app/data/iptt.db` and `SESSION_SECRET` (from a Secret).
4. The console creates the Route for you (enable "Secure route" → edge termination).
5. Terminal tab of the running pod → run `python seed_admin.py` once.

---

## 5. Updating the app later

```bash
git push origin main                 # new code
oc start-build iptt --follow         # rebuild image on the cluster
oc rollout restart deploy/iptt       # (only needed if image auto-trigger is off)
oc rollout status deploy/iptt
```

---

## 6. Troubleshooting

| Symptom | What to check |
|---|---|
| Build fails at `pip install` | Confirm the **new** `requirements.txt` was pushed (§2). Old file references `C:\...` Windows paths and will always fail |
| Pod `CrashLoopBackOff` | `oc logs deploy/iptt` — usually the `iptt-secret` is missing (§3.3) |
| 401s / login not sticking | Each restart invalidates sessions if `SESSION_SECRET` isn't fixed — make sure it comes from the Secret, not the fallback |
| DB resets after pod restart | PVC not mounted. The Deployment must mount `iptt-data` at `/app/data` and `DATABASE_URL` must point there (both already in the YAML) |
| `permission denied` writing DB | The PVC dir must be group-writable. OpenShift's restricted SCC usually sets `fsGroup` automatically; check with `oc exec deploy/iptt -- ls -ld /app/data` |
| Scaling to 2+ replicas breaks the app | Expected: **SQLite allows one writer**. Keep `replicas: 1` (and `strategy: Recreate`), or migrate to PostgreSQL (§7) |
| 503 via route right after deploy | Normal while the build rolls out; wait for `oc rollout status` |

Useful commands:

```bash
oc logs -f deploy/iptt          # app logs
oc get pods -l app=iptt         # pod state
oc describe pod <pod>           # events (probe failures, mounts)
oc rsh deploy/iptt              # shell into the pod
```

---

## 7. Before calling it "production"

1. **Change default passwords** — `seed_admin.py` ships `admin123/pm123/viewer123`.
   Re-run with `SEED_ADMIN_PASSWORD=<strong>` or change them in the UI.
2. **PostgreSQL instead of SQLite** (needed for HA / >1 replica):
   ```bash
   oc new-app postgresql-persistent -p POSTGRESQL_DATABASE=iptt ...
   oc set env deploy/iptt DATABASE_URL="postgresql+psycopg2://user:pass@postgresql:5432/iptt"
   ```
   and add `psycopg2-binary` to `requirements.txt`. SQLAlchemy already abstracts the DB.
3. **Email** is disabled by default (`ENABLE_EMAIL=False` in `email_utils.py`); wire the
   SMTP credentials through an OpenShift Secret if you enable it.
4. **Backups**: snapshot the PVC or schedule `oc exec ... sqlite3 backup` jobs.
5. **Resource requests/limits** in the Deployment are starting points — tune from
   `oc adm top pod` data.
