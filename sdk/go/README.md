# SeaRei Go SDK

Official Go client library for [SeaRei AI Safety API](https://github.com/searei/safety-eval-mini).

## Installation

```bash
go get github.com/searei/searei-go
```

## Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/searei/searei-go"
)

func main() {
    // Initialize client
    client := searei.NewClient(&searei.Config{
        APIKey:  "your_api_key",  // Optional for self-hosted
        BaseURL: "http://localhost:8001",  // Or your API URL
    })

    // Score a single text
    result, err := client.Score(context.Background(), "I will kill you", nil)
    if err != nil {
        log.Fatal(err)
    }

    if result.IsUnsafe() {
        fmt.Printf("⚠️  Flagged: %s (score: %.2f)\n", result.Category, result.Score)
        fmt.Printf("Rationale: %s\n", result.Rationale)
    } else {
        fmt.Println("✅ Content is safe")
    }

    // Batch scoring
    texts := []string{"Hello world", "I will kill you", "Nice weather today"}
    batch, err := client.BatchScore(context.Background(), texts, nil)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Flagged %d/%d texts\n", batch.Flagged(), batch.Total())
    for i, result := range batch.Results {
        if result.IsUnsafe() {
            fmt.Printf("  [%d] %s: %s\n", i, result.Category, texts[i])
        }
    }
}
```

## API Reference

### `searei.NewClient(config *Config) *Client`

Creates a new SeaRei API client.

**Config fields:**
- `APIKey` (string): API key for authentication (optional for self-hosted)
- `BaseURL` (string): Base URL for API (default: `http://localhost:8001`)
- `HTTPClient` (*http.Client): Custom HTTP client (optional)
- `MaxRetries` (int): Maximum number of retries (default: 3)

**Example:**
```go
client := searei.NewClient(&searei.Config{
    APIKey:     "sk_test_...",
    BaseURL:    "https://api.searei.ai",
    MaxRetries: 5,
})
```

### `client.Score(ctx, text, options) (*ScoreResult, error)`

Score a single text for safety violations.

**Parameters:**
- `ctx` (context.Context): Request context
- `text` (string): Text content to score
- `options` (*ScoreOptions): Optional parameters
  - `Category` (string): Filter by category
  - `Language` (string): Language code

**Returns:** `*ScoreResult, error`

**Example:**
```go
result, err := client.Score(ctx, "I hate you", &searei.ScoreOptions{
    Category: "harassment",
})
if err != nil {
    log.Fatal(err)
}

fmt.Println(result.Prediction)  // "flag" or "pass"
fmt.Println(result.Score)       // 0.0-1.0
fmt.Println(result.Category)    // "harassment"
```

### `client.BatchScore(ctx, texts, options) (*BatchResult, error)`

Score multiple texts in a single request.

**Parameters:**
- `ctx` (context.Context): Request context
- `texts` ([]string): Slice of text contents
- `options` (*ScoreOptions): Optional parameters

**Returns:** `*BatchResult, error`

**Example:**
```go
texts := []string{"Hello", "I will hurt you", "Good morning"}
batch, err := client.BatchScore(ctx, texts, nil)
if err != nil {
    log.Fatal(err)
}

fmt.Println(batch.Flagged())  // Number of flagged texts
```

### `client.Health(ctx) (map[string]interface{}, error)`

Check API health status.

**Returns:** Health status map

**Example:**
```go
health, err := client.Health(ctx)
if err != nil {
    log.Fatal(err)
}

fmt.Println(health["status"])  // "healthy"
```

### `ScoreResult`

Result from a score request.

**Fields:**
- `Prediction` (string): "flag" or "pass"
- `Score` (float64): Confidence score (0.0-1.0)
- `Category` (string): Violation category
- `Rationale` (string): Explanation
- `Method` (string): Detection method used
- `LatencyMs` (int): Request latency
- `PolicyVersion` (string): Policy version
- `PolicyChecksum` (string): Policy checksum

**Methods:**
- `IsSafe() bool`: True if prediction == "pass"
- `IsUnsafe() bool`: True if prediction == "flag"

### `BatchResult`

Result from a batch request.

**Fields:**
- `Results` ([]*ScoreResult): Individual results
- `LatencyMs` (int): Total latency

**Methods:**
- `Total() int`: Total texts scored
- `Flagged() int`: Number flagged
- `Safe() int`: Number safe

## Error Handling

```go
import "github.com/searei/searei-go"

result, err := client.Score(ctx, "some text", nil)
if err != nil {
    switch e := err.(type) {
    case *searei.AuthenticationError:
        log.Println("Invalid API key")
    case *searei.RateLimitError:
        log.Println("Rate limit exceeded")
    case *searei.ValidationError:
        log.Println("Validation error:", e.Message)
    case *searei.APIError:
        log.Printf("API error (%d): %s", e.StatusCode, e.Message)
    default:
        log.Println("Unknown error:", err)
    }
}
```

## Advanced Usage

### Context Timeout

```go
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

result, err := client.Score(ctx, "text", nil)
```

### Custom HTTP Client

```go
import "net/http"

httpClient := &http.Client{
    Timeout: 60 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
    },
}

client := searei.NewClient(&searei.Config{
    APIKey:     "your_api_key",
    HTTPClient: httpClient,
})
```

### Environment Variables

```bash
export SEAREI_API_KEY="your_api_key"
```

```go
// API key automatically loaded from environment
client := searei.NewClient(&searei.Config{})
```

### Quick Score Function

```go
import "github.com/searei/searei-go"

result, err := searei.Score(
    context.Background(),
    "I will kill you",
    &searei.Config{APIKey: "..."},
    &searei.ScoreOptions{Category: "violence"},
)
```

### Custom Categories

```go
// Filter by specific category
result, err := client.Score(ctx, "I will hurt you", &searei.ScoreOptions{
    Category: "violence",
})

// Score for self-harm content only
result, err := client.Score(ctx, "I want to hurt myself", &searei.ScoreOptions{
    Category: "self_harm",
})
```

### Multilingual Support

```go
// Spanish content
result, err := client.Score(ctx, "Te voy a matar", &searei.ScoreOptions{
    Language: "es",
})

// Arabic content
result, err := client.Score(ctx, "سأقتلك", &searei.ScoreOptions{
    Language: "ar",
})
```

## Testing

```bash
go test -v
go test -cover
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Documentation:** https://docs.searei.ai
- **Issues:** https://github.com/searei/searei-go/issues
- **Email:** support@searei.ai












