from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("users/", views.users_list, name="users_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:user_id>/availability/", views.doctor_availability, name="doctor_availability"),
    path("doctors/", views.doctors_list, name="doctors_list"),
    path("appointments/", views.appointments_list, name="appointments_list"),
    path("appointments/book/", views.appointment_create, name="appointment_create"),
    path("appointments/<int:appointment_id>/status/", views.appointment_status, name="appointment_status"),
    path("records/", views.records_list, name="records_list"),
    path("records/create/", views.record_create, name="record_create"),
    path("bills/", views.bills_list, name="bills_list"),
    path("bills/create/", views.bill_create, name="bill_create"),
]
