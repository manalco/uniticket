import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from tickets.models import Ticket

User = get_user_model()


@pytest.mark.django_db
def test_seed_demo_creates_three_users_and_tickets():
    call_command("seed_demo")
    assert User.objects.filter(username="usuario_demo").exists()
    assert User.objects.filter(username="tecnico_demo").exists()
    assert User.objects.filter(username="super_demo", is_superuser=True).exists()
    assert Ticket.objects.count() >= 3


@pytest.mark.django_db
def test_seed_demo_idempotent_in_count():
    call_command("seed_demo")
    user_count = User.objects.count()
    ticket_count = Ticket.objects.count()
    call_command("seed_demo")
    assert User.objects.count() == user_count
    assert Ticket.objects.count() == ticket_count


@pytest.mark.django_db
def test_seed_demo_respects_env_overrides(monkeypatch):
    monkeypatch.setenv("SEED_USUARIO_USERNAME", "alice")
    monkeypatch.setenv("SEED_USUARIO_PASSWORD", "alice-strong-pass-123")
    monkeypatch.setenv("SEED_USUARIO_EMAIL", "alice@grupo7.local")
    monkeypatch.setenv("SEED_TECNICO_USERNAME", "bob")
    monkeypatch.setenv("SEED_TECNICO_PASSWORD", "bob-strong-pass-123")
    monkeypatch.setenv("SEED_SUPER_USERNAME", "root7")
    monkeypatch.setenv("SEED_SUPER_PASSWORD", "root-strong-pass-123")

    call_command("seed_demo")

    alice = User.objects.get(username="alice")
    assert alice.email == "alice@grupo7.local"
    assert alice.check_password("alice-strong-pass-123")
    assert alice.groups.filter(name="usuario").exists()

    bob = User.objects.get(username="bob")
    assert bob.check_password("bob-strong-pass-123")
    assert bob.groups.filter(name="tecnico").exists()

    root = User.objects.get(username="root7")
    assert root.is_superuser
    assert root.is_staff
    assert root.check_password("root-strong-pass-123")


@pytest.mark.django_db
def test_seed_demo_rotates_passwords_on_rerun(monkeypatch):
    monkeypatch.setenv("SEED_USUARIO_USERNAME", "ana")
    monkeypatch.setenv("SEED_USUARIO_PASSWORD", "first-pass-1234")
    call_command("seed_demo")
    ana = User.objects.get(username="ana")
    assert ana.check_password("first-pass-1234")

    monkeypatch.setenv("SEED_USUARIO_PASSWORD", "rotated-pass-1234")
    call_command("seed_demo")
    ana.refresh_from_db()
    assert ana.check_password("rotated-pass-1234")
    assert not ana.check_password("first-pass-1234")
