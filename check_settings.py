import os
import django
from pathlib import Path

# Fix path to settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings

print(f"USE_SUPABASE: {settings.USE_SUPABASE}")
print(f"AWS_ACCESS_KEY_ID: {settings.AWS_ACCESS_KEY_ID}")
print(f"AWS_S3_ENDPOINT_URL: {settings.AWS_S3_ENDPOINT_URL}")
print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
