"""
Mock CRM tools for the Nuit Bot v2.
Simulates HubSpot CRM database operations with atomic transactions.
"""

import json
from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Mock Data
# ---------------------------------------------------------------------------

PRODUCT_CATALOG = {
    "flagship_edp_50ml": {
        "name": "Flagship Eau de Parfum (EDP) — 50ml",
        "standard_price": "EGP 855.00",
        "promo_price": "EGP 599.00",
        "variants": [
            "Rum",
            "Dulce de Leche",
            "Head Turner",
            "Born in Milano",
            "Born in Vegas",
            "Bounty Hunter",
            "Red Flag",
            "Green Flag",
            "Espresso Martini",
            "Forbidden Fruit",
            "Casa Di Rosa",
            "Lindo Día",
            "Monroe",
            "Warm Vanilla",
            "French Foulard",
            "True Hipster",
            "Leather Jacket",
            "Cappuccina",
            "Choco Frappe",
            "Hazelwood",
            "Heritage",
            "I am Harvey",
        ],
    },
    "luxury_collaboration": {
        "name": "Avec Hatshepsut (Nuit X Temraza)",
        "price": "EGP 1,950.00",
        "notes": "exclusive art flacon, NOT eligible for standard EDP discounts",
    },
    "perfume_oils_shots_khamrias": {
        "name": "Concentrated Perfume Oils (Shots) & Khamrias",
        "price": "EGP 475.00",
        "examples": [
            "Vanilla Shot",
            "Born in Milano Shot",
            "Caramel Shot",
            "Head Turner Shot",
        ],
    },
    "body_splash_mists": {
        "name": "Body Splash & Mists",
        "price": "EGP 315.00",
        "examples": ["Soft Cloud Heart", "Very Delicate Vanilla", "The Harvey Splash"],
    },
}


MOCK_ORDERS = {
    "3021": {
        "phone": "01023456789",
        "customer_name": "Ahmed Hassan",
        "status": "delivered",
        "delivery_date": "2026-06-25",
        "items": ["Nuit Signature 50ml"],
        "price": 1450.0,
        "eligible_for_return": True,
    },
    "4022": {
        "phone": "01234567890",
        "customer_name": "Sara Mohamed",
        "status": "shipped",
        "eta": "2 days",
        "items": ["Temraza Edition 50ml"],
        "price": 1850.0,
        "eligible_for_return": False,
    },
    "5023": {
        "phone": "01098765432",
        "customer_name": "Youssef Ali",
        "status": "cancelled",
        "reason": "payment_failed",
        "items": ["Discovery Box"],
        "price": 368.0,
        "eligible_for_return": False,
    },
}

MOCK_CRM_PROFILES = {}
ESCALATION_QUEUE = []

#  ---------------------------------------------------------------------------


@tool
def query_products(query: str = "") -> str:
    """Query the product catalog for pricing, availability, and fragrance variants.

    Args:
        query: Optional keywords to filter products (e.g. 'Rum', 'splashes', 'price').

    Returns:
        JSON string containing the matched products and their details.
    """
    clean_query = str(query).strip().lower()
    if not clean_query:
        return json.dumps(PRODUCT_CATALOG)

    matched = {}
    for key, product in PRODUCT_CATALOG.items():
        # Check in name, variants, examples
        name_match = clean_query in product.get("name", "").lower()
        variants_match = any(
            clean_query in v.lower() for v in product.get("variants", [])
        )
        examples_match = any(
            clean_query in e.lower() for e in product.get("examples", [])
        )

        if name_match or variants_match or examples_match:
            matched[key] = product

    if not matched:
        return json.dumps(
            {
                "status": "not_found",
                "message": f"No products found matching '{query}'.",
                "available_categories": list(PRODUCT_CATALOG.keys()),
            }
        )

    return json.dumps(matched)


