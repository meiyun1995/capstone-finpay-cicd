# FinSecure Pay — Transaction Validation API

A small Python Flask application for an end-to-end CI/CD assignment. FinSecure
Pay needs a fast, repeatable, reliable way to deploy a transaction validation
API with minimal manual intervention.

The application validates transaction payloads and exposes a health endpoint.
It does not transfer money, verify account existence, or store transactions.
The project includes automated tests, a versioned Docker image, and a managed
Azure Kubernetes Service deployment. CI/CD automation is the next stage.

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
k8s/               ConfigMap, Deployment, and Service manifests
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

## Task 3: Kubernetes and cloud deployment

### Cloud design

The application was deployed to Azure Kubernetes Service (AKS), using the
public Docker Hub image `cmyaa/finsecure-pay:v1.0.0`.

| Setting | Configuration |
| --- | --- |
| Resource group | `rg-finsecure-pay` |
| Cluster | `aks-finsecure-pay` |
| Region | East Asia (`eastasia`) |
| Kubernetes version | `1.36.5` |
| AKS tier | Free |
| Node pool | `systempool` |
| Nodes | One `Standard_D4s_v5` Linux AMD64 node |
| Application replicas | Two |
| Networking | Azure CNI Overlay and Standard Load Balancer |

East Asia was selected because the chosen VM size had no listed subscription
restrictions there, while it was restricted in Southeast Asia. One node uses
the subscription's available four-vCPU regional and DSv5-family quotas.
The Free AKS tier suits this learning deployment; compute, disks, and networking
still incur charges.

Two application pods allow Kubernetes to replace an individual deleted pod
while retaining another replica. Both pods share the same node, so this design
does not provide node-level high availability. A production design would spread
replicas across multiple nodes and, where appropriate, availability zones.

### Kubernetes manifests

| File | Purpose |
| --- | --- |
| [configmap.yaml](k8s/configmap.yaml) | Supplies non-sensitive Python runtime environment variables |
| [deployment.yaml](k8s/deployment.yaml) | Defines two replicas, the versioned image, probes, and resource settings |
| [service.yaml](k8s/service.yaml) | Exposes the application through a LoadBalancer Service |

The Deployment loads `PYTHONUNBUFFERED="1"` and
`PYTHONDONTWRITEBYTECODE="1"` from `finsecure-pay-config` using `envFrom`.
The public image does not require private registry credentials. No credentials
are included in these manifests.

Each pod requests `100m` CPU and `128Mi` memory, with limits of `500m` CPU and
`256Mi` memory. These are initial resource settings for the small validation API.

Both probes use HTTP `/health` on port `8000`:

| Probe | Initial delay | Interval | Timeout | Failure threshold |
| --- | --- | --- | --- | --- |
| Readiness | 5 seconds | 5 seconds | 2 seconds | 3 |
| Liveness | 15 seconds | 10 seconds | 2 seconds | 3 |

Readiness controls whether a pod receives Service traffic. Repeated liveness
failures trigger a container restart. The longer liveness delay allows the
application time to start before restart checks begin.

### Deploy and verify

Connect to the existing cluster and confirm the selected context:

```bash
az aks get-credentials --resource-group rg-finsecure-pay --name aks-finsecure-pay
kubectl config current-context
kubectl get nodes -o wide
```

Ensure the context is `aks-finsecure-pay`, then validate and apply the manifests:

```bash
kubectl apply --dry-run=server -f k8s/
kubectl apply -f k8s/
kubectl rollout status deployment/finsecure-pay --timeout=180s
kubectl get pods -l app=finsecure-pay -o wide
kubectl get service finsecure-pay-service
```

The expected application state is two pods showing `1/1` Ready and `Running`.
To inspect the environment variables supplied to a running container:

```bash
kubectl exec deployment/finsecure-pay -- printenv PYTHONUNBUFFERED PYTHONDONTWRITEBYTECODE
```

### External access

The Service selects pods labelled `app: finsecure-pay` and forwards incoming
TCP traffic from port `80` to Gunicorn on container port `8000`.

```text
Client → Azure external IP:80 → Service → ready pod:8000 → Flask
```

The external IP observed during deployment was `57.158.99.15`:

```bash
curl -i --max-time 10 http://57.158.99.15/health
```

The request returned HTTP `200 OK` from Gunicorn with:

```json
{"status":"ok"}
```

The IP may change if the Service or cluster is recreated. Retrieve its current
address with `kubectl get service finsecure-pay-service`.

### Automatic pod recovery demonstration

Before deletion, both application pods were `1/1 Running`. The demonstration
deleted `finsecure-pay-7dff58f77-gc728` while watching the Deployment's pods:

```bash
kubectl get pods -l app=finsecure-pay -o wide
kubectl get pods -l app=finsecure-pay -w
```

In a separate terminal, delete one selected pod using its current name:

```bash
kubectl delete pod POD_NAME
```

The observed replacement, `finsecure-pay-7dff58f77-txm8h`, progressed through
`Pending`, `ContainerCreating`, and `Running`, reaching `1/1` Ready at approximately
seven seconds of age. The Deployment's ReplicaSet automatically restored the
desired replica count without manually creating a replacement pod.

Pod names change between deployments. Capture the final state using:

```bash
kubectl get pods -l app=finsecure-pay -o wide
```

This demonstrates automatic pod replacement. It does not establish a guarantee
of uninterrupted requests or recovery from failure of the shared node.

### Submission evidence

Save the following with the assignment submission:

- ConfigMap, Deployment, and Service manifests, including both health probes.
- AKS node output showing the managed cloud node in `Ready` state.
- Pod output showing two ready application replicas.
- Service output and a successful external `/health` response.
- Before, during, and after pod output demonstrating automatic replacement.

Retain the single-node limitation in the design explanation. After completing
the cloud tasks, remove the dedicated assignment resources and verify that
associated billable resources have also been removed.

## Development workflow

Work on a feature branch, run the tests, and review changes before committing.
Push the feature branch and open a pull request into `main`. The next assignment
stage is to configure CI to run the test suite automatically and then add the
deployment pipeline.
