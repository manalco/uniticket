import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def superuser(db, usuario_group, tecnico_group):
    return User.objects.create_superuser(
        username="admin_demo", password="Complex-pass-12345", email="a@uni.local"
    )


@pytest.mark.django_db
def test_manage_users_requires_login(client):
    response = client.get(reverse("manage_users"))
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_manage_users_blocked_for_usuario(client, usuario):
    client.force_login(usuario)
    response = client.get(reverse("manage_users"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_manage_users_blocked_for_tecnico(client, tecnico):
    client.force_login(tecnico)
    response = client.get(reverse("manage_users"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_manage_users_renders_for_superuser(client, superuser, usuario, tecnico):
    client.force_login(superuser)
    response = client.get(reverse("manage_users"))
    assert response.status_code == 200
    listed = list(response.context["users"])
    usernames = {u.username for u in listed}
    assert usuario.username in usernames
    assert tecnico.username in usernames
    # superusuarios no se listan
    assert superuser.username not in usernames


@pytest.mark.django_db
def test_superuser_promotes_usuario_to_tecnico(client, superuser, usuario):
    client.force_login(superuser)
    response = client.post(
        reverse("manage_users"),
        {"user_id": usuario.pk, "role": "tecnico"},
    )
    assert response.status_code == 302
    usuario.refresh_from_db()
    assert usuario.groups.filter(name="tecnico").exists()
    assert not usuario.groups.filter(name="usuario").exists()


@pytest.mark.django_db
def test_superuser_demotes_tecnico_to_usuario(client, superuser, tecnico):
    client.force_login(superuser)
    client.post(
        reverse("manage_users"),
        {"user_id": tecnico.pk, "role": "usuario"},
    )
    tecnico.refresh_from_db()
    assert tecnico.groups.filter(name="usuario").exists()
    assert not tecnico.groups.filter(name="tecnico").exists()


@pytest.mark.django_db
def test_superuser_cannot_change_own_role(client, superuser):
    client.force_login(superuser)
    client.post(
        reverse("manage_users"),
        {"user_id": superuser.pk, "role": "usuario"},
    )
    superuser.refresh_from_db()
    assert superuser.is_superuser
    assert not superuser.groups.filter(name="usuario").exists()


@pytest.mark.django_db
def test_superuser_cannot_change_another_superuser(client, superuser, usuario_group):
    other_super = User.objects.create_superuser(
        username="otro_super", password="Complex-pass-12345", email="o@uni.local"
    )
    client.force_login(superuser)
    client.post(
        reverse("manage_users"),
        {"user_id": other_super.pk, "role": "usuario"},
    )
    other_super.refresh_from_db()
    assert other_super.is_superuser


@pytest.mark.django_db
def test_invalid_role_is_rejected(client, superuser, usuario):
    client.force_login(superuser)
    client.post(
        reverse("manage_users"),
        {"user_id": usuario.pk, "role": "evil_role"},
    )
    usuario.refresh_from_db()
    # Mantiene su rol original (usuario)
    assert usuario.groups.filter(name="usuario").exists()
    assert not usuario.groups.filter(name="evil_role").exists()
