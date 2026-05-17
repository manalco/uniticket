import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_signup_creates_user_in_usuario_group_by_default(client, usuario_group, tecnico_group):
    response = client.post(
        reverse("signup"),
        {
            "username": "nuevo_estudiante",
            "email": "ne@uni.local",
            "password1": "Complex-pass-12345",
            "password2": "Complex-pass-12345",
            "role": "usuario",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(username="nuevo_estudiante")
    assert user.groups.filter(name="usuario").exists()
    assert not user.groups.filter(name="tecnico").exists()


@pytest.mark.django_db
def test_signup_can_register_as_tecnico(client, usuario_group, tecnico_group):
    client.post(
        reverse("signup"),
        {
            "username": "nuevo_tecnico",
            "email": "nt@uni.local",
            "password1": "Complex-pass-12345",
            "password2": "Complex-pass-12345",
            "role": "tecnico",
        },
    )
    user = User.objects.get(username="nuevo_tecnico")
    assert user.groups.filter(name="tecnico").exists()


@pytest.mark.django_db
def test_login_redirects_to_dashboard(client, usuario):
    response = client.post(
        reverse("login"),
        {"username": usuario.username, "password": "secret-pass-123"},
        follow=False,
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard")


@pytest.mark.django_db
def test_home_redirects_anon_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_home_redirects_authenticated_to_dashboard(client, usuario):
    client.force_login(usuario)
    response = client.get("/")
    assert response.status_code == 302
    assert response.url == reverse("dashboard")


@pytest.mark.django_db
def test_default_groups_exist_from_data_migration():
    # La migración 0002_create_default_groups crea estos grupos.
    assert Group.objects.filter(name="usuario").exists()
    assert Group.objects.filter(name="tecnico").exists()
