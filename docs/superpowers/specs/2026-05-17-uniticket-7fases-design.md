# UniTicket — Diseño 7 Fases

**Fecha:** 2026-05-17
**Curso:** 750021C — Desarrollo de Software II
**Grupo:** 7
**Repositorio (objetivo):** público en GitHub, GitFlow estricto

---

## 1. Contexto

Sistema web de gestión de incidencias técnicas para laboratorios universitarios. Énfasis en ecosistema DevOps con Jenkins centralizado en VPS, CI/CD automatizado, contenedores Docker y GitFlow. Desarrollo en 7 fases: fases 1–6 corresponden a los Documentos de Apoyo 01–06; fase 7 es la construcción completa de UniTicket sobre el pipeline ya operativo.

## 2. Infraestructura asignada (Grupo 7)

| Recurso | Valor |
|---|---|
| VPS | `45.55.145.98` |
| Jenkins UI | `http://45.55.145.98:8087` |
| Password inicial Jenkins | `ba6debd312b5482487bf17136cf8d780` |
| Webhook URL | `http://45.55.145.98:9007/github-webhook/` |
| Puerto app | `7007` |
| URL app | `http://45.55.145.98:7007` |
| Compose project name | `uniticket-grupo-7` |
| Credential ID en Jenkins | `github-token-grupo-7` |

## 3. Stack técnico

- **Backend:** Django 5 (Python 3.11)
- **DB:** PostgreSQL 15 (contenedor)
- **Frontend:** Django templates + Bootstrap 5 (server-rendered, sin contenedor frontend SPA adicional; la app web y la DB sí viven en contenedores separados)
- **Auth:** Django auth nativa + grupos (`usuario`, `tecnico`)
- **Tests:** pytest + pytest-django + coverage.py
- **Lint:** flake8
- **Orquestación:** Docker Compose
- **CI/CD:** Jenkins Declarative Pipeline (`Jenkinsfile`)

Razón: alineado a ejemplos de los documentos; arquitectura de **dos contenedores como mínimo** (`web` + `db`) cumpliendo el entregable 8.2 del Proyecto de Curso; cobertura natural con pytest; CRUD simple no justifica añadir contenedor frontend SPA.

## 4. Reglas operativas (todas las fases)

- **GitFlow estricto:** `main` (producción) ← `develop` (integración) ← `feature/*`. `hotfix/*` directo a `main` solo si se justifica.
- **Pull Requests obligatorios** hacia `develop` y `main`. Code review por compañero.
- **Conventional Commits:** `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `refactor:`, `style:`, `build:`.
- **Pipeline rojo bloquea merge.** Nunca se mezcla un feature si el pipeline falla.
- **Sin atribución de IA** en commits.
- **OWASP Top 10:**
  - `SECRET_KEY` desde variable de entorno
  - `DEBUG=False` en producción
  - `ALLOWED_HOSTS` configurado
  - CSRF middleware activo
  - Password hashing PBKDF2 (Django default)
  - Validadores de password
  - Permisos por vista (decoradores + role checks)
  - Inputs validados por Forms/Serializers

## 5. Fases

### Fase 1 — Configuración de Entorno y Flujo de Trabajo (Doc Apoyo 01)

**Objetivo:** Acceso a Jenkins, repo en GitHub con ramas GitFlow, PAT registrado en Jenkins.

**Entregables:**
- Repo público en GitHub con ramas `main` y `develop`.
- `develop` como rama por defecto en GitHub.
- Protección de ramas: prohibir push directo a `main` y `develop`.
- Credencial `github-token-grupo-7` (Username+Password con PAT) en Jenkins.

**Acción humana ya cubierta por el usuario** (per confirmación):
- Cambio de password Jenkins.
- Generación de PAT en GitHub.
- Creación de repo público.
- Registro de credencial en Jenkins.

**Cómo confirmar:**
- Login a `http://45.55.145.98:8087` exitoso.
- `git ls-remote` muestra `main` y `develop`.
- En GitHub Settings → Branches → reglas activas en `main` y `develop`.
- En Jenkins → Manage Credentials → `github-token-grupo-7` listada.

---

### Fase 2 — Contenerización (Doc Apoyo 02)

**Objetivo:** App Django ejecutable en contenedores con persistencia y comunicación con Postgres.

**Entregables:**
- Proyecto Django mínimo (`uniticket/` + app `tickets/` placeholder).
- `requirements.txt` (Django, psycopg2-binary, gunicorn).
- `Dockerfile` (python:3.11-slim, gunicorn).
- `docker-compose.yml` con servicios `web` y `db`, volumen `db_data`, puerto host `7007` → `8000` contenedor.
- `.env.example` con `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`.
- `.gitignore` (Python, Django, venv, .env).

