# SeaRei Node.js SDK

Official Node.js client library for [SeaRei AI Safety API](https://github.com/searei/safety-eval-mini).

## Installation

```bash
npm install searei
# or
yarn add searei
```

## Quick Start

```javascript
const { SeaReiClient } = require('searei');

// Initialize client
const client = new SeaReiClient({
  apiKey: 'your_api_key',  // Optional for self-hosted
  baseUrl: 'http://localhost:8001'  // Or your API URL
});

// Score a single text
const result = await client.score('I will kill you');

if (result.isUnsafe) {
  console.log(`⚠️  Flagged: ${result.category} (score: ${result.score.toFixed(2)})`);
  console.log(`Rationale: ${result.rationale}`);
} else {
  console.log('✅ Content is safe');
}

// Batch scoring
const texts = ['Hello world', 'I will kill you', 'Nice weather today'];
const batch = await client.batchScore(texts);

console.log(`Flagged ${batch.flagged}/${batch.total} texts`);
batch.results.forEach((result, i) => {
  if (result.isUnsafe) {
    console.log(`  [${i}] ${result.category}: ${texts[i]}`);
  }
});
```

## API Reference

### `SeaReiClient`

Main client class for interacting with the API.

**Constructor:**
```javascript
new SeaReiClient({
  apiKey: 'optional_api_key',
  baseUrl: 'http://localhost:8001',
  timeout: 30000,  // 30 seconds
  maxRetries: 3
})
```

**Methods:**

#### `score(text, options)`

Score a single text for safety violations.

**Parameters:**
- `text` (string): Text content to score
- `options` (object, optional):
  - `category` (string): Filter by category (violence, harassment, etc.)
  - `language` (string): Language code (en, es, ar, etc.)

**Returns:** `Promise<ScoreResult>`

**Example:**
```javascript
const result = await client.score('I hate you', { category: 'harassment' });
console.log(result.prediction);  // 'flag' or 'pass'
console.log(result.score);        // 0.0-1.0
console.log(result.category);     // 'harassment'
```

#### `batchScore(texts, options)`

Score multiple texts in a single request.

**Parameters:**
- `texts` (string[]): Array of text contents
- `options` (object, optional): Same as `score()`

**Returns:** `Promise<BatchResult>`

**Example:**
```javascript
const texts = ['Hello', 'I will hurt you', 'Good morning'];
const batch = await client.batchScore(texts);
console.log(batch.flagged);  // Number of flagged texts
```

#### `health()`

Check API health status.

**Returns:** `Promise<Object>` with status information

### `ScoreResult`

Result object from a score request.

**Properties:**
- `prediction` (string): "flag" or "pass"
- `score` (number): Confidence score (0.0-1.0)
- `category` (string): Violation category
- `rationale` (string): Explanation
- `method` (string): Detection method used
- `latencyMs` (number): Request latency
- `policyVersion` (string): Policy version
- `policyChecksum` (string): Policy checksum

**Getters:**
- `isSafe` (boolean): True if prediction === "pass"
- `isUnsafe` (boolean): True if prediction === "flag"

### `BatchResult`

Result object from a batch request.

**Properties:**
- `results` (ScoreResult[]): Individual results
- `total` (number): Total texts scored
- `flagged` (number): Number flagged
- `safe` (number): Number safe
- `latencyMs` (number): Total latency

## Error Handling

```javascript
const {
  SeaReiClient,
  SeaReiError,
  AuthenticationError,
  RateLimitError
} = require('searei');

try {
  const result = await client.score('some text');
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.log('Rate limit exceeded, please retry later');
  } else if (error instanceof SeaReiError) {
    console.log(`API error: ${error.message}`);
  }
}
```

## Advanced Usage

### Quick Score Function

```javascript
const { score } = require('searei');

const result = await score('I will kill you', { apiKey: '...' });
console.log(result.prediction);
```

### Environment Variables

```bash
export SEAREI_API_KEY="your_api_key"
```

```javascript
// API key automatically loaded from environment
const client = new SeaReiClient();
```

### TypeScript Support

```typescript
import { SeaReiClient, ScoreResult, BatchResult } from 'searei';

const client = new SeaReiClient({ apiKey: 'your_api_key' });
const result: ScoreResult = await client.score('text');
```

### Custom Categories

```javascript
// Filter by specific category
const result = await client.score('I will hurt you', { category: 'violence' });

// Score for self-harm content only
const result = await client.score('I want to hurt myself', { category: 'self_harm' });
```

### Multilingual Support

```javascript
// Spanish content
const result = await client.score('Te voy a matar', { language: 'es' });

// Arabic content
const result = await client.score('سأقتلك', { language: 'ar' });
```

## CLI Usage

```bash
# Score from command line
node index.js "I will kill you"

# Or if installed globally
npm install -g searei
searei "text to score"
```

## Testing

```bash
# Install dev dependencies
npm install

# Run tests
npm test

# With coverage
npm run test:coverage
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Documentation:** https://docs.searei.ai
- **Issues:** https://github.com/searei/searei-nodejs/issues
- **Email:** support@searei.ai












