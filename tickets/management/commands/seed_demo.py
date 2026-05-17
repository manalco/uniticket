"""Carga datos de demostración para UniTicket.

Uso: python manage.py seed_demo
Idempotente: vuelve a correrlo no duplica usuarios ni tickets.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from tickets.models import Ticket

User = get_user_model()


DEMO_USERS = [
    ("usuario_demo", "demo1234", "usuario@demo.local", "usuario"),
    ("tecnico_demo", "demo1234", "tecnico@demo.local", "tecnico"),
]

DEMO_TICKETS = [
    {
        "location": "Laboratorio de Redes",
        "equipment_id": "PC-05",
        "description": "No enciende la pantalla, el equipo arranca pero sin señal.",
        "status": Ticket.STATUS_ABIERTO,
    },
    {
        "location": "Sala de Software",
        "equipment_id": "PC-12",
        "description": "VS Code se cierra solo al abrir proyectos grandes.",
        "status": Ticket.STATUS_EN_PROGRESO,
    },
    {
        "location": "Laboratorio de Bases de Datos",
        "equipment_id": "SRV-DB-01",
        "description": "PostgreSQL no acepta conexiones desde estaciones.",
        "status": Ticket.STATUS_RESUELTO,
        "resolution_note": "Se reinició el servicio y se actualizó pg_hba.conf.",
    },
]


class Command(BaseCommand):
    help = "Crea grupos, usuarios demo y tickets de muestra."

    @transaction.atomic
    def handle(self, *args, **options):
        usuario_group, _ = Group.objects.get_or_create(name="usuario")
        tecnico_group, _ = Group.objects.get_or_create(name="tecnico")
        groups_by_name = {"usuario": usuario_group, "tecnico": tecnico_group}

        users = {}
        for username, password, email, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email},
            )
            if created:
                user.set_password(password)
                user.save()
            user.groups.add(groups_by_name[role])
            users[username] = user
            self.stdout.write(
                f"{'creado' if created else 'existente'}: {username} ({role})"
            )

        author = users["usuario_demo"]
        tecnico = users["tecnico_demo"]
        for spec in DEMO_TICKETS:
            ticket, created = Ticket.objects.get_or_create(
                equipment_id=spec["equipment_id"],
                location=spec["location"],
                defaults={
                    "description": spec["description"],
                    "status": spec["status"],
                    "resolution_note": spec.get("resolution_note", ""),
                    "created_by": author,
                    "assigned_to": tecnico if spec["status"] != Ticket.STATUS_ABIERTO else None,
                },
            )
            if created and spec["status"] == Ticket.STATUS_RESUELTO:
                ticket.mark_resolved(spec.get("resolution_note", ""))
                ticket.save()
            self.stdout.write(
                f"{'creado' if created else 'existente'}: ticket #{ticket.pk} {ticket.equipment_id}"
            )

        self.stdout.write(self.style.SUCCESS("Seed completo."))
