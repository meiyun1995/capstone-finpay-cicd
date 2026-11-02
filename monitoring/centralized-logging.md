# Centralized application logs

Azure Monitor Container Insights collects Kubernetes container stdout/stderr into
the `ContainerLogV2` table in the `law-finsecure-pay` Log Analytics workspace
(`eastasia`, resource group `rg-finsecure-pay`). The workspace has 30-day
retention. This complements the existing Prometheus metrics, Grafana dashboard,
and Discord alerts.

## Collection configuration

[container-log-settings.json](container-log-settings.json) requests the
`Microsoft-ContainerLogV2` stream rather than the full Container Insights metrics
and inventory stream group. Collection uses managed identity; no workspace keys
or Azure credentials belong in this repository. The KQL query filters the search
to the application; it does not restrict which namespaces the agent collects.

Container logs can include request paths and query strings. Keep credentials,
personal data, and full transaction payloads out of application log messages.
Log ingestion and retention can incur Azure charges.

## Reproduce the setup

Sign in with Azure CLI and select the subscription containing the cluster and
workspace. Register these prerequisites if they are not already registered:

```bash
az provider register --namespace Microsoft.Insights --wait
az provider register --namespace Microsoft.KubernetesConfiguration --wait
```

From the repository root, link the existing workspace:

```bash
FINSECURE_LOG_WORKSPACE_ID="$(az monitor log-analytics workspace show \
  --resource-group rg-finsecure-pay \
  --workspace-name law-finsecure-pay --query id --output tsv)"

az aks enable-addons \
  --resource-group rg-finsecure-pay --name aks-finsecure-pay \
  --addons monitoring \
  --workspace-resource-id "$FINSECURE_LOG_WORKSPACE_ID" \
  --data-collection-settings monitoring/container-log-settings.json
```

Check the add-on and agents without displaying credentials:

```bash
az aks show --resource-group rg-finsecure-pay --name aks-finsecure-pay \
  --query '{Enabled:addonProfiles.omsagent.enabled,ManagedIdentityAuth:addonProfiles.omsagent.config.useAADAuth}'

kubectl --context aks-finsecure-pay -n kube-system get daemonset ama-logs
kubectl --context aks-finsecure-pay -n kube-system get deployment ama-logs-rs
```

## Search and troubleshoot

In Azure Portal, open **Log Analytics workspaces → law-finsecure-pay → Logs**,
switch to the KQL editor if needed, and run
[finsecure-pay-logs.kql](finsecure-pay-logs.kql). Allow time for initial ingestion.
The query shows timestamp, pod, container, stdout/stderr source, and message for
`/health` and `/validate` requests across replicas. A 400 validation response is
an expected input rejection, not a service outage.

For immediate investigation, `kubectl logs` remains useful; centralized logs
already ingested into the workspace remain searchable independently of the
original pod. They are subject to the workspace retention and access policies.
Grafana continues to display Prometheus metrics; the logs are searched in Azure
Monitor rather than added to the Grafana dashboard.

Capture the KQL query and actual result rows, agent readiness, and workspace
retention as submission evidence. Exclude tokens, connection details containing
secrets, and any unrelated sensitive logs.

## Verified result

On 3 November 2026 (Singapore time), the add-on reached `Succeeded`, managed
identity authentication was enabled, and both `ama-logs` and `ama-logs-rs` were
Ready. The effective collection rule contained `Microsoft-ContainerLogV2` only.
The marked `/health` 200 and `/validate` 400 requests appeared in the workspace
from two different application pods. Actual query rows and setup metadata are
saved in the [verification log](<../screenshots/task 6/centralized_logging_evidence.txt>)
and [JSON evidence](<../screenshots/task 6/centralized_logging_evidence.json>).

During setup, the application pods also showed frequent existing restarts and
probe timeouts. A previous-container log contained a Gunicorn control-server
permission error for `/home/appuser`. These observations predated logging
onboarding; their root cause has not been established by this change.

Reference: [Enable monitoring for AKS](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/kubernetes-monitoring-enable),
[ContainerLogV2 schema](https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/containerlogv2).
