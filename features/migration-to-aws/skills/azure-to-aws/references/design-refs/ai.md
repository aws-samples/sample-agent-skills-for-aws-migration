# AI/ML Services Design Rubric

**Applies to:** Azure Cognitive Services, Azure Machine Learning, Azure AI services

## LLM Routing

If the detected AI workload is LLM-based (generative models), load the source-specific design reference instead of this file:

- If `ai-workload-profile.json` → `summary.ai_source` = `"azure_openai"`: load `ai-openai-to-bedrock.md`
- If `ai-workload-profile.json` → `summary.ai_source` = `"openai"`: load `ai-openai-to-bedrock.md`
- If `ai-workload-profile.json` → `summary.ai_source` = `"both"`: load `ai-openai-to-bedrock.md`
- If `ai-workload-profile.json` → `summary.ai_source` = `"other"` or absent, OR if the workload is traditional ML (custom models, Cognitive Services, Computer Vision, Speech, etc.): use the SageMaker/Rekognition/Textract rubric below.

---

## Signals (Decision Criteria)

### Azure Machine Learning Workspace

- **Custom model training/inference** → SageMaker (managed training jobs + endpoints)
- **Batch scoring pipelines** → SageMaker Batch Transform
- **AutoML** → SageMaker Autopilot / Canvas

### Azure Cognitive Services (`azurerm_cognitive_account`)

Route by `kind` field:

- **`kind=ComputerVision`** → Amazon Rekognition (image analysis, classification) or AWS Textract (OCR/document text extraction)
- **`kind=SpeechServices`** → Amazon Transcribe (speech-to-text) + Amazon Polly (text-to-speech)
- **`kind=TextAnalytics`** → Amazon Comprehend (sentiment, entity recognition, key phrases, language detection)
- **`kind=Translator`** → Amazon Translate
- **`kind=FormRecognizer`** → AWS Textract (form/table extraction, document intelligence)
- **`kind=OpenAI`** → Amazon Bedrock — **do not use this file**; load `ai-openai-to-bedrock.md` instead

### Azure AI Services (multi-service accounts)

Multi-service `azurerm_cognitive_account` resources (no explicit `kind` or `kind=CognitiveServices`) should be decomposed by feature usage detected in application code. Apply per-feature routing above.

## 6-Criteria Rubric

Apply in order:

1. **Eliminators**: Does Azure config require AWS-unsupported features? If yes: use alternative
2. **Operational Model**: Managed (SageMaker / AWS AI APIs) vs Custom (EC2 + training)?
   - Prefer managed
3. **User Preference**: From `preferences.json`: `design_constraints.cost_sensitivity` + `ai_constraints` (if present)
   - If cost-sensitive → check SageMaker Spot + Autopilot; prefer AWS managed AI APIs over SageMaker where feature parity exists
4. **Feature Parity**: Does Azure config need a model type unavailable in AWS?
   - Example: PyTorch model → SageMaker (supported); ONNX model → SageMaker (supported)
5. **Cluster Context**: Are other compute resources running ML? Prefer SageMaker affinity
6. **Simplicity**: AWS managed AI APIs (Rekognition, Comprehend, etc.) > SageMaker endpoints > custom EC2 instances

## Examples

### Example 1: Azure Machine Learning Workspace (PyTorch model)

- Azure: `azurerm_machine_learning_workspace` + registered model (framework=PyTorch)
- Signals: Custom model training and inference, PyTorch
- Criterion 1 (Eliminators): PASS (PyTorch supported on SageMaker)
- Criterion 2 (Operational Model): SageMaker Endpoint (managed)
- → **AWS: SageMaker Endpoint (PyTorch container)**
- Confidence: `inferred`

### Example 2: Cognitive Account (ComputerVision)

- Azure: `azurerm_cognitive_account` (kind=ComputerVision)
- Signals: Pre-built vision API
- → **AWS: Rekognition (image classification/labeling) or Textract (if OCR/document use case)**
- Confidence: `inferred`

### Example 3: Cognitive Account (FormRecognizer)

- Azure: `azurerm_cognitive_account` (kind=FormRecognizer)
- Signals: Document/form extraction pipeline
- Criterion 1 (Eliminators): PASS (Textract supports forms and tables)
- Criterion 2 (Operational Model): AWS Textract (fully managed)
- → **AWS: Textract**
- Confidence: `inferred`

### Example 4: Cognitive Account (SpeechServices)

- Azure: `azurerm_cognitive_account` (kind=SpeechServices)
- Signals: Speech-to-text and/or text-to-speech usage
- → **AWS: Amazon Transcribe (STT) + Amazon Polly (TTS)**
- Confidence: `inferred`

## Output Schema

```json
{
  "azure_type": "azurerm_cognitive_account",
  "azure_address": "form-recognizer-prod",
  "azure_config": {
    "kind": "FormRecognizer",
    "sku_name": "S0"
  },
  "aws_service": "Textract",
  "aws_config": {
    "features": ["FORMS", "TABLES"],
    "async_api": true
  },
  "confidence": "inferred",
  "rationale": "Azure FormRecognizer → AWS Textract (form/table extraction, document intelligence)"
}
```
