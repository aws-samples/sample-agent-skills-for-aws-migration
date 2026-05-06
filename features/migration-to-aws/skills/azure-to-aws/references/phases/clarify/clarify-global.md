# Category A: Global/Strategic Questions (Q1–Q7)

Always fires. Present all questions in Batch 1.

---

## Q1 — Target AWS Region

**Context:** Azure regions map closely to AWS regions. Your current Azure region suggests a default.

> Which AWS region should be your primary deployment target?
>
> A) US East (N. Virginia) — `us-east-1`
> B) US West (Oregon) — `us-west-2`
> C) EU West (Ireland) — `eu-west-1`
> D) EU West (London) — `eu-west-2`
> E) AP Southeast (Singapore) — `ap-southeast-1`
> F) AP Southeast (Sydney) — `ap-southeast-2`
> G) AP Northeast (Tokyo) — `ap-northeast-1`
> H) Other — specify

Interpret → `target_region`: map letter to region code. Default: closest AWS region to detected Azure region.

---

## Q2 — Compliance Requirements

**Context:** Compliance requirements constrain which AWS services and regions are available.

> Does your workload have any compliance requirements?
>
> A) None
> B) SOC 2 Type II
> C) ISO 27001
> D) HIPAA (Healthcare)
> E) PCI DSS (Payment Card)
> F) FedRAMP (US Government)
> G) GDPR (EU data residency)
> H) Multiple — specify

Interpret → `compliance`: A → `[]`, B → `["soc2"]`, C → `["iso27001"]`, D → `["hipaa"]`, E → `["pci_dss"]`, F → `["fedramp"]`, G → `["gdpr"]`, H → user-specified list. Default: A → `[]`.

---

## Q3 — Current Azure Monthly Spend

**Context:** Current spend informs AWS budget expectations and migration funding options.

> What is your approximate total Azure monthly spend?
>
> A) Under $1K
> B) $1K–$5K
> C) $5K–$20K
> D) $20K–$100K
> E) Over $100K
> F) I don't know

Interpret → `azure_monthly_spend`: map to string label. Default: B → `"$1K-$5K"`.

---

## Q4 — Funding Stage (skip in IDE/CLI mode)

**Context:** Helps identify relevant AWS migration funding programs (MAP, etc.).

> What is your company's current stage?
>
> A) Pre-seed / Seed
> B) Series A
> C) Series B or later
> D) Public company / Enterprise
> E) Non-profit / Public sector
> F) Skip

Interpret → `funding_stage`: A → `"seed"`, B → `"series-a"`, C → `"series-b-plus"`, D → `"enterprise"`, E → `"nonprofit"`, F → no constraint. Default: F → no constraint.

---

## Q5 — Multi-Cloud Requirements

**Context:** Multi-cloud requirements constrain container platform selection (EKS vs Fargate).

> After migrating to AWS, will you need to run the same workload on multiple clouds simultaneously?
>
> A) Yes — we need multi-cloud portability
> B) No — AWS-only is fine

**Early-exit:** If A → record `kubernetes: "eks"`. Q8 (K8s sentiment) is auto-set and skipped.

Interpret → `multi_cloud`: A → `true`, B → `false`. Default: B → `false`.

---

## Q6 — Uptime Requirements

**Context:** Determines single-AZ vs multi-AZ architecture defaults.

> What is the impact of 1–4 hours of downtime for your application?
>
> A) Negligible — internal tool or low-traffic service
> B) Significant — customers notice, but recoverable
> C) Severe — SLA breach or revenue impact
> D) Catastrophic — safety, regulatory, or critical infrastructure

Interpret → `availability`: A → `"single-az"`, B → `"multi-az"`, C → `"multi-az"`, D → `"multi-az-ha"`. Default: B → `"multi-az"`.

---

## Q7 — Maintenance Window Tolerance

**Context:** Determines cutover strategy — zero-downtime blue/green vs maintenance window.

> How much downtime can you tolerate during the migration cutover?
>
> A) Zero — live traffic cutover required (blue/green or canary)
> B) Under 30 minutes — off-peak window
> C) 1–4 hours — planned maintenance window
> D) Flexible — weekends or low-traffic periods
> E) No constraint

**Zero downtime:** If A → set `cutover_strategy: "blue_green"`. Requires AWS DMS for databases.

Interpret → `cutover_strategy`: A → `"blue_green"`, B → `"maintenance-window-offpeak"`, C → `"maintenance-window-hourly"`, D → `"maintenance-window-weekly"`, E → `"flexible"`. Default: D → `"maintenance-window-weekly"`.
