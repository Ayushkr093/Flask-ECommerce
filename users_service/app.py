from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mysql.connector
import os
import time

app = Flask(__name__)
app.secret_key = 'users-service-secret-key'

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
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                cash_balance DECIMAL(10,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    return redirect(url_for('list_users'))

@app.route('/users')
def list_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('list_users.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'danger')
        return render_template('list_users.html', users=[])

@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            cash_balance = float(request.form['cash_balance'])
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (name, email, cash_balance) VALUES (%s, %s, %s)',
                (name, email, cash_balance)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('User added successfully!', 'success')
            return redirect(url_for('list_users'))
            
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Error: Email already exists!', 'danger')
            else:
                flash(f'Error adding user: {str(err)}', 'danger')
        except ValueError:
            flash('Error: Invalid cash balance format!', 'danger')
        except Exception as e:
            flash(f'Error adding user: {str(e)}', 'danger')
    
    return render_template('add_user.html')

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    try:
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            cash_balance = float(request.form['cash_balance'])
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET name = %s, email = %s, cash_balance = %s WHERE id = %s',
                (name, email, cash_balance, user_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('User updated successfully!', 'success')
            return redirect(url_for('list_users'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            flash('User not found!', 'danger')
            return redirect(url_for('list_users'))
        
        return render_template('edit_user.html', user=user)
        
    except mysql.connector.Error as err:
        if err.errno == 1062:
            flash('Error: Email already exists!', 'danger')
        else:
            flash(f'Error updating user: {str(err)}', 'danger')
        return redirect(url_for('list_users'))
    except ValueError:
        flash('Error: Invalid cash balance format!', 'danger')
        return redirect(url_for('list_users'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('list_users'))

@app.route('/users/delete/<int:user_id>')
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('list_users'))

# API Endpoints
@app.route('/api/users', methods=['GET'])
def api_get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, email, cash_balance FROM users')
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, email, cash_balance FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify(user)
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
def api_create_user():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['name', 'email', 'cash_balance']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO users (name, email, cash_balance) VALUES (%s, %s, %s)',
            (data['name'], data['email'], float(data['cash_balance']))
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({
            'id': user_id, 
            'message': 'User created successfully'
        }), 201
        
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({'error': 'Email already exists'}), 400
        return jsonify({'error': str(err)}), 400
    except ValueError:
        return jsonify({'error': 'Invalid cash balance format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['name', 'email', 'cash_balance']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        cursor.execute(
            'UPDATE users SET name = %s, email = %s, cash_balance = %s WHERE id = %s',
            (data['name'], data['email'], float(data['cash_balance']), user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'User updated successfully'})
        
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({'error': 'Email already exists'}), 400
        return jsonify({'error': str(err)}), 400
    except ValueError:
        return jsonify({'error': 'Invalid cash balance format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'User deleted successfully'})
        
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
        return jsonify({'status': 'healthy', 'service': 'users'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Initialize database when app starts
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)