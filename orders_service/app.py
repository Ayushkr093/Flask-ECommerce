from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mysql.connector
import requests
import os
import time

app = Flask(__name__)
app.secret_key = 'orders-service-secret-key'

# Database configuration
db_config = {
    'host': os.getenv('MYSQL_HOST', 'mysql'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'password'),
    'database': os.getenv('MYSQL_DB', 'microservices')
}

# Service URLs
USERS_SERVICE_URL = os.getenv('USERS_SERVICE_URL', 'http://users-service:5000')
PRODUCTS_SERVICE_URL = os.getenv('PRODUCTS_SERVICE_URL', 'http://products-service:5000')


def get_db_connection():
    """Create and return a database connection with retry logic"""
    max_retries = 5
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            conn = mysql.connector.connect(**db_config)
            return conn
        except mysql.connector.Error as err:
            print(f"DB connection attempt {attempt+1} failed: {err}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise


def init_db():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                status ENUM('pending','completed','cancelled') DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("Orders table initialized successfully")
    except Exception as e:
        print(f"Error initializing DB: {e}")


# ------------------ USERS + PRODUCTS SERVICE HELPERS ------------------

def get_users():
    try:
        r = requests.get(f"{USERS_SERVICE_URL}/api/users", timeout=5)
        if r.status_code == 200:
            users = r.json()
            for u in users:
                u['cash_balance'] = float(u.get('cash_balance', 0.0))
            return users
    except:
        pass
    return []


def get_products():
    try:
        r = requests.get(f"{PRODUCTS_SERVICE_URL}/api/products", timeout=5)
        if r.status_code == 200:
            products = r.json()
            for p in products:
                p['price'] = float(p.get('price', 0.0))
            return products
    except:
        pass
    return []


def get_user(user_id):
    try:
        r = requests.get(f"{USERS_SERVICE_URL}/api/users/{user_id}", timeout=5)
        if r.status_code == 200:
            u = r.json()
            u['cash_balance'] = float(u.get('cash_balance', 0.0))
            return u
    except:
        pass
    return None


def get_product(product_id):
    try:
        r = requests.get(f"{PRODUCTS_SERVICE_URL}/api/products/{product_id}", timeout=5)
        if r.status_code == 200:
            p = r.json()
            p['price'] = float(p.get('price', 0.0))
            p['stock'] = int(p.get('stock', 0))
            return p
    except:
        pass
    return None


def update_user_balance(user_id, new_balance):
    user = get_user(user_id)
    if not user:
        return False
    try:
        r = requests.put(
            f"{USERS_SERVICE_URL}/api/users/{user_id}",
            json={
                "name": user["name"],
                "email": user["email"],
                "cash_balance": float(new_balance)
            },
            timeout=5
        )
        return r.status_code == 200
    except:
        return False


def update_product_stock(product_id, new_stock):
    product = get_product(product_id)
    if not product:
        return False
    try:
        r = requests.put(
            f"{PRODUCTS_SERVICE_URL}/api/products/{product_id}",
            json={
                "name": product["name"],
                "description": product.get("description", ""),
                "price": float(product["price"]),
                "stock": int(new_stock),
                "category": product.get("category", ""),
                "image_url": product.get("image_url", "")
            },
            timeout=5
        )
        return r.status_code == 200
    except:
        return False


# ------------------ ROUTES ------------------

@app.route('/')
def index():
    return redirect(url_for('list_orders'))


@app.route('/orders')
def list_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
        orders = cursor.fetchall()
        cursor.close()
        conn.close()

        for o in orders:
            o["total_price"] = float(o["total_price"])

        return render_template("list_orders.html", orders=orders)
    except Exception as e:
        flash(f"Error loading orders: {e}", "danger")
        return render_template("list_orders.html", orders=[])


@app.route('/orders/create', methods=['GET', 'POST'])
def create_order():
    if request.method == 'POST':
        try:
            user_id = int(request.form['user_id'])
            product_id = int(request.form['product_id'])
            qty = int(request.form['quantity'])

            if qty <= 0:
                flash("Quantity must be > 0", "danger")
                return redirect(url_for("create_order"))

            user = get_user(user_id)
            product = get_product(product_id)

            if not user or not product:
                flash("Invalid user or product", "danger")
                return redirect(url_for("create_order"))

            total_price = product["price"] * qty

            if user["cash_balance"] < total_price:
                flash("Insufficient balance", "danger")
                return redirect(url_for("create_order"))

            if product["stock"] < qty:
                flash("Insufficient stock", "danger")
                return redirect(url_for("create_order"))

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO orders (user_id, product_id, quantity, total_price, status) VALUES (%s,%s,%s,%s,%s)",
                (user_id, product_id, qty, total_price, "completed")
            )
            order_id = cursor.lastrowid

            if not update_user_balance(user_id, user["cash_balance"] - total_price):
                conn.rollback()
                flash("Error updating user balance", "danger")
                return redirect(url_for("create_order"))

            if not update_product_stock(product_id, product["stock"] - qty):
                conn.rollback()
                flash("Error updating product stock", "danger")
                return redirect(url_for("create_order"))

            conn.commit()
            cursor.close()
            conn.close()

            flash(f"Order #{order_id} created!", "success")
            return redirect(url_for("order_details", order_id=order_id))

        except Exception as e:
            flash(f"Error creating order: {e}", "danger")
            return redirect(url_for("create_order"))

    return render_template("create_order.html", users=get_users(), products=get_products())


@app.route('/orders/<int:order_id>')
def order_details(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
        order = cursor.fetchone()
        cursor.close()
        conn.close()

        if not order:
            flash("Order not found", "danger")
            return redirect(url_for("list_orders"))

        order["total_price"] = float(order["total_price"])
        return render_template("order_details.html", order=order)

    except Exception as e:
        flash(f"Error loading details: {e}", "danger")
        return redirect(url_for("list_orders"))


@app.route('/orders/cancel/<int:order_id>')
def cancel_order(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
        order = cursor.fetchone()

        if not order:
            flash("Order not found", "danger")
            return redirect(url_for("list_orders"))

        if order["status"] == "cancelled":
            flash("Already cancelled", "warning")
            return redirect(url_for("order_details", order_id=order_id))

        # Refund user
        user = get_user(order["user_id"])
        if user:
            update_user_balance(order["user_id"], user["cash_balance"] + float(order["total_price"]))

        # Restock product
        product = get_product(order["product_id"])
        if product:
            update_product_stock(order["product_id"], product["stock"] + order["quantity"])

        cursor.execute("UPDATE orders SET status='cancelled' WHERE id=%s", (order_id,))
        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Order #{order_id} cancelled", "success")
        return redirect(url_for("order_details", order_id=order_id))

    except Exception as e:
        flash(f"Error cancelling: {e}", "danger")
        return redirect(url_for("list_orders"))


# ------------------ API + HEALTH ------------------

@app.route('/api/orders')
def api_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/orders/<int:order_id>')
def api_order(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
        order = cursor.fetchone()
        cursor.close()
        conn.close()
        if order:
            return jsonify(order)
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return jsonify({"status": "healthy", "service": "orders"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
