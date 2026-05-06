# Networking Services Design Rubric

**Applies to:** Virtual Network (VNet), Network Security Group (NSG), Load Balancer, Application Gateway, Azure DNS, Azure Firewall, Azure CDN, ExpressRoute, Azure Container Registry

**Quick lookup (no rubric):** Check `fast-path.md` first (VNet → VPC, NSG → Security Groups, Azure DNS → Route 53, etc.)

## Eliminators (Hard Blockers)

| Azure Service         | AWS Target | Blocker                                                                                                       |
| --------------------- | ---------- | ------------------------------------------------------------------------------------------------------------- |
| ExpressRoute          | Direct Connect | Dedicated connection requires 4–12 weeks setup → use AWS Site-to-Site VPN as temporary connectivity during migration |
| Application Gateway   | ALB        | SSL/TLS passthrough required (no termination at L7) → use NLB (L4, pass-through) instead                    |
| Load Balancer (Standard) | NLB     | Host/path-based HTTP routing required → use ALB (L7) instead                                                  |

## Signals (Decision Criteria)

### Virtual Network (VNet)

- Always → AWS VPC (1:1 deterministic)
- Preserve CIDR blocks, subnets (public/private), and routing table configuration
- VNet peering → VPC Peering or AWS Transit Gateway (if hub-and-spoke topology)

### Network Security Group (NSG)

- Always → AWS Security Group (1:1 deterministic)
- Convert inbound/outbound rules: priority order, port ranges, source/destination IP ranges
- NSG rules mapped to security group ingress/egress rules
- **Note:** AWS Security Groups are stateful (return traffic is automatically allowed); preserve rule intent, not priority numbers

### Application Gateway

- **HTTP/HTTPS + path-based or host-based routing (L7)** → ALB (Application Load Balancer)
- **WAF rules enabled** → ALB + AWS WAF (attach WAF Web ACL to ALB)
- **SSL/TLS termination** → ALB (terminate TLS on port 443; configure HTTP redirect on port 80)
- **TLS passthrough (no termination)** → NLB (L4, pass-through to backend)
- For internet-facing ALB: terminate TLS on 443 and configure 80 as redirect-only to HTTPS (no direct HTTP forwarding)

### Azure Load Balancer (Standard)

- **TCP/UDP + high throughput, Layer 4** → NLB (Network Load Balancer)
- **Internal load balancing within VNet** → NLB (internal scheme)
- **Internet-facing, latency-sensitive** → NLB (internet-facing scheme)
- **Host/path-based routing needed** → use ALB instead (see eliminator above)

### Azure DNS

- Always → Route 53 (1:1 deterministic)
- Preserve zone name, record types (A, CNAME, MX, TXT, etc.), and TTLs
- Private DNS Zones → Route 53 Private Hosted Zones (associate with VPC)

### Azure Firewall

- **DDoS protection + stateful packet inspection** → AWS WAF + AWS Shield Standard
- **Shield Standard** is automatic and free — no extra config required
- **Rate limiting** → AWS WAF rate-based rules
- **Bot management** → AWS WAF Bot Control
- **IP allowlist/denylist** → AWS WAF IP set rules
- **For Layer 3/4 stateful firewall** → AWS Network Firewall (if deep packet inspection or centralized policy is required)

### Azure CDN

- **Content delivery, static assets, global edge** → Amazon CloudFront
- Preserve custom domain, HTTPS settings, caching rules, and origin configuration
- **Dynamic content acceleration** → CloudFront with origin shield

### Azure ExpressRoute

- **Dedicated private connection** → AWS Direct Connect
- **Temporary/dev connectivity or migration path** → AWS Site-to-Site VPN (quicker setup, encrypted)

### Azure Container Registry (ACR)

- Always → Amazon ECR (Elastic Container Registry) (1:1 deterministic)
- Preserve repository names and image tags
- Geo-replication → ECR replication rules (cross-region or cross-account)

## 6-Criteria Rubric

