from django.conf import settings
from django.db import models
from django.utils import timezone


class Ticket(models.Model):
    STATUS_ABIERTO = "abierto"
    STATUS_EN_PROGRESO = "en_progreso"
    STATUS_RESUELTO = "resuelto"
    STATUS_CHOICES = [
        (STATUS_ABIERTO, "Abierto"),
        (STATUS_EN_PROGRESO, "En Progreso"),
        (STATUS_RESUELTO, "Resuelto"),
    ]
    STATUS_BADGE_CLASS = {
        STATUS_ABIERTO: "bg-danger",
        STATUS_EN_PROGRESO: "bg-warning text-dark",
        STATUS_RESUELTO: "bg-success",
    }

    location = models.CharField("Ubicación", max_length=120)
    equipment_id = models.CharField("Identificador del equipo", max_length=60)
    description = models.TextField("Descripción detallada")
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ABIERTO,
    )
    resolution_note = models.TextField("Nota de resolución", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets_created",
        verbose_name="Reportado por",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_assigned",
        verbose_name="Asignado a",
    )
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)
    resolved_at = models.DateTimeField("Resuelto en", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"

    def __str__(self):
        return f"#{self.pk} {self.equipment_id} ({self.get_status_display()})"

    def badge_class(self):
        return self.STATUS_BADGE_CLASS.get(self.status, "bg-secondary")

    def mark_resolved(self, note: str = "") -> None:
        self.status = self.STATUS_RESUELTO
        if note:
            self.resolution_note = note
        if self.resolved_at is None:
            self.resolved_at = timezone.now()
