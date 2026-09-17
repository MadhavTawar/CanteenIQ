from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Dish, Inventory, Profile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    """Every User gets a Profile automatically. Superusers (created via
    createsuperuser) default to STAFF; everyone else defaults to STUDENT
    (signup() in views.py sets this explicitly too, but this covers
    users created through /admin/ or the shell)."""
    if created and not hasattr(instance, 'profile'):
        role = Profile.Role.STAFF if instance.is_superuser else Profile.Role.STUDENT
        Profile.objects.create(user=instance, role=role)


@receiver(post_save, sender=Dish)
def ensure_inventory(sender, instance, created, **kwargs):
    """Every Dish gets an Inventory row (starting at 0) so staff just
    need to update the quantity, not remember to create the row."""
    if created:
        Inventory.objects.get_or_create(dish=instance)
