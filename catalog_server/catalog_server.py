
from contextlib import contextmanager
from flask import Flask, jsonify, request
import sqlite3
import os
import math

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.getenv(
    "CATALOG_DB_PATH",
    os.path.join(BASE_DIR, "catalog.db")
)


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    if not os.path.exists(DB_FILE):
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL
                )
            """)

            initial_books = [
                ("How to get a good grade in DOS in 40 minutes a day",
                 "distributed systems", 40.0, 10),
                ("RPCs for Noobs", "distributed systems", 50.0, 5),
                ("Xen and the Art of Surviving Undergraduate School",
                 "undergraduate school", 30.0, 8),
                ("Cooking for the Impatient Undergrad",
                 "undergraduate school", 25.0, 12)
            ]

            cursor.executemany("""
                INSERT INTO books (title, topic, price, quantity)
                VALUES (?, ?, ?, ?)
            """, initial_books)

@app.route('/search/<path:topic>', methods=['GET'])
def search_books(topic):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title
            FROM books
            WHERE LOWER(topic) = LOWER(?)
        """, (topic.strip(),))

        rows = cursor.fetchall()

    items = [{"id": row[0], "title": row[1]} for row in rows]
    return jsonify(items)


@app.route('/info/<int:item_number>', methods=['GET'])
def book_info(item_number):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title, quantity, price
            FROM books
            WHERE id = ?
        """, (item_number,))

        row = cursor.fetchone()

    if row:
        return jsonify({
            "title": row[0],
            "quantity": row[1],
            "price": row[2]
        })

    return jsonify({"error": "Item not found"}), 404


@app.route('/update', methods=['PUT', 'POST'])
def update_catalog():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    item_id = data.get('id')
    price = data.get('price')
    quantity_change = data.get('quantity_change', 0)

    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({"error": "A valid book ID is required"}), 400

    if isinstance(quantity_change, bool) or not isinstance(quantity_change, int):
        return jsonify({"error": "quantity_change must be an integer"}), 400

    if price is not None:
        if (isinstance(price, bool)
                or not isinstance(price, (int, float))
                or not math.isfinite(price)
                or price <= 0):
            return jsonify({"error": "Price must be a positive number"}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM books WHERE id = ?", (item_id,))
        if cursor.fetchone() is None:
            return jsonify({"error": "Item not found"}), 404

        if price is not None:
            cursor.execute(
                "UPDATE books SET price = ? WHERE id = ?",
                (price, item_id)
            )

        if quantity_change != 0:
            cursor.execute("""
                UPDATE books
                SET quantity = quantity + ?
                WHERE id = ? AND quantity + ? >= 0
            """, (quantity_change, item_id, quantity_change))

            if cursor.rowcount == 0:
                return jsonify({"error": "Quantity cannot become negative"}), 400

    return jsonify({
        "status": "success",
        "message": "Catalog updated successfully"
    })


@app.route('/purchase', methods=['POST'])
def purchase_book():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    item_id = data.get('id')
    quantity = data.get('quantity')

    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({"error": "A valid book ID is required"}), 400

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "Quantity must be a positive integer"}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # This single conditional UPDATE prevents overselling.
        cursor.execute("""
            UPDATE books
            SET quantity = quantity - ?
            WHERE id = ? AND quantity >= ?
        """, (quantity, item_id, quantity))

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM books WHERE id = ?",
                (item_id,)
            )

            if cursor.fetchone() is None:
                return jsonify({"error": "Item not found"}), 404

            return jsonify({
                "error": "Out of stock or insufficient quantity"
            }), 400

        cursor.execute("""
            SELECT title, quantity
            FROM books
            WHERE id = ?
        """, (item_id,))

        title, remaining_quantity = cursor.fetchone()

    return jsonify({
        "status": "success",
        "title": title,
        "quantity_remaining": remaining_quantity,
        "message": "Inventory updated successfully"
    }), 200


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001)
