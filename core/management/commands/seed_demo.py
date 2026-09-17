import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Dish, Inventory, Order, OrderItem, Profile

User = get_user_model()

DISHES = [
    ('Masala Dosa', Dish.Category.BREAKFAST, 40, 'Crispy rice crepe with potato masala.'),
    ('Poha', Dish.Category.BREAKFAST, 25, 'Flattened rice with peanuts and curry leaves.'),
    ('Veg Thali', Dish.Category.LUNCH, 70, 'Dal, sabzi, rice, roti, and salad.'),
    ('Paneer Butter Masala + Rice', Dish.Category.LUNCH, 90, 'Rich paneer curry with steamed rice.'),
    ('Samosa (2 pc)', Dish.Category.SNACKS, 20, 'Deep-fried pastry with spiced potato filling.'),
    ('Veg Sandwich', Dish.Category.SNACKS, 30, 'Grilled sandwich with chutney.'),
    ('Masala Chai', Dish.Category.BEVERAGES, 10, 'Spiced milk tea.'),
    ('Cold Coffee', Dish.Category.BEVERAGES, 35, 'Chilled coffee with ice cream.'),
]


class Command(BaseCommand):
    help = 'Seed CanteenIQ with demo users, dishes, inventory, and order history for the forecaster.'

    def handle(self, *args, **options):
        # --- Users ---
        staff, created = User.objects.get_or_create(username='staff', defaults={'is_staff': True})
        if created:
            staff.set_password('staff12345')
            staff.save()
        Profile.objects.update_or_create(user=staff, defaults={'role': Profile.Role.STAFF})

        students = []
        for i in range(1, 4):
            u, created = User.objects.get_or_create(username=f'student{i}')
            if created:
                u.set_password('student12345')
                u.save()
            Profile.objects.get_or_create(user=u, defaults={'role': Profile.Role.STUDENT})
            students.append(u)

        # --- Dishes + inventory ---
        dish_objs = []
        for name, category, price, desc in DISHES:
            dish, _ = Dish.objects.update_or_create(
                name=name, defaults={'category': category, 'price': price, 'description': desc}
            )
            Inventory.objects.update_or_create(dish=dish, defaults={'quantity_available': random.randint(15, 40)})
            dish_objs.append(dish)

        # --- Backdated order history (last 8 weeks) so the forecaster has
        # same-weekday data to average over. ---
        Order.objects.filter(student__in=students).delete()
        today = timezone.localdate()
        created_count = 0

        for days_ago in range(1, 8 * 7):
            order_date = today - timedelta(days=days_ago)
            # Skip roughly a third of days to make the data look like real
            # (imperfect, not-every-single-day) usage.
            if random.random() < 0.3:
                continue

            num_orders = random.randint(2, 5)
            for _ in range(num_orders):
                student = random.choice(students)
                order = Order.objects.create(student=student, status=Order.Status.COMPLETED)
                Order.objects.filter(pk=order.pk).update(
                    created_at=timezone.make_aware(
                        timezone.datetime.combine(order_date, timezone.datetime.min.time())
                        + timedelta(hours=random.randint(8, 18))
                    )
                )
                chosen = random.sample(dish_objs, k=random.randint(1, 3))
                for dish in chosen:
                    OrderItem.objects.create(
                        order=order, dish=dish, quantity=random.randint(1, 2), price_at_order=dish.price
                    )
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded: 1 staff user (staff/staff12345), {len(students)} student users '
            f'(student1/student2/student3, password: student12345), {len(dish_objs)} dishes, '
            f'and {created_count} historical orders.'
        ))
