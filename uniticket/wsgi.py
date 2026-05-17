"""WSGI config for uniticket project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniticket.settings")

application = get_wsgi_application()
