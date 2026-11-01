# FinSecure Pay — Transaction Validation API

A small Python Flask application for an end-to-end CI/CD assignment. FinSecure
Pay needs a fast, repeatable, reliable way to deploy a transaction validation
API with minimal manual intervention.

The application validates transaction payloads and exposes a health endpoint.
It does not transfer money, verify account existence, or store transactions.
The project includes automated tests, a versioned Docker image, and a managed
Azure Kubernetes Service deployment and a Jenkins pipeline that tests, scans,
packages, publishes, and deploys versioned application images.

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
sonar-project.properties  SonarQube analysis scope and gate polling
Jenkinsfile        Declarative CI/CD pipeline
jenkins/           Agent/test Dockerfiles and deployment access configuration
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

## Task 4: Jenkins CI/CD automation

### Jenkins architecture

Jenkins runs locally in Docker Desktop and deploys the application to the managed
AKS cluster from Task 3. The controller has zero build executors; pipeline steps
run on a dedicated agent.

| Component | Configuration |
| --- | --- |
| Controller | Container `jenkins`, image `jenkins/jenkins:2.580.2-jdk21` |
| Dashboard | `http://localhost:8081/`, bound to the Mac's loopback interface |
| Agent | Container and Jenkins node `finsecure-agent`, label `finsecure-agent`, one executor |
| Agent image | `finsecure-jenkins-agent:0.5`, built from [Dockerfile.agent](jenkins/Dockerfile.agent) |
| Agent connection | WebSocket to `http://jenkins:8080` on `jenkins-network` |
| Build engine | Container `jenkins-docker`, image `docker:29-dind` |
| Docker connection | TLS to `tcp://docker:2376`; engine port is not published to the host |
| Deployment target | `aks-finsecure-pay`, namespace `default` |

The agent runs as UID/GID 1000 (`jenkins`) and includes Git, Python, Docker CLI,
Buildx, and checksum-verified kubectl `v1.36.2`. Its Debian Python is 3.13; pipeline
tests run in the separate Python 3.12 test image to match the application runtime.
The Docker-in-Docker engine runs privileged for this trusted local assignment
environment. The agent's non-root user does not remove the power granted by
access to that engine.

Persistent volumes retain controller data (`jenkins_home`), agent workspace
(`finsecure-agent-work`), engine data (`jenkins-docker-data`), and client TLS
certificates (`jenkins-docker-certs`). The agent secret is mounted read-only from
outside the Git repository.

To rebuild the agent from the repository root:

```bash
docker build --platform linux/amd64 -f jenkins/Dockerfile.agent -t finsecure-jenkins-agent:0.5 .
```

### Job and automatic trigger

The Pipeline job `finsecure-pay-pipeline` uses **Pipeline script from SCM**:

- Repository: `https://github.com/meiyun1995/capstone-finpay-cicd.git` (public).
- Branch specifier: `*/feature/devsecops` (originally `*/feature/jenkins-pipeline` for Task 4).
- Script path: `Jenkinsfile`.
- SCM polling: `H/2 * * * *`, approximately every two minutes.

The first run loads the trigger configuration. Later changes pushed to the
configured branch trigger builds through polling. The controller, agent, build
engine, Docker Desktop, and Mac must be running for this local setup to operate.
SCM polling avoids requiring an internet-accessible webhook endpoint.
`disableConcurrentBuilds()` prevents overlapping executions of this job.

### Pipeline stages and artifacts

The [Jenkinsfile](Jenkinsfile) defines these sequential stages:

| Stage | Behavior |
| --- | --- |
| Checkout | Checks out the configured Git revision and prints its commit |
| Build | Builds `finsecure-pay-test:$BUILD_NUMBER` using [Dockerfile.test](jenkins/Dockerfile.test) |
| Test | Runs pytest in the Python 3.12 test container; the normal suite has 39 cases |
| SonarQube Analysis | Scans application code and tests, then waits for the configured quality gate |
| Snyk Dependency Scan | Resolves requirements in a temporary environment and blocks High/Critical dependency findings |
| Package | Archives selected committed application and deployment files as `finsecure-pay-N.tar.gz` and fingerprints the Jenkins artifact |
| Security Checks | Runs Bandit 1.9.4 against `app.py` and `transaction.py` |
| Container Build | Builds the root Dockerfile for `linux/amd64`, tagged `cmyaa/finsecure-pay:build-N` |
| Trivy Container Scan | Scans the built image archive and blocks High/Critical vulnerabilities before publication |
| Push | Authenticates with a Docker Hub token and pushes the build tag |
| Deploy | Applies ConfigMap and Service, renders the build image into a temporary Deployment manifest, applies it, and waits up to 180 seconds for rollout |

