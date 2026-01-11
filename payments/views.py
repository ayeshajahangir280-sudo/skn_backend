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

# =========================
# CURRENCY CONFIG
# =========================
CURRENCY_RATES = {
    "USD": Decimal("1"),
    "GBP": Decimal("0.79"),
    "AED": Decimal("3.67"),
    "AUD": Decimal("1.52"),
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "GBP": "£",
    "AED": "د.إ",
    "AUD": "A$",
}

@csrf_exempt
def create_checkout_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))

        items_data = data.get("items", [])
        if not items_data:
            return JsonResponse({"error": "Items are required"}, status=400)

        # =========================
        # READ CURRENCY
        # =========================
        currency = data.get("currency", "USD")
        if currency not in CURRENCY_RATES:
            return JsonResponse({"error": "Invalid currency"}, status=400)

        rate = CURRENCY_RATES[currency]

        shipping_cost = Decimal(str(data.get("shipping_cost") or 0)) * rate
        email = data.get("email")
        first_name = data.get("firstName")
        last_name = data.get("lastName")
        address = data.get("address")
        city = data.get("city")
        country = data.get("country")
        postal_code = data.get("postalCode")
        phone = data.get("phone", "")

        subtotal = Decimal("0.00")
        order_items_to_create = []

        for item in items_data:
            product_id = item.get("product", {}).get("id")
            quantity = item.get("quantity") or 1

            try:
                product = Product.objects.get(id=product_id)

                converted_price = Decimal(str(product.price)) * rate
                item_total = converted_price * Decimal(str(quantity))
                subtotal += item_total

                order_items_to_create.append({
                    "product": product,
                    "name": product.name,
                    "price": converted_price,
                    "quantity": quantity,
                    "image_url": product.image.url if product.image else ""
                })

            except Product.DoesNotExist:
                return JsonResponse(
                    {"error": f"Product with id {product_id} not found"},
                    status=404
                )

        total = subtotal + shipping_cost

        # =========================
        # CREATE ORDER
        # =========================
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
            currency=currency,  # ✅ ADD FIELD IN MODEL
            status="pending"
        )

        # =========================
        # CREATE ORDER ITEMS
        # =========================
        for item_data in order_items_to_create:
            OrderItem.objects.create(
                order=order,
                product=item_data["product"],
                name=item_data["name"],
                price=item_data["price"],
                quantity=item_data["quantity"],
                image_url=item_data["image_url"]
            )

        # =========================
        # SEND EMAIL
        # =========================
        send_order_confirmation_email(order)

        # =========================
        # STRIPE SESSION
        # =========================
        stripe_amount = int(total * 100)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=email,
            line_items=[
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {
                            "name": "SKN Hair Care Order",
                            "description": f"Order #{order.id}",
                        },
                        "unit_amount": stripe_amount,
                    },
                    "quantity": 1,
                }
            ],
            success_url=settings.FRONTEND_URL + "/order-confirmation?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.FRONTEND_URL + "/checkout",
        )

        return JsonResponse({"url": checkout_session.url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# =========================
# RECEIPT PDF
# =========================
def generate_receipt_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    symbol = CURRENCY_SYMBOLS.get(order.currency, "$")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="receipt_{order.id}.pdf"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=20,
        alignment=2
    )
    normal_style = styles["Normal"]
    bold_style = ParagraphStyle(
        "BoldStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold"
    )

    # Logo
    logo_path = os.path.join(
        settings.BASE_DIR, "..", "src", "images", "SKN transparent-03.png"
    )

    logo_img = ""
    if os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=1.2 * inch, height=1.2 * inch)
        except:
            logo_img = ""

    header_table = Table(
        [[
            [Paragraph("SKN Hair Care", bold_style),
             Paragraph("hello@sknhaircare.com", normal_style)],
            logo_img
        ]],
        colWidths=[4 * inch, 2.5 * inch]
    )
    elements.append(header_table)
    elements.append(Spacer(1, 0.5 * inch))

    elements.append(Paragraph("ORDER RECEIPT", title_style))

    billing_data = [
        ["Billed To", "Receipt #", f"{order.id:07d}"],
        [f"{order.first_name} {order.last_name}", "Date", order.created_at.strftime("%m-%d-%Y")],
        [order.address, "", ""],
        [f"{order.city}, {order.country} {order.postal_code}", "", ""],
    ]

    elements.append(Table(billing_data, colWidths=[4 * inch, 1.2 * inch, 1.3 * inch]))
    elements.append(Spacer(1, 0.4 * inch))

    data = [["QTY", "Description", "Unit Price", "Amount"]]
    for item in order.items.all():
        data.append([
            item.quantity,
            item.name,
            f"{symbol}{item.price:.2f}",
            f"{symbol}{(item.price * item.quantity):.2f}",
        ])

    elements.append(Table(data, colWidths=[0.6 * inch, 3.4 * inch, 1.25 * inch, 1.25 * inch]))

    subtotal = order.total - order.shipping
    totals_data = [
        ["", "", "Subtotal", f"{symbol}{subtotal:.2f}"],
        ["", "", "Shipping", f"{symbol}{order.shipping:.2f}"],
        ["", "", f"Total ({order.currency})", f"{symbol}{order.total:.2f}"],
    ]

    elements.append(Table(totals_data, colWidths=[0.6 * inch, 3.4 * inch, 1.25 * inch, 1.25 * inch]))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
