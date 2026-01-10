from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, CollectionViewSet, OrderViewSet, CategoryViewSet,
    LoginView, LogoutView, CurrentUserView, RegisterView,
    create_checkout_session, stripe_webhook
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'collections', CollectionViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    path('', include(router.get_urls())),
    path('register/', RegisterView, name='register'),
    path('login/', LoginView, name='login'),
    path('logout/', LogoutView, name='logout'),
    path('me/', CurrentUserView, name='me'),
    path('payments/create-checkout-session/', create_checkout_session, name='create-checkout-session'),
    path('payments/webhook/', stripe_webhook, name='stripe-webhook'),
]
