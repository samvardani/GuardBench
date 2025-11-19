#!/bin/bash
# Test script for ChatGPT OAuth discovery endpoints

echo "=== Testing Required Endpoints ==="
echo ""

echo "1. PRM (Resource-specific):"
echo "curl -i https://searei.com/.well-known/oauth-protected-resource/wp-json/wpai/v1/mcp"
echo ""

echo "2. AS Discovery (Path-inserted):"
echo "curl -i https://searei.com/.well-known/oauth-authorization-server/wp-json/wpai/v1"
echo ""

echo "3. JWKS:"
echo "curl -i https://searei.com/wp-json/wpai/v1/oauth/jwks.json"
echo ""

echo "4. DCR:"
echo "curl -i -X POST https://searei.com/wp-json/wpai/v1/oauth/register -H 'Content-Type: application/json' -d '{\"application_type\":\"web\",\"token_endpoint_auth_method\":\"none\"}'"
echo ""

echo "Expected: All should return 200/201 with Content-Type: application/json"
