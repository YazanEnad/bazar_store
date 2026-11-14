from flask import Flask, jsonify, request
import requests
import sqlite3
import os

app = Flask(__name__)
CATALOG_SERVER_URL = "http://127.0.0.1:5001"
DB_FILE = "orders.db"

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                status TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

@app.route('/order', methods=['POST'])
def place_order():
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)

    try:
        catalog_response = requests.get(f"{CATALOG_SERVER_URL}/info/{item_id}")
        if catalog_response.status_code != 200:
            return jsonify({"error": "Item not found in catalog"}), 404
        
        book_info = catalog_response.json()
        current_stock = book_info['quantity']

        if current_stock < quantity:
            return jsonify({"error": "Out of stock or insufficient quantity"}), 400

        update_response = requests.put(f"{CATALOG_SERVER_URL}/update", json={
            "id": item_id,
            "quantity_change": -quantity
        })

        if update_response.status_code != 200:
            return jsonify({"error": "Failed to update catalog"}), 500

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (item_id, quantity, status) VALUES (?, ?, ?)", 
                       (item_id, quantity, "SUCCESS"))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success", 
            "message": f"Successfully ordered {quantity} copy/copies of '{book_info['title']}'"
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not connect to Catalog Server: {str(e)}"}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5002)