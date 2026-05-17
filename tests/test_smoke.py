"""Smoke tests para verificar arranque mínimo del proyecto.

Cubre rutas placeholder de Fase 2 (home + healthz). Tests reales por
funcionalidad llegan en Fase 7 junto con cada feature.
"""

from django.urls import reverse


def test_truthy():
    assert True


def test_healthz_returns_ok(client):
    response = client.get("/healthz/")
    assert response.status_code == 200
    assert response.content == b"ok"


def test_home_renders_uniticket(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"UniTicket" in response.content


def test_home_url_reverse():
    assert reverse("home") == "/"


def test_healthz_url_reverse():
    assert reverse("healthz") == "/healthz/"
