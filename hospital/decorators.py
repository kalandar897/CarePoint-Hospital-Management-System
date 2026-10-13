from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Profile

def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            role = getattr(getattr(request.user, "profile", None), "role", None)
            if role not in roles and not request.user.is_superuser:
                messages.error(request, "You do not have permission to access that page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

def user_role(user):
    if user.is_superuser:
        return Profile.Role.ADMIN
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None
