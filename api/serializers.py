from rest_framework import serializers
from .models import Product, ProductImage, Collection, Order, OrderItem, Category
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image']

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except Exception as e:
            raise serializers.ValidationError(str(e))

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except Exception as e:
            raise serializers.ValidationError(str(e))

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True, required=False
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'category_name', 'price', 'description', 'details', 
            'image', 'video', 'delivery_charges', 'featured', 'bestseller', 
            'images', 'uploaded_images', 'created_at'
        ]

    def get_category_name(self, obj):
        try:
            if hasattr(obj, 'category') and obj.category:
                return obj.category.name
        except Exception:
            pass
        return None

    def create(self, validated_data):
        try:
            uploaded_images = validated_data.pop('uploaded_images', [])
            product = Product.objects.create(**validated_data)
            for image in uploaded_images:
                ProductImage.objects.create(product=product, image=image)
            return product
        except Exception as e:
            raise serializers.ValidationError(str(e))

class CollectionSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'image', 'products']

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except Exception as e:
            raise serializers.ValidationError(str(e))

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'name', 'price', 'quantity', 'image_url']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'id', 'first_name', 'last_name', 'email', 'address', 'city', 
            'country', 'postal_code', 'phone', 'total', 'shipping', 
            'status', 'created_at', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    is_staff = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_staff']

    def create(self, validated_data):
        is_staff = validated_data.pop('is_staff', False)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        if is_staff:
            user.is_staff = True
            user.save()
        return user
