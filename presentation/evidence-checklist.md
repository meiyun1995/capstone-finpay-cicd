# Capstone presentation evidence review

Reviewed against the 29 evidence items supplied for Tasks 1–6, updated 3 November 2026.
The revised [PowerPoint](finsecure-pay-capstone.pptx) and
[PDF](finsecure-pay-capstone.pdf) remain 10 slides and also retain the Task 7
AI proposal, architecture, technical decisions, lessons, and project links.

The 3 November update adds Azure Monitor / Log Analytics centralized logging.
Slide 8 includes the [Azure Portal query screenshot](<../screenshots/task 6/log_analytics_azure.png>)
alongside the original dashboard, alert, Discord, and local-log evidence. Slide 10
and the Task 7 report include the implemented logging path. The
[actual query and setup evidence](<../screenshots/task 6/centralized_logging_evidence.txt>)
records managed-identity authentication, ready agents, 30-day retention, and
marked 200/400 requests from two distinct pods.

All 29 evidence types have a visible representation in the revised slides.
Where a source/configuration screenshot did not exist, the slides use actual
repository excerpts with links to the complete files. Recorded console logs
and JSON reports supply the test and scan evidence. These are historical
results, not newly executed demonstrations. Code excerpts are selected lines,
not complete executable files, except the displayed Dockerfile with blank lines
removed and long lines wrapped.

