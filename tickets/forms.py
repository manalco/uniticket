from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import Ticket

User = get_user_model()


ROLE_USUARIO = "usuario"
ROLE_TECNICO = "tecnico"
ROLE_CHOICES = [
    (ROLE_USUARIO, "Usuario estándar (reportar fallas)"),
    (ROLE_TECNICO, "Técnico (resolver tickets)"),
]


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,
        label="Rol",
        initial=ROLE_USUARIO,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2", "role")

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            group_name = self.cleaned_data["role"]
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        return user


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["location", "equipment_id", "description"]
        widgets = {
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Laboratorio de Redes"}
            ),
            "equipment_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. PC-05"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }


class TicketUpdateForm(forms.ModelForm):
    """Form para técnicos: cambiar estado y opcionalmente añadir nota."""

    class Meta:
        model = Ticket
        fields = ["status", "resolution_note"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "resolution_note": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }
