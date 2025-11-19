/**
 * SeaRei Node.js SDK
 * Official Node.js client for SeaRei AI Safety API
 * 
 * Installation:
 *   npm install searei
 * 
 * Usage:
 *   const { SeaReiClient } = require('searei');
 *   
 *   const client = new SeaReiClient({ apiKey: 'your_api_key' });
 *   const result = await client.score('I will kill you');
 *   
 *   if (result.isUnsafe) {
 *     console.log(`Flagged: ${result.category} (${result.score})`);
 *   }
 */

const https = require('https');
const http = require('http');
const { URL } = require('url');

const VERSION = '0.1.0';

/**
 * Result from a content safety score request
 */
class ScoreResult {
  constructor(data) {
    this.prediction = data.prediction;
    this.score = data.score;
    this.category = data.category || null;
    this.rationale = data.rationale || null;
    this.method = data.method || null;
    this.latencyMs = data.latency_ms || null;
    this.policyVersion = data.policy_version || null;
    this.policyChecksum = data.policy_checksum || null;
  }

  /**
   * Returns true if content is safe (prediction === 'pass')
   */
  get isSafe() {
    return this.prediction === 'pass';
  }

  /**
   * Returns true if content is unsafe (prediction === 'flag')
   */
  get isUnsafe() {
    return this.prediction === 'flag';
  }

  toString() {
    return `ScoreResult(prediction='${this.prediction}', score=${this.score.toFixed(3)}, category='${this.category}')`;
  }
}

/**
 * Result from a batch score request
 */
class BatchResult {
  constructor(data) {
    this.results = data.results.map(r => new ScoreResult(r));
    this.total = this.results.length;
    this.flagged = this.results.filter(r => r.isUnsafe).length;
    this.safe = this.results.filter(r => r.isSafe).length;
    this.latencyMs = data.latency_ms || 0;
  }

  toString() {
    return `BatchResult(total=${this.total}, flagged=${this.flagged}, safe=${this.safe})`;
  }
}

/**
 * Base exception for SeaRei SDK errors
 */
class SeaReiError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SeaReiError';
  }
}

/**
 * Raised when API key is invalid or missing
 */
class AuthenticationError extends SeaReiError {
  constructor(message) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

/**
 * Raised when rate limit is exceeded
 */
class RateLimitError extends SeaReiError {
  constructor(message) {
    super(message);
    this.name = 'RateLimitError';
  }
}

/**
 * Raised when request validation fails
 */
class ValidationError extends SeaReiError {
  constructor(message) {
    super(message);
    this.name = 'ValidationError';
  }
}

/**
 * SeaRei AI Safety API Client
 * 
 * @param {Object} options - Configuration options
 * @param {string} [options.apiKey] - API key for authentication (optional for self-hosted)
 * @param {string} [options.baseUrl='http://localhost:8001'] - Base URL for API
 * @param {number} [options.timeout=30000] - Request timeout in milliseconds
 * @param {number} [options.maxRetries=3] - Maximum number of retries on failure
 * 
 * @example
 * const client = new SeaReiClient({ apiKey: 'sk_test_...' });
 * const result = await client.score('I will kill you');
 * console.log(result.prediction); // 'flag'
 */
class SeaReiClient {
  constructor(options = {}) {
    this.apiKey = options.apiKey || process.env.SEAREI_API_KEY;
    this.baseUrl = (options.baseUrl || 'http://localhost:8001').replace(/\/$/, '');
    this.timeout = options.timeout || 30000;
    this.maxRetries = options.maxRetries || 3;
  }

  /**
   * Make an HTTP request with retry logic
   * @private
   */
  async _request(method, endpoint, body = null) {
    const url = new URL(endpoint, this.baseUrl);
    const protocol = url.protocol === 'https:' ? https : http;

    const headers = {
      'User-Agent': `searei-nodejs/${VERSION}`,
      'Content-Type': 'application/json',
    };

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const options = {
      method,
      headers,
      timeout: this.timeout,
    };

    let lastError = null;
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const response = await this._makeRequest(protocol, url, options, body);
        return response;
      } catch (error) {
        lastError = error;
        if (attempt < this.maxRetries - 1 && error.name !== 'AuthenticationError' && error.name !== 'ValidationError') {
          await this._sleep(Math.pow(2, attempt) * 1000); // Exponential backoff
          continue;
        }
        throw error;
      }
    }

