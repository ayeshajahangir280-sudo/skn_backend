from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class SupabaseStorage(S3Boto3Storage):
    file_overwrite = False

    def exists(self, name):
        return False  # 🚨 THIS BYPASSES HeadObject

    def __init__(self, *args, **kwargs):
        # Use SUPABASE_SERVICE_ROLE_KEY as the secret key if not provided
        if not kwargs.get('access_key'):
            kwargs['access_key'] = 'supabase' # Supabase S3 accepts any string for access key ID
        if not kwargs.get('secret_key'):
            kwargs['secret_key'] = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
        super().__init__(*args, **kwargs)