`N` is the Jenkins job's build number, not a Kubernetes revision number. Tags
identify successive executions of this job; Docker Hub does not inherently make
them immutable. Preserve the job's build history and avoid overwriting release
tags. Unchanged application files can produce identical image content under
different build tags.

The source archive is a downloadable record of the build's committed source.
Kubernetes runs the Docker image, not the archive. The Docker build uses the
checked-out files directly.

Bandit checks common Python source-code security issues. This stage does not
perform dependency CVE scanning or container image vulnerability scanning; the
separate Snyk and Trivy stages added in Task 5 provide those checks.
Nonzero test or scan exit codes fail their stage and prevent later stages from
running; errors are not suppressed with `|| true` or `--exit-zero`.

The Deployment file in Git retains `v1.0.0` as its initial image. During CI/CD,
`kubectl set image --local` substitutes the current build tag into a temporary
manifest before applying it, without changing the tracked YAML. Applying the
original `k8s/deployment.yaml` manually would restore its original image tag.

### Credentials and deployment permissions

| Jenkins credential ID | Kind | Purpose |
| --- | --- | --- |
| `dockerhub-credentials` | Username with password | Docker Hub username and Read/Write personal access token |
| `aks-kubeconfig` | Secret file | Dedicated kubeconfig for `jenkins-deployer` |

The Push stage uses `withCredentials`, disables shell tracing, passes the token
through `docker login --password-stdin`, and deletes its temporary Docker login
configuration on shell exit. The Deploy stage binds its secret file to
`KUBECONFIG`. Neither credential belongs in Git, Docker build arguments, or
submission screenshots.

[deploy-access.yaml](jenkins/deploy-access.yaml) defines a ServiceAccount, Role,
and RoleBinding in `default`. Jenkins can create or update Deployments,
ConfigMaps, and Services, and read ReplicaSets, pods, and events. These
permissions cover those resource types throughout `default`; they are not
restricted to the FinSecure Pay resource names. The identity has no direct
permission to read Secrets or manage RBAC. Apply this bootstrap configuration
manually using the administrator's cluster access:

```bash
kubectl --context aks-finsecure-pay apply -f jenkins/deploy-access.yaml
```

### Renew the temporary AKS credential

The deployment token requests an eight-hour lifetime, subject to the server's
issued expiry. Renewal is manual in this assignment setup. An expired token can
cause `the server has asked for the client to provide credentials`, including
during OpenAPI validation. Disabling manifest validation does not fix expired
authentication.

On the Mac, refresh personal access with `az login` if necessary, then:

```bash
az aks get-credentials --resource-group rg-finsecure-pay --name aks-finsecure-pay
```

Regenerate the dedicated credential outside the repository. This script writes
the token to a restricted file without printing it:

```bash
python3 - <<'PY'
import json
import os
import subprocess
from pathlib import Path

def kubectl(*args):
    return subprocess.check_output(
        ["kubectl", "--context", "aks-finsecure-pay", *args], text=True
    ).strip()

cluster = json.loads(kubectl(
    "config", "view", "--raw", "--minify",
    "-o", "jsonpath={.clusters[0].cluster}",
))
token = kubectl("create", "token", "jenkins-deployer",
                "--namespace", "default", "--duration=8h")
config = {
    "apiVersion": "v1", "kind": "Config",
    "clusters": [{"name": "aks-finsecure-pay", "cluster": cluster}],
    "users": [{"name": "jenkins-deployer", "user": {"token": token}}],
    "contexts": [{"name": "jenkins-deploy", "context": {
        "cluster": "aks-finsecure-pay", "user": "jenkins-deployer",
        "namespace": "default",
    }}],
    "current-context": "jenkins-deploy",
}
directory = Path.home() / ".jenkins-agent-secrets"
directory.mkdir(mode=0o700, exist_ok=True)
path = directory / "aks-jenkins-config.json"
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.fchmod(fd, 0o600)
with os.fdopen(fd, "w") as output:
    json.dump(config, output, indent=2)
print(f"Saved credential to: {path}")
PY

kubectl --kubeconfig "$HOME/.jenkins-agent-secrets/aks-jenkins-config.json" \
  get deployment finsecure-pay
```

