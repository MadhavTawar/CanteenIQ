from rest_framework import serializers

from .models import Dish, Inventory, Order, OrderItem


class DishSerializer(serializers.ModelSerializer):
    quantity_available = serializers.IntegerField(
        source='inventory.quantity_available', read_only=True, default=0
    )

    class Meta:
        model = Dish
        fields = ['id', 'name', 'description', 'category', 'price', 'is_available', 'quantity_available']


class InventorySerializer(serializers.ModelSerializer):
    dish_name = serializers.CharField(source='dish.name', read_only=True)

    class Meta:
        model = Inventory
        fields = ['id', 'dish', 'dish_name', 'quantity_available', 'updated_at']
        read_only_fields = ['updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    dish_name = serializers.CharField(source='dish.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'dish', 'dish_name', 'quantity', 'price_at_order', 'subtotal']
        read_only_fields = ['price_at_order']


class OrderItemInputSerializer(serializers.Serializer):
    """Used only for validating the incoming order-creation payload."""
    dish = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'student', 'student_username', 'status', 'created_at', 'updated_at', 'items', 'total_amount']
        read_only_fields = ['student', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Order must contain at least one item.')
        dish_ids = [item['dish'].id for item in value]
        if len(dish_ids) != len(set(dish_ids)):
            raise serializers.ValidationError('Duplicate dish in one order — combine quantities instead.')
        return value
