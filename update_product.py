import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Product

product = Product.objects.get(id=1)
product.featured = True
product.bestseller = True
product.save()

print(f"Updated product: {product.name}")
print(f"  Featured: {product.featured}")
print(f"  Bestseller: {product.bestseller}")