**Cómo confirmar:**
- `docker compose build` sin errores.
- `docker compose up -d` levanta `web` y `db`.
- `curl http://localhost:7007/` retorna página Django.
- `docker compose down && docker compose up -d` mantiene datos.

**Commits sugeridos:**
- `chore: bootstrap django project`
- `build: add dockerfile and compose for web+postgres`

---

### Fase 3 — Construcción Automática del Pipeline (Doc Apoyo 03)

**Objetivo:** `Jenkinsfile` + Job en Jenkins que detecta cambios y construye imagen.

**Entregables:**
- `Jenkinsfile` en raíz con stages `Checkout` y `Build Image`.
- Variable `IMAGE_NAME = "uniticket-grupo-7"`.

**Acción humana requerida:**
1. Abrir `http://45.55.145.98:8087`.
2. New Item → `uniticket-grupo-7` → Pipeline.
3. Build Triggers → ✓ `GitHub hook trigger for GITScm polling`.
4. Build Triggers → ✓ `Poll SCM` con schedule `H/2 * * * *` (provisional, se desactiva en Fase 4).
5. Pipeline → Definition: `Pipeline script from SCM`.
6. SCM: Git → Repository URL: `<URL del repo>` → Credentials: `github-token-grupo-7` → Branch Specifier: `*/develop`.
7. Script Path: `Jenkinsfile`.
8. Save.

**Cómo confirmar:**
- `git push origin develop` con cambio trivial → Jenkins ejecuta build ≤2 min y queda verde.
- En VPS: imagen `uniticket-grupo-7:latest` existe (visible en build log).

**Commit sugerido:**
- `ci: add jenkinsfile with checkout and build stages`

---

### Fase 4 — Webhooks y Validación de PRs (Doc Apoyo 04)

**Objetivo:** Comunicación en tiempo real GitHub→Jenkins. Validación en PR con status checks en GitHub.

**Entregables:**
- `Jenkinsfile` actualizado con bloque `post { success / failure }`.
- Validación de PR: pipeline dispara en apertura/actualización de PR a `develop`.

**Acción humana requerida:**
1. **GitHub** → repo → Settings → Webhooks → Add webhook.
2. Payload URL: `http://45.55.145.98:9007/github-webhook/` (con `/` final).
3. Content type: `application/json`.
4. Events: Let me select individual events → ✓ Pushes, ✓ Pull requests.
5. Add webhook. Verificar ✓ verde tras "Recent Deliveries".
6. **Jenkins** → Job → Configure → desmarcar `Poll SCM` (queda solo el GitHub hook).
7. **GitHub** → repo → Settings → Branches → Branch protection rule para `develop` y `main` → ✓ "Require status checks to pass before merging" → seleccionar el check de Jenkins (aparece tras primera ejecución).

**Cómo confirmar:**
- Crear PR `feature/test-webhook` → `develop` con cambio trivial → pestaña Conversation del PR muestra check amarillo → verde tras éxito.
- Branch protection bloquea merge si check rojo.

**Commit sugerido:**
- `ci: add post-build status reporting to jenkinsfile`

---

### Fase 5 — Pruebas Automatizadas y Análisis Estático (Doc Apoyo 05)

**Objetivo:** Stages de lint + tests que detienen el pipeline si fallan, con reportes visibles.

**Entregables:**
- `requirements.txt` con `pytest`, `pytest-django`, `coverage`, `flake8`.
- `pytest.ini` o `pyproject.toml` configurado para Django.
- `.flake8` con `max-line-length = 100`, `exclude = venv,migrations,*/settings/*`.
- Suite mínima de tests (`tests/test_smoke.py`).
- `Jenkinsfile` con stages `Static Analysis` y `Unit Tests` antes de `Build Image` (o usando imagen ya construida).
- Generación de `junit.xml` y `coverage.xml`; publicación en bloque `post { always { junit ... } }`.

**Cómo confirmar:**
- PR con error de flake8 (línea larga) → pipeline rojo, merge bloqueado.
- PR con test fallido → pipeline rojo.
- PR limpio → verde, reporte JUnit visible en Jenkins, % coverage publicado.

**Commits sugeridos:**
- `test: add pytest config and smoke test`
- `ci: add lint and test stages with junit reports`

---

### Fase 6 — Despliegue Continuo y Cierre (Doc Apoyo 06)

**Objetivo:** Stage de deploy automatizado en VPS + limpieza de imágenes huérfanas.

**Entregables:**
- `Jenkinsfile` con stage `Deploy to Staging` que solo corre cuando branch == `main` (o cuando pasan las anteriores):
  ```
  docker compose -p uniticket-grupo-7 down || true
  docker compose -p uniticket-grupo-7 up -d --build
  docker image prune -f
  ```
