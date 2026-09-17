from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls_api')),

    path('', views.menu_view, name='menu'),
    path('orders/', views.orders_view, name='orders'),
    path('staff/', views.staff_dashboard_view, name='staff_dashboard'),

    path('accounts/signup/', views.signup, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
