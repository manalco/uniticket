from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SignUpForm, TicketCreateForm, TicketUpdateForm
from .models import Ticket
from .permissions import (
    GROUP_TECNICO,
    GROUP_USUARIO,
    MANAGED_ROLES,
    is_tecnico,
    superuser_required,
)

User = get_user_model()


def home(request):
    """Landing: si autenticado va al dashboard, si no al login."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Bienvenido a UniTicket.")
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    qs = Ticket.objects.select_related("created_by", "assigned_to")
    if not is_tecnico(request.user):
        qs = qs.filter(created_by=request.user)

    status_filter = request.GET.get("status", "")
    if status_filter in dict(Ticket.STATUS_CHOICES):
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "status_choices": Ticket.STATUS_CHOICES,
        "status_filter": status_filter,
        "is_tecnico": is_tecnico(request.user),
    }
    return render(request, "tickets/dashboard.html", context)


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            messages.success(request, f"Ticket #{ticket.pk} creado.")
            return redirect("ticket_detail", pk=ticket.pk)
    else:
        form = TicketCreateForm()
    return render(request, "tickets/ticket_form.html", {"form": form})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("created_by", "assigned_to"),
        pk=pk,
    )

    user_is_tecnico = is_tecnico(request.user)
    if not user_is_tecnico and ticket.created_by_id != request.user.id:
        messages.error(request, "No tienes permiso para ver este ticket.")
        return redirect("dashboard")

    update_form = None
    if user_is_tecnico:
        if request.method == "POST":
            update_form = TicketUpdateForm(request.POST, instance=ticket)
            if update_form.is_valid():
                updated = update_form.save(commit=False)
                if updated.status == Ticket.STATUS_RESUELTO:
                    updated.mark_resolved(updated.resolution_note)
                if updated.assigned_to_id is None and updated.status != Ticket.STATUS_ABIERTO:
                    updated.assigned_to = request.user
                updated.save()
                messages.success(request, "Ticket actualizado.")
                return redirect("ticket_detail", pk=ticket.pk)
        else:
            update_form = TicketUpdateForm(instance=ticket)

    context = {
        "ticket": ticket,
        "update_form": update_form,
        "is_tecnico": user_is_tecnico,
    }
    return render(request, "tickets/ticket_detail.html", context)


@superuser_required
def manage_users(request):
    """Gestión de roles. Solo superusuarios pueden cambiar roles ajenos."""
    if request.method == "POST":
        target = get_object_or_404(User, pk=request.POST.get("user_id"))
        new_role = request.POST.get("role", "")

        if target.is_superuser:
            messages.error(request, "No se puede modificar el rol de otro superusuario.")
        elif target.pk == request.user.pk:
            messages.error(request, "No puedes cambiar tu propio rol.")
        elif new_role not in MANAGED_ROLES:
            messages.error(request, "Rol inválido.")
        else:
            usuario_group, _ = Group.objects.get_or_create(name=GROUP_USUARIO)
            tecnico_group, _ = Group.objects.get_or_create(name=GROUP_TECNICO)
            target.groups.remove(usuario_group, tecnico_group)
            new_group = usuario_group if new_role == GROUP_USUARIO else tecnico_group
            target.groups.add(new_group)
            messages.success(
                request, f"Rol de {target.username} actualizado a {new_role}."
            )

        return redirect("manage_users")

    users = (
        User.objects.exclude(is_superuser=True)
        .order_by("username")
        .prefetch_related("groups")
    )
    return render(
        request,
        "tickets/manage_users.html",
        {"users": users, "managed_roles": MANAGED_ROLES},
    )
