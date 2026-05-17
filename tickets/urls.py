from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz/", views.healthz, name="healthz"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("tickets/new/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("accounts/signup/", views.signup, name="signup"),
    path("manage/users/", views.manage_users, name="manage_users"),
]
