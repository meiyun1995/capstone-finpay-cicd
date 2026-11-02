"""API behavior tests using Flask's in-process test client."""

from app import app
import pytest


def test_health():
    """Verify the health endpoint returns HTTP 200 and its liveness payload."""
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


@pytest.mark.parametrize("amount", [0.01, 150.50, 10000])
def test_validate_valid_transaction(amount):
    """Accept positive amounts including the maximum permitted amount."""
    app.config["TESTING"] = True
    client = app.test_client()
    payload = {
        "transaction_id": "txn-001",
        "account_id": "acct-001",
        "amount": amount,
        "currency": "SGD",
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    output = response.get_json()
    assert output["valid"] is True
    assert output["transaction_id"] == "txn-001"


@pytest.mark.parametrize("amount", [0, -10, 10000.01])
def test_validate_out_of_range_amount(amount):
    """Reject zero, negative amounts, and amounts above the limit."""
    app.config["TESTING"] = True
    client = app.test_client()
    payload = {
        "transaction_id": "txn-001",
        "account_id": "acct-001",
        "amount": amount,
        "currency": "SGD",
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 400
    output = response.get_json()
    assert output["valid"] is False
    assert "amount: must be greater than 0 and no more than 10000" in output["errors"]


@pytest.mark.parametrize("amount", ["150", True, False, None, [], {}])
def test_validate_invalid_amount_type(amount):
    """Reject nonnumeric amounts and booleans with exactly one type error."""
    app.config["TESTING"] = True
    client = app.test_client()
    payload = {
        "transaction_id": "txn-001",
        "account_id": "acct-001",
        "amount": amount,
        "currency": "SGD",
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 400
    output = response.get_json()
    assert output["valid"] is False
    assert "amount: is not of int or float type" in output["errors"]
    assert len(output["errors"]) == 1


@pytest.mark.parametrize("currency", ["SGD", "USD", "EUR"])
def test_valid_currencies(currency):
    """Accept each supported uppercase currency code."""
    app.config["TESTING"] = True
    client = app.test_client()
    payload = {
        "transaction_id": "txn-001",
        "account_id": "acct-001",
        "amount": 150.5,
        "currency": currency,
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    output = response.get_json()
    assert output["valid"] is True


@pytest.mark.parametrize("currency", ["GBP", "sgd", "", 123, None])
def test_invalid_currencies(currency):
    """Reject unsupported, lowercase, blank, and non-string currencies."""
    app.config["TESTING"] = True
    client = app.test_client()
    payload = {
        "transaction_id": "txn-001",
        "account_id": "acct-001",
        "amount": 150.5,
        "currency": currency,
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 400
    output = response.get_json()
    assert output["valid"] is False
    assert "currency: currency should only be in SGD, USD or EUR" in output["errors"]


@pytest.mark.parametrize(
    "field", ["transaction_id", "account_id", "amount", "currency"]
)
def test_validate_missing_field(field):
    """Reject each missing required field with one field-specific error."""
    app.config["TESTING"] = True
    client = app.test_client()
    payload = {
        "transaction_id": "txn-001",
        "account_id": "acct-001",
        "amount": 150.5,
        "currency": "SGD",
    }
    del payload[field]
    response = client.post("/validate", json=payload)
    assert response.status_code == 400
    output = response.get_json()
    assert len(output["errors"]) == 1
    assert output["errors"][0].startswith(f"{field}:")


@pytest.mark.parametrize("field", ["transaction_id", "account_id"])
@pytest.mark.parametrize("value", ["", "   ", 123, None])
def test_validate_invalid_identifier(field, value):
    """Reject blank or non-string values for either identifier."""
    app.config["TESTING"] = True
    client = app.test_client()
    payload = {
        "transaction_id": "txn-001",
        "account_id": "acct-001",
        "amount": 150.5,
        "currency": "SGD",
    }
    payload[field] = value
    response = client.post("/validate", json=payload)
    assert response.status_code == 400
    output = response.get_json()
    assert len(output["errors"]) == 1
    if isinstance(value, str):
        assert f"{field}: Is an empty string" in output["errors"]
    else:
        assert f"{field}: Is not of data type string" in output["errors"]


def test_wrong_content_type_request():
    """Return HTTP 415 when the request uses a non-JSON content type."""
    app.config["TESTING"] = True
    client = app.test_client()
    data = "hello"
    response = client.post("/validate", data=data, content_type="text/plain")
    assert response.status_code == 415
    output = response.get_json()
    assert "Unsupported Media Type" in output["error"]


def test_malformed_json_request():
    """Return HTTP 400 when a JSON request contains incomplete JSON."""
    app.config["TESTING"] = True
    client = app.test_client()
    data = '{"amount":'
    response = client.post("/validate", data=data, content_type="application/json")
    assert response.status_code == 400
    output = response.get_json()
    assert "Bad Request" in output["error"]


@pytest.mark.parametrize("raw_body", ["[]", "null", '"hello"', "123"])
def test_valid_json_bad_request(raw_body):
    """Reject valid JSON values that are not objects with HTTP 400."""
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.post("/validate", data=raw_body, content_type="application/json")
    assert response.status_code == 400
    output = response.get_json()
    assert "Bad Request" in output["error"]