In Jenkins, update the existing `aks-kubeconfig` Secret file credential by
uploading the regenerated file, preserving its credential ID. Updating the file
on the Mac alone does not update Jenkins' stored copy. Rerun the failed build
after updating the credential.

### Controlled test failure

The failure demonstration introduced `tests/test_pipeline_gate.py` with an
intentional failing assertion on the branch polled by Jenkins. The Test stage
failed and subsequent stages, including Deploy, were skipped. The deployed image
was checked before and after the failed run to confirm it was unchanged.

The demonstration was repeated after the Deploy stage had been added. Reverting
the deliberate-failure commit removed the test while retaining its history and
allowed subsequent pipeline runs to pass. Preserve the failed build's console
output and stage view as evidence; the intentionally failing test should not
remain in the normal test suite.

### Automated rollout and rollback results

The captured successful Jenkins deployment rolled out
`cmyaa/finsecure-pay:build-17`, finishing with two ready, up-to-date, available
replicas. The previous ReplicaSets for `build-15` and `v1.0.0` remained with zero
desired replicas. A subsequent manual rollback to `build-15` completed
successfully.

To identify the target revision before a rollback:

```bash
kubectl --context aks-finsecure-pay -n default rollout history deployment/finsecure-pay
kubectl --context aks-finsecure-pay -n default get replicasets \
  -l app=finsecure-pay \
  -o 'custom-columns=REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision,IMAGE:.spec.template.spec.containers[0].image'
```

With no Jenkins deployment running, replace `REVISION_NUMBER` with the revision
whose image is the verified rollback target:

```bash
kubectl --context aks-finsecure-pay -n default rollout undo deployment/finsecure-pay \
  --to-revision=REVISION_NUMBER
kubectl --context aks-finsecure-pay -n default rollout status deployment/finsecure-pay \
  --timeout=180s
kubectl --context aks-finsecure-pay -n default get deployment finsecure-pay -o wide
kubectl --context aks-finsecure-pay -n default get pods -l app=finsecure-pay -o wide
kubectl --context aks-finsecure-pay -n default get service finsecure-pay-service
```

Verify `/health` using the Service's current external IP. Rollback restores a
previous pod template, not Git or ConfigMap contents. A later successful pipeline
run will deploy its new build tag again. Capture rollback evidence before
pushing further changes.

### Task 4 submission evidence

- Committed Jenkinsfile and supporting agent/test Dockerfiles.
- Automatically triggered build showing an SCM change as its cause.
- Successful stage view from Checkout through Deploy and downloadable archive.
- Failed-test logs and skipped downstream stages, including Deploy.
- Docker Hub version tag and successful AKS rollout to `build-17`.
- Rollback command, completion output, restored `build-15` image, ready pods,
  and external health-check result.

## Task 5: DevSecOps and security integration

### Tools and execution order

Three security layers run in the existing Jenkins pipeline. Bandit remains as an
additional Python check. The current pipeline order is:

```text
Checkout → Build → Test → SonarQube Analysis → Snyk Dependency Scan
→ Package → Security Checks (Bandit) → Container Build
→ Trivy Container Scan → Push → Deploy
```

| Component | Version/configuration |
| --- | --- |
| SonarQube Community Build | `26.10.0.133078`, local container `sonarqube` |
| SonarQube image | `sonarqube@sha256:f95aaa9016dd4e92c7d70691167a6d96dbb5d8acffd61eba1cb4335d364a7840` |
| Jenkins SonarScanner tool | Name `SonarScanner`, CLI `8.3.0.16463` |
| Jenkins server configuration | `finsecure-sonarqube`, URL `http://sonarqube:9000` |
| Snyk CLI | `1.1308.3` |
| Trivy | `0.76.1` |
| Current agent image | `finsecure-jenkins-agent:0.5`, Linux AMD64 |

