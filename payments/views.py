import json
import stripe
import os
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from api.models import Product, Order, OrderItem
from api.emails import send_order_confirmation_email
from decimal import Decimal
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_checkout_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))

        items_data = data.get("items", [])
        if not items_data:
            return JsonResponse({"error": "Items are required"}, status=400)

        shipping_cost = Decimal(str(data.get("shipping_cost") or 0))
        email = data.get("email")
        first_name = data.get("firstName")
        last_name = data.get("lastName")
        address = data.get("address")
        city = data.get("city")
        country = data.get("country")
        postal_code = data.get("postalCode")
        phone = data.get("phone", "")

        subtotal = Decimal('0.00')
        order_items_to_create = []

        for item in items_data:
            product_id = item.get("product", {}).get("id")
            quantity = item.get("quantity") or 1
            
            try:
                product = Product.objects.get(id=product_id)
                item_total = Decimal(str(product.price)) * Decimal(str(quantity))
                subtotal += item_total
                
                order_items_to_create.append({
                    'product': product,
                    'name': product.name,
                    'price': product.price,
                    'quantity': quantity,
                    'image_url': product.image.url if product.image else ""
                })
            except Product.DoesNotExist:
                return JsonResponse({"error": f"Product with id {product_id} not found"}, status=404)

        total = subtotal + shipping_cost

        # Create Order
        order = Order.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            address=address,
            city=city,
            country=country,
            postal_code=postal_code,
            phone=phone,
            total=total,
            shipping=shipping_cost,
            status='pending'
        )

        # Create OrderItems
        for item_data in order_items_to_create:
            OrderItem.objects.create(
                order=order,
                product=item_data['product'],
                name=item_data['name'],
                price=item_data['price'],
                quantity=item_data['quantity'],
                image_url=item_data['image_url']
            )

        # Send Confirmation Email
        send_order_confirmation_email(order)

        # Stripe amount in cents
        stripe_amount = int(total * 100)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=email,
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {
                            "name": "SKN Hair Care Order",
                            "description": f"Order #{order.id}",
                        },
                        "unit_amount": stripe_amount,
                    },
                    "quantity": 1,
                }
            ],

           

            # When payment succeeds/cancels, Stripe will send user back here:
            success_url=settings.FRONTEND_URL + "/order-confirmation?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.FRONTEND_URL + "/checkout",

        )

        return JsonResponse({"url": checkout_session.url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

def generate_receipt_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{order.id}.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, alignment=2) # Right aligned
    normal_style = styles['Normal']
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')
    
    # Logo and Company Info
    logo_path = os.path.join(settings.BASE_DIR, "..", "src", "images", "SKN transparent-03.png")
    
    company_info_text = [
        Paragraph("SKN Hair Care", bold_style),
        Paragraph("hello@sknhaircare.com", normal_style)
    ]
    
    company_col = []
    for p in company_info_text:
        company_col.append(p)
        
    logo_img = ""
    if os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=1.2*inch, height=1.2*inch)
        except:
            logo_img = "Logo Placeholder"
    
    header_data = [[company_col, logo_img]]
    header_table = Table(header_data, colWidths=[4*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Receipt Title
    elements.append(Paragraph("ORDER RECEIPT", title_style))
    
    # Billing Info
    billing_data = [
        [Paragraph("Billed To", bold_style), Paragraph("Receipt #", bold_style), f"{order.id:07d}"],
        [f"{order.first_name} {order.last_name}", Paragraph("Receipt date", bold_style), order.created_at.strftime('%m-%d-%Y')],
        [order.address, "", ""],
        [f"{order.city}, {order.country} {order.postal_code}", "", ""],
    ]
    billing_table = Table(billing_data, colWidths=[4*inch, 1.2*inch, 1.3*inch])
    billing_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,1), 'LEFT'),
        ('ALIGN', (2,0), (2,1), 'RIGHT'),
    ]))
    elements.append(billing_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Order Items Table
    data = [["QTY", "Description", "Unit Price", "Amount"]]
    for item in order.items.all():
        data.append([
            str(item.quantity),
            item.name,
            f"${item.price:.2f}",
            f"${(item.price * item.quantity):.2f}"
        ])
    
    item_table = Table(data, colWidths=[0.6*inch, 3.4*inch, 1.25*inch, 1.25*inch])
    item_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
    ]))
    elements.append(item_table)
    
    # Totals
    subtotal = order.total - order.shipping
    totals_data = [
        ["", "", "Subtotal", f"€{subtotal:.2f}"],
        ["", "", "Shipping", f"€{order.shipping:.2f}"],
        ["", "", Paragraph("Total (eur)", bold_style), Paragraph(f"€{order.total:.2f}", bold_style)],
    ]
    totals_table = Table(totals_data, colWidths=[0.6*inch, 3.4*inch, 1.25*inch, 1.25*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LINEABOVE', (2,2), (-1,2), 1, colors.black),
        ('LINEBELOW', (2,2), (-1,2), 1, colors.black),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 0.8*inch))
    
    # Notes
    elements.append(Paragraph("Notes", bold_style))
    elements.append(Spacer(1, 0.1*inch))
    notes_text = "Thank you for your purchase! All sales are final after 30 days. Please retain this receipt for warranty or exchange purposes."
    elements.append(Paragraph(notes_text, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("For questions or support, contact us at hello@sknhaircare.com", normal_style))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
