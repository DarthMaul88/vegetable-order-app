from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import json
import os # To get environment variables for database connection

app = Flask(__name__)
CORS(app) # Enable CORS for all routes (for development)

# Database configuration (for local SQLite or remote PostgreSQL)
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///orders.db') # Use env var for prod, sqlite for local

def get_db_connection():
    if DATABASE_URL.startswith('sqlite:///'):
        db_path = DATABASE_URL.replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Allows accessing rows by column name
        return conn
    else:
        # This part will be for PostgreSQL (Supabase)
        # You'll use a library like psycopg2 or SQLAlchemy
        # For now, keep it simple for SQLite testing
        raise NotImplementedError("PostgreSQL connection not implemented yet for this example.")


def init_db():
    # This function initializes the database schema
    # It's called when the app starts
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL.startswith('sqlite:///'):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                items TEXT NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
        ''')
    # For PostgreSQL, you'd use a different schema creation (e.g., via migrations or direct SQL)
    conn.commit()
    conn.close()

@app.route('/api/orders', methods=['POST'])
def place_order():
    data = request.json
    customer_name = data.get('customer', {}).get('name')
    customer_email = data.get('customer', {}).get('email')
    items = data.get('items')

    if not all([customer_name, customer_email, items]):
        return jsonify({"message": "Missing order data"}), 400

    items_json = json.dumps(items)
    order_date = datetime.now().isoformat()
    status = "pending"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (customer_name, customer_email, items, order_date, status) VALUES (?, ?, ?, ?, ?)",
        (customer_name, customer_email, items_json, order_date, status)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # --- REAL NOTIFICATION LOGIC GOES HERE ---
    # For production, use a service like SendGrid, Mailgun, etc. (often have free tiers)
    print(f"NEW ORDER RECEIVED! Order ID: {order_id} from {customer_name} ({customer_email})")
    # Example placeholder for email (requires a real email sending library and configuration)
    # try:
    #     send_email_notification(customer_email, order_id, items)
    # except Exception as e:
    #     print(f"Failed to send email notification: {e}")
    # ------------------------------------------

    return jsonify({"message": "Order placed successfully", "orderId": order_id}), 201

@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, customer_email, items, order_date, status FROM orders ORDER BY order_date DESC")
    orders_raw = cursor.fetchall()
    conn.close()

    orders = []
    for row in orders_raw:
        order_dict = {
            "id": row['id'],
            "customer_name": row['customer_name'],
            "customer_email": row['customer_email'],
            "items": json.loads(row['items']),
            "order_date": row['order_date'],
            "status": row['status']
        }
        orders.append(order_dict)
    return jsonify(orders)

if __name__ == '__main__':
    init_db() # Initialize the database (creates 'orders.db' file if using SQLite)
    app.run(debug=True, port=5000) # Run locally on port 5000