Snyk and Trivy are installed with pinned versions and SHA-256 verification in
[Dockerfile.agent](jenkins/Dockerfile.agent). Rebuilding an agent image does not
update a running container; recreate the agent with its existing network,
workspace volume, TLS certificate volume, and read-only agent-secret mount.

SonarQube shares `jenkins-network` with Jenkins. Its browser address on the Mac is
`http://localhost:9000`; `http://sonarqube:9000` is the internal Docker address.
The host port is bound to `127.0.0.1`. Named volumes `sonarqube-data`,
`sonarqube-extensions`, and `sonarqube-logs` preserve its local data. The embedded
database is used for this assignment setup, not as a production database design.

### Source analysis and quality gate

[sonar-project.properties](sonar-project.properties) sets project key
`finsecure-pay`, sources `app.py,transaction.py`, tests `tests`, and target Python
version `3.12`. Jenkins supplies authentication through the Secret text credential
`sonarqube-token`, explicitly bound to `SONAR_TOKEN`. No token is stored in the
properties file.

The project uses the custom **FinSecure Security Gate**. Its overall-code
condition fails when **Security Rating is worse than A**, covering existing code
as well as changes. The inherited new-code conditions are:

- Issues greater than zero.
- Security Hotspots Reviewed below 100%.
- Coverage below 80%.
- Duplicated Lines above 3%.

The pipeline polls for the result using `sonar.qualitygate.wait=true` and
`sonar.qualitygate.timeout=300`. A failed gate or unsuccessful scan blocks later
stages. Webhook creation was rejected by SonarQube's private-address validation,
so the final implementation uses polling and does not require a webhook secret
or a separate `waitForQualityGate` stage.

The pipeline does not currently generate/import a coverage XML report. Passing
pytest tests therefore does not establish the coverage percentage in SonarQube.
The passing gate should not be described as proof of 80% overall test coverage.
SonarQube server settings and project-gate association are configured in its UI;
the repository properties file alone does not recreate those settings.

### CSRF finding review

SonarQube initially reported `python:S4502` at `app = Flask(__name__)` with High
security impact. The Security Rating gate failed, and Jenkins stopped with
`QUALITY GATE STATUS: FAILED` and exit code 3.

The finding was reviewed against the application's actual behavior: `/validate`
only checks the submitted JSON and returns a result. The API uses no login
sessions or authentication cookies, does not change stored data, and does not
execute payments. The issue was resolved as a false positive with this rationale
recorded in SonarQube. Subsequent analysis passed.

This is a documented finding review, **not a vulnerability patch**. Reassess CSRF
protection if browser authentication or state-changing operations are added.
The container base-image migration below supplies the actual remediation
before-and-after evidence.

### Dependency scanning and reports

Snyk authenticates using Jenkins Secret text credential `snyk-token`, bound to
`SNYK_TOKEN`. The stage creates a fresh temporary virtual environment, installs
`requirements.txt`, and runs `snyk test --severity-threshold=high`. This threshold
blocks High and Critical dependency vulnerabilities. Scanner errors also fail
the stage; failures are not ignored.

The observed baseline scanned **13 dependencies**, reporting zero findings at
that threshold. This does not assert the absence of lower-severity issues.
The Snyk environment uses the agent's Python 3.13; application tests and runtime
use Python 3.12. This is a resolution-environment limitation, particularly if
Python-version-dependent requirements are introduced. Trivy additionally scans
the packages installed in the actual deployment image.

The stage archives `reports/snyk-N.json` in its `post { always { ... } }` block,
including when vulnerability findings cause failure. A scanner/setup error may
prevent report creation; allowing an empty archive does not change the failed
stage into a successful one. The temporary environment is removed on shell exit.

### Container scanning and release gate

After building `cmyaa/finsecure-pay:build-N`, Jenkins exports that exact image
using `docker save`. Trivy scans the temporary archive with `--scanners vuln`,
covering OS packages and supported application packages. This archive approach
works with the separate Docker-in-Docker engine without assuming shared bind
mount paths between the engine and agent.

