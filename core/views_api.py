from datetime import date, timedelta

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .forecasting import predict_demand, predict_demand_for_all
from .models import Dish, Inventory, Order, OrderItem, Profile
from .permissions import IsOwnerOrStaff, IsStaffOrReadOnly, IsStaffRole
from .serializers import (
    DishSerializer,
    InventorySerializer,
    OrderCreateSerializer,
    OrderSerializer,
)


class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.select_related('inventory').all()
    serializer_class = DishSerializer
    permission_classes = [IsStaffOrReadOnly]


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.select_related('dish').all()
    serializer_class = InventorySerializer
    permission_classes = [IsStaffRole]


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsOwnerOrStaff]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = Order.objects.select_related('student').prefetch_related('items__dish')
        user = self.request.user
        if user.profile.role == Profile.Role.STAFF:
            return qs.all()
        return qs.filter(student=user)

    def create(self, request, *args, **kwargs):
        """Place an order.

        Wrapped in a single DB transaction with select_for_update() on the
        Inventory rows involved, so that if two students order the last
        portion of the same dish at the same moment, the second request
        sees the row locked, re-reads the now-updated quantity, and fails
        cleanly with 'out of stock' instead of both succeeding and taking
        the count negative.
        """
        input_serializer = OrderCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        items = input_serializer.validated_data['items']

        with transaction.atomic():
            order = Order.objects.create(student=request.user)
            for entry in items:
                dish = entry['dish']
                qty = entry['quantity']

                inventory = (
                    Inventory.objects.select_for_update()
                    .filter(dish=dish)
                    .first()
                )
                if inventory is None or inventory.quantity_available < qty:
                    transaction.set_rollback(True)
                    return Response(
                        {'detail': f'"{dish.name}" does not have {qty} unit(s) available right now.'},
                        status=status.HTTP_409_CONFLICT,
                    )

                inventory.quantity_available -= qty
                inventory.save(update_fields=['quantity_available'])

                OrderItem.objects.create(
                    order=order, dish=dish, quantity=qty, price_at_order=dish.price
                )

        output = OrderSerializer(order)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsStaffRole])
    def set_status(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.data.get('status')
        valid_statuses = dict(Order.Status.choices)
        if new_status not in valid_statuses:
            return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = new_status
        order.save(update_fields=['status'])
        return Response(OrderSerializer(order).data)


class ForecastView(APIView):
    """GET /api/forecast/?date=YYYY-MM-DD (defaults to tomorrow) — staff only.

    Returns the predicted quantity to prepare per dish. See
    core/forecasting.py for why this is a simple weekday-average model
    rather than anything heavier.
    """

    permission_classes = [IsStaffRole]

    def get(self, request):
        date_param = request.query_params.get('date')
        target_date = date.fromisoformat(date_param) if date_param else date.today() + timedelta(days=1)
        dishes = Dish.objects.filter(is_available=True)
        return Response(predict_demand_for_all(target_date, dishes))


class DailySalesView(APIView):
    """GET /api/sales/?date=YYYY-MM-DD (defaults to today) — staff only."""

    permission_classes = [IsStaffRole]

    def get(self, request):
        date_param = request.query_params.get('date')
        target_date = date.fromisoformat(date_param) if date_param else date.today()

        items = OrderItem.objects.filter(
            order__created_at__date=target_date,
            order__status__in=['PLACED', 'PREPARING', 'READY', 'COMPLETED'],
        )
        per_dish = (
            items.values('dish__name')
            .annotate(units_sold=Sum('quantity'))
            .order_by('-units_sold')
        )
        revenue = sum(i.subtotal for i in items)
        return Response({'date': target_date.isoformat(), 'revenue': revenue, 'per_dish': list(per_dish)})
