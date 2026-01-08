import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Product, Category

print(f"Total products: {Product.objects.count()}")
print(f"Total categories: {Category.objects.count()}")

print("\nCategories:")
for c in Category.objects.all():
    print(f"  - {c.name} (ID: {c.id})")

print("\nProducts:")
for p in Product.objects.all():
    print(f"  - {p.name} (ID: {p.id}, Category: {p.category}, Featured: {p.featured}, Bestseller: {p.bestseller})")
