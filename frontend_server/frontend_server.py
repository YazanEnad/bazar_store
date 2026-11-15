from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

# Service URLs: localhost for local development,
# Docker service names will be configured later.
CATALOG_SERVER_URL = os.getenv(
    "CATALOG_SERVER_URL",
    "http://127.0.0.1:5001"
).rstrip("/")

ORDER_SERVER_URL = os.getenv(
    "ORDER_SERVER_URL",
    "http://127.0.0.1:5002"
).rstrip("/")


def forward_request(method, url, **kwargs):
    """Forward a request and return the downstream response."""

    try:
        response = requests.request(
            method,
            url,
            timeout=5,
            **kwargs
        )

        try:
            result = response.json()
            return jsonify(result), response.status_code
        except ValueError:
            return jsonify({
                "error": "Invalid response from downstream service",
                "details": response.text
            }), 502

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Downstream service request timed out"
        }), 504

    except requests.exceptions.RequestException:
        app.logger.exception("Could not connect to downstream service")
        return jsonify({
            "error": "Could not connect to downstream service"
        }), 502


@app.route('/search/<path:topic>', methods=['GET'])
def search_books(topic):
    return forward_request(
        "GET",
        f"{CATALOG_SERVER_URL}/search/{topic}"
    )


@app.route('/info/<int:item_id>', methods=['GET'])
def get_book_info(item_id):
    return forward_request(
        "GET",
        f"{CATALOG_SERVER_URL}/info/{item_id}"
    )


@app.route('/order', methods=['POST'])
def place_order():
    data = request.get_json(silent=True)

    return forward_request(
        "POST",
        f"{ORDER_SERVER_URL}/order",
        json=data
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)