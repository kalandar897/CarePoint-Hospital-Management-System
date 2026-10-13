from django.contrib import admin
from django.urls import path, include
from hospital import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("hospital.urls")),
]
