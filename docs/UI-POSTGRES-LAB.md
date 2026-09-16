# UI refresh and PostgreSQL lab

This branch adds a responsive UI and a PostgreSQL driver. Backend routes, form
actions, authentication, roles, calculations, models and PDF templates are
unchanged. The small local ui.js adds presentation behavior (mobile navigation,
table scrolling and accessible labels). SQLite remains the default when
DATABASE_URL is absent.

The lab starts with an **empty PostgreSQL database**. Changing DATABASE_URL does
not migrate SQLite data. Keep the existing deployment and its database intact.
Before a real migration, stop writes, back up SQLite, rehearse a typed data copy
preserving IDs/password hashes, reset PostgreSQL sequences, and reconcile every
table plus reports. PostgreSQL enforces foreign keys that SQLite may not have
enforced; existing orphan records or deletion paths need validation.

## 1. Killercoda: container test

Use a Killercoda environment with Docker and either Compose v2 (`docker compose`)
or legacy Compose v1.21+ (`docker-compose`) installed. The file uses format 2.4
for compatibility with both; modern Compose may warn that `version` is obsolete.
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
docker compose -p iptt-lab -f compose.postgres.yaml up -d --build --wait
docker compose -p iptt-lab -f compose.postgres.yaml exec app python seed_admin.py
docker compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_database.py
curl -f http://localhost:8080/login >/dev/null
```

### If your environment uses `docker-compose`

Use the same .env setup above, then run these commands instead of the v2 commands:

```bash
docker-compose -p iptt-lab -f compose.postgres.yaml config --quiet
docker-compose -p iptt-lab -f compose.postgres.yaml up -d --build
docker-compose -p iptt-lab -f compose.postgres.yaml ps
# Once app is running, seed and check the database:
docker-compose -p iptt-lab -f compose.postgres.yaml exec app python seed_admin.py
docker-compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_database.py
```

Legacy Compose does not support `up --wait`. The dependency health check still
waits for PostgreSQL before starting the app. Use `ps` to confirm app health.
For subsequent commands, replace `docker compose` with `docker-compose -p iptt-lab`.
Keep the project name consistent so restarts reuse the same database volume.

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
docker compose -p iptt-lab -f compose.postgres.yaml restart
docker compose -p iptt-lab -f compose.postgres.yaml ps
docker compose -p iptt-lab -f compose.postgres.yaml logs --tail=100 app postgres
docker compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_database.py
```

The named volume survives container recreation but is local to the Killercoda
environment. Export a backup before the environment expires:

```bash
docker compose -p iptt-lab -f compose.postgres.yaml exec -T postgres \
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
- Compiled all Jinja templates; verified home data conditions, loops, form actions
  and option values remain unchanged after the responsive revision.
- Checked all three roles across seven pages, one main landmark and one footer
  per page, and role-specific home controls. Checked JavaScript syntax.
- Parsed deployment YAML; compiled all nine SQLAlchemy tables to PostgreSQL DDL.
- Checked database connectivity and table inventory against SQLite.

Not yet executed: live PostgreSQL operations, container builds, Killercoda and
OpenShift. This workspace has no container runtime or PostgreSQL server.
The responsive revision was browser-tested locally at 390px, 768px and 1440px;
home had no horizontal overflow and the mobile Menu/Escape behavior passed.
Six additional pages passed a 390px horizontal-overflow check.
DDL compilation is not proof of PostgreSQL workflow compatibility. Complete the
acceptance checks above before promoting this draft.

## References

- [Killercoda port access](https://killercoda.com/creators)
- [SQLAlchemy database URLs](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [Official PostgreSQL container](https://hub.docker.com/_/postgres)
- [OpenShift-oriented PostgreSQL containers](https://github.com/sclorg/postgresql-container)


## Responsive UI revision (theme v3)

Theme v3 keeps the workspace shell introduced in v2 and extends it to every
route, so each page shares one navigation, one footer and one accessible
palette. CSS and JS stay local; no new runtime dependency, API call or build
step was added.

### Responsive design
- One content column with a `1440px` ceiling, `clamp()` page padding and
  `repeat(auto-fit, minmax(min(100%, 340px), 1fr))` card grids that reflow from
  large monitors down to 320px phones.
- Explicit breakpoints at `1000px` (tablet, home grid collapses, navigation
  becomes a Menu button), `640px` (phones) and `420px` (small phones).
- Download/upload toolbars, filter bars and KPI panels wrap instead of forcing
  a fixed width; wide data tables scroll inside their own region.
- Verified with a headless browser at 320px, 390px, 768px and 1440px: no page
  exceeds the viewport width on any of the audited routes.

### Intuitive navigation
- Same primary nav on every page, same label for the same destination
  (Home, Programmes, Projects, Users, Audit Logs, Circle Dashboard, Sign out),
  with current-page marking and a keyboard-operable mobile menu
  (Enter/Space to open, Escape to close, `aria-expanded` kept in sync).
- Removed duplicate "Create Project" links that pointed at the same route and
  deep-linked it to the create form (`/projects/{id}#create-project`).
