# Safety Copilot AI Assistant

Safety Copilot is an AI-powered assistant that helps users understand content safety evaluations through natural language conversation.

## Overview

Safety Copilot leverages large language models (LLMs) to provide:
- **Explanations**: Why content was flagged or not flagged
- **Metric Interpretation**: What precision, recall, FNR, and FPR mean
- **Policy Guidance**: Understanding safety categories and rules
- **Optimization Tips**: How to improve evaluation results
- **General Q&A**: Answering questions about the safety system

## Features

✅ **Natural Language Interface**: Ask questions in plain English  
✅ **Context-Aware**: Provides specific answers based on evaluation runs  
✅ **Multi-Domain**: Explains metrics, policies, and results  
✅ **Beautiful UI**: Modern chat interface with markdown support  
✅ **API-First**: REST API for programmatic access  
✅ **Safety Moderation**: Keeps conversations on-topic  
✅ **Fast Responses**: Typical response time 200-500ms  

## Quick Start

### 1. Set OpenAI API Key

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### 2. Start Service

```bash
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### 3. Open Chat UI

Visit: http://localhost:8001/assistant/chat

### 4. Ask Questions

Try these:
- "What categories does the system detect?"
- "Explain precision and recall metrics"
- "How can I reduce false positives?"
- "Why was this content flagged?" (with run ID)

## API Endpoints

### POST /assistant/query

Query the assistant with a question.

**Request**:
```json
{
  "question": "What categories are detected?",
  "run_id": "abc123",           // Optional: specific run context
  "category": "violence",        // Optional: category context
  "language": "en"               // Optional: language context
}
```

**Response**:
```json
{
  "answer": "The system detects 7 categories: violence, hate, harassment, self-harm, sexual content, malware, and extortion. Each category has specific rules and thresholds...",
  "query": "What categories are detected?",
  "latency_ms": 320,
  "model": "gpt-4",
  "tokens_used": 145
}
```

**Example**:
```bash
curl -X POST http://localhost:8001/assistant/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What categories are detected?"
  }'
```

### GET /assistant/health

Check assistant health status.

**Response**:
```json
{
  "status": "healthy",
  "model": "gpt-4"
}
```

### GET /assistant/info

Get assistant information and capabilities.

**Response**:
```json
{
  "name": "Safety Copilot",
  "version": "1.0",
  "description": "AI assistant for safety evaluation analysis",
  "capabilities": [
    "Explain evaluation results",
    "Describe safety categories and policies",
    ...
  ]
}
```

### GET /assistant/chat

Serves the chat UI (HTML page).

## Usage Examples

### Basic Query

```python
import httpx

response = httpx.post(
    "http://localhost:8001/assistant/query",
    json={"question": "What categories are detected?"}
)

data = response.json()
print(f"Answer: {data['answer']}")
print(f"Latency: {data['latency_ms']}ms")
```

### With Run Context

```python
response = httpx.post(
    "http://localhost:8001/assistant/query",
    json={
        "question": "Why was this flagged?",
        "run_id": "abc123"  # Specific evaluation run
    }
)

print(response.json()["answer"])
```

### Programmatic Usage

```python
from assistant import SafetyCopilot, AssistantQuery

# Initialize copilot
copilot = SafetyCopilot(api_key="sk-...")

# Create query
query = AssistantQuery(
    question="Explain false positive rate",
    run_id="abc123"
)

# Get response
response = copilot.query(query, tenant_id="my-tenant")

print(f"Answer: {response.answer}")
print(f"Latency: {response.latency_ms}ms")
print(f"Tokens: {response.tokens_used}")
```

## Example Questions

### About Metrics

- "What is precision and recall?"
- "Explain false positive rate"
- "What does FNR mean?"
- "How do I interpret these metrics?"

### About Results

- "Why was this content flagged?"
- "Why wasn't this flagged?"
- "What rule triggered this?"
- "How confident is this prediction?"

### About Categories

- "What categories are detected?"
- "What is the violence category?"
- "Give examples of harassment"
- "What languages are supported?"

### About Optimization

- "How can I reduce false positives?"
- "How do I improve recall?"
- "Should I adjust thresholds?"
- "What's causing low precision?"

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `ASSISTANT_MODEL` | No | Model to use (default: gpt-4) |
| `ASSISTANT_MAX_TOKENS` | No | Max response tokens (default: 500) |
| `ASSISTANT_TEMPERATURE` | No | Temperature 0-1 (default: 0.7) |

### Custom Configuration

```python
from assistant import SafetyCopilot

