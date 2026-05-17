import pytest
from django.urls import reverse

from tickets.models import Ticket


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_usuario_sees_only_own_tickets(client, usuario, tecnico, ticket):
    other_ticket = Ticket.objects.create(
        location="Sala", equipment_id="PC-99", description="x", created_by=tecnico
    )
    client.force_login(usuario)
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200
    assert ticket in response.context["page_obj"].object_list
    assert other_ticket not in response.context["page_obj"].object_list


@pytest.mark.django_db
def test_tecnico_sees_all_tickets(client, usuario, tecnico, ticket):
    other_ticket = Ticket.objects.create(
        location="Sala", equipment_id="PC-99", description="x", created_by=tecnico
    )
    client.force_login(tecnico)
    response = client.get(reverse("dashboard"))
    objects = list(response.context["page_obj"].object_list)
    assert ticket in objects
    assert other_ticket in objects


@pytest.mark.django_db
def test_dashboard_filters_by_status(client, tecnico, usuario):
    Ticket.objects.create(
        location="A", equipment_id="X1", description="x",
        created_by=usuario, status=Ticket.STATUS_ABIERTO,
    )
    Ticket.objects.create(
        location="B", equipment_id="X2", description="x",
        created_by=usuario, status=Ticket.STATUS_RESUELTO,
    )
    client.force_login(tecnico)
    response = client.get(reverse("dashboard"), {"status": Ticket.STATUS_RESUELTO})
    assert response.status_code == 200
    objects = list(response.context["page_obj"].object_list)
    assert len(objects) == 1
    assert objects[0].status == Ticket.STATUS_RESUELTO


@pytest.mark.django_db
def test_ticket_create_persists_with_current_user(client, usuario):
    client.force_login(usuario)
    response = client.post(
        reverse("ticket_create"),
        {
            "location": "Lab Principal",
            "equipment_id": "PC-77",
            "description": "Bluescreen al arrancar.",
        },
    )
    assert response.status_code == 302
    ticket = Ticket.objects.get(equipment_id="PC-77")
    assert ticket.created_by == usuario
    assert ticket.status == Ticket.STATUS_ABIERTO


@pytest.mark.django_db
def test_ticket_create_requires_login(client):
    response = client.post(
        reverse("ticket_create"),
        {"location": "x", "equipment_id": "y", "description": "z"},
    )
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_ticket_detail_blocks_other_usuarios(client, usuario, tecnico, ticket):
    other_user_password = "secret-pass-123"
    from django.contrib.auth import get_user_model

    User = get_user_model()
    intruso = User.objects.create_user(username="intruso", password=other_user_password)

    client.force_login(intruso)
    response = client.get(reverse("ticket_detail", args=[ticket.pk]))
    assert response.status_code == 302
    assert response.url == reverse("dashboard")


@pytest.mark.django_db
def test_ticket_detail_allows_owner(client, usuario, ticket):
    client.force_login(usuario)
    response = client.get(reverse("ticket_detail", args=[ticket.pk]))
    assert response.status_code == 200
    assert response.context["ticket"] == ticket
    assert response.context["update_form"] is None


@pytest.mark.django_db
def test_ticket_detail_allows_tecnico_with_update_form(client, tecnico, ticket):
    client.force_login(tecnico)
    response = client.get(reverse("ticket_detail", args=[ticket.pk]))
    assert response.status_code == 200
    assert response.context["update_form"] is not None


@pytest.mark.django_db
def test_tecnico_can_resolve_ticket(client, tecnico, ticket):
    client.force_login(tecnico)
    response = client.post(
        reverse("ticket_detail", args=[ticket.pk]),
        {
            "status": Ticket.STATUS_RESUELTO,
            "resolution_note": "Cable reemplazado.",
        },
    )
    assert response.status_code == 302
    ticket.refresh_from_db()
    assert ticket.status == Ticket.STATUS_RESUELTO
    assert ticket.resolution_note == "Cable reemplazado."
    assert ticket.resolved_at is not None
    assert ticket.assigned_to == tecnico


@pytest.mark.django_db
def test_usuario_cannot_post_update(client, usuario, ticket):
    client.force_login(usuario)
    response = client.post(
        reverse("ticket_detail", args=[ticket.pk]),
        {
            "status": Ticket.STATUS_RESUELTO,
            "resolution_note": "intento desde usuario",
        },
    )
    # Owner puede ver pero update_form es None: el POST se ignora y
    # se renderiza el detalle sin aplicar cambios.
    ticket.refresh_from_db()
    assert ticket.status == Ticket.STATUS_ABIERTO
    assert response.status_code in (200, 302)