Apply in order:

1. **Eliminators**: Does Azure config require AWS-unsupported features? If yes: switch to alternative
2. **Operational Model**: Managed (ALB, Route 53, CloudFront) vs Custom (VPN, custom routing)?
   - Prefer managed
3. **User Preference**: From `preferences.json`: `design_constraints.compliance`?
   - **PCI or HIPAA:** Neither framework mandates Direct Connect. **Bias toward documented private connectivity** between on-premises and AWS (e.g. **AWS Direct Connect** or **Site-to-Site VPN** with encryption, monitoring, and change control) — confirm with your QSA / BAA / security team; many compliant designs use VPN-only or no hybrid link when all workloads move fully to AWS.
   - **FedRAMP:** GovCloud and federal boundary requirements dominate; private connectivity is often part of the approved architecture — confirm with your authorizing official / security team.
   - If `compliance` includes `"ccpa"` → VPN or Direct Connect both acceptable; prioritize documented data paths, retention controls, and logging for consumer privacy workflows — not a forced Direct Connect gate.
   - If none of the above: VPN or public-internet paths are commonly acceptable when encrypted and documented.
4. **Feature Parity**: Does Azure config require AWS-unsupported features?
   - Example: Azure Policy-based routing → Custom route tables in AWS (AWS supports this natively)
   - Example: Application Gateway multi-site hosting → ALB host-based routing rules
5. **Cluster Context**: Are other resources in cluster using specific load balancers? Match for consistency
6. **Simplicity**: Fewer resources = higher score

## Examples

### Example 1: Virtual Network

- Azure: `azurerm_virtual_network` (address_space=["10.0.0.0/16"], subnets=[public, private])
- Signals: Explicit subnets, dual-tier (public/private)
- Criterion 1 (Eliminators): PASS
- → **AWS: VPC (10.0.0.0/16 CIDR, public + private subnets per AZ)**
- Confidence: `deterministic`

### Example 2: Network Security Group

- Azure: `azurerm_network_security_group` (inbound rule: port 443, source=*, priority=100)
- Signals: HTTPS ingress, public
- → **AWS: Security Group (ingress rule: 443/tcp from 0.0.0.0/0)**
- Confidence: `deterministic`

### Example 3: Application Gateway (HTTP + path-based routing)

- Azure: `azurerm_application_gateway` (http_listener=[443], request_routing_rule=[path_based_routing to /api/*])
- Signals: Path-based routing, HTTPS, L7
- Criterion 1 (Eliminators): PASS (no SSL passthrough)
- Criterion 2 (Operational Model): ALB (managed, L7)
- → **AWS: ALB with target groups + listener rules (path-based)**
- Confidence: `inferred`

### Example 4: Azure DNS Zone

- Azure: `azurerm_dns_zone` (name="example.com")
- Signals: Public DNS zone
- → **AWS: Route 53 Hosted Zone (example.com)**
- Confidence: `deterministic`

## Output Schema

```json
{
  "azure_type": "azurerm_application_gateway",
  "azure_address": "prod-app-gateway",
  "azure_config": {
    "sku": {
      "name": "WAF_v2",
      "tier": "WAF_v2"
    },
    "http_listener": [{ "protocol": "Https", "port": 443 }],
    "request_routing_rule": [{ "rule_type": "PathBasedRouting" }]
  },
  "aws_service": "Application Load Balancer",
  "aws_config": {
    "load_balancer_type": "application",
    "scheme": "internet-facing",
    "listener": {
      "protocol": "HTTPS",
      "port": 443
    },
    "waf_web_acl_arn": "arn:aws:wafv2:us-east-1:ACCOUNT_ID:regional/webacl/prod-waf",
    "region": "us-east-1"
  },
  "confidence": "inferred",
  "rationale": "Rubric: Azure Application Gateway (WAF_v2, HTTPS, path routing) → AWS ALB + AWS WAF (L7, host/path routing with WAF)"
}
```
