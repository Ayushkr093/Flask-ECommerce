from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mysql.connector
import os
import time

app = Flask(__name__)
app.secret_key = 'products-service-secret-key'

# Database configuration
db_config = {
    'host': os.getenv('MYSQL_HOST', 'mysql'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'password'),
    'database': os.getenv('MYSQL_DB', 'microservices')
}

def get_db_connection():
    """Create and return a database connection with retry logic"""
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            conn = mysql.connector.connect(**db_config)
            return conn
        except mysql.connector.Error as err:
            print(f"Database connection attempt {attempt + 1} failed: {err}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise

def init_db():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                stock INT DEFAULT 0,
                category VARCHAR(50),
                image_url VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

@app.route('/')
def index():
    return redirect(url_for('list_products'))

@app.route('/products')
def list_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('list_products.html', products=products)
    except Exception as e:
        flash(f'Error loading products: {str(e)}', 'danger')
        return render_template('list_products.html', products=[])

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        try:
            name = request.form['name']
            description = request.form.get('description', '')
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            category = request.form.get('category', '')
            image_url = request.form.get('image_url', '')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO products (name, description, price, stock, category, image_url) VALUES (%s, %s, %s, %s, %s, %s)',
                (name, description, price, stock, category, image_url)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('list_products'))
            
        except mysql.connector.Error as err:
            flash(f'Error adding product: {str(err)}', 'danger')
        except ValueError:
            flash('Error: Invalid price or stock format!', 'danger')
        except Exception as e:
            flash(f'Error adding product: {str(e)}', 'danger')
    
    return render_template('add_product.html')

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    try:
        if request.method == 'POST':
            name = request.form['name']
            description = request.form.get('description', '')
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            category = request.form.get('category', '')
            image_url = request.form.get('image_url', '')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE products SET name = %s, description = %s, price = %s, 
                   stock = %s, category = %s, image_url = %s WHERE id = %s''',
                (name, description, price, stock, category, image_url, product_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('list_products'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not product:
            flash('Product not found!', 'danger')
            return redirect(url_for('list_products'))
        
        return render_template('edit_product.html', product=product)
        
    except mysql.connector.Error as err:
        flash(f'Error updating product: {str(err)}', 'danger')
        return redirect(url_for('list_products'))
    except ValueError:
        flash('Error: Invalid price or stock format!', 'danger')
        return redirect(url_for('list_products'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('list_products'))

@app.route('/products/delete/<int:product_id>')
def delete_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'danger')
    
    return redirect(url_for('list_products'))

# API Endpoints
@app.route('/api/products', methods=['GET'])
def api_get_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, description, price, stock, category, image_url FROM products')
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(products)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
def api_get_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, description, price, stock, category, image_url FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if product:
            return jsonify(product)
        return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def api_create_product():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['name', 'price', 'stock']):
            return jsonify({'error': 'Missing required fields: name, price, stock'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO products (name, description, price, stock, category, image_url) VALUES (%s, %s, %s, %s, %s, %s)',
            (data['name'], data.get('description', ''), float(data['price']), 
             int(data['stock']), data.get('category', ''), data.get('image_url', ''))
        )
        conn.commit()
        product_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({
            'id': product_id, 
            'message': 'Product created successfully'
        }), 201
        
    except ValueError:
        return jsonify({'error': 'Invalid price or stock format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT id FROM products WHERE id = %s', (product_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        update_fields = []
        update_values = []
        
        if 'name' in data:
            update_fields.append('name = %s')
            update_values.append(data['name'])
        if 'description' in data:
            update_fields.append('description = %s')
            update_values.append(data['description'])
        if 'price' in data:
            update_fields.append('price = %s')
            update_values.append(float(data['price']))
        if 'stock' in data:
            update_fields.append('stock = %s')
            update_values.append(int(data['stock']))
        if 'category' in data:
            update_fields.append('category = %s')
            update_values.append(data['category'])
        if 'image_url' in data:
            update_fields.append('image_url = %s')
            update_values.append(data['image_url'])
        
        if not update_fields:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        update_values.append(product_id)
        update_query = f'UPDATE products SET {", ".join(update_fields)} WHERE id = %s'
        
        cursor.execute(update_query, update_values)
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Product updated successfully'})
        
    except ValueError:
        return jsonify({'error': 'Invalid price or stock format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM products WHERE id = %s', (product_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Product deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        return jsonify({'status': 'healthy', 'service': 'products'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Initialize database when app starts
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)