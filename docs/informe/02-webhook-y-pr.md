# Webhook GitHub → Jenkins y Validación de Pull Requests

Documento del informe técnico — Fase 4.

## 1. Topología

```
[Dev local] --git push--> [GitHub manalco/uniticket]
                                |
                                | webhook (pull_request, push)
                                v
                  [Jenkins http://45.55.145.98:9007/github-webhook/]
                                |
                                | dispara pipeline (Jenkinsfile)
                                v
                  [Docker build en VPS 45.55.145.98]
                                |
                                | reporta status (commit status API)
                                v
                  [GitHub PR check ✓/✗]
```

## 2. Webhook GitHub

| Campo | Valor |
|---|---|
| Payload URL | `http://45.55.145.98:9007/github-webhook/` |
| Content type | `application/json` |
| Secret | (ninguno; opcional, recomendado) |
| Eventos | `Pushes`, `Pull requests` |
| SSL verification | Disabled (VPS sin TLS) |

Evidencia: pestaña *Recent Deliveries* del webhook debe mostrar entregas con código 200.

## 3. Job en Jenkins (Multibranch Pipeline)

Se reemplaza el Job de tipo *Pipeline* (single-branch) creado en Fase 3 por uno tipo *Multibranch Pipeline*. Razón: Multibranch descubre automáticamente ramas y Pull Requests del repositorio y ejecuta el `Jenkinsfile` por cada uno, posteando el estado de cada build como *check* en el PR de GitHub.

### Configuración
- **Name:** `uniticket-grupo-7`
- **Branch Sources → GitHub**
  - Credentials: `github-token-grupo-7`
  - Repository HTTPS URL: `https://github.com/manalco/uniticket.git`
  - Behaviors:
    - *Discover branches* → "All branches"
    - *Discover pull requests from origin* → "Merging the pull request with the current target branch revision"
    - *Filter by name (with regular expression)* (opcional): `^(develop|main|feature/.*|hotfix/.*)$`
- **Build Configuration:** by Jenkinsfile, Script Path `Jenkinsfile`
- **Scan Repository Triggers:** *Periodically if not otherwise run* → 1 day (fallback)
- **Orphaned Item Strategy:** retener 20 builds

## 4. Branch Protection en GitHub

`Settings → Branches → Branch protection rules` para `develop` y `main`:

- ✓ Require a pull request before merging
- ✓ Require approvals: 1
- ✓ Require status checks to pass before merging
  - Status check requerido: `continuous-integration/jenkins/branch` (aparece tras el primer build de Jenkins en cada rama)
- ✓ Require branches to be up to date before merging
- ✓ Do not allow bypassing the above settings

Efecto: ningún PR puede mezclarse mientras el check de Jenkins esté en rojo o pendiente. Cumple la regla *"nunca merge si pipeline rojo"*.

## 5. Verificación

1. Crear rama `feature/test-webhook` con un cambio trivial.
2. `git push origin feature/test-webhook`.
3. Abrir PR contra `develop` desde GitHub UI.
4. Esperar ≤30s: aparece check amarillo *"Some checks haven't completed yet"*.
5. Tras éxito del build: check verde con link al build de Jenkins.
6. Si se intenta *Merge* con check rojo, GitHub bloquea el botón.

## 6. Solución de problemas

| Problema | Causa | Mitigación |
|---|---|---|
| Webhook 404 | URL sin `/` final | Verificar `http://45.55.145.98:9007/github-webhook/` |
| Webhook 500 / timeout | Puerto 9007 bloqueado / Jenkins caído | `curl -I` desde host externo; revisar contenedor Jenkins |
| Jenkins no postea status | PAT sin scope `repo:status` | Reemitir PAT con scopes `repo` (incluye `repo:status`) |
| Check no aparece en PR | Job tipo Pipeline simple, no Multibranch | Migrar a Multibranch Pipeline |
| PR no dispara build | Branch Source no detecta PRs | Behavior *Discover pull requests* habilitado |