copilot = SafetyCopilot(
    api_key="sk-...",
    model="gpt-3.5-turbo",  # Faster, cheaper
    max_tokens=300,
    temperature=0.5,  # More focused
)
```

## Context System

The assistant gathers context automatically:

### Policy Context (Always Included)

- Supported categories
- Supported languages
- Number of rules
- Policy description

### Run Context (When run_id Provided)

- Run ID and timestamp
- Guards used (baseline vs candidate)
- Metrics (precision, recall, FNR, FPR)
- True positives, false positives, etc.
- Policy version

### Example Context

```
Policy Information:
Policy: Safety evaluation policy for content moderation
Supported Categories: harassment, hate, malware, self_harm, sexual, violence
Supported Languages: ar, de, en, es, fa, fr, it, pt, ru, zh
Total Rules: 42

Evaluation Run:
Run ID: abc123
Guards: internal (baseline) vs openai (candidate)
Policy Version: v1.2.3

Metrics:
  baseline:
    Precision: 0.950
    Recall: 0.920
    FNR: 0.080
    FPR: 0.010
    TP: 100, FP: 5, TN: 495, FN: 10
    
  candidate:
    Precision: 0.980
    Recall: 0.940
    FNR: 0.060
    FPR: 0.005
    TP: 105, FP: 2, TN: 498, FN: 7
```

## Chat UI

### Features

- 💬 **Conversational Interface**: Natural chat experience
- 🎨 **Beautiful Design**: Modern gradient UI
- ⚡ **Fast**: Real-time responses
- 📝 **Markdown Support**: Bold, italics, code blocks
- 💡 **Suggestions**: Quick-start questions
- 🔄 **Run ID Input**: Optionalprovide run context

### Accessing the UI

1. Start the service
2. Visit: `http://localhost:8001/assistant/chat`
3. Enter a question
4. Optionally provide a run ID for context
5. Click "Send" or press Enter

### UI Features

**Suggested Questions**:
- What categories are detected?
- Explain metrics
- Reduce false positives
- Supported languages

**Run ID Field**:
- Optional field above chat input
- Provide run ID for specific evaluation context
- Leave empty for general questions

## System Prompt

The assistant uses a carefully crafted system prompt:

```
You are Safety Copilot, an AI assistant helping users understand AI content safety evaluations.

Your role is to:
1. Explain why content was flagged or not flagged
2. Describe safety categories and policies
3. Help users understand metrics (precision, recall, FNR, FPR)
4. Suggest ways to improve evaluation results
5. Answer questions about the safety evaluation system

Guidelines:
- Be concise but thorough
- Use simple language for technical concepts
- Reference specific metrics/data from the provided context
- Stay focused on content safety topics
- If asked about unrelated topics, politely redirect
- Never provide instructions for creating harmful content
- Format responses with markdown for readability
```

## Safety & Moderation

### Question Filtering

The assistant includes basic question filtering:
- Checks for safety-related keywords
- Allows short questions (likely relevant)
- Defaults to allowing questions (LLM will redirect if needed)

### On-Topic Responses

If asked off-topic questions (e.g., "What's the weather?"), the assistant will:
- Politely redirect to safety evaluation topics
- Suggest relevant questions
- Stay focused on its domain

### No Harmful Content

The system prompt explicitly forbids:
- Instructions for creating harmful content
- Bypassing safety policies
- Revealing sensitive system internals

## Performance

- **Response Time**: Typically 200-500ms (depends on LLM)
- **Token Usage**: ~100-200 tokens per query
- **Concurrent Requests**: Supported (async)
- **Rate Limiting**: Subject to OpenAI API limits

