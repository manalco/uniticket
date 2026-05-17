"""Smoke tests: rutas críticas y health endpoint."""

from django.urls import reverse


def test_truthy():
    assert True


def test_healthz_returns_ok(client):
    response = client.get("/healthz/")
    assert response.status_code == 200
    assert response.content == b"ok"


def test_home_redirects(client):
    response = client.get("/")
    assert response.status_code == 302


def test_home_url_reverse():
    assert reverse("home") == "/"


def test_healthz_url_reverse():
    assert reverse("healthz") == "/healthz/"


def test_login_page_renders(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200
    assert b"UniTicket" in response.content
