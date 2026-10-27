# FinSecure Pay — Transaction Validation API

A small Python Flask application for an end-to-end CI/CD assignment. FinSecure
Pay needs a fast, repeatable, reliable way to deploy a transaction validation
API with minimal manual intervention.

The application validates transaction payloads and exposes a health endpoint.
It does not transfer money, verify account existence, or store transactions.
The current stage includes the application and automated tests; CI/CD setup
is the next stage.

## Prerequisites and setup

Developed using **Python 3.12.13**. Install Python 3.12 and Git before starting.
Run these macOS/Linux commands from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If the virtual environment already exists, activate it and install dependencies.
`requirements.txt` includes Flask and pytest.

## Run locally

```bash
python -m flask --app app run --debug
```

The API is available at `http://127.0.0.1:5000`. This command uses Flask's
development server and debug mode for local development.

## Project structure

```text
app.py             Flask routes and payload validation
transaction.py     Transaction dataclass
tests/test_app.py  Automated API tests
requirements.txt   Pinned application and test dependencies
README.md          Setup, API usage, and testing instructions
```

## Validation rules

All four fields are required in the JSON object.

| Field            | Rule                                                           |
| ---------------- | -------------------------------------------------------------- |
| `transaction_id` | String containing at least one non-whitespace character        |
| `account_id`     | String containing at least one non-whitespace character        |
| `amount`         | Finite integer or float, greater than 0 and no more than 10000 |
| `currency`       | Exactly `SGD`, `USD`, or `EUR`                                 |

Booleans and numeric strings are not valid amounts. Currency codes are
case-sensitive. Identifiers are checked using trimmed text, but their original
values are preserved. Additional fields are ignored. Validation collects errors
across fields rather than stopping at the first error.

These rules are assignment-specific. There is no decimal-place restriction,
currency conversion, duplicate transaction detection, or account lookup.
The `Transaction` dataclass holds validated data; its type annotations do not
perform validation themselves.

## API endpoints

### GET /health

Checks that the API can respond. It does not check external dependencies.

```bash
curl -i http://127.0.0.1:5000/health
```

HTTP **200**:

```json
{ "status": "ok" }
```

### POST /validate

Send a JSON object with `Content-Type: application/json`.

```bash
curl -i http://127.0.0.1:5000/validate \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn-001","account_id":"acct-001","amount":150.50,"currency":"SGD"}'
```

HTTP **200**:

```json
{
  "valid": true,
  "transaction_id": "txn-001",
  "message": "Transaction received"
}
```

Success confirms validation only; it does not mean a payment was processed.

#### Failed field validation

```bash
curl -i http://127.0.0.1:5000/validate \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn-001","account_id":"acct-001","amount":0,"currency":"SGD"}'
```

HTTP **400**:

```json
{
  "valid": false,
  "errors": ["amount: must be greater than 0 and no more than 10000"]
}
```

#### Malformed JSON or a non-object body

Arrays, strings, numbers, booleans, and `null` are not transaction objects.
Malformed JSON and non-object JSON bodies return HTTP **400**:

```json
{
  "error": "Bad Request",
  "message": "Malformed or invalid JSON payload provided."
}
```

#### Unsupported content type

A non-JSON content type returns HTTP **415**:

```json
{
  "error": "Unsupported Media Type",
  "message": "Expected application/json"
}
```

## Automated tests

With the virtual environment active, run from the repository root:

```bash
python -m pytest -v
```

Tests use Flask's in-process test client, so no running server is required.
Using `python -m pytest` from the project root also makes `app.py` importable.

The current suite contains 39 test cases covering:

- Health response.
- Valid amounts, including 0.01 and the upper boundary of 10000.
- Zero, negative, and above-limit amounts.
- Invalid amount types, including booleans and null.
- Supported and unsupported currencies.
- Missing required fields and invalid identifiers.
- Incorrect content type, malformed JSON, and non-object JSON bodies.

The suite does not yet directly test non-finite amounts or aggregation of
multiple field errors in one request.

## Development workflow

Work on a feature branch, run the tests, and review changes before committing.
Push the feature branch and open a pull request into `main`. The next assignment
stage is to configure CI to run the test suite automatically and then add the
deployment pipeline.
