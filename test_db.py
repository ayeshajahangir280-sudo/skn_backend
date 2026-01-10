import os
import django
import sys

# Add the current directory to sys.path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Product
try:
    count = Product.objects.count()
    print(f"Total products: {count}")
except Exception as e:
    print(f"Error connecting to DB: {e}")
