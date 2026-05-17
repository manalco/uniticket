"""Carga datos de demostración para UniTicket.

Uso:
    python manage.py seed_demo

Credenciales y emails se leen de variables de entorno (inyectadas por
Jenkins en producción). Si no están definidas, usa defaults inseguros
para desarrollo local.

Idempotente: get_or_create por username. Passwords y emails se
re-aplican en cada corrida para permitir rotación desde Jenkins.
"""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from tickets.models import Ticket

User = get_user_model()


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


# Esquema: (rol_logico, env_prefix, default_username, default_email)
DEMO_USER_SPECS = [
    ("usuario", "SEED_USUARIO", "usuario_demo", "usuario@demo.local"),
    ("tecnico", "SEED_TECNICO", "tecnico_demo", "tecnico@demo.local"),
    ("superuser", "SEED_SUPER", "super_demo", "super@demo.local"),
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
    help = "Crea/actualiza usuarios demo desde env vars y tickets de muestra."

    @transaction.atomic
    def handle(self, *args, **options):
        usuario_group, _ = Group.objects.get_or_create(name="usuario")
        tecnico_group, _ = Group.objects.get_or_create(name="tecnico")

        created_users = {}

        for role, prefix, default_user, default_email in DEMO_USER_SPECS:
            username = _env(f"{prefix}_USERNAME", default_user)
            password = _env(f"{prefix}_PASSWORD", "demo1234")
            email = _env(f"{prefix}_EMAIL", default_email)

            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email},
            )
            user.email = email
            user.set_password(password)

            if role == "superuser":
                user.is_superuser = True
                user.is_staff = True
                user.groups.clear()
            elif role == "usuario":
                user.is_superuser = False
                user.is_staff = False
                user.groups.set([usuario_group])
            elif role == "tecnico":
                user.is_superuser = False
                user.is_staff = False
                user.groups.set([tecnico_group])

            user.save()
            created_users[role] = user
            self.stdout.write(
                f"{'creado' if created else 'actualizado'}: {username} ({role})"
            )

        author = created_users["usuario"]
        tecnico = created_users["tecnico"]
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
