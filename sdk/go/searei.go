// Package searei provides the official Go client for SeaRei AI Safety API
//
// Installation:
//
//	go get github.com/searei/searei-go
//
// Usage:
//
//	import "github.com/searei/searei-go"
//
//	client := searei.NewClient(&searei.Config{
//	    APIKey: "your_api_key",
//	})
//
//	result, err := client.Score(context.Background(), "I will kill you", nil)
//	if err != nil {
//	    log.Fatal(err)
//	}
//
//	if result.IsUnsafe() {
//	    fmt.Printf("Flagged: %s (%.2f)\n", result.Category, result.Score)
//	}
package searei

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

const (
	// Version is the current SDK version
	Version = "0.1.0"

	// DefaultBaseURL is the default API base URL
	DefaultBaseURL = "http://localhost:8001"

	// DefaultTimeout is the default request timeout
	DefaultTimeout = 30 * time.Second

	// DefaultMaxRetries is the default maximum number of retries
	DefaultMaxRetries = 3
)

// Config holds the client configuration
type Config struct {
	// APIKey for authentication (optional for self-hosted)
	APIKey string

	// BaseURL for the API (default: http://localhost:8001)
	BaseURL string

	// HTTPClient to use for requests (optional)
	HTTPClient *http.Client

	// MaxRetries for failed requests (default: 3)
	MaxRetries int
}

// ScoreResult represents the result of a content safety score request
type ScoreResult struct {
	Prediction      string  `json:"prediction"`
	Score           float64 `json:"score"`
	Category        string  `json:"category,omitempty"`
	Rationale       string  `json:"rationale,omitempty"`
	Method          string  `json:"method,omitempty"`
	LatencyMs       int     `json:"latency_ms,omitempty"`
	PolicyVersion   string  `json:"policy_version,omitempty"`
	PolicyChecksum  string  `json:"policy_checksum,omitempty"`
}

// IsSafe returns true if the content is safe (prediction == "pass")
func (r *ScoreResult) IsSafe() bool {
	return r.Prediction == "pass"
}

// IsUnsafe returns true if the content is unsafe (prediction == "flag")
func (r *ScoreResult) IsUnsafe() bool {
	return r.Prediction == "flag"
}

// String returns a string representation of the result
func (r *ScoreResult) String() string {
	return fmt.Sprintf("ScoreResult(prediction='%s', score=%.3f, category='%s')",
		r.Prediction, r.Score, r.Category)
}

// BatchResult represents the result of a batch score request
type BatchResult struct {
	Results   []*ScoreResult `json:"results"`
	LatencyMs int            `json:"latency_ms,omitempty"`
}

// Total returns the total number of texts scored
func (b *BatchResult) Total() int {
	return len(b.Results)
}

// Flagged returns the number of flagged texts
func (b *BatchResult) Flagged() int {
	count := 0
	for _, r := range b.Results {
		if r.IsUnsafe() {
			count++
		}
	}
	return count
}

// Safe returns the number of safe texts
func (b *BatchResult) Safe() int {
	return b.Total() - b.Flagged()
}

// String returns a string representation of the result
func (b *BatchResult) String() string {
	return fmt.Sprintf("BatchResult(total=%d, flagged=%d, safe=%d)",
		b.Total(), b.Flagged(), b.Safe())
}

// ScoreOptions holds options for score requests
type ScoreOptions struct {
	// Category filter (violence, harassment, etc.)
	Category string `json:"category,omitempty"`

	// Language code (en, es, ar, etc.)
	Language string `json:"language,omitempty"`
}

// Client is the SeaRei API client
type Client struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
	maxRetries int
}

// NewClient creates a new SeaRei API client
func NewClient(config *Config) *Client {
	if config == nil {
		config = &Config{}
	}

	apiKey := config.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("SEAREI_API_KEY")
	}

	baseURL := config.BaseURL
	if baseURL == "" {
		baseURL = DefaultBaseURL
	}

	httpClient := config.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{
			Timeout: DefaultTimeout,
		}
	}

	maxRetries := config.MaxRetries
	if maxRetries == 0 {
		maxRetries = DefaultMaxRetries
	}

	return &Client{
		apiKey:     apiKey,
		baseURL:    baseURL,
		httpClient: httpClient,
		maxRetries: maxRetries,
	}
}

