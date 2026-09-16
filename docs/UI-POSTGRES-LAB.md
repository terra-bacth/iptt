# UI refresh and PostgreSQL lab

This branch adds a shared CSS theme and a PostgreSQL driver. Routes, forms,
JavaScript, authentication, roles, calculations, models and PDF templates are
unchanged. SQLite remains the default when DATABASE_URL is absent.

The lab starts with an **empty PostgreSQL database**. Changing DATABASE_URL does
not migrate SQLite data. Keep the existing deployment and its database intact.
Before a real migration, stop writes, back up SQLite, rehearse a typed data copy
preserving IDs/password hashes, reset PostgreSQL sequences, and reconcile every
table plus reports. PostgreSQL enforces foreign keys that SQLite may not have
enforced; existing orphan records or deletion paths need validation.

## 1. Killercoda: container test

Use a Killercoda environment with Docker and Docker Compose v2 installed.
This step tests the app and database in containers, not Kubernetes scheduling.
Check both commands before proceeding:

```bash
docker version
docker compose version
```

From this branch's repository checkout:

```bash
# Create credentials only once; retain .env when restarting the lab.
test -e .env || (umask 077; printf 'POSTGRES_PASSWORD=%s\nSESSION_SECRET=%s\n' \
  "$(openssl rand -hex 24)" "$(openssl rand -hex 32)" > .env)
docker compose -f compose.postgres.yaml up -d --build --wait
docker compose -f compose.postgres.yaml exec app python seed_admin.py
docker compose -f compose.postgres.yaml exec app python scripts/check_database.py
curl -f http://localhost:8080/login >/dev/null
```

Open Killercoda's **Traffic / Ports** interface and access port **8080**.
Use the existing lab accounts from seed_admin.py: admin/admin123,
Manoj_PM/pm123 and Manoj_Viewer/viewer123. These are test accounts; use generated
credentials and the existing password-change UI for any persistent deployment.
Seeding is idempotent and does not reset existing passwords.

The database port is internal; only the app's port is published.
Generated hexadecimal passwords are URL-safe. If you supply another password,
URL-encode it in DATABASE_URL (the database itself receives the raw password).

## 2. Acceptance checks before OpenShift

Run the same actions with equivalent disposable data on the current app and
this branch. Compare results, not just page appearance:

| Area | Check |
|---|---|
| Authentication | Login/logout; invalid login; admin, PM and viewer permissions; current registration policy |
| Programme/project | Create, edit, assignment, and delete with and without child records |
| Scope/tasks | Upload the existing Excel templates; dependencies, plan generation, baseline locking |
| Execution | Update status/dates, delay reasons, and audit entries |
| Reporting | Dashboard totals, forecasts, filters, Excel/PDF exports |
| UI | Desktop and phone layouts; keyboard focus; status colours; all existing links/buttons |
| Persistence | Create a programme, restart both containers, log in and verify the programme remains |

```bash
docker compose -f compose.postgres.yaml restart
docker compose -f compose.postgres.yaml ps
docker compose -f compose.postgres.yaml logs --tail=100 app postgres
docker compose -f compose.postgres.yaml exec app python scripts/check_database.py
```

The named volume survives container recreation but is local to the Killercoda
environment. Export a backup before the environment expires:

```bash
docker compose -f compose.postgres.yaml exec -T postgres \
  pg_dump -U iptt -d iptt -Fc > iptt-lab.dump
```

Download the dump to your own machine. `docker compose ... down` preserves the
volume; `down -v` deletes it. Do not delete the volume when testing persistence.

## 3. OpenShift: separate test project

Build the same code and push to your registry as described in the main README.
Use a new project, e.g. `oc new-project iptt-ui-test`. The PostgreSQL manifest
requires a default StorageClass (or set storageClassName on its PVC). It uses
the Red Hat PostgreSQL 16 image, with its own environment variable names and
data path. Mirror that image into JFrog for a disconnected cluster; pin approved
image digests before promotion. Registry pull credentials must cover both images.

```bash
# Registry authentication: link your existing pull secret in this new project.
oc secrets link default jfrog-pull-secret --for=pull

# Create the following secrets once. Do not regenerate on an existing database.
IPTT_DB_PASSWORD=$(openssl rand -hex 24)
oc create secret generic iptt-postgres-secret \
  --from-literal=POSTGRES_PASSWORD="$IPTT_DB_PASSWORD"
oc create secret generic iptt-secret \
  --from-literal=SESSION_SECRET="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URL="postgresql+psycopg2://iptt:${IPTT_DB_PASSWORD}@iptt-postgres:5432/iptt"
unset IPTT_DB_PASSWORD

# Edit image references in BOTH files to the images available in your registry.
oc apply -f deploy/openshift/postgres.yaml
oc rollout status deploy/iptt-postgres --timeout=180s
oc apply -f deploy/openshift/app.yaml
oc rollout status deploy/iptt --timeout=180s
oc exec deploy/iptt -- python seed_admin.py
oc exec deploy/iptt -- python scripts/check_database.py
oc get route iptt
```

If using registry.redhat.io directly, configure an appropriate Red Hat registry
pull secret instead. The manifests leave UID/fsGroup allocation to OpenShift,
drop capabilities, and retain the app's IPv6 bind (`HOST=::`). Keep one app replica
while validating; PostgreSQL alone does not establish whole-application HA.
Readiness checks `/login`; the database check above separately verifies SQL.
Repeat the acceptance matrix through the Route, including a database pod restart
and persistence check. This database is a single instance, not an HA deployment.

## Scope and rollback

The original OpenShift manifests are unchanged. Do not apply both SQLite and
PostgreSQL app manifests into the same project. Your current environment can
continue to use its original image and SQLite PVC during the lab.

To revert only styling, remove the theme.css links (or revert the UI commit).
Reverting an image does not transfer data back from PostgreSQL to SQLite.

## Checks performed on this draft

- Installed Python dependencies and started the app with a disposable SQLite DB.
- Seeded all three existing roles; checked login/logout, five main pages per
  role, admin user-list access, programme creation and non-admin creation denial
  with FastAPI TestClient.
- Compiled all Jinja templates and verified the original template bytes are
  preserved after removing only the added stylesheet and viewport tags.
- Parsed deployment YAML; compiled all nine SQLAlchemy tables to PostgreSQL DDL.
- Checked database connectivity and table inventory against SQLite.

Not yet executed: live PostgreSQL operations, container builds, Killercoda,
OpenShift and visual browser QA. This workspace had no container runtime or
PostgreSQL server; browser installation failed on the download endpoint.
DDL compilation is not proof of PostgreSQL workflow compatibility. Complete the
acceptance checks above before promoting this draft.

## References

- [Killercoda port access](https://killercoda.com/creators)
- [SQLAlchemy database URLs](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [Official PostgreSQL container](https://hub.docker.com/_/postgres)
- [OpenShift-oriented PostgreSQL containers](https://github.com/sclorg/postgresql-container)
