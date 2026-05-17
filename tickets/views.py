from django.http import HttpResponse


def home(request):
    """Placeholder home view. Real views land in Fase 7."""
    return HttpResponse(
        "<h1>UniTicket — Grupo 7</h1>"
        "<p>Bootstrap OK. Funcionalidades llegan en Fase 7.</p>",
        content_type="text/html; charset=utf-8",
    )


def healthz(request):
    """Liveness endpoint used by smoke checks and pipelines."""
    return HttpResponse("ok", content_type="text/plain")
