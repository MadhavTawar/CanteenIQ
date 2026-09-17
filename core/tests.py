from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .forecasting import predict_demand
from .models import Dish, Inventory, Order, OrderItem, Profile

User = get_user_model()


class RoleSetupMixin:
    def setUp(self):
        self.staff = User.objects.create_user('staffuser', password='pass12345')
        self.staff.profile.role = Profile.Role.STAFF
        self.staff.profile.save()

        self.student1 = User.objects.create_user('student1', password='pass12345')
        self.student2 = User.objects.create_user('student2', password='pass12345')

        self.dish = Dish.objects.create(
            name='Veg Thali', category=Dish.Category.LUNCH, price=70
        )
        # signal creates an Inventory row at 0 — top it up
        self.dish.inventory.quantity_available = 10
        self.dish.inventory.save()

        self.staff_client = APIClient()
        self.staff_client.login(username='staffuser', password='pass12345')

        self.student1_client = APIClient()
        self.student1_client.login(username='student1', password='pass12345')

        self.student2_client = APIClient()
        self.student2_client.login(username='student2', password='pass12345')


class ProfileSignalTests(TestCase):
    def test_new_user_gets_student_profile_by_default(self):
        user = User.objects.create_user('plain', password='pass12345')
        self.assertEqual(user.profile.role, Profile.Role.STUDENT)

    def test_superuser_gets_staff_profile(self):
        admin = User.objects.create_superuser('admin', password='pass12345')
        self.assertEqual(admin.profile.role, Profile.Role.STAFF)

    def test_new_dish_gets_zeroed_inventory_row(self):
        dish = Dish.objects.create(name='Idli', category=Dish.Category.BREAKFAST, price=30)
        self.assertTrue(hasattr(dish, 'inventory'))
        self.assertEqual(dish.inventory.quantity_available, 0)


