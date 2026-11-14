from flask import Flask, jsonify, request
import sqlite3
import os

app = Flask(__name__)
DB_FILE = 'catalog.db'

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL
            )
        ''')
        
        initial_books = [
            ("How to get a good grade in DOS in 40 minutes a day", "distributed systems", 40.0, 10),
            ("RPCs for Noobs", "distributed systems", 50.0, 5),
            ("Xen and the Art of Surviving Undergraduate School", "undergraduate school", 30.0, 8),
            ("Cooking for the Impatient Undergrad", "undergraduate school", 25.0, 12)
        ]
        
        cursor.executemany("INSERT INTO books (title, topic, price, quantity) VALUES (?, ?, ?, ?)", initial_books)
        conn.commit()
        conn.close()

@app.route('/search/<path:topic>', methods=['GET'])
def search_books(topic):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM books WHERE LOWER(topic) = LOWER(?)", (topic.strip(),))
    rows = cursor.fetchall()
    conn.close()
    
    items = [{"id": row[0], "title": row[1]} for row in rows]
    return jsonify(items)

@app.route('/info/<int:item_number>', methods=['GET'])
def book_info(item_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT title, quantity, price FROM books WHERE id = ?", (item_number,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            "title": row[0],
            "quantity": row[1],
            "price": row[2]
        })
    return jsonify({"error": "Item not found"}), 404

@app.route('/update', methods=['PUT', 'POST'])
def update_catalog():
    data = request.get_json()
    item_id = data.get('id')
    price = data.get('price')
    quantity_change = data.get('quantity_change', 0)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if price is not None:
        cursor.execute("UPDATE books SET price = ? WHERE id = ?", (price, item_id))
    if quantity_change != 0:
        cursor.execute("UPDATE books SET quantity = quantity + ? WHERE id = ?", (quantity_change, item_id))
        
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Catalog updated successfully"})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001)