The initial scan writes a full JSON vulnerability report with `--exit-code 0`.
The following `trivy convert --severity HIGH,CRITICAL --exit-code 1` command prints
the relevant findings and enforces the gate. Thus the report-generation option
does not bypass the release gate. Scan errors stop the shell as well.
`--ignore-unfixed` is not used: High/Critical findings without available fixes
also block publication and deployment.

`reports/trivy-N.json` is archived even when the gate fails, if a report was
produced. The temporary image archive is deleted on shell exit. These scans
check vulnerabilities; this Trivy stage does not enable its secret or
misconfiguration scanners. Scan results depend on the vulnerability database
available at execution time, so a later scan of the same image may differ.

### Base-image remediation and verified deployment

The initial Debian-based application image failed with **44 High package/CVE
findings representing 8 distinct CVEs**. There were no High/Critical Python
package findings. The affected OS package families included util-linux, acl,
ncurses, systemd, and perl; the reports listed no fixed versions for these
findings.

Refreshing the Python slim base to digest
`sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159`
did not resolve them: the next scan reported the same findings and affected
package versions. The High/Critical threshold remained unchanged.

The application and test images were then migrated to the official Python 3.12
Alpine base, pinned in both Dockerfiles:

```dockerfile
FROM python:3.12-alpine@sha256:e6dae589c1c05976188fd3bd019afd091445fc533ed2ea29001beddc7368a9c8
```

The candidate base scan detected Alpine `3.24.3` and reported no High/Critical
findings. Alpine uses a different OS package set and musl libc, so compatibility
was checked through the test pipeline and a local application smoke test. The
root Dockerfile uses Alpine's `addgroup`/`adduser` commands and retains the
non-root application UID/GID `10001`. The local `/health` check returned HTTP 200.

The subsequent full application-image scan passed and Jenkins deployed
**`cmyaa/finsecure-pay:build-27`**. Verification on **1 November 2026** showed:

| Check | Observed result |
| --- | --- |
| AKS Deployment | `finsecure-pay`: 2/2 ready, 2 up-to-date, 2 available |
| Deployed image | `cmyaa/finsecure-pay:build-27` |
| Service | `finsecure-pay-service`, LoadBalancer, external IP `57.158.99.15` |
| External request | `GET /health`: HTTP `200 OK` from Gunicorn, `{"status":"ok"}` |

This remediation **replaced the affected base-image package set**; it did not
patch the Debian packages in place. The passing scan establishes no reported
High/Critical findings at scan time, not an absence of all possible security
risks. The failure demonstration used actual detected vulnerabilities in the
previous base image, rather than a deliberately introduced application flaw.

### Secret management and submission evidence

In addition to the Docker Hub and AKS credentials described in Task 4, Jenkins
stores `sonarqube-token` and `snyk-token` as Secret text credentials. The pipeline
binds them only around the relevant scans and disables shell tracing. Credentials
are not embedded in Dockerfiles, Git, application manifests, or scanner reports
intentionally. Screenshots show credential IDs/types only, never secret values.

Retain the following evidence with the submission:

- Committed Jenkinsfile, scanner properties, and checksum-pinned agent Dockerfile.
- SonarQube gate configuration, passing result, and documented CSRF review.
- Snyk scan summary and archived `reports/snyk-N.json`.
- Failed Debian-image Trivy report and console output, with the Jenkins build
  number and skipped Push/Deploy stages visible.
- The base-image migration commit and passing test/Trivy results.
- Successful build 27 stage view, Docker Hub tag, AKS Deployment output, and
  external health response.
- Jenkins credentials-list screenshot showing IDs and types without values.

Use the actual failed build numbers from Jenkins when labelling the saved
screenshots and reports; they are not recorded here. Preserve both failed and
passing reports before deleting build history. The JSON reports are Jenkins
artifacts, while SonarQube results and review history remain on its server.

## Development workflow

Work on a feature branch, run the tests, and review changes before committing.
Push the feature branch and open a pull request into `main`. The configured
Jenkins job currently polls `feature/devsecops`; pushes to that branch,
including documentation changes, trigger the full pipeline and deployment.
Update the job's branch configuration deliberately when changing the release
workflow. Keep credentials outside Git and retain the evidence from each
assignment demonstration.
