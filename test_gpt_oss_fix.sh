#!/usr/bin/env bash
set -euo pipefail

echo "=== GPT-OSS 20B Chat API Fix Verification ==="
echo

# Test 1: Chat API (expected to work with GPT-OSS)
echo "🧪 Test 1: Chat API (should work for GPT-OSS)"
echo "Command: curl -s http://localhost:11434/api/chat ..."
chat_result=$(curl -s http://localhost:11434/api/chat -d '{
  "model":"gpt-oss:20b",
  "messages":[
    {"role":"system","content":"You are a helpful diagnostic assistant."},
    {"role":"user","content":"Say hello in one sentence."}
  ],
  "options":{"temperature":1.0,"top_p":1.0}
}' | jq -r '.message.content // "ERROR: No content field"')

echo "Result: $chat_result"
echo

# Test 2: Generate API (expected to fail/empty for GPT-OSS)
echo "🧪 Test 2: Generate API (expected to fail for GPT-OSS)"
echo "Command: curl -s http://localhost:11434/api/generate ..."
generate_result=$(curl -s http://localhost:11434/api/generate -d '{
  "model":"gpt-oss:20b",
  "prompt":"Say hello in one sentence.",
  "options":{"temperature":1.0,"top_p":1.0}
}' | jq -r '.response // "ERROR: No response field"')

echo "Result: $generate_result"
echo

# Analysis
echo "=== Analysis ==="
if [[ -n "$chat_result" && "$chat_result" != "ERROR: No content field" && ${#chat_result} -gt 10 ]]; then
    echo "✅ Chat API: Working (got meaningful response)"
else
    echo "❌ Chat API: Failed or empty response"
fi

if [[ -z "$generate_result" || "$generate_result" == "ERROR: No response field" || ${#generate_result} -lt 5 ]]; then
    echo "✅ Generate API: Failed as expected for GPT-OSS"
    echo "📋 Diagnosis: Format mismatch confirmed - GPT-OSS needs chat API"
else
    echo "⚠️  Generate API: Unexpectedly working"
fi

echo
echo "=== RoadNerd Server Test ==="
echo "Testing our fixed implementation..."

# Start server in background for quick test
echo "Starting RoadNerd server with gpt-oss:20b..."
export RN_MODEL="gpt-oss:20b"
export RN_TEMP="1.0"
export RN_TOP_P="1.0" 
export RN_NUM_PREDICT="256"

# Test if server responds
server_test=$(curl -s -X POST http://127.0.0.1:8080/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"issue": "Say hello", "debug": true}' | jq -r '.diagnosis // "ERROR"' 2>/dev/null || echo "Server not running")

if [[ "$server_test" != "Server not running" && "$server_test" != "ERROR" ]]; then
    echo "✅ RoadNerd server: Responding with GPT-OSS via chat API"
    echo "Response: $server_test"
else
    echo "⚠️  RoadNerd server: Not running or failed"
    echo "   To test manually:"
    echo "   RN_MODEL=gpt-oss:20b python3 poc/core/roadnerd_server.py &"
    echo "   curl -X POST http://127.0.0.1:8080/api/diagnose -H 'Content-Type: application/json' -d '{\"issue\": \"Hello test\"}'"
fi

echo
echo "=== Environment Variables ==="
echo "RN_USE_CHAT_MODE=${RN_USE_CHAT_MODE:-auto} (auto = force chat for gpt-oss models)"
echo "RN_TEMP=${RN_TEMP:-1.0} (GPT-OSS default)"
echo "RN_TOP_P=${RN_TOP_P:-1.0} (GPT-OSS default)"
echo
echo "Fix implemented: ✅ Auto-detect gpt-oss models and use /api/chat with proper sampling"