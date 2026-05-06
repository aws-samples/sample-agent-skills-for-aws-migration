# Categories B + C: Configuration Gaps + Compute Questions (Q8–Q11)

**Category B** fires when `billing-profile.json` exists and `azure-resource-inventory.json` does NOT (billing-only path).
**Category C** fires when compute resources are present in IaC discovery.

---

## Category B — Configuration Gaps (Billing-Only Mode)

Ask these when billing data is the only source. Use answers to fill in gaps that Terraform would normally provide.

### B1 — Container / App Service Tier

> Your billing shows Azure Container Apps or App Service usage. What tier are you running?
>
> A) Consumption (serverless, pay-per-use)
> B) Dedicated (always-on, fixed CPU/memory)
> C) I don't know

Interpret → `inventory_clarifications.container_tier`: A → `"consumption"`, B → `"dedicated"`, C → `"unknown"`.

### B2 — Database HA Configuration

> For your Azure SQL / PostgreSQL: are you using zone-redundant or geo-redundant configuration?
>
> A) Zone-redundant (high availability within region)
> B) Geo-redundant (cross-region failover)
> C) Standard (no redundancy)
> D) I don't know

Interpret → `inventory_clarifications.database_ha`: A → `"zone_redundant"`, B → `"geo_redundant"`, C → `"standard"`, D → `"unknown"`.

### B3 — Redis Cache Tier

> What Azure Cache for Redis tier are you on?
>
> A) Basic (single node, dev/test)
> B) Standard (replicated, SLA-backed)
> C) Premium (enterprise features, persistence)
> D) I don't know

Interpret → `inventory_clarifications.redis_tier`: A → `"basic"`, B → `"standard"`, C → `"premium"`, D → `"unknown"`.

---

## Category C — Compute Model Questions (Q8–Q11)

### Q8 — Kubernetes Sentiment

**Fires if:** AKS (`azurerm_kubernetes_cluster`) present. **Skip if:** Q5 = multi-cloud (auto-set to EKS).

**Context:** AKS clusters can migrate to EKS or be re-platformed to Fargate depending on your Kubernetes dependency.

> How do you feel about continuing to manage Kubernetes on AWS?
>
> A) We love Kubernetes — EKS preferred, we manage our own clusters
> B) Neutral — either EKS or managed container service is fine
> C) Frustrated with K8s complexity — prefer a fully managed container service (Fargate/ECS)
> D) We're using AKS only because it was the easiest Azure option — open to alternatives

Interpret → `kubernetes`: A → `"eks"`, B → `"eks-or-ecs"`, C → `"ecs"`, D → `"ecs"`. Default: B → `"eks-or-ecs"`.

---

### Q9 — WebSocket / Long-Lived Connections

**Fires if:** Any web-facing compute present (Container Apps, App Service, AKS).

> Does your application use WebSockets or long-lived HTTP connections?
>
> A) Yes — WebSocket connections required
> B) No — standard HTTP/REST only

Interpret → `websocket_required`: A → `true`, B → `false`. Default: B → `false`.

If A → Note: ALB WebSocket configuration required in Design.

---

### Q10 — Container Apps / App Service Traffic Pattern

**Fires if:** `azurerm_container_app` or `azurerm_app_service` or `azurerm_linux_web_app` present.

> What is the traffic pattern for your Container Apps / App Service workloads?
>
> A) Business hours only (8am–6pm workday)
> B) Bursty — predictable spikes (e.g., end-of-day batch, morning rush)
> C) Constant 24/7 traffic
> D) Highly variable / unpredictable

Interpret → `container_traffic_pattern`: A → `"business-hours"`, B → `"bursty"`, C → `"constant-24-7"`, D → `"variable"`. Default: C → `"constant-24-7"`.

---

### Q11 — Container Apps / App Service Monthly Spend

**Fires if:** Q10 was asked (Container Apps / App Service present).

**Context:** Helps determine if re-platforming to Fargate is worth the migration effort vs staying on a managed container service.

> What is your approximate Azure Container Apps / App Service monthly cost?
>
> A) Under $100
> B) $100–$500
> C) $500–$2K
> D) Over $2K

Interpret → `container_monthly_spend`: map to string label. Default: B → `"$100-$500"`.

**Low-spend check:** If A (under $100) + Q10 = business hours → Surface advisory: "Your low-spend, business-hours Container Apps workload may be cost-effective to stay on Azure. Evaluate whether migration cost exceeds savings before proceeding."