| Task | Expected evidence | Original deck | Revised slide | Evidence used |
| --- | --- | --- | --- | --- |
| 1 | GitHub repository link | Present | 1, 10 | Public [repository](https://github.com/meiyun1995/capstone-finpay-cicd) and [final implementation on main](https://github.com/meiyun1995/capstone-finpay-cicd/tree/main) |
| 1 | Application source code | Missing on slide | 1 | [app.py](../app.py) health handler and validation response excerpts, plus [transaction.py](../transaction.py) fields |
| 1 | Unit-test results | Summary excerpt only | 1 | Build 27 recorded `39 passed in 0.37s` from [console log](<../screenshots/task 5/trivy_success_console_output.txt>) |
| 1 | Build and test evidence | Partial, limited build context | 1, 5 | Same console's test-image export and `docker run`, plus successful pipeline stages |
| 2 | Dockerfile | Mentioned, not displayed | 2 | Current [Dockerfile](../Dockerfile), including digest, install, non-root user, port, and Gunicorn command |
| 2 | Image and version evidence | Registry tag present | 2 | [Local image listing](<../screenshots/task 2/image_listing.png>) and [successful build](<../screenshots/task 2/success_build_image.png>) |
| 2 | Container execution evidence | Health/user check present | 2 | [docker ps capture](<../screenshots/task 2/image_running.png>) showing Up, image tag, container name, and port mapping |
| 2 | Container registry evidence | Present | 2, 10 | [Docker Hub screenshot](<../screenshots/task 2/docker_hub_repo.png>) version row and public registry link |
| 3 | Deployment and Service configurations | Mentioned, not displayed | 3 | [Deployment](../k8s/deployment.yaml) and [LoadBalancer Service](../k8s/service.yaml) source excerpts |
| 3 | ConfigMap | Mentioned, not displayed | 3 | [ConfigMap](../k8s/configmap.yaml) source |
| 3 | Readiness and liveness probes | Mentioned, not displayed | 3 | Actual readiness/liveness blocks from the Deployment, both using `/health:8000` |
| 3 | Running pods | Recovery capture present | 4 | [Final pod state](<../screenshots/task 3/final_pod_state.png>) showing two 1/1 Running pods |
| 3 | External application access | Described, not displayed | 4 | [External health response](<../screenshots/task 3/health_output.png>) with HTTP 200 and JSON status ok |
| 3 | Automatic recovery | Present | 4 | [Pod replacement watch](<../screenshots/task 3/after_disruption_new_pod_creation.png>) showing the replacement becoming Ready |
| 4 | Jenkinsfile | Mentioned, not displayed | 5 | [Jenkinsfile](../Jenkinsfile) selected agent, polling, and Test-stage lines, linked to complete file |
| 4 | Successful pipeline execution | Present | 5 | [Build 27 green stages](<../screenshots/task 5/trivy_pipeline_success.png>) through Deploy |
| 4 | Failed-test pipeline execution | Present | 5 | [Build 16 red Test stage](<../screenshots/task 4/build_failed_error_pipeline.png>) and [console](<../screenshots/task 4/build_error_console_output.txt>) with skipped Push/Deploy and exit code 1 |
| 4 | Application rollout | Updated Deployment visible, limited rollout detail | 4 | Recorded build-17 rollout completion and deployment fields from [Jenkins console](<../screenshots/task 4/reverted_build_success_console_output.txt>) |
| 4 | Rollback | Present | 4 | Cropped actual rolled-back and rollout-completed messages from [rollback capture](<../screenshots/task 4/rollback_to_rev2.png>); [post-rollback state](<../screenshots/task 4/successful_rollout.png>) confirms build-15 |
| 5 | Security scan reports | Summary counts, limited report detail | 6 | [SonarQube gate result](<../screenshots/task 5/quality-gate-passed.png>), [Snyk console](<../screenshots/task 5/synk_console_output_success.txt>), and comparison calculated from [Trivy 25](<../screenshots/task 5/trivy-25.json>) / [Trivy 27](<../screenshots/task 5/trivy-27.json>) JSON |
| 5 | Blocked pipeline | Present | 7 | [Trivy failed pipeline](<../screenshots/task 5/trivy_pipeline_failed.png>) before Push/Deploy |
| 5 | Remediation evidence | Successful result, limited change evidence | 5–7 | [Alpine migration commit](<../screenshots/task 5/remediation-changes-base-image.png>), before/after scan comparison, full successful pipeline, and [build-27 deployment](<../screenshots/task 5/successful_remediation_deployment.png>) |
| 5 | Secret/credential management | Present | 7 | [Jenkins credentials list](<../screenshots/task 5/secret_management.png>) with credential IDs/types and hidden values |
| 6 | Monitoring dashboard | Present | 8 | [Grafana dashboard](<../screenshots/task 6/dashboard_restored_2_replica.png>) |
| 6 | Metrics | Present | 8 | Same dashboard's live CPU, memory working set, and replica panels |
| 6 | Alert configuration | Written threshold only | 8 | Threshold block cropped from [Grafana alert rule](<../screenshots/task 6/firing_state.png>), with pending/evaluation settings in slide text |
| 6 | Triggered alert | Present | 8 | Actual Firing threshold state from the same alert capture |
| 6 | Received notification | Present | 8 | [Received Discord firing message](<../screenshots/task 6/discord_alert.png>); webhook URL excluded |
| 6 | Logging/troubleshooting | Local logs only | 8, 10 | [Azure Log Analytics query](<../screenshots/task 6/log_analytics_azure.png>) shows centralized health logs; [kubectl logs capture](<../screenshots/task 6/kubectl_logs_200_400.png>) shows immediate 200/400 troubleshooting. [API verification](<../screenshots/task 6/centralized_logging_evidence.json>) records both marked responses in the workspace. |

## Evidence interpretation

- Task 2 screenshots record the original `v1.0.0` release. The Dockerfile shown
  is the later Alpine version. The remediation slide identifies that later change.
- The checked-in Deployment starts with `v1.0.0`. Jenkins renders a temporary
  manifest with `build-N`; the slides make that distinction explicit.
- The file named `successful_rollout.png` records the **post-rollback**
  `build-15` state. The forward `build-17` rollout uses its actual Jenkins log.
- Trivy build 25 had 44 High package/CVE entries across eight distinct CVEs.
  Build 27 had zero High/Critical findings, while lower-severity findings
  remained. The slides do not claim that every severity was zero.
- The SonarQube CSRF finding was reviewed as a false positive for the current
  stateless API. It was not a code patch. The base-image migration is the
  demonstrated vulnerability remediation.
- Recovery proves that a deleted pod was replaced. Two replicas still share
  one AKS worker node. No node-level availability guarantee is claimed.
- Grafana displays Prometheus metrics. Azure Monitor Agent sends container logs
  to Log Analytics for centralized search with 30-day retention; `kubectl logs`
  supports immediate inspection. The Azure screenshot shows health records;
  the separate API evidence contains the marked 200 and 400 records.

The full captures and logs remain unchanged in `screenshots/`. The presentation
uses focused crops and editable code/log excerpts to fit the submission limit.
