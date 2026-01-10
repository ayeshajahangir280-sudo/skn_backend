from django.urls import path
from .views import create_checkout_session, generate_receipt_pdf

urlpatterns = [
    path('create-checkout-session/', create_checkout_session, name='create-checkout-session'),
    path('generate-receipt/<int:order_id>/', generate_receipt_pdf, name='generate-receipt'),
]
