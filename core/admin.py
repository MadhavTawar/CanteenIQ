from django.contrib import admin

from .models import Dish, Inventory, Order, OrderItem, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('dish', 'quantity_available', 'updated_at')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'status', 'created_at', 'total_amount')
    list_filter = ('status',)
    inlines = [OrderItemInline]