class OrderPlacementTests(RoleSetupMixin, TestCase):
    def test_student_can_place_order_and_stock_decrements(self):
        res = self.student1_client.post(
            '/api/orders/', {'items': [{'dish': self.dish.id, 'quantity': 3}]}, format='json'
        )
        self.assertEqual(res.status_code, 201)
        self.dish.inventory.refresh_from_db()
        self.assertEqual(self.dish.inventory.quantity_available, 7)

    def test_cannot_order_more_than_available_stock(self):
        res = self.student1_client.post(
            '/api/orders/', {'items': [{'dish': self.dish.id, 'quantity': 999}]}, format='json'
        )
        self.assertEqual(res.status_code, 409)
        self.dish.inventory.refresh_from_db()
        self.assertEqual(self.dish.inventory.quantity_available, 10, 'stock must be unchanged on a rejected order')

    def test_failed_order_does_not_create_a_partial_order_row(self):
        """The whole order (and its stock deduction) must roll back
        together — no order should be left behind if any single item
        in it fails."""
        before = Order.objects.count()
        self.student1_client.post(
            '/api/orders/', {'items': [{'dish': self.dish.id, 'quantity': 999}]}, format='json'
        )
        self.assertEqual(Order.objects.count(), before)

    def test_duplicate_dish_in_one_order_is_rejected(self):
        res = self.student1_client.post(
            '/api/orders/',
            {'items': [
                {'dish': self.dish.id, 'quantity': 1},
                {'dish': self.dish.id, 'quantity': 2},
            ]},
            format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_empty_order_is_rejected(self):
        res = self.student1_client.post('/api/orders/', {'items': []}, format='json')
        self.assertEqual(res.status_code, 400)


class OrderVisibilityTests(RoleSetupMixin, TestCase):
    def test_student_only_sees_own_orders(self):
        Order.objects.create(student=self.student1)
        Order.objects.create(student=self.student2)

        res = self.student1_client.get('/api/orders/')
        self.assertEqual(res.status_code, 200)
        student_ids = {o['student'] for o in res.json()}
        self.assertEqual(student_ids, {self.student1.id})

    def test_staff_sees_all_orders(self):
        Order.objects.create(student=self.student1)
        Order.objects.create(student=self.student2)

        res = self.staff_client.get('/api/orders/')
        self.assertEqual(len(res.json()), 2)

    def test_student_cannot_patch_another_students_order_status(self):
        order = Order.objects.create(student=self.student2)
        res = self.student1_client.patch(f'/api/orders/{order.id}/set_status/', {'status': 'READY'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_student_can_filter_orders_and_receive_paginated_shape(self):
        Order.objects.create(student=self.student1, status=Order.Status.READY)
        Order.objects.create(student=self.student1, status=Order.Status.PLACED)

        res = self.student1_client.get('/api/orders/?status=READY&page=1')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)
        self.assertEqual(res.json()['results'][0]['status'], Order.Status.READY)


class RolePermissionTests(RoleSetupMixin, TestCase):
    def test_student_cannot_create_dish(self):
        res = self.student1_client.post(
            '/api/menu/', {'name': 'Hack Dish', 'category': 'SNACKS', 'price': 10}, format='json'
        )
        self.assertEqual(res.status_code, 403)

    def test_staff_can_create_dish(self):
        res = self.staff_client.post(
            '/api/menu/', {'name': 'New Dish', 'category': 'SNACKS', 'price': 10}, format='json'
        )
        self.assertEqual(res.status_code, 201)

    def test_student_can_read_menu(self):
        res = self.student1_client.get('/api/menu/')
        self.assertEqual(res.status_code, 200)

    def test_student_cannot_access_forecast(self):
        res = self.student1_client.get('/api/forecast/')
        self.assertEqual(res.status_code, 403)

    def test_staff_can_access_forecast(self):
        res = self.staff_client.get('/api/forecast/')
        self.assertEqual(res.status_code, 200)

    def test_anonymous_user_is_rejected(self):
        anon = APIClient()
        res = anon.get('/api/orders/')
        self.assertEqual(res.status_code, 403)

    def test_staff_can_download_sales_csv(self):
        order = Order.objects.create(student=self.student1, status=Order.Status.COMPLETED)
        OrderItem.objects.create(order=order, dish=self.dish, quantity=2, price_at_order=self.dish.price)

        res = self.staff_client.get('/api/sales/?export=csv')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        self.assertIn('Veg Thali', res.content.decode())

    def test_api_docs_are_available_to_authenticated_user(self):
        res = self.student1_client.get('/api/docs/')
        self.assertEqual(res.status_code, 200)


class ForecastingTests(RoleSetupMixin, TestCase):
    def _place_completed_order(self, dish, quantity, on_date):
        order = Order.objects.create(student=self.student1, status=Order.Status.COMPLETED)
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.make_aware(timezone.datetime.combine(on_date, timezone.datetime.min.time()))
        )
        OrderItem.objects.create(order=order, dish=dish, quantity=quantity, price_at_order=dish.price)

    def test_predicts_average_of_same_weekday_history(self):
        target = date.today() + timedelta(days=(7 - date.today().weekday()))  # a future date
        same_weekday_dates = [target - timedelta(weeks=w) for w in range(1, 4)]

        for d, qty in zip(same_weekday_dates, [4, 6, 5]):
            self._place_completed_order(self.dish, qty, d)

        result = predict_demand(self.dish, target)
        # average of 4, 6, 5 = 5.0 -> rounds up to 5
        self.assertEqual(result['predicted_quantity'], 5)
        self.assertIn('same-weekday average', result['basis'])

    def test_falls_back_to_all_time_average_with_no_same_weekday_history(self):
        target = date.today() + timedelta(days=10)
        # orders on a different weekday only
        self._place_completed_order(self.dish, 3, target - timedelta(days=3))

        result = predict_demand(self.dish, target)
        self.assertEqual(result['predicted_quantity'], 3)
        self.assertIn('all-time', result['basis'])

    def test_zero_prediction_with_no_history_at_all(self):
        fresh_dish = Dish.objects.create(name='Brand New Dish', category=Dish.Category.SNACKS, price=15)
        result = predict_demand(fresh_dish, date.today() + timedelta(days=5))
        self.assertEqual(result['predicted_quantity'], 0)
        self.assertIn('no order history', result['basis'])


class InventoryNotificationTests(RoleSetupMixin, TestCase):
    def test_crossing_low_stock_threshold_logs_notification(self):
        with self.assertLogs('core.views_api', level='WARNING') as logs:
            res = self.staff_client.patch(
                f'/api/inventory/{self.dish.inventory.id}/',
                {'quantity_available': 5},
                format='json',
            )

        self.assertEqual(res.status_code, 200)
        self.assertIn('LOW STOCK notification', logs.output[0])
