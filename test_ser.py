import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.serializers import CategorySerializer
from api.models import Category

# Clean up
Category.objects.filter(name='Test Category').delete()
Category.objects.create(name='Test Category')

data = {'name': 'Test Category'}
serializer = CategorySerializer(data=data)
print(f'Valid: {serializer.is_valid()}')
print(f'Errors: {serializer.errors}')
