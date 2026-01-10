from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_order_confirmation_email(order):
    subject = f'Order Confirmation #{order.id}'
    
    order_items_details = []
    for item in order.items.all():
        order_items_details.append({
            'name': item.name,
            'quantity': item.quantity,
            'price': item.price,
            'total': item.price * item.quantity
        })
    
    context = {
        'order_id': order.id,
        'first_name': order.first_name,
        'last_name': order.last_name,
        'email': order.email,
        'phone': order.phone,
        'address': order.address,
        'city': order.city,
        'country': order.country,
        'postal_code': order.postal_code,
        'items': order_items_details,
        'subtotal': order.total - order.shipping,
        'shipping': order.shipping,
        'total': order.total,
        'status': order.get_status_display(),
        'created_at': order.created_at,
    }
    
    html_message = render_to_string('order_confirmation_email.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        # Send to customer
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[order.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Send notification to admin
        admin_subject = f'NEW ORDER RECEIVED: #{order.id}'
        send_mail(
            subject=admin_subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.EMAIL_HOST_USER],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending order confirmation email to {order.email}: {e}")
        return False
