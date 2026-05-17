from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "equipment_id", "location", "status", "created_by", "created_at")
    list_filter = ("status", "location")
    search_fields = ("equipment_id", "location", "description", "created_by__username")
    autocomplete_fields = ("created_by", "assigned_to")
    readonly_fields = ("created_at", "updated_at", "resolved_at")