## Testing

Run assistant tests:

```bash
pytest tests/test_assistant*.py -v
```

**18 comprehensive tests** covering:
- ✅ Query/Response dataclasses
- ✅ Run and Policy context gathering
- ✅ SafetyCopilot initialization
- ✅ Query processing with mocked LLM
- ✅ Error handling
- ✅ Question moderation
- ✅ Health checks
- ✅ Message building
- ✅ Singleton pattern
- ✅ API model validation

### Mocking LLM for Tests

```python
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_openai():
    with patch("assistant.service.openai") as mock:
        mock_client = MagicMock()
        
        # Mock response
        mock_message = MagicMock()
        mock_message.content = "Test response"
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.total_tokens = 100
        
        mock_client.chat.completions.create.return_value = mock_response
        mock.OpenAI.return_value = mock_client
        
        yield mock_client

def test_copilot(mock_openai):
    copilot = SafetyCopilot(api_key="test-key")
    result = copilot.query(query, tenant_id="test")
    
    assert result.answer == "Test response"
```

## Troubleshooting

### "OpenAI API key is required"

**Fix**: Set the `OPENAI_API_KEY` environment variable:
```bash
export OPENAI_API_KEY=sk-your-key-here
```

### "Safety Copilot not available"

**Cause**: OpenAI package not installed or import error

**Fix**:
```bash
pip install openai
```

### Slow Responses

**Cause**: LLM API latency

**Solutions**:
- Use `gpt-3.5-turbo` instead of `gpt-4` (faster)
- Reduce `max_tokens` to 300
- Check OpenAI API status

### Off-Topic Responses

**Cause**: Question not clearly safety-related

**Fix**: Add more context to your question or provide a run ID

## Advanced Usage

### Custom Model

```python
copilot = SafetyCopilot(
    api_key="sk-...",
    model="gpt-3.5-turbo",  # Faster, cheaper
)
```

### Lower Temperature (More Focused)

```python
copilot = SafetyCopilot(
    api_key="sk-...",
    temperature=0.3,  # More deterministic
)
```

### Batch Questions

```python
questions = [
    "What categories are detected?",
    "Explain precision",
    "How to reduce FPs?",
]

for question in questions:
    query = AssistantQuery(question=question)
    response = copilot.query(query, tenant_id="test")
    print(f"Q: {question}")
    print(f"A: {response.answer}\n")
```

## Cost Estimation

Based on OpenAI pricing (as of 2024):

**GPT-4**:
- Input: $0.03 / 1K tokens
- Output: $0.06 / 1K tokens
- ~150 tokens per query
- **Cost**: ~$0.01 per query

**GPT-3.5-Turbo**:
- Input: $0.0015 / 1K tokens
- Output: $0.002 / 1K tokens
- **Cost**: ~$0.0005 per query (20x cheaper)

For high usage, consider gpt-3.5-turbo.

## Security

- **API Key**: Never logged or exposed
- **Question Filtering**: Basic on-topic check
- **System Prompt**: Forbids harmful instructions
- **No PII**: Context doesn't include user content (only hashes/metrics)
- **Rate Limiting**: Subject to OpenAI limits

## Future Enhancements

- [ ] Multi-turn conversations with memory
- [ ] Streaming responses
- [ ] Voice interface
- [ ] Suggested follow-up questions
- [ ] Integration with documentation search
- [ ] Custom knowledge base
- [ ] Local LLM support (Llama, Mistral)
- [ ] Multi-language support

## Related Documentation

- [API Documentation](API.md)
- [Metrics Guide](METRICS.md)
- [Policy Documentation](POLICY.md)
- [Evaluation Guide](GETTING_STARTED.md)

## Support

For issues:
1. Check `OPENAI_API_KEY` is set
2. Verify OpenAI package installed: `pip show openai`
3. Check OpenAI API status
4. Enable debug logging: `logging.getLogger("assistant").setLevel(logging.DEBUG)`
5. Test with `/assistant/health` endpoint

