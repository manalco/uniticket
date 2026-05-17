import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from tickets.models import Ticket


User = get_user_model()


@pytest.fixture
def usuario_group(db):
    group, _ = Group.objects.get_or_create(name="usuario")
    return group


@pytest.fixture
def tecnico_group(db):
    group, _ = Group.objects.get_or_create(name="tecnico")
    return group


@pytest.fixture
def usuario(db, usuario_group):
    user = User.objects.create_user(username="estudiante", password="secret-pass-123")
    user.groups.add(usuario_group)
    return user


@pytest.fixture
def tecnico(db, tecnico_group):
    user = User.objects.create_user(username="soporte", password="secret-pass-123")
    user.groups.add(tecnico_group)
    return user


@pytest.fixture
def ticket(db, usuario):
    return Ticket.objects.create(
        location="Laboratorio de Redes",
        equipment_id="PC-05",
        description="No enciende.",
        created_by=usuario,
    )
