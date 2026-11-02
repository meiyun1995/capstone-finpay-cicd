"""Flask API for health checks and transaction payload validation."""

import math

from flask import Flask, request, jsonify
from transaction import Transaction

app = Flask(__name__)


def validate_transaction_payload(payload):
    """Return all field validation errors for a parsed transaction dictionary.

    Identifiers must be nonblank strings. Amounts must be finite numbers in
    (0, 10000], excluding booleans. Currency must be SGD, USD, or EUR.
    Missing fields are invalid; extra fields are ignored. The payload is
    neither modified nor coerced. An empty list indicates valid input.
    """
    amount = payload.get("amount")
    currency = payload.get("currency")

    errors = []
    for field in ("transaction_id", "account_id"):
        val = payload.get(field)
        if not isinstance(val, str):
            errors.append(f"{field}: Is not of data type string")
        else:
            if not val.strip():
                errors.append(f"{field}: Is an empty string")

    # amount check
    if isinstance(amount, bool):
        errors.append(f"amount: is not of int or float type")

    elif not isinstance(amount, (int, float)):
        errors.append(f"amount: is not of int or float type")

    else:
        if isinstance(amount, float) and not math.isfinite(amount):
            errors.append(f"amount: must be finite")
        elif amount <= 0 or amount > 10000:
            errors.append(f"amount: must be greater than 0 and no more than 10000")

    # currency check
    if currency not in ["SGD", "USD", "EUR"]:
        errors.append("currency: currency should only be in SGD, USD or EUR")
    return errors


@app.get("/health")
def health():
    """Return a JSON liveness status and HTTP 200 without checking dependencies."""
    return {"status": "ok"}, 200


@app.post("/validate")
def validate_transaction():
    """Validate a JSON transaction and return its identifier on success.

    Return HTTP 415 for a non-JSON content type, HTTP 400 for malformed JSON,
    a non-object body, or invalid fields, and HTTP 200 for valid input.
    Successful validation creates a Transaction but does not persist it or
    execute a payment.
    """
    if request.is_json:
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            response = jsonify(
                {
                    "error": "Bad Request",
                    "message": "Malformed or invalid JSON payload provided.",
                }
            )
            return response, 400
        else:
            errors = validate_transaction_payload(body)
            if errors:
                response = jsonify({"valid": False, "errors": errors})
                return response, 400
            else:
                transaction = Transaction(
                    transaction_id=body.get("transaction_id"),
                    account_id=body.get("account_id"),
                    amount=body.get("amount"),
                    currency=body.get("currency"),
                )
                response = jsonify(
                    {
                        "valid": True,
                        "transaction_id": transaction.transaction_id,
                        "message": "Transaction received",
                    }
                )
                return response, 200

    else:
        response = jsonify(
            {"error": "Unsupported Media Type", "message": "Expected application/json"}
        )
        return response, 415
