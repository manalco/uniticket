# UniTicket — Grupo 7

Sistema de gestión de incidencias técnicas. Proyecto del curso 750021C — Desarrollo de Software II.

## Stack
- Django 5 (Python 3.11)
- PostgreSQL 15 (contenedor)
- Docker + Docker Compose
- Jenkins (CI/CD)

## Quickstart (local)

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

App en http://localhost:7007 — health en http://localhost:7007/healthz/

Apagar:

```bash
docker compose down            # conserva datos (volumen)
docker compose down -v         # borra datos
```

## Infraestructura Grupo 7
- Jenkins: http://45.55.145.98:8087
- Webhook: http://45.55.145.98:9007/github-webhook/
- App pública: http://45.55.145.98:7007
- Compose project: `uniticket-grupo-7`

## Documentación
- Spec de diseño: `docs/superpowers/specs/2026-05-17-uniticket-7fases-design.md`
- Documentos de apoyo del curso: `docs/`

## GitFlow
- `main` — producción
- `develop` — integración
- `feature/*` — features (PR a `develop`)
- `hotfix/*` — urgencias (PR a `main`, justificar)

Conventional Commits. **No se mezcla un feature si el pipeline está rojo.**
# test
