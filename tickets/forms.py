from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import Ticket
from .permissions import GROUP_USUARIO

User = get_user_model()


class SignUpForm(UserCreationForm):
    """Self-service signup. Solo crea usuarios con rol 'usuario'.

    Roles tecnico y superusuario solo los asigna un superusuario via
    /manage/users/ o via el Django admin.
    """

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=GROUP_USUARIO)
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
