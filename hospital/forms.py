from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.utils import timezone
from .models import Profile, Appointment, MedicalRecord, Bill
User = get_user_model()

class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            current = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (current + " form-control").strip()
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"

class LoginForm(StyledFormMixin, AuthenticationForm):
    pass

class UserCreateForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8, help_text="At least 8 characters.")
    role = forms.ChoiceField(choices=Profile.Role.choices)
    phone = forms.CharField(required=False)
    specialization = forms.CharField(required=False, help_text="Only needed for doctors")
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Profile.Role.DOCTOR and not cleaned.get("specialization"):
            self.add_error("specialization", "Enter the doctor's specialization.")
        return cleaned
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            Profile.objects.create(user=user, role=self.cleaned_data["role"], phone=self.cleaned_data.get("phone", ""), specialization=self.cleaned_data.get("specialization", ""))
        return user

class AppointmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["doctor", "appointment_date", "appointment_time", "reason"]
        widgets = {"appointment_date": forms.DateInput(attrs={"type": "date"}), "appointment_time": forms.TimeInput(attrs={"type": "time"})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = User.objects.filter(profile__role=Profile.Role.DOCTOR, profile__available=True, is_active=True).order_by("first_name", "username")
    def clean_appointment_date(self):
        date = self.cleaned_data["appointment_date"]
        if date < timezone.localdate():
            raise forms.ValidationError("Choose today or a future date.")
        return date
    def clean(self):
        cleaned = super().clean()
        doctor, date, time = cleaned.get("doctor"), cleaned.get("appointment_date"), cleaned.get("appointment_time")
        if doctor and date and time:
            clashes = Appointment.objects.filter(doctor=doctor, appointment_date=date, appointment_time=time).exclude(status=Appointment.Status.CANCELLED)
            if self.instance.pk:
                clashes = clashes.exclude(pk=self.instance.pk)
            if clashes.exists():
                raise forms.ValidationError("That doctor already has an appointment at this date and time. Choose another slot.")
        return cleaned

class MedicalRecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ["patient", "visit_date", "diagnosis", "treatment", "notes"]
        widgets = {"visit_date": forms.DateInput(attrs={"type": "date"})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = User.objects.filter(profile__role=Profile.Role.PATIENT).order_by("username")

class BillForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Bill
        fields = ["patient", "appointment", "description", "amount", "amount_paid"]
        widgets = {"amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}), "amount_paid": forms.NumberInput(attrs={"min": "0", "step": "0.01"})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = User.objects.filter(profile__role=Profile.Role.PATIENT).order_by("username")
        self.fields["appointment"].queryset = Appointment.objects.select_related("patient", "doctor").order_by("-appointment_date")
    def clean(self):
        cleaned = super().clean()
        amount, paid = cleaned.get("amount"), cleaned.get("amount_paid")
        if amount is not None and amount <= 0:
            self.add_error("amount", "Amount must be greater than zero.")
        if amount is not None and paid is not None and (paid < 0 or paid > amount):
            self.add_error("amount_paid", "Amount paid must be between zero and the bill amount.")
        return cleaned
