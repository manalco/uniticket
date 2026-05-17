from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


GROUP_USUARIO = "usuario"
GROUP_TECNICO = "tecnico"


def is_tecnico(user) -> bool:
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name=GROUP_TECNICO).exists()
    )


def is_usuario(user) -> bool:
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name=GROUP_USUARIO).exists()
    )


def tecnico_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_tecnico(request.user):
            raise PermissionDenied("Solo técnicos pueden ejecutar esta acción.")
        return view_func(request, *args, **kwargs)

    return _wrapped
