# Messaging Services Design Rubric

**Applies to:** Azure Service Bus, Azure Event Hubs, Azure Event Grid

**Quick lookup (no rubric):** Check `fast-path.md` first (Service Bus Queue → SQS, Event Hubs → Kinesis, Event Grid → EventBridge, etc.)

## Eliminators (Hard Blockers)

| Azure Service       | AWS Target | Blocker                                                                                                           |
| ------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| Service Bus Queue   | SQS        | Multiple subscribers per message (broadcast/fan-out) required → use SNS + SQS (SQS is single-consumer queue)     |
| Service Bus Topic   | SNS        | Exactly-once delivery required → SNS FIFO + SQS FIFO (standard SNS does not guarantee exactly-once)             |
| Event Hubs          | Kinesis    | AMQP 1.0 protocol required by consumers → use Amazon MSK (Managed Kafka); Kinesis does not support AMQP          |

## Signals (Decision Criteria)

### Service Bus Queue

- **Single consumer, durability, point-to-point** → SQS (Standard Queue)
- **Ordered delivery (FIFO)** → SQS FIFO Queue
- **Session-based processing (message grouping)** → SQS FIFO Queue with message group IDs
- **Dead-letter queue configured** → SQS Dead-Letter Queue (DLQ)

### Service Bus Topic (Publish/Subscribe)

- **Multiple subscribers, broadcast/fan-out** → SNS Topic + SQS Subscriptions (fan-out pattern)
- **Filtered subscriptions** → SNS with message filtering attributes (subscription filter policy)
- **Exactly-once, ordered delivery** → SNS FIFO Topic + SQS FIFO Queues

### Service Bus Namespace (general)

- **Queues only** → SQS
- **Topics + subscriptions (fan-out)** → SNS + SQS
- **Mixed (queues + topics)** → SNS + SQS (model queues as SQS, topics as SNS + SQS)

### Event Hubs

- **High-throughput streaming, multiple consumer groups** → Amazon Kinesis Data Streams
- **Kafka-compatible protocol (producers/consumers using Kafka SDK)** → Amazon MSK (Managed Streaming for Apache Kafka)
  - Note: Event Hubs is Kafka-protocol compatible; MSK preserves Kafka SDK compatibility without code changes
- **Consumer group semantics** → Kinesis Data Streams (shard-level consumers) or MSK (consumer groups)
- **Capture to storage (Event Hubs Capture)** → Kinesis Data Firehose (delivery to S3/Redshift)

### Event Grid

- **Event-driven routing, topic subscriptions** → Amazon EventBridge
- **System events (Azure resource events)** → EventBridge (AWS resource events via CloudTrail + EventBridge rules)
- **Custom events (application-defined)** → EventBridge custom event buses
- **Dead-letter and retry** → EventBridge with DLQ configured on target Lambda/SQS

## 6-Criteria Rubric

Apply in order:

1. **Eliminators**: Does Azure config require AWS-unsupported features? If yes: switch
2. **Operational Model**: Managed (SNS, SQS, EventBridge, Kinesis) vs Custom queue?
   - Prefer managed
3. **User Preference**: From `preferences.json`: `design_constraints.availability`?
   - SNS and SQS are multi-AZ by default — no special config needed for HA
   - If ordering or exactly-once delivery required → SQS FIFO (see Eliminators)
   - If Kafka compatibility critical → MSK preferred over Kinesis
4. **Feature Parity**: Does Azure config need features unavailable in AWS?
   - Example: Service Bus message sessions (ordered, grouped) → SQS FIFO (message group IDs)
   - Example: Event Hubs Kafka endpoint → MSK (Kafka-compatible, no SDK changes)
5. **Cluster Context**: Are other resources using SNS/SQS or Kinesis? Match if possible
6. **Simplicity**: SNS + SQS (fan-out) vs single SQS (point-to-point)

## Examples

### Example 1: Service Bus Namespace (queue pattern)

- Azure: `azurerm_servicebus_namespace` (sku=Standard) + `azurerm_servicebus_queue` (name="orders", dead_lettering_on_message_expiration=true)
- Signals: Single consumer queue, dead-letter enabled
- Criterion 1 (Eliminators): PASS (single consumer, no broadcast required)
- Criterion 2 (Operational Model): SQS (managed queue, single consumer)
- → **AWS: SQS Standard Queue + SQS Dead-Letter Queue**
- Confidence: `inferred`

### Example 2: Service Bus Namespace (topic/broadcast pattern)

- Azure: `azurerm_servicebus_namespace` (sku=Standard) + `azurerm_servicebus_topic` (name="user-events") + `azurerm_servicebus_subscription` × 3
- Signals: Topic with multiple subscribers (fan-out/broadcast)
- Criterion 1 (Eliminators): Multiple subscribers → must use SNS + SQS
- → **AWS: SNS Topic + SQS Queue per subscriber (fan-out pattern)**
- Confidence: `inferred`

### Example 3: Event Hubs (high-throughput streaming)

- Azure: `azurerm_eventhub_namespace` (sku=Standard, capacity=2) + `azurerm_eventhub` (name="telemetry", partition_count=4, message_retention=3)
- Signals: High-throughput streaming, multiple consumer groups, partition-based
- Criterion 1 (Eliminators): No AMQP requirement detected
- Criterion 2 (Operational Model): Kinesis Data Streams (managed, shard-based)
- → **AWS: Kinesis Data Streams (4 shards, 3-day retention)**
- Confidence: `inferred`

### Example 4: Event Grid Topic (event-driven routing)

- Azure: `azurerm_eventgrid_topic` (name="app-events", location=eastus) + `azurerm_eventgrid_event_subscription` × 2
- Signals: Custom event topic, multiple subscriptions with filtering
- Criterion 1 (Eliminators): PASS
- Criterion 2 (Operational Model): EventBridge (managed, event-driven routing)
- → **AWS: EventBridge Custom Event Bus + EventBridge Rules (per subscription)**
- Confidence: `inferred`

## Output Schema

```json
{
  "azure_type": "azurerm_servicebus_namespace",
  "azure_address": "prod-servicebus",
  "azure_config": {
    "sku": "Standard",
    "queues": [
      { "name": "orders", "dead_lettering_on_message_expiration": true }
    ],
    "topics": []
  },
  "aws_service": "SQS",
  "aws_config": {
    "queue_name": "orders",
    "message_retention_seconds": 345600,
    "redrive_policy": {
      "deadLetterTargetArn": "arn:aws:sqs:us-east-1:ACCOUNT_ID:orders-dlq",
      "maxReceiveCount": 3
    },
    "region": "us-east-1"
  },
  "confidence": "inferred",
  "rationale": "Service Bus Queue (single consumer, dead-letter) → SQS Standard Queue + SQS DLQ"
}
```
