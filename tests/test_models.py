import pytest

from tickets.models import Ticket


@pytest.mark.django_db
def test_ticket_defaults_to_abierto(usuario):
    ticket = Ticket.objects.create(
        location="Lab", equipment_id="PC-01", description="x", created_by=usuario
    )
    assert ticket.status == Ticket.STATUS_ABIERTO
    assert ticket.resolved_at is None
    assert ticket.resolution_note == ""


@pytest.mark.django_db
def test_ticket_str(ticket):
    assert f"#{ticket.pk}" in str(ticket)
    assert "PC-05" in str(ticket)


@pytest.mark.django_db
def test_badge_class_per_status(ticket):
    ticket.status = Ticket.STATUS_RESUELTO
    assert "success" in ticket.badge_class()
    ticket.status = Ticket.STATUS_EN_PROGRESO
    assert "warning" in ticket.badge_class()
    ticket.status = Ticket.STATUS_ABIERTO
    assert "danger" in ticket.badge_class()


@pytest.mark.django_db
def test_mark_resolved_sets_status_note_and_timestamp(ticket):
    assert ticket.resolved_at is None
    ticket.mark_resolved("Reemplazado cable de poder")
    ticket.save()
    ticket.refresh_from_db()
    assert ticket.status == Ticket.STATUS_RESUELTO
    assert ticket.resolution_note == "Reemplazado cable de poder"
    assert ticket.resolved_at is not None


@pytest.mark.django_db
def test_mark_resolved_idempotent_on_timestamp(ticket):
    ticket.mark_resolved("primera vez")
    ticket.save()
    first = ticket.resolved_at
    ticket.mark_resolved("segunda")
    ticket.save()
    assert ticket.resolved_at == first