@tool
def lookup_order(order_id: str = "", phone: str = "") -> str:
    """Look up an order by order ID or phone number. ONLY ONE OF THEM IS NEEDED

    Args:
        order_id: The order ID to look up.
        phone: The customer's phone number to search by.

    Returns:
        JSON string with order details or not-found message.
    """
    clean_order_id = str(order_id).strip()
    clean_phone = str(phone).strip()

    # Match by order_id
    if clean_order_id and clean_order_id in MOCK_ORDERS:
        order = MOCK_ORDERS[clean_order_id]
        if clean_phone and order["phone"] != clean_phone:
            return json.dumps(
                {
                    "status": "not_found",
                    "message": "Phone number does not match order ID.",
                }
            )
        return json.dumps(
            {
                "status": "success",
                "order_id": clean_order_id,
                "data": order,
            }
        )

    # Fallback: search by phone
    for oid, order in MOCK_ORDERS.items():
        if clean_phone and order["phone"] == clean_phone:
            return json.dumps(
                {
                    "status": "success",
                    "order_id": oid,
                    "data": order,
                }
            )

    return json.dumps(
        {
            "status": "not_found",
            "message": "No order matching the provided order ID or phone number.",
        }
    )


@tool
def register_return(order_id: str, reason: str = "not_specified") -> str:
    """Register a return request for an order.

    Args:
        order_id: The order ID to return.
        reason: The reason for the return.

    Returns:
        JSON string with the return registration result.
    """
    clean_order_id = str(order_id).strip()

    if clean_order_id not in MOCK_ORDERS:
        return json.dumps(
            {
                "status": "error",
                "message": f"Order {clean_order_id} not found.",
            }
        )

    order = MOCK_ORDERS[clean_order_id]
    if not order["eligible_for_return"]:
        return json.dumps(
            {
                "status": "failed",
                "message": "Item is not eligible for return (out of 14-day window or promo item).",
            }
        )

    try:
        return json.dumps(
            {
                "status": "success",
                "transaction_type": "register_return",
                "order_id": clean_order_id,
                "committed_update": {
                    "item": order["items"][0],
                    "reason": reason,
                    "timestamp": "2026-07-01T19:28:00Z",
                },
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "status": "rollback_failed",
                "message": f"Database transaction crashed and rolled back. Error: {str(e)}",
            }
        )


@tool
def register_exchange(
    order_id: str, new_item: str = "", reason: str = "not_specified"
) -> str:
    """Register an exchange request for an order.

    Args:
        order_id: The order ID to exchange.
        new_item: The item the customer wants instead.
        reason: The reason for the exchange.

    Returns:
        JSON string with the exchange registration result.
    """
    clean_order_id = str(order_id).strip()

    if clean_order_id not in MOCK_ORDERS:
        return json.dumps(
            {
                "status": "error",
                "message": f"Order {clean_order_id} not found.",
            }
        )

    order = MOCK_ORDERS[clean_order_id]
    if not order["eligible_for_return"]:
        return json.dumps(
            {
                "status": "failed",
                "message": "Item is not eligible for exchange (out of 14-day window or promo item).",
            }
        )

    try:
        return json.dumps(
            {
                "status": "success",
                "transaction_type": "register_exchange",
                "order_id": clean_order_id,
                "committed_update": {
                    "original_item": order["items"][0],
                    "new_item": new_item or "TBD",
                    "reason": reason,
                    "timestamp": "2026-07-01T19:28:00Z",
                },
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "status": "rollback_failed",
                "message": f"Database transaction crashed and rolled back. Error: {str(e)}",
            }
        )


def update_crm_profile(phone: str, info: dict) -> None:
    """Update or create a CRM profile for a customer (mock)."""
    if phone in MOCK_CRM_PROFILES:
        MOCK_CRM_PROFILES[phone].update(info)
    else:
        MOCK_CRM_PROFILES[phone] = info


def get_crm_profile(phone: str) -> dict | None:
    """Retrieve a CRM profile by phone number (mock)."""
    return MOCK_CRM_PROFILES.get(phone)


@tool
def lookup_crm_profile(phone: str) -> str:
    """Retrieve the customer's CRM profile, history, preferences, and details.

    Args:
        phone: The customer's contact phone number.
    """
    profile = get_crm_profile(phone)
    if profile:
        return json.dumps({"status": "success", "profile": profile})
    return json.dumps(
        {
            "status": "not_found",
            "message": "No CRM profile found for this phone number.",
        }
    )


def add_to_escalation_queue(report: dict) -> None:
    """Add an escalation report to the queue (mock)."""
    ESCALATION_QUEUE.append(report)


from .products_db import query_products_sql, get_product_details, search_products_by_description
