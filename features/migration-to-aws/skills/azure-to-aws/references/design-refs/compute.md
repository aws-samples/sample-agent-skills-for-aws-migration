# Compute Services Design Rubric

**Applies to:** Container Apps, Azure Functions, Virtual Machines, AKS (Azure Kubernetes Service), App Service

**Table lookup first:** Check `fast-path.md` **Direct Mappings** for this Terraform type.

- `azurerm_container_app` and `azurerm_function_app` are currently in Direct Mappings and usually resolve with `confidence: "deterministic"` when row conditions are met.
- `azurerm_linux_virtual_machine`, `azurerm_windows_virtual_machine`, `azurerm_kubernetes_cluster`, `azurerm_app_service`, and `azurerm_linux_web_app` are not direct-mapped in `fast-path.md`; use the rubric below (typically `confidence: "inferred"`).
- If a resource is not eligible for Direct Mappings (or row conditions are not met), use the rubric below.

## Eliminators (Hard Blockers)

| Azure Service      | AWS Target | Blocker                                                                                                       |
| ------------------ | ---------- | ------------------------------------------------------------------------------------------------------------- |
| Container Apps     | Lambda     | Execution time >15 min → use Fargate                                                                          |
| Container Apps     | Fargate    | GPU workload or >16 vCPU or >120 GB memory → use EC2                                                          |
| Azure Functions    | Lambda     | Runtime not supported by Lambda (e.g. custom runtime, unsupported language version) → use custom runtime on Fargate |
| AKS                | EKS        | Custom CRI incompatible with EKS → manual workaround or ECS                                                   |
| Any                | App Runner | **Closed to new customers (April 30 2026).** Do not target App Runner for new migrations. Use Fargate (default), Lambda (event-driven), or EKS (K8s required). |

## Signals (Decision Criteria)

### Container Apps

- **Consumption plan (serverless, scale-to-zero)** → Lambda (if stateless, <15 min) or Fargate (if always-on or container-native)
- **Dedicated plan (always-on)** → Fargate
- **Stateless microservice** + **<15 min execution** → Lambda
- **HTTP-only** + **container-native** → Fargate preferred (better dev/prod parity)

### Azure Functions

- **Event-driven** + **<15 min** + **supported runtime (Python/Node/Go/.NET)** → Lambda
- **Always-on or long-running (>15 min)** → Fargate or ECS task
- **HTTP trigger only** + **stateless** → Lambda (with API Gateway trigger)

### Virtual Machines

- **Always-on workload** → EC2 (reserved or on-demand based on cost sensitivity)
- **Batch/periodic jobs** → EC2 with Auto Scaling Group (scale to 0 in dev)
- **Windows-only workload** → EC2 Windows AMI (Lambda/Fargate support limited for Windows)

### AKS

- **Kubernetes orchestration required** → EKS
- **No K8s requirement** + **microservices** → Fargate (simpler, no cluster overhead)

### App Service

- **Web application** + **containerized** → Fargate
- **Static site** + **no backend** → Amplify (static hosting)
- **Full-stack web app** + **always-on** → Fargate or EC2 (based on cost sensitivity)

## 6-Criteria Rubric

Apply in order; first match wins:

1. **Eliminators**: Does Azure config violate AWS constraints? If yes: switch to alternative
2. **Operational Model**: Managed (Lambda, Fargate) vs Self-Hosted (EC2, EKS)?
   - Prefer managed unless: Always-on + high baseline cost → EC2
3. **User Preference**: From `preferences.json`: `design_constraints.kubernetes`, `design_constraints.cost_sensitivity`?
   - If `kubernetes = "eks-managed"` → EKS (preserves K8s investment)
   - If `kubernetes = "ecs-fargate"` → Fargate (simpler managed containers)
   - If `cost_sensitivity` present and high → prefer Fargate (lower operational cost)
4. **Feature Parity**: Does Azure config require AWS-unsupported features?
   - Example: Container Apps with DAPR sidecar → Fargate with custom sidecar container (DAPR is not natively managed on AWS; containerise the full workload)
   - Example: Azure Functions Durable Functions → AWS Step Functions + Lambda (stateful orchestration)
5. **Cluster Context**: Are other resources in this cluster using EKS/EC2/Fargate?
   - Prefer same platform (affinity)
6. **Simplicity**: Fewer resources = higher score
   - Fargate (1 service) > EC2 (N services for ASG + monitoring)

## Examples

### Example 1: Container Apps (dedicated plan, stateless API)

- Azure: `azurerm_container_app` (cpu=0.5, memory=1Gi, min_replicas=1, max_replicas=10)
- Signals: HTTP, stateless, dedicated plan (always-on)
- Criterion 1 (Eliminators): PASS (no GPU, <16 vCPU, stateless OK)
- Criterion 2 (Operational Model): Fargate preferred (always-on, container-native)
- → **AWS: Fargate (0.5 CPU, 1 GB memory)**
- Confidence: `inferred` (rubric-based — Container App is not in fast-path for dedicated plan)

### Example 2: Azure Function (event-driven, short-running)

- Azure: `azurerm_function_app` (os_type=linux, runtime=python, timeout=540s)
- Signals: Event-driven, 540s = 9 minutes (< 15 min limit), supported runtime
- Criterion 1 (Eliminators): PASS on timeout (540s < 900s)
- Criterion 2 (Operational Model): Lambda preferred for event-driven + short-running
- → **AWS: Lambda with EventBridge or SQS trigger**
- Confidence: `inferred`

### Example 3: Virtual Machine (background job)

- Azure: `azurerm_linux_virtual_machine` (size=Standard_B2s, region=eastus, custom_data=startup_script)
- Signals: Periodic batch job (inferred from startup script / custom_data), always-on
- Criterion 1 (Eliminators): PASS
- Criterion 2 (Operational Model): EC2 (explicit compute control)
- Criterion 3 (User Preference): If `design_constraints.azure_monthly_spend` indicates cost sensitivity, prefer auto-scaling → EC2 + ASG (scale to 0 in dev)
- → **AWS: EC2 t3.small + Auto Scaling Group (min=0 in dev)**
- Confidence: `inferred`

### Example 4: AKS Cluster

- Azure: `azurerm_kubernetes_cluster` (node_count=3, vm_size=Standard_D2_v3)
- Signals: Kubernetes orchestration, multi-node cluster
- Criterion 1 (Eliminators): PASS
- Criterion 2 (Operational Model): EKS (K8s required, managed control plane)
- Criterion 3 (User Preference): If `design_constraints.kubernetes = "ecs-fargate"` → Fargate
- → **AWS: EKS (managed node groups, t3.medium equivalent)**
- Confidence: `inferred` (or `deterministic` if `preferences.json` confirms kubernetes preference)

## Output Schema

```json
{
  "azure_type": "azurerm_container_app",
  "azure_address": "example-api",
  "azure_config": {
    "cpu": "0.5",
    "memory": "1Gi",
    "min_replicas": 1,
    "max_replicas": 10
  },
  "aws_service": "Fargate",
  "aws_config": {
    "cpu": "0.5",
    "memory_mb": 1024,
    "region": "us-east-1"
  },
  "confidence": "inferred",
  "rationale": "Rubric: Container Apps (dedicated, stateless, always-on) → Fargate (managed container runtime)",
  "rubric_applied": [
    "Eliminators: PASS",
    "Operational Model: Managed preferred",
    "User Preference: N/A",
    "Feature Parity: Full",
    "Cluster Context: Fargate affinity",
    "Simplicity: Fargate (1 service)"
  ]
}
```
