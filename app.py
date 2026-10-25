from flask import Flask, request, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return {"status": "ok"}, 200


@app.post("/validate")
def validate_transaction():
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
            response = jsonify({"message": "Transaction received"})
            return response, 200

    else:
        response = jsonify(
            {"error": "Unsupported Media Type", "message": "Expected application/json"}
        )
        return response, 415
