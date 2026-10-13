from functools import wraps
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Profile, Appointment, MedicalRecord, Bill
from .forms import LoginForm, UserCreateForm, AppointmentForm, MedicalRecordForm, BillForm
from .decorators import role_required, user_role
User = get_user_model()


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "hospital/home.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "hospital/form_page.html", {"form": form, "title": "Sign in", "submit_label": "Sign in", "hide_nav": True})


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have signed out successfully.")
    return redirect("home")


@login_required
def dashboard(request):
    role = user_role(request.user)
    today = timezone.localdate()
    if role == Profile.Role.ADMIN:
        context = {"total_patients": User.objects.filter(profile__role=Profile.Role.PATIENT).count(), "total_doctors": User.objects.filter(profile__role=Profile.Role.DOCTOR).count(), "total_appointments": Appointment.objects.count(), "unpaid_bills": Bill.objects.exclude(payment_status=Bill.PaymentStatus.PAID).count(), "appointments": Appointment.objects.select_related("patient", "doctor").filter(appointment_date__gte=today).exclude(status=Appointment.Status.CANCELLED)[:8]}
    elif role == Profile.Role.DOCTOR:
        context = {"appointments": Appointment.objects.filter(doctor=request.user, appointment_date__gte=today).exclude(status=Appointment.Status.CANCELLED).select_related("patient").order_by("appointment_date", "appointment_time")[:10], "record_count": MedicalRecord.objects.filter(doctor=request.user).count()}
    elif role == Profile.Role.RECEPTIONIST:
        context = {"appointments": Appointment.objects.filter(appointment_date__gte=today).exclude(status=Appointment.Status.CANCELLED).select_related("patient", "doctor")[:10], "total_patients": User.objects.filter(profile__role=Profile.Role.PATIENT).count(), "pending_appointments": Appointment.objects.filter(status=Appointment.Status.REQUESTED).count()}
    else:
        context = {"appointments": Appointment.objects.filter(patient=request.user).select_related("doctor").order_by("-appointment_date", "-appointment_time")[:10], "records_count": MedicalRecord.objects.filter(patient=request.user).count(), "unpaid_bills": Bill.objects.filter(patient=request.user).exclude(payment_status=Bill.PaymentStatus.PAID).count()}
    return render(request, "hospital/dashboard.html", {"role": role, **context})


@role_required(Profile.Role.ADMIN, Profile.Role.RECEPTIONIST)
def users_list(request):
    q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "")
    users = User.objects.select_related("profile").order_by("username")
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    if role_filter in Profile.Role.values:
        users = users.filter(profile__role=role_filter)
    return render(request, "hospital/users_list.html", {"users": users, "q": q, "role_filter": role_filter, "roles": Profile.Role.choices})


@role_required(Profile.Role.ADMIN, Profile.Role.RECEPTIONIST)
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Account for {user.username} was created.")
        return redirect("users_list")
    return render(request, "hospital/form_page.html", {"form": form, "title": "Create account", "submit_label": "Create account", "help_text": "Use this page to create doctor, receptionist, or patient accounts."})


@login_required
def doctors_list(request):
    doctors = User.objects.filter(profile__role=Profile.Role.DOCTOR, profile__available=True).select_related("profile").order_by("first_name", "username")
    return render(request, "hospital/doctors_list.html", {"doctors": doctors, "role": user_role(request.user) if request.user.is_authenticated else None})


@role_required(Profile.Role.ADMIN)
def doctor_availability(request, user_id):
    doctor = get_object_or_404(User, pk=user_id, profile__role=Profile.Role.DOCTOR)
    if request.method == "POST":
        doctor.profile.available = request.POST.get("available") == "yes"
        doctor.profile.save(update_fields=["available"])
        messages.success(request, f"Availability updated for {doctor.username}.")
    return redirect("users_list")


@login_required
def appointments_list(request):
    role = user_role(request.user)
    appointments = Appointment.objects.select_related("patient", "doctor")
    if role == Profile.Role.PATIENT:
        appointments = appointments.filter(patient=request.user)
    elif role == Profile.Role.DOCTOR:
        appointments = appointments.filter(doctor=request.user)
    appointments = appointments.order_by("-appointment_date", "-appointment_time")
    return render(request, "hospital/appointments_list.html", {"appointments": appointments, "role": role, "status_choices": Appointment.Status.choices})


@login_required
def appointment_create(request):
    role = user_role(request.user)
    if role not in [Profile.Role.PATIENT, Profile.Role.ADMIN, Profile.Role.RECEPTIONIST]:
        messages.error(request, "Only patients and front-desk staff can create appointments.")
        return redirect("appointments_list")
    form = AppointmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        if role == Profile.Role.PATIENT:
            appointment.patient = request.user
        else:
            patient_id = request.POST.get("patient")
            appointment.patient = get_object_or_404(User, pk=patient_id, profile__role=Profile.Role.PATIENT)
        appointment.save()
        messages.success(request, "Appointment has been requested.")
        return redirect("appointments_list")
    patients = User.objects.filter(profile__role=Profile.Role.PATIENT).order_by("username") if role != Profile.Role.PATIENT else None
    return render(request, "hospital/appointment_form.html", {"form": form, "patients": patients, "role": role, "title": "Book appointment"})


@role_required(Profile.Role.ADMIN, Profile.Role.RECEPTIONIST, Profile.Role.DOCTOR)
def appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment.objects.select_related("patient", "doctor"), pk=appointment_id)
    role = user_role(request.user)
    if role == Profile.Role.DOCTOR and appointment.doctor_id != request.user.id:
        messages.error(request, "You can only update your own appointments.")
        return redirect("appointments_list")
    if request.method == "POST":
        status = request.POST.get("status")
        if status in Appointment.Status.values:
            appointment.status = status
            appointment.save(update_fields=["status"])
            messages.success(request, "Appointment status updated.")
        else:
            messages.error(request, "Invalid appointment status.")
    return redirect("appointments_list")


@login_required
def records_list(request):
    role = user_role(request.user)
    records = MedicalRecord.objects.select_related("patient", "doctor")
    if role == Profile.Role.PATIENT:
        records = records.filter(patient=request.user)
    elif role == Profile.Role.DOCTOR:
        records = records.filter(Q(doctor=request.user) | Q(patient__patient_appointments__doctor=request.user)).distinct()
    return render(request, "hospital/records_list.html", {"records": records.order_by("-visit_date", "-created_at"), "role": role})


@role_required(Profile.Role.ADMIN, Profile.Role.DOCTOR)
def record_create(request):
    form = MedicalRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        if user_role(request.user) == Profile.Role.DOCTOR:
            record.doctor = request.user
        else:
            record.doctor = None
        record.save()
        messages.success(request, "Medical record saved.")
        return redirect("records_list")
    return render(request, "hospital/form_page.html", {"form": form, "title": "Add medical record", "submit_label": "Save record"})


@login_required
def bills_list(request):
    role = user_role(request.user)
    bills = Bill.objects.select_related("patient", "appointment")
    if role == Profile.Role.PATIENT:
        bills = bills.filter(patient=request.user)
    return render(request, "hospital/bills_list.html", {"bills": bills.order_by("-created_at"), "role": role})


@role_required(Profile.Role.ADMIN, Profile.Role.RECEPTIONIST)
def bill_create(request):
    form = BillForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        bill = form.save()
        messages.success(request, f"Bill #{bill.pk} created.")
        return redirect("bills_list")
    return render(request, "hospital/form_page.html", {"form": form, "title": "Create bill", "submit_label": "Save bill"})
