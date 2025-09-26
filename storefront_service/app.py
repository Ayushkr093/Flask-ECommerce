from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import requests
import os
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = os.getenv("STOREFRONT_SECRET_KEY", "dev-secret-key")

# Session configuration (extendable to Redis/DB later)
app.config.update(
    SESSION_PERMANENT=False,
    SESSION_TYPE="filesystem"
)

# Logging
logging.basicConfig(level=logging.INFO)

# Service URLs from environment (defaults for local/dev)
app.config["PRODUCTS_SERVICE_URL"] = os.getenv("PRODUCTS_SERVICE_URL", "http://products-service:5000")
app.config["ORDERS_SERVICE_URL"] = os.getenv("ORDERS_SERVICE_URL", "http://orders-service:5000")
app.config["USERS_SERVICE_URL"] = os.getenv("USERS_SERVICE_URL", "http://users-service:5000")


# --- Context Processor ---
@app.context_processor
def inject_global_variables():
    """Inject common globals into templates."""
    return {"current_year": datetime.utcnow().year}


# --- Helper: Safe Service Requests ---
def _safe_request(method, url, **kwargs):
    """Wrapper around requests with logging & error handling."""
    try:
        resp = requests.request(method, url, timeout=kwargs.pop("timeout", 5), **kwargs)
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as e:
        app.logger.error(f"[Service Request Failed] {method} {url} | Error: {e}")
        return None


# --- Helpers ---
def _get_cart_details():
    """Compute cart items, total, and item count."""
    cart_items, total, item_count = [], 0, 0
    cart = session.get("cart", {})

    for product_id, quantity in cart.items():
        product = get_product(int(product_id))
        if not product:
            continue
        item_total = product["price"] * quantity
        cart_items.append({
            "id": product_id,
            "product": product,
            "quantity": quantity,
            "item_total": item_total,
        })
        total += item_total
        item_count += quantity

    return cart_items, total, item_count


# --- Microservice Calls ---
def get_products():
    resp = _safe_request("GET", f"{app.config['PRODUCTS_SERVICE_URL']}/api/products")
    if not resp:
        return []
    products = resp.json()
    for p in products:
        p["price"] = float(p.get("price", 0))
    return products


def get_product(product_id):
    resp = _safe_request("GET", f"{app.config['PRODUCTS_SERVICE_URL']}/api/products/{product_id}")
    if not resp:
        return None
    product = resp.json()
    product["price"] = float(product.get("price", 0))
    return product


def get_users():
    resp = _safe_request("GET", f"{app.config['USERS_SERVICE_URL']}/api/users")
    return resp.json() if resp else []


def get_user(user_id):
    resp = _safe_request("GET", f"{app.config['USERS_SERVICE_URL']}/api/users/{user_id}")
    return resp.json() if resp else None


# --- Routes ---
@app.route("/")
def index():
    products = get_products()
    return render_template("index.html", products=products)


# --- Cart ---
@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    try:
        product_id = int(request.form.get("product_id"))
        quantity = max(int(request.form.get("quantity", 1)), 1)
    except (TypeError, ValueError):
        flash("Invalid product or quantity.", "danger")
        return redirect(request.referrer or url_for("index"))

    product = get_product(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("index"))

    cart = session.get("cart", {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    session["cart"] = cart
    session.modified = True

    flash(f"Added {quantity} × {product['name']} to cart.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cart")
def view_cart():
    cart_items, total, item_count = _get_cart_details()
    return render_template("cart.html", cart_items=cart_items, total=total, item_count=item_count)


@app.route("/update-cart", methods=["POST"])
def update_cart():
    try:
        product_id = request.form.get("product_id")
        quantity = int(request.form.get("quantity", 0))
    except (TypeError, ValueError):
        flash("Invalid input.", "danger")
        return redirect(url_for("view_cart"))

    cart = session.get("cart", {})
    if product_id in cart:
        if quantity <= 0:
            cart.pop(product_id, None)
            flash("Item removed.", "info")
        else:
            cart[product_id] = quantity
            flash("Cart updated.", "success")
        session["cart"] = cart
        session.modified = True

    return redirect(url_for("view_cart"))


@app.route("/remove-from-cart/<string:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    if product_id in cart:
        product = get_product(int(product_id))
        name = product["name"] if product else "Item"
        cart.pop(product_id, None)
        session["cart"] = cart
        session.modified = True
        flash(f"{name} removed from cart.", "info")
    return redirect(url_for("view_cart"))


@app.route("/clear-cart")
def clear_cart():
    session.pop("cart", None)
    flash("Cart cleared.", "info")
    return redirect(url_for("view_cart"))


# --- Checkout ---
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Cart is empty.", "warning")
        return redirect(url_for("index"))

    cart_items, total, _ = _get_cart_details()

    if request.method == "GET":
        return render_template("checkout.html", cart_items=cart_items, total=total, users=get_users())

    # POST → Process Order
    try:
        user_id = int(request.form.get("user_id"))
    except (TypeError, ValueError):
        flash("Please select a valid user.", "danger")
        return redirect(url_for("checkout"))

    user = get_user(user_id)
    if not user:
        flash("Selected user not found.", "danger")
        return redirect(url_for("checkout"))

    if float(user.get("cash_balance", 0)) < total:
        flash("User has insufficient funds.", "danger")
        return redirect(url_for("checkout"))

    successful_orders, failed_orders = [], []
    for product_id, quantity in cart.items():
        product = get_product(int(product_id))
        if not product:
            failed_orders.append(f"Product {product_id} not found.")
            continue

        order_data = {"user_id": user_id, "product_id": int(product_id), "quantity": quantity}
        resp = _safe_request("POST", f"{app.config['ORDERS_SERVICE_URL']}/api/orders", json=order_data, timeout=10)

        if resp and resp.status_code == 201:
            successful_orders.append({
                "product_name": product["name"],
                "quantity": quantity,
                "total": product["price"] * quantity,
            })
        else:
            error_msg = (resp.json().get("error") if resp else "Service unavailable")
            failed_orders.append(f"{product['name']}: {error_msg}")

    session.pop("cart", None)  # Clear cart after checkout

    return render_template("order_confirmation.html",
                           successful_orders=successful_orders,
                           failed_orders=failed_orders,
                           user=user)


# --- Health & Errors ---
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "service": "storefront"})


@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server Error: {error}")
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
