import os
import psycopg2
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---

# Set up CORS (Cross-Origin Resource Sharing)
# This allows your frontend (running on a different URL) to make requests to this backend.
# It gets the frontend's URL from an environment variable for security.
FRONTEND_URL = os.environ.get('FRONTEND_URL')
if FRONTEND_URL:
    # In production, only allow requests from your specific frontend URL
    CORS(app, resources={r"/api/*": {"origins": FRONTEND_URL}})
else:
    # For local development, you can allow all origins
    CORS(app, resources={r"/api/*": {"origins": "*"}})

# Get the database connection URL from environment variables.
# This is crucial for connecting to your Supabase/PostgreSQL database on Render.
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- Database Helper Functions ---

def get_db_connection():
    """Establishes a connection to the database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def create_tables():
    """
    Creates the 'vegetables' and 'orders' tables in the database if they don't already exist.
    This ensures your application can start without manual database setup.
    """
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Create vegetables table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS vegetables (
                        id VARCHAR(50) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        price INTEGER NOT NULL,
                        stock INTEGER NOT NULL,
                        available BOOLEAN NOT NULL
                    );
                """)
                # Create orders table
                # The 'items' column uses JSONB to store the list of ordered products.
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id SERIAL PRIMARY KEY,
                        customer_name VARCHAR(255) NOT NULL,
                        customer_mobile VARCHAR(20) NOT NULL,
                        customer_address TEXT NOT NULL,
                        items JSONB NOT NULL,
                        total_amount NUMERIC(10, 2) NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        payment_status VARCHAR(50) NOT NULL,
                        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()
            print("Tables created or already exist.")
        except Exception as e:
            print(f"Error creating tables: {e}")
        finally:
            conn.close()

# --- API Routes ---

# === VEGETABLE ROUTES ===

@app.route('/api/vegetables', methods=['GET'])
def get_vegetables():
    """Fetches all vegetables from the database."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, price, stock, available FROM vegetables ORDER BY name")
            vegetables_data = cur.fetchall()
        
        vegetables = [
            {"id": row[0], "name": row[1], "price": row[2], "stock": row[3], "available": row[4]}
            for row in vegetables_data
        ]
        return jsonify(vegetables)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/vegetables', methods=['POST'])
def add_vegetable():
    """Adds a new vegetable to the database."""
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO vegetables (id, name, price, stock, available) VALUES (%s, %s, %s, %s, %s)",
                (data['id'], data['name'], data['price'], data['stock'], data['available'])
            )
        conn.commit()
        return jsonify({"message": "Vegetable added successfully"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/vegetables/<string:veg_id>', methods=['PUT'])
def update_vegetable(veg_id):
    """Updates an existing vegetable's details."""
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE vegetables SET name=%s, price=%s, stock=%s, available=%s WHERE id=%s",
                (data['name'], data['price'], data['stock'], data['available'], veg_id)
            )
        conn.commit()
        return jsonify({"message": f"Vegetable {veg_id} updated successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/vegetables/<string:veg_id>', methods=['DELETE'])
def remove_vegetable(veg_id):
    """Deletes a vegetable from the database."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM vegetables WHERE id = %s", (veg_id,))
        conn.commit()
        return jsonify({"message": f"Vegetable {veg_id} removed successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# === ORDER ROUTES ===

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Fetches all orders, sorted by newest first."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, customer_name, customer_mobile, customer_address, items, total_amount, status, payment_status, timestamp FROM orders ORDER BY timestamp DESC")
            orders_data = cur.fetchall()
        
        orders = [
            {
                "id": row[0], "customer_name": row[1], "customer_mobile": row[2],
                "customer_address": row[3], "items": row[4], "total_amount": float(row[5]),
                "status": row[6], "payment_status": row[7], "timestamp": row[8].isoformat()
            }
            for row in orders_data
        ]
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_by_id(order_id):
    """Fetches a single order by its ID."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, customer_name, customer_mobile, customer_address, items, total_amount, status, payment_status, timestamp FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()
        
        if order:
            return jsonify({
                "id": order[0], "customer_name": order[1], "customer_mobile": order[2],
                "customer_address": order[3], "items": order[4], "total_amount": float(order[5]),
                "status": order[6], "payment_status": order[7], "timestamp": order[8].isoformat()
            })
        else:
            return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Creates a new order and updates vegetable stock."""
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cur:
            # Insert the new order and get its ID
            cur.execute(
                """
                INSERT INTO orders (customer_name, customer_mobile, customer_address, items, total_amount, status, payment_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (
                    data['customer_name'], data['customer_mobile'], data['customer_address'],
                    json.dumps(data['items']), data['total_amount'], data['status'], data['payment_status']
                )
            )
            order_id = cur.fetchone()[0]

            # Update stock for each item in the order
            for item in data['items']:
                # The weight is a string like "0.25kg", so we parse it
                weight_kg = float(item['weight'].replace('kg', ''))
                total_deduction = weight_kg * item['quantity']
                cur.execute(
                    "UPDATE vegetables SET stock = stock - %s WHERE id = %s AND stock >= %s",
                    (total_deduction, item['id'], total_deduction)
                )
                if cur.rowcount == 0:
                    # This check prevents selling more stock than available
                    raise ValueError(f"Not enough stock for {item['name']}")

        conn.commit()
        return jsonify({"message": "Order created successfully", "order_id": order_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
        
@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    """Updates an order's status or payment status."""
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        with conn.cursor() as cur:
            if 'status' in data:
                cur.execute("UPDATE orders SET status = %s WHERE id = %s", (data['status'], order_id))
            if 'payment_status' in data:
                cur.execute("UPDATE orders SET payment_status = %s WHERE id = %s", (data['payment_status'], order_id))
        
        conn.commit()
        return jsonify({"message": f"Order {order_id} updated successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# --- Main Execution ---

if __name__ == '__main__':
    # Create database tables if they don't exist
    create_tables()
    # Get the port number from the environment variable provided by Render. Default to 5000 for local dev.
    port = int(os.environ.get('PORT', 5000))
    # Run the app. 'host=0.0.0.0' is important for it to be accessible in a container.
    app.run(host='0.0.0.0', port=port)
