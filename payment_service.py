import argparse
import time
import uuid
from typing import Dict

from flask import Flask, jsonify, request

from service_common import ServiceRegistrar, build_service_address, install_signal_handlers


def create_app() -> Flask:
    app = Flask(__name__)
    payments: Dict[str, dict] = {}
    idempotency_store: Dict[str, dict] = {}

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy", "service": "payment-service"})

    @app.post("/payment/charge")
    def charge():
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        amount = data.get("amount")
        method = data.get("method", "card")
        idempotency_key = data.get("idempotency_key") or request.headers.get("Idempotency-Key")

        if not user_id or amount is None:
            return jsonify({"status": "error", "message": "user_id and amount required"}), 400

        if idempotency_key and idempotency_key in idempotency_store:
            previous = idempotency_store[idempotency_key]
            return jsonify({"status": "ok", "payment": previous, "idempotent": True})

        payment_id = str(uuid.uuid4())
        payments[payment_id] = {
            "payment_id": payment_id,
            "user_id": user_id,
            "amount": amount,
            "method": method,
            "status": "approved",
            "timestamp": int(time.time()),
        }
        if idempotency_key:
            idempotency_store[idempotency_key] = payments[payment_id]

        return jsonify({"status": "ok", "payment": payments[payment_id]})

    @app.get("/payment/<payment_id>")
    def payment_status(payment_id: str):
        payment = payments.get(payment_id)
        if not payment:
            return jsonify({"status": "not_found", "payment_id": payment_id}), 404
        return jsonify({"status": "ok", "payment": payment})

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Payment Service")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--registry", default="http://localhost:5001")
    parser.add_argument("--address", default=None)
    args = parser.parse_args()

    address = build_service_address(args.port, args.address)
    registrar = ServiceRegistrar("payment-service", address, args.registry)
    install_signal_handlers(registrar)
    registrar.start()

    app = create_app()
    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