// request makes an HTTP request with retry logic
func (c *Client) request(ctx context.Context, method, endpoint string, body interface{}) ([]byte, error) {
	url := c.baseURL + endpoint

	var reqBody io.Reader
	if body != nil {
		jsonData, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		reqBody = bytes.NewBuffer(jsonData)
	}

	var lastErr error
	for attempt := 0; attempt < c.maxRetries; attempt++ {
		req, err := http.NewRequestWithContext(ctx, method, url, reqBody)
		if err != nil {
			return nil, fmt.Errorf("failed to create request: %w", err)
		}

		req.Header.Set("User-Agent", "searei-go/"+Version)
		req.Header.Set("Content-Type", "application/json")

		if c.apiKey != "" {
			req.Header.Set("Authorization", "Bearer "+c.apiKey)
		}

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			if attempt < c.maxRetries-1 {
				time.Sleep(time.Duration(1<<uint(attempt)) * time.Second) // Exponential backoff
				continue
			}
			return nil, fmt.Errorf("request failed after %d retries: %w", c.maxRetries, err)
		}
		defer resp.Body.Close()

		respBody, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read response body: %w", err)
		}

		// Handle errors
		if resp.StatusCode == http.StatusUnauthorized {
			return nil, &AuthenticationError{Message: "Invalid or missing API key"}
		} else if resp.StatusCode == http.StatusTooManyRequests {
			return nil, &RateLimitError{Message: "Rate limit exceeded"}
		} else if resp.StatusCode == http.StatusUnprocessableEntity {
			return nil, &ValidationError{Message: fmt.Sprintf("Validation error: %s", string(respBody))}
		} else if resp.StatusCode >= 400 {
			return nil, &APIError{StatusCode: resp.StatusCode, Message: string(respBody)}
		}

		return respBody, nil
	}

	return nil, fmt.Errorf("request failed after %d retries: %w", c.maxRetries, lastErr)
}

// Score scores a single text for safety violations
//
// Example:
//
//	result, err := client.Score(ctx, "I will kill you", &searei.ScoreOptions{
//	    Category: "violence",
//	})
func (c *Client) Score(ctx context.Context, text string, options *ScoreOptions) (*ScoreResult, error) {
	payload := map[string]interface{}{
		"text": text,
	}

	if options != nil {
		if options.Category != "" {
			payload["category"] = options.Category
		}
		if options.Language != "" {
			payload["language"] = options.Language
		}
	}

	respBody, err := c.request(ctx, http.MethodPost, "/score", payload)
	if err != nil {
		return nil, err
	}

	var result ScoreResult
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &result, nil
}

// BatchScore scores multiple texts in a single request
//
// Example:
//
//	texts := []string{"Hello world", "I will kill you", "Nice weather"}
//	result, err := client.BatchScore(ctx, texts, nil)
func (c *Client) BatchScore(ctx context.Context, texts []string, options *ScoreOptions) (*BatchResult, error) {
	rows := make([]map[string]string, len(texts))
	for i, text := range texts {
		rows[i] = map[string]string{"text": text}
	}

	payload := map[string]interface{}{
		"rows": rows,
	}

	if options != nil {
		if options.Category != "" {
			payload["category"] = options.Category
		}
		if options.Language != "" {
			payload["language"] = options.Language
		}
	}

	respBody, err := c.request(ctx, http.MethodPost, "/score-batch", payload)
	if err != nil {
		return nil, err
	}

	var result BatchResult
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &result, nil
}

// Health checks the API health status
//
// Example:
//
//	health, err := client.Health(ctx)
//	fmt.Println(health["status"])
func (c *Client) Health(ctx context.Context) (map[string]interface{}, error) {
	respBody, err := c.request(ctx, http.MethodGet, "/healthz", nil)
	if err != nil {
		return nil, err
	}

	var health map[string]interface{}
	if err := json.Unmarshal(respBody, &health); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return health, nil
}

// Error types

// APIError represents a generic API error
type APIError struct {
	StatusCode int
	Message    string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("API error (%d): %s", e.StatusCode, e.Message)
}

// AuthenticationError represents an authentication error
type AuthenticationError struct {
	Message string
}

func (e *AuthenticationError) Error() string {
	return e.Message
}

// RateLimitError represents a rate limit error
type RateLimitError struct {
	Message string
}

func (e *RateLimitError) Error() string {
	return e.Message
}

// ValidationError represents a validation error
type ValidationError struct {
	Message string
}

func (e *ValidationError) Error() string {
	return e.Message
}

// Quick score function without creating a client
func Score(ctx context.Context, text string, config *Config, options *ScoreOptions) (*ScoreResult, error) {
	client := NewClient(config)
	return client.Score(ctx, text, options)
}












