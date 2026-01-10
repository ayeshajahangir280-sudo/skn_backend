from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Product, Collection, Order, OrderItem, Category
from .serializers import (
    ProductSerializer, CollectionSerializer, OrderSerializer, 
    UserSerializer, RegisterSerializer, CategorySerializer
)
from .emails import send_order_confirmation_email
import stripe
from django.conf import settings

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'your_stripe_secret_key_here')

@method_decorator(csrf_exempt, name='dispatch')
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

@method_decorator(csrf_exempt, name='dispatch')
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

@method_decorator(csrf_exempt, name='dispatch')
class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

@method_decorator(csrf_exempt, name='dispatch')
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        order = serializer.save()
        send_order_confirmation_email(order)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        login(request, user)
        return Response(UserSerializer(user).data)
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)

@csrf_exempt
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    return Response(UserSerializer(request.user).data)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def create_checkout_session(request):
    try:
        data = request.data
        items = data.get('items', [])
        email = data.get('email', '')
        first_name = data.get('firstName', '')
        last_name = data.get('lastName', '')
        address = data.get('address', '')
        city = data.get('city', '')
        country = data.get('country', '')
        postal_code = data.get('postalCode', '')
        phone = data.get('phone', '')
        shipping_cost = data.get('shipping_cost', 0)

        # Create order in database first
        total_amount = 0
        order = Order.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            address=address,
            city=city,
            country=country,
            postal_code=postal_code,
            phone=phone,
            total=0, # Will update after adding items
            shipping=shipping_cost,
            status='pending'
        )

        line_items = []
        for item in items:
            product_id = item.get('product', {}).get('id')
            quantity = item.get('quantity', 1)
            product = Product.objects.get(id=product_id)
            
            price = product.price
            total_amount += price * quantity
            
            OrderItem.objects.create(
                order=order,
                product=product,
                name=product.name,
                price=price,
                quantity=quantity,
                image_url=request.build_absolute_uri(product.image.url) if product.image else ''
            )

            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                    },
                    'unit_amount': int(price * 100),
                },
                'quantity': quantity,
            })

        # Add shipping to total amount
        total_amount += shipping_cost
        order.total = total_amount
        order.save()

        # Add shipping as a line item if > 0
        if shipping_cost > 0:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Shipping Fee',
                    },
                    'unit_amount': int(shipping_cost * 100),
                },
                'quantity': 1,
            })

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=settings.FRONTEND_URL + '/order-confirmation?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=settings.FRONTEND_URL + '/checkout',
            customer_email=email,
            metadata={
                'order_id': order.id
            }
        )

        return Response({'url': checkout_session.url})
    except Exception as e:
        print(f"Error in create_checkout_session: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, getattr(settings, 'STRIPE_WEBHOOK_SECRET', 'your_webhook_secret_here')
        )
    except ValueError as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id')
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                order.status = 'paid'
                order.save()
                send_order_confirmation_email(order)
            except Order.DoesNotExist:
                pass

    return Response(status=status.HTTP_200_OK)

RegisterView = register_view
LoginView = login_view
LogoutView = logout_view
CurrentUserView = current_user_view
