import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from tickets.models import Ticket

User = get_user_model()


@pytest.mark.django_db
def test_seed_demo_creates_users_and_tickets():
    call_command("seed_demo")
    assert User.objects.filter(username="usuario_demo").exists()
    assert User.objects.filter(username="tecnico_demo").exists()
    assert Ticket.objects.count() >= 3


@pytest.mark.django_db
def test_seed_demo_idempotent():
    call_command("seed_demo")
    user_count = User.objects.count()
    ticket_count = Ticket.objects.count()
    call_command("seed_demo")
    assert User.objects.count() == user_count
    assert Ticket.objects.count() == ticket_count
