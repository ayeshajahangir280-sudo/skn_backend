from django.contrib import admin
from .models import Product, ProductImage, Collection, Order, OrderItem, Category

from .emails import send_order_confirmation_email

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'featured', 'bestseller')
    list_filter = ('category', 'featured', 'bestseller')
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    filter_horizontal = ('products',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'name', 'price', 'quantity')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'status', 'created_at', 'total')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'first_name', 'last_name', 'email')
    readonly_fields = ('created_at',)
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = Order.objects.get(pk=obj.pk)
            # If status is being changed to 'paid' from something else
            if old_obj.status != 'paid' and obj.status == 'paid':
                send_order_confirmation_email(obj)
        super().save_model(request, obj, form, change)