- `GET /projects` no longer answers `422` when the programme id is missing: it
  forwards to the only programme the user can open, otherwise to `/programmes`.

### User experience
- Consistent 44px minimum control height, visible keyboard focus rings and a
  "Skip to main content" link on every page.
- Fewer layout surprises: the execution KPI gauges no longer print a duplicate
  percentage inside a narrow fill, and empty states are centred and legible.
- The login logo went from 1.3 MB to 83 KB (320px master, still far above its
  100px render size) which cuts first-paint time on slow links; the two unused
  logo variants were downscaled as well.

### Accessibility (WCAG 2.1 AA)
- Palette rebuilt so every text colour clears 4.5:1 on the surfaces it is used
  on: links `#16509f`, secondary text `#4b5b70`, success `#0f6b45`, warning
  `#8a4b08`, danger `#a4262c`; white text sits only on surfaces of `4.5:1` or
  better (`#146c43`, `#b45309`, `#b02a37`, `#5b6a7a`).
- Status meaning is no longer carried by colour alone, links are underlined in
  text blocks, and progress gauges are marked decorative because the value is
  already printed next to them.
- Audit result: `axe-core` (WCAG 2.0/2.1 A + AA) reports **0 violations across
  17 routes at 390px and 1440px**, down from 121 contrast/link-in-text failures
  before this revision.

### Footer credit
`templates/partials/footer.html` is included by every full page and renders
`made with` + a heart + **CloudTeam** at the end of the page. The heart is an
inline SVG with `role="img"` and `aria-label="love"`, so it renders identically
on devices without an emoji font. The shell is a flex column, which keeps the
footer at the bottom of short pages.

### Automated check
```bash
docker-compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_ui.py
```

The script is read-only. It asserts the shared shell contract (viewport, main
landmark, skip link, theme/script includes, single footer with the CloudTeam
credit), the absence of the low-contrast colour literals that were removed,
the presence of the responsive/focus/reduced-motion rules, the palette contrast
ratios and the static asset budget, then logs in and re-checks the rendered
pages. Override the target with `IPTT_BASE_URL`, `IPTT_USERNAME`,
`IPTT_PASSWORD`, or set `IPTT_OFFLINE=1` for the static checks only.

Update the existing lab without removing the database volume:

```bash
git switch ui-postgres-lab
git pull --ff-only origin ui-postgres-lab
docker-compose -p iptt-lab -f compose.postgres.yaml up -d --build --force-recreate app
docker-compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_ui.py
```

CSS/JS cache keys were bumped (`theme.css?v=3`, `ui.js?v=4`,
`execution.js?v=1.0.2`); refresh the browser with Ctrl+Shift+R. If Git reports
the earlier local Compose fix as an overlapping change, compare it first: the
remote file already uses `version: "2.4"`. Preserve any other local edits
before pulling.

During visual acceptance, check 390px, 768px and desktop widths, 200% zoom,
keyboard-only navigation, the Menu/Escape behavior, long project names and
populated tables. Report rendering, contrast and screen-reader findings from
your environment back into this file.
