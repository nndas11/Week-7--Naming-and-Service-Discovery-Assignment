import argparse
from typing import Dict, List

from flask import Flask, jsonify, request

from service_common import ServiceRegistrar, build_service_address, install_signal_handlers


def create_app() -> Flask:
    app = Flask(__name__)
    cart_store: Dict[str, List[dict]] = {}

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy", "service": "cart-service"})

    @app.post("/cart/add")
    def add_to_cart():
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        item_id = data.get("item_id")
        quantity = int(data.get("quantity", 1))

        if not user_id or not item_id:
            return jsonify({"status": "error", "message": "user_id and item_id required"}), 400

        cart_store.setdefault(user_id, []).append(
            {"item_id": item_id, "quantity": quantity}
        )

        return jsonify({"status": "ok", "user_id": user_id, "items": cart_store[user_id]})

    @app.get("/cart/<user_id>")
    def get_cart(user_id: str):
        return jsonify({"status": "ok", "user_id": user_id, "items": cart_store.get(user_id, [])})

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Cart Service")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--registry", default="http://localhost:5001")
    parser.add_argument("--address", default=None)
    args = parser.parse_args()

    address = build_service_address(args.port, args.address)
    registrar = ServiceRegistrar("cart-service", address, args.registry)
    install_signal_handlers(registrar)
    registrar.start()

    app = create_app()
    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
