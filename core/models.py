from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class Profile(models.Model):
    """Extends Django's built-in User with a role, instead of a custom
    User model — keeps auth simple while still giving us role-based
    permissions (student vs staff)."""

    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        STAFF = 'STAFF', 'Staff'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)

    def __str__(self):
        return f'{self.user.username} ({self.role})'


class Dish(models.Model):
    class Category(models.TextChoices):
        BREAKFAST = 'BREAKFAST', 'Breakfast'
        LUNCH = 'LUNCH', 'Lunch'
        SNACKS = 'SNACKS', 'Snacks'
        BEVERAGES = 'BEVERAGES', 'Beverages'

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    price = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class Inventory(models.Model):
    """Today's prepared/stocked quantity for a dish. Reduced atomically
    on every order to avoid overselling when two students order the
    last few portions at the same time."""

    dish = models.OneToOneField(Dish, on_delete=models.CASCADE, related_name='inventory')
    quantity_available = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.dish.name}: {self.quantity_available} left'


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = 'PLACED', 'Placed'
        PREPARING = 'PREPARING', 'Preparing'
        READY = 'READY', 'Ready for pickup'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders'
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLACED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        return f'Order #{self.id} — {self.student.username} ({self.status})'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    dish = models.ForeignKey(Dish, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_at_order = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        # A dish shouldn't appear twice as separate line items on the same order
        unique_together = ('order', 'dish')

    @property
    def subtotal(self):
        return self.price_at_order * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.dish.name}'
