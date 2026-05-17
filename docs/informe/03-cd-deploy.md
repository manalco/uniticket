# Despliegue Continuo (CD) y Manejo de Entornos

Documento del informe técnico — Fase 6.

## 1. Pipeline completo

```
git push -> GitHub
              |
              | webhook
              v
           Jenkins (Multibranch Pipeline)
              |
              v
       +---------------------+
       | Build Info          |
       | Checkout            |
       | Build Image (retry) |
       | Prepare Reports     |
       | Static Analysis     |  (flake8)
       | SAST                |  (bandit)
       | Unit Tests          |  (pytest + coverage)
       | Deploy to Staging   |  (solo cuando branch == main)
       +---------------------+
              |
              | docker compose up -d --build
              v
       Contenedores en VPS
       (web :7007  +  db :5432 interno)
              |
              | smoke check curl /healthz/
              v
       App publica:
       http://45.55.145.98:7007
```

## 2. Stage Deploy to Staging

### Disparador
- Solo se ejecuta en builds de la rama `main` (`when { branch 'main' }`).
- `develop` y feature branches construyen, lintean, escanean y testean — pero **no despliegan**.
- Resultado: solo los PR `develop -> main` previamente aprobados llegan a producción.

### Secretos
Se inyectan al stage vía credenciales de Jenkins (no se almacenan en el repo):

| Credential ID en Jenkins | Tipo | Variable expuesta | Uso |
|---|---|---|---|
| `uniticket-prod-secret-key` | Secret text | `PROD_SECRET_KEY` | `SECRET_KEY` Django prod |
| `uniticket-prod-pg-password` | Secret text | `PROD_PG_PASSWORD` | `POSTGRES_PASSWORD` |

Durante el stage se escribe un `.env` transitorio en el workspace, se usa para `docker compose up`, y se borra al final. No queda copia en disco ni en logs (los `echo` de las variables están deshabilitados por Jenkins automáticamente al usar `withCredentials`).

### Comandos efectivos
```bash
docker compose -p uniticket-grupo-7 down || true
docker compose -p uniticket-grupo-7 up -d --build
docker image prune -f
```

### Smoke check
Tras `up -d`, el pipeline corre hasta 10 reintentos de:
```bash
docker run --rm --network uniticket-grupo-7_uniticket_net \
  curlimages/curl:8.10.1 -fsS --max-time 5 http://web:8000/healthz/
```
Si la app no responde 200 en 30s, el stage falla y se imprimen los logs del contenedor `web` para diagnóstico.

## 3. Gestión de Entornos

| Entorno | DB | SECRET_KEY | ALLOWED_HOSTS | DEBUG | Origen vars |
|---|---|---|---|---|---|
| Local dev | Postgres en compose | desde `.env` local (gitignored) | `localhost,127.0.0.1` | True | `.env.example` -> `.env` |
| CI tests | SQLite tmp | `ci-test-only` | `*` | False | env del `docker run` |
| Producción VPS | Postgres en compose (volumen `db_data` persistente) | Jenkins credential | `45.55.145.98,localhost` | False | Jenkins credentials -> `.env` transitorio |

## 4. Red y Aislamiento

`docker-compose.yml` define una red dedicada `uniticket_net` (driver bridge). Solo los contenedores del proyecto `uniticket-grupo-7` están en esa red. Otros grupos del VPS quedan aislados.

```
+----------------------------------------------+
|        Red docker uniticket_net (bridge)      |
|                                              |
|  +-----------+         +------------------+  |
|  | web       | <--->   | db (postgres:15) |  |
|  | gunicorn  |         | volumen db_data  |  |
|  +-----------+         +------------------+  |
|       ^                                      |
+-------|--------------------------------------+
        |  publicado al host 0.0.0.0:7007 -> :8000
        v
   Internet (45.55.145.98:7007)
```

- `db` no publica puertos al host. Solo `web` puede alcanzarlo (via nombre DNS `db:5432`).
- Volumen nombrado `db_data` persiste datos entre reinicios y redeploys.
- `docker image prune -f` al final elimina capas huérfanas para no llenar disco del VPS.

## 5. Política de despliegue (GitFlow estricto)

1. Feature complete -> push `feature/*` -> PR a `develop`.
2. PR debe pasar todos los gates (build + lint + SAST + tests) -> verde.
3. Aprobación por compañero -> merge a `develop`. Pipeline corre en `develop` sin deploy.
4. Cuando `develop` esté lista para release:
   1. `git checkout develop && git pull`
   2. `git checkout -b release/x.y.z`
   3. Ajustes finales si aplica (bump version, changelog).
   4. Push -> PR `release/x.y.z` -> `main`.
5. Mismo set de gates en el `pr-merge` build de la release.
6. Aprobación + merge a `main` -> **stage Deploy to Staging se activa** -> despliega a `:7007`.
7. Smoke check verifica disponibilidad.
8. Tag en `main`: `git tag -a vx.y.z -m "release x.y.z" && git push origin vx.y.z`.
9. **Back-merge** `main` -> `develop` para sincronizar (commit de merge + tag history).

## 6. Rollback

Si un deploy a `main` deja la app caída:

1. **Opción A — Revert + redeploy:**
   ```bash
   git checkout main && git pull
   git checkout -b hotfix/revert-broken-release
   git revert <SHA-del-merge-commit> --no-edit -m 1
   git push -u origin hotfix/revert-broken-release
   # PR hotfix -> main; tras merge se redeploya version anterior
   ```
2. **Opción B — Hotfix forward:**
   - Rama `hotfix/x.y.z+1` desde `main`.
   - Fix + tests.
   - PR a `main` (pipeline verde) -> merge -> deploy automatico.
   - Back-merge `main` -> `develop`.

## 7. Tabla de problemas frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| Stage Deploy salta sin ejecutar | Build no es de `main` | OK, comportamiento esperado |
| `Port already in use` | Compose previo no bajó | `docker compose -p uniticket-grupo-7 down -v` manual |
| App 500 tras deploy | Migración falló | `docker compose -p uniticket-grupo-7 logs web` |
| Smoke check timeout | Migración pendiente o gunicorn no arranca | Logs web, esperar mas tiempo o aumentar reintentos |
| Sin espacio en disco VPS | Imágenes acumuladas | `docker system prune -af` (cuidado) |
