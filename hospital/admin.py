from django.contrib import admin
from .models import Profile, MedicalRecord, Appointment, Bill

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "specialization", "available")
    list_filter = ("role", "available")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone")

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "visit_date", "diagnosis")
    list_filter = ("visit_date",)
    search_fields = ("patient__username", "diagnosis")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "appointment_date", "appointment_time", "status")
    list_filter = ("status", "appointment_date")
    search_fields = ("patient__username", "doctor__username")

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "description", "amount", "amount_paid", "payment_status")
    list_filter = ("payment_status",)
