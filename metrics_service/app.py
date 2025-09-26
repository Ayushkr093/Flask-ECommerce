from flask import Flask, render_template, request
import mysql.connector
import os

app = Flask(__name__)

def get_db_connection():
    """Establishes a connection to the MySQL database."""
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DB", "microservices"),
        port=int(os.environ.get("MYSQL_PORT", 3306))
    )

@app.route('/')
def dashboard():
    """Renders the main dashboard with various statistics."""
    stats = {}
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total users
    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    stats['Total Users'] = cursor.fetchone()['total_users']

    # Total products
    cursor.execute("SELECT COUNT(*) AS total_products FROM products")
    stats['Total Products'] = cursor.fetchone()['total_products']

    # Total orders
    cursor.execute("SELECT COUNT(*) AS total_orders FROM orders")
    stats['Total Orders'] = cursor.fetchone()['total_orders']

    # Completed orders
    cursor.execute("SELECT COUNT(*) AS completed_orders FROM orders WHERE status='completed'")
    stats['Completed Orders'] = cursor.fetchone()['completed_orders']

    # Pending orders
    cursor.execute("SELECT COUNT(*) AS pending_orders FROM orders WHERE status='pending'")
    stats['Pending Orders'] = cursor.fetchone()['pending_orders']

    # Cancelled orders
    cursor.execute("SELECT COUNT(*) AS cancelled_orders FROM orders WHERE status='cancelled'")
    stats['Cancelled Orders'] = cursor.fetchone()['cancelled_orders']

    # Total revenue
    cursor.execute("SELECT SUM(total_price) AS revenue FROM orders WHERE status='completed'")
    stats['Total Revenue'] = f"₹{float(cursor.fetchone()['revenue'] or 0):.2f}"

    # Top product by sales
    cursor.execute("""
        SELECT p.name, SUM(o.quantity) as total_sold
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.status='completed'
        GROUP BY p.id, p.name
        ORDER BY total_sold DESC LIMIT 1
    """)
    row = cursor.fetchone()
    stats['Top Product'] = f"{row['name']} ({row['total_sold']})" if row else "N/A"

    # Richest user
    cursor.execute("SELECT name, cash_balance FROM users ORDER BY cash_balance DESC LIMIT 1")
    row = cursor.fetchone()
    stats['Richest User'] = f"{row['name']} (₹{row['cash_balance']:.2f})" if row else "N/A"

    # Avg order value
    cursor.execute("SELECT AVG(total_price) AS avg_order FROM orders WHERE status='completed'")
    stats['Avg Order Value'] = f"₹{float(cursor.fetchone()['avg_order'] or 0):.2f}"

    # Total stock
    cursor.execute("SELECT SUM(stock) AS total_stock FROM products")
    stats['Total Stock'] = cursor.fetchone()['total_stock']

    # Most expensive product
    cursor.execute("SELECT name, price FROM products ORDER BY price DESC LIMIT 1")
    row = cursor.fetchone()
    stats['Most Expensive Product'] = f"{row['name']} (₹{row['price']:.2f})" if row else "N/A"

    # Least stock product
    cursor.execute("SELECT name, stock FROM products ORDER BY stock ASC LIMIT 1")
    row = cursor.fetchone()
    stats['Low Stock Product'] = f"{row['name']} ({row['stock']})" if row else "N/A"

    # Total categories
    cursor.execute("SELECT COUNT(DISTINCT category) AS categories FROM products")
    stats['Total Categories'] = cursor.fetchone()['categories']

    # Orders this month
    cursor.execute("SELECT COUNT(*) AS this_month FROM orders WHERE MONTH(created_at)=MONTH(NOW()) AND YEAR(created_at)=YEAR(NOW())")
    stats['Orders This Month'] = cursor.fetchone()['this_month']

    cursor.close()
    conn.close()

    return render_template("dashboard.html", stats=stats)

@app.route('/stat/<string:stat_name>')
def stat_detail(stat_name):
    """Renders a detail page for a specific statistic."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    rows = []
    columns = []

    # Base query for joining orders with users and products
    orders_query = """
        SELECT o.id, u.name as user, p.name as product, o.quantity, o.total_price, o.status, o.created_at
        FROM orders o
        JOIN users u ON o.user_id=u.id
        JOIN products p ON o.product_id=p.id
    """

    if stat_name == "users":
        cursor.execute("SELECT id, name, email, cash_balance, created_at FROM users ORDER BY created_at DESC")
    elif stat_name == "products":
        cursor.execute("SELECT id, name, price, stock, category FROM products ORDER BY name")
    elif stat_name == "orders":
        cursor.execute(f"{orders_query} ORDER BY o.created_at DESC")
    elif stat_name == "completed-orders":
        cursor.execute(f"{orders_query} WHERE o.status='completed' ORDER BY o.created_at DESC")
    elif stat_name == "pending-orders":
        cursor.execute(f"{orders_query} WHERE o.status='pending' ORDER BY o.created_at DESC")
    elif stat_name == "cancelled-orders":
        cursor.execute(f"{orders_query} WHERE o.status='cancelled' ORDER BY o.created_at DESC")
    elif stat_name == "top-products":
        cursor.execute("""
            SELECT p.name, p.category, SUM(o.quantity) as total_sold, SUM(o.total_price) as total_revenue
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.status='completed'
            GROUP BY p.id, p.name, p.category
            ORDER BY total_sold DESC
        """)
    elif stat_name == "richest-users":
        cursor.execute("SELECT id, name, email, cash_balance FROM users ORDER BY cash_balance DESC")
    elif stat_name == "low-stock-products":
        cursor.execute("SELECT id, name, stock, price, category FROM products ORDER BY stock ASC")
    elif stat_name == "most-expensive-products":
        cursor.execute("SELECT id, name, price, stock, category FROM products ORDER BY price DESC")
    elif stat_name == "categories":
        cursor.execute("""
            SELECT category, COUNT(*) as product_count, SUM(stock) as total_stock
            FROM products
            GROUP BY category
            ORDER BY product_count DESC
        """)
    elif stat_name == "monthly-orders":
        cursor.execute(f"{orders_query} WHERE MONTH(o.created_at)=MONTH(NOW()) AND YEAR(o.created_at)=YEAR(NOW()) ORDER BY o.created_at DESC")
    
    rows = cursor.fetchall()
    if rows:
        columns = rows[0].keys()

    cursor.close()
    conn.close()

    return render_template("detail.html", stat_name=stat_name.replace('-', ' ').title(), columns=columns, rows=rows)

if __name__ == "__main__":
    # Run inside container on port 5000
    app.run(debug=True, host="0.0.0.0", port=5000)
