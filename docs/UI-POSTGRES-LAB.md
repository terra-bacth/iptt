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


## Responsive UI revision (theme v4)

Theme v4 extends the workspace shell to **every** route and adds motion. CSS and
JS stay local; no new runtime dependency, API call or build step was added.

### One navigation, on every page
- `templates/partials/nav.html` is now the single source of truth for the menu.
  Seventeen templates that carried their own copy of the bar (with drifting
  labels such as "Overview", "Sign out" and "Logout") now include the partial,
  and six pages that had no navigation at all gained it: audit logs, the circle
  executive dashboard and the scope pages.
- **Fixed: invisible navigation links.** Each legacy page shipped a local style
  block, loaded after `theme.css`, whose equal-specificity rules (for example
  `.top-nav .nav-links a { color: #ffffff }`) beat the shared theme and painted
  white links on the white bar. The local navigation CSS was removed from every
  template, and the shared rules now use a `body`-prefixed selector that no page
  rule can outrank.
- **The IPTT brand is a link to `/home` on every page**, with an accessible name
  and a hover treatment (the mark tilts and lifts). Its label is hidden from
  screen readers only when the wordmark is already visible.
- The menu is identical everywhere: Home, Programmes, Governance, and for admins
  Users and Audit Logs, then Security settings and Sign out.

### Motion
| Effect | Where | Notes |
| --- | --- | --- |
| `iptt-drop-in` | navigation bar | 0.45s on load |
| `iptt-rise` | page sections | staggered 0.5s entrance |
| Hover lift | cards, KPI tiles, report cards | 3px rise + soft shadow |
| Press feedback | buttons | 2px rise, `scale(.985)` on active |
| `iptt-grow` | progress gauges | grows from the left on load |
| `iptt-menu-in` | mobile menu | 0.28s slide instead of a jump |
| `iptt-footer-fade` | footer credit | fades in, then rests subdued |
| `iptt-heartbeat` | the credit's heart | beats while hovered or keyboard-focused |
| Scroll reveal | below-the-fold cards | driven by `IntersectionObserver` |

Motion is deliberately conservative: durations stay under 1.1s, no parallax or
carousels, and a `setTimeout` safety net reveals every block after 3s so no
browser can leave content hidden. `@media (prefers-reduced-motion: reduce)`
disables all of it and pins the credit to full opacity; `@media print` forces
revealed blocks visible.

### Footer credit
The credit now reads **Hosted with ❤️ by CloudTeam**, fades in on load, rests at
80% opacity and brightens with a slight lift when the pointer reaches it, while
the heart beats twice per second. The heart is an inline SVG with `role="img"`
and `aria-label="love"`, so it renders on devices without an emoji font. The
resting state measures 7.2:1 against the page background, so the faded look never
costs legibility.

### Also in this revision
- `GET /projects` without a programme id redirects instead of returning HTTP 422.
- The circle executive dashboard's executive summary rendered with no card
  surface (the `.dashboard-card` class had no rule anywhere) and the template's
  own newlines were expanded by `white-space: pre-line`, pushing the text outside
  the box. Both are fixed, and the summary is trimmed.
- Summary tiles use two columns on phones: six KPIs in one column made a very
  long scroll.
- Login logo 1.3 MB -> 83 KB; unused logo variants downscaled (~2 MB saved).

### Verification
- `axe-core` (WCAG 2.0/2.1 A + AA): **0 violations across 17 routes at 390px and
  1440px**, measured after animations settle.
- No horizontal overflow at 320/390/768/1440px; every page renders exactly one
  navigation bar, the brand resolves to `/home`, and every footer carries the
  credit (checked in the browser on all 17 routes).
- `prefers-reduced-motion` verified: no animations, credit at full opacity,
  scroll-reveal off.

### Automated check
```bash
docker-compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_ui.py
```

`scripts/check_ui.py` is read-only and now runs **365 checks**: the shell
contract, single-navigation and single-footer rules, footer credit wording,
the animation set and its reduced-motion guard, the faded-credit contrast ratio,
the absence of page-local navigation CSS and of the removed low-contrast colours,
plus live requests to the running app. It fails if any of the regressions fixed
above is reintroduced.

Update the existing lab without removing the database volume:

```bash
git switch ui-postgres-lab
git pull --ff-only origin ui-postgres-lab
docker-compose -p iptt-lab -f compose.postgres.yaml up -d --build --force-recreate app
docker-compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_ui.py
```

Cache keys were bumped (`theme.css?v=9`, `ui.js?v=8`, `execution.js?v=1.0.2`);
refresh the browser with Ctrl+Shift+R. If Git reports the earlier local Compose
fix as an overlapping change, compare it first: the remote file already uses
`version: "2.4"`. Preserve any other local edits before pulling.

During visual acceptance, check 390px, 768px and desktop widths, 200% zoom,
keyboard-only navigation, the Menu/Escape behavior, the footer credit hover,
and the same pages with "reduce motion" enabled in the operating system. Report
rendering, contrast and screen-reader findings from your environment here.