- Variables sensibles vía credentials de Jenkins (no en repo).
- Esqueleto de informe técnico en `docs/informe/`.

**Cómo confirmar:**
- Merge `develop` → `main` (vía PR aprobado y pipeline verde) dispara pipeline completo.
- `curl http://45.55.145.98:7007/` responde con la versión actualizada.
- `docker ps` en VPS muestra `uniticket-grupo-7-web-1` y `uniticket-grupo-7-db-1`.

**Commit sugerido:**
- `ci: add deploy-to-staging stage with cleanup`

---

### Fase 7 — Construcción completa de UniTicket (GitFlow)

**Objetivo:** Implementar todas las funcionalidades del producto sobre el pipeline ya operativo.

**Requisitos funcionales (del Proyecto de Curso):**
1. **Autenticación con roles:** `Usuario Estándar` y `Técnico/Administrador`.
2. **Creación de tickets:** ubicación, identificador de equipo, descripción, fecha automática.
3. **Dashboard:** lista de tickets con estado visual (`Abierto`, `En Progreso`, `Resuelto`).
4. **Gestión por técnico:** detalle, cambio de estado, nota de resolución.

**Features (ramas):**
- `feature/auth-roles` — User + grupos `usuario`/`tecnico`, login/logout, decoradores de permiso, registro de usuarios.
- `feature/ticket-model-and-create` — modelo `Ticket` (location, equipment_id, description, status, created_by, created_at, updated_at, resolved_at, resolution_note), form crear, vista crear.
- `feature/dashboard` — lista paginada, filtros por estado, badges Bootstrap.
- `feature/ticket-detail-and-update` — detalle, transición de estados (solo técnico), nota de resolución, historial.
- `feature/ui-polish` — uso de skill `ui-ux-pro-max` para layout consistente y accesible.
- `feature/seed-and-fixtures` — comando `manage.py seed_demo` con datos de prueba.

**Por cada feature:**
1. `git checkout develop && git pull`
2. `git checkout -b feature/<nombre>`
3. Tests primero (TDD) → implementación → flake8 limpio.
4. Push → PR → pipeline verde → review compañero → merge a `develop`.
5. Cuando develop estable: PR `develop` → `main` → deploy automático.

**Cómo confirmar:**
- Login con usuario estándar permite crear ticket pero no cambiar estado de otros.
- Login con técnico ve dashboard completo y puede actualizar estados.
- Dashboard refleja cambios en tiempo real.
- Historial de PRs y reviews visible en GitHub.
- App accesible en `http://45.55.145.98:7007` y refleja últimos cambios merged a `main`.

---

## 6. Mecanismo de pausa/confirmación

Al cierre de cada fase, el asistente emite:

```
=== FASE N COMPLETA ===
Cambios: <lista de archivos/commits>
Cómo confirmar: <pasos verificables>
Acción humana requerida: <pasos detallados si aplica>
Confirmar con: "ok fase N" o "continuar"
```

El asistente no avanza a la siguiente fase hasta recibir confirmación explícita del usuario.

## 7. Estructura inicial del repo (al final de Fase 2)

```
.
├── Dockerfile
├── Jenkinsfile                  # añadido en Fase 3
├── docker-compose.yml
├── manage.py
├── requirements.txt
├── .env.example
├── .flake8                      # añadido en Fase 5
├── .gitignore
├── pytest.ini                   # añadido en Fase 5
├── uniticket/                   # settings module
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tickets/                     # app principal
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── templates/tickets/
│   └── migrations/
├── tests/                       # añadido en Fase 5
│   └── test_smoke.py
└── docs/
    └── informe/                 # añadido en Fase 6
```

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Puerto 7007 ocupado por contenedor previo | `docker compose down` en stage deploy + verificar `docker ps` |
| PAT expira durante desarrollo | Reemitir PAT con scopes `repo`, `repo:status`; actualizar credencial en Jenkins |
| Webhook con error 500 | Revisar Recent Deliveries en GitHub; validar puerto 9007 accesible |
| Pipeline falla por dependencia faltante | `requirements.txt` único origen de verdad; build local antes de push |
| VPS sin espacio | `docker image prune -f` en stage deploy |
| Merge accidental con pipeline rojo | Branch protection rules con required status checks |

## 9. Criterio de éxito global

- Pipeline completo `Checkout → Lint → Test → Build → Deploy` verde de extremo a extremo.
- App UniTicket funcional accesible públicamente en `http://45.55.145.98:7007`.
- Historial GitFlow limpio en GitHub con PRs y code reviews documentados.
- Cobertura de pruebas reportada y > 0% (ideal ≥ 60% para CRUD básico).
- Informe técnico final con diagramas (pipeline, infra, red).
