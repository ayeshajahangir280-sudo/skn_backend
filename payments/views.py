import json
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_checkout_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))

        # amount from frontend in cents (e.g. 199.99 -> 19999)
        amount = data.get("amount")
        if amount is None:
            return JsonResponse({"error": "Amount is required"}, status=400)

        # currency – your frontend uses "$", so we'll use USD
        currency = data.get("currency", "usd")

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": "SKN Hair Care Order",
                        },
                        "unit_amount": amount,
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
