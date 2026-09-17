from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views_api

router = DefaultRouter()
router.register('menu', views_api.DishViewSet, basename='dish')
router.register('inventory', views_api.InventoryViewSet, basename='inventory')
router.register('orders', views_api.OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path('forecast/', views_api.ForecastView.as_view(), name='api-forecast'),
    path('sales/', views_api.DailySalesView.as_view(), name='api-sales'),
]