    throw new SeaReiError(`Request failed after ${this.maxRetries} retries: ${lastError.message}`);
  }

  /**
   * Make a single HTTP request
   * @private
   */
  _makeRequest(protocol, url, options, body) {
    return new Promise((resolve, reject) => {
      const req = protocol.request(url, options, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', () => {
          try {
            const json = JSON.parse(data);

            // Handle errors
            if (res.statusCode === 401) {
              reject(new AuthenticationError('Invalid or missing API key'));
            } else if (res.statusCode === 429) {
              reject(new RateLimitError('Rate limit exceeded'));
            } else if (res.statusCode === 422) {
              reject(new ValidationError(`Validation error: ${data}`));
            } else if (res.statusCode >= 400) {
              reject(new SeaReiError(`API error (${res.statusCode}): ${data}`));
            } else {
              resolve(json);
            }
          } catch (error) {
            reject(new SeaReiError(`Failed to parse response: ${error.message}`));
          }
        });
      });

      req.on('error', (error) => {
        reject(new SeaReiError(`Request failed: ${error.message}`));
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new SeaReiError('Request timeout'));
      });

      if (body) {
        req.write(JSON.stringify(body));
      }

      req.end();
    });
  }

  /**
   * Sleep helper for exponential backoff
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Score a single text for safety violations
   * 
   * @param {string} text - Text content to score
   * @param {Object} [options] - Additional options
   * @param {string} [options.category] - Optional category filter
   * @param {string} [options.language] - Optional language code
   * @returns {Promise<ScoreResult>}
   * 
   * @example
   * const result = await client.score('I will kill you');
   * if (result.isUnsafe) {
   *   console.log(`Flagged: ${result.category}`);
   * }
   */
  async score(text, options = {}) {
    const payload = { text };
    if (options.category) payload.category = options.category;
    if (options.language) payload.language = options.language;

    const data = await this._request('POST', '/score', payload);
    return new ScoreResult(data);
  }

  /**
   * Score multiple texts in a single request
   * 
   * @param {string[]} texts - List of text contents to score
   * @param {Object} [options] - Additional options
   * @param {string} [options.category] - Optional category filter
   * @param {string} [options.language] - Optional language code
   * @returns {Promise<BatchResult>}
   * 
   * @example
   * const texts = ['Hello world', 'I will kill you', 'Nice weather'];
   * const result = await client.batchScore(texts);
   * console.log(`Flagged ${result.flagged}/${result.total}`);
   */
  async batchScore(texts, options = {}) {
    const rows = texts.map(text => ({ text }));
    const payload = { rows };
    if (options.category) payload.category = options.category;
    if (options.language) payload.language = options.language;

    const data = await this._request('POST', '/score-batch', payload);
    return new BatchResult(data);
  }

  /**
   * Check API health status
   * 
   * @returns {Promise<Object>} Health status object
   * 
   * @example
   * const health = await client.health();
   * console.log(health.status); // 'healthy'
   */
  async health() {
    return await this._request('GET', '/healthz');
  }
}

/**
 * Quick score function without creating a client
 * 
 * @param {string} text - Text to score
 * @param {Object} [options] - Client and score options
 * @returns {Promise<ScoreResult>}
 * 
 * @example
 * const { score } = require('searei');
 * const result = await score('I will kill you');
 * console.log(result.prediction); // 'flag'
 */
async function score(text, options = {}) {
  const client = new SeaReiClient(options);
  return await client.score(text, options);
}

module.exports = {
  SeaReiClient,
  ScoreResult,
  BatchResult,
  SeaReiError,
  AuthenticationError,
  RateLimitError,
  ValidationError,
  score,
  VERSION,
};

// CLI support
if (require.main === module) {
  (async () => {
    const args = process.argv.slice(2);
    if (args.length === 0) {
      console.log('Usage: node index.js "text to score"');
      process.exit(1);
    }

    const text = args.join(' ');

    try {
      const result = await score(text);
      console.log(`\nResult: ${result.prediction}`);
      console.log(`Score: ${result.score.toFixed(3)}`);
      if (result.category) console.log(`Category: ${result.category}`);
      if (result.rationale) console.log(`Rationale: ${result.rationale}`);
      console.log(`Method: ${result.method}`);
      console.log(`Latency: ${result.latencyMs}ms`);
    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  })();
}












