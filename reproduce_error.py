import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from api.models import Category, Product

def reproduce():
    client = APIClient()
    
    # Create an admin user
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser('admin', 'admin@test.com', 'password')
    else:
        admin = User.objects.get(username='admin')
    
    client.force_authenticate(user=admin)
    
    # Create a category
    category = Category.objects.create(name="Test Category")
    
    # Create a dummy image
    image = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
    
    # Try to create a product without a category (to trigger the bug I fixed)
    data = {
        "name": "Product Without Category",
        "price": "100.00",
        "description": "Test description",
        "image": image,
    }
    
    print("Testing product creation without category...")
    response = client.post('/api/products/', data, format='multipart')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 500:
        print("Reproduced 500 error!")
    elif response.status_code == 201:
        print("Product created successfully!")
    else:
        print(f"Response data: {response.data}")

    # Try to create a product with a category
    image2 = SimpleUploadedFile("test2.jpg", b"file_content", content_type="image/jpeg")
    data_with_cat = {
        "name": "Product With Category",
        "category": category.id,
        "price": "200.00",
        "description": "Test description with category",
        "image": image2,
    }
    
    print("\nTesting product creation with category...")
    response = client.post('/api/products/', data_with_cat, format='multipart')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        print("Product with category created successfully!")
    else:
        print(f"Response data: {response.data}")

if __name__ == "__main__":
    reproduce()
