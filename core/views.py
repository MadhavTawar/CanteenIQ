from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from .models import Dish, Profile


def is_staff_role(user):
    return user.is_authenticated and getattr(user.profile, 'role', None) == Profile.Role.STAFF


def signup(request):
    """Simple demo signup — new accounts default to the STUDENT role.
    Staff accounts are promoted via /admin/ (Profile.role = STAFF)."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user, role=Profile.Role.STUDENT)
            from django.contrib.auth import login
            login(request, user)
            return redirect('menu')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def menu_view(request):
    dishes = Dish.objects.filter(is_available=True).select_related('inventory')
    return render(request, 'core/menu.html', {'dishes': dishes})


@login_required
def orders_view(request):
    return render(request, 'core/orders.html')


@login_required
@user_passes_test(is_staff_role, login_url='menu')
def staff_dashboard_view(request):
    return render(request, 'core/staff_dashboard.html')
