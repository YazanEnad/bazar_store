
from flask import Flask, jsonify, request
import requests
import sqlite3
import os

app = Flask(__name__)

# Use localhost during local development.
# Docker Compose will override this with http://catalog:5001.
CATALOG_SERVER_URL = os.getenv(
    "CATALOG_SERVER_URL",
    "http://127.0.0.1:5001"
).rstrip("/")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.getenv(
    "ORDER_DB_PATH",
    os.path.join(BASE_DIR, "orders.db")
)


def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()


@app.route('/order', methods=['POST'])
def place_order():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON object is required"}), 400

    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)

    # Validate input. Booleans are rejected even though bool is a Python int.
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({"error": "item_id must be a positive integer"}), 400

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "quantity must be a positive integer"}), 400

    try:
        # Ask Catalog to check and decrease stock atomically.
        catalog_response = requests.post(
            f"{CATALOG_SERVER_URL}/purchase",
            json={
                "id": item_id,
                "quantity": quantity
            },
            timeout=5
        )

        if catalog_response.status_code in (400, 404):
            return jsonify(catalog_response.json()), catalog_response.status_code

        if catalog_response.status_code != 200:
            return jsonify({"error": "Catalog Server failed to process the purchase"}), 502

        purchase_info = catalog_response.json()
        book_title = purchase_info['title']

        # Save the successful order.
        conn = sqlite3.connect(DB_FILE, timeout=10)

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (item_id, quantity, status)
                VALUES (?, ?, ?)
                """,
                (item_id, quantity, "SUCCESS")
            )
            conn.commit()
        finally:
            conn.close()

        return jsonify({
            "status": "success",
            "message": f"Successfully ordered {quantity} copy/copies of '{book_title}'"
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({"error": "Catalog Server request timed out"}), 504

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": f"Could not connect to Catalog Server: {str(e)}"
        }), 502

    except (sqlite3.Error, KeyError, ValueError) as e:
        app.logger.exception("Failed to save or process the order")
        return jsonify({"error": "Failed to process the order"}), 500


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5002)
