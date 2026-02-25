#!/bin/bash
# LLM API setup script

echo "=========================================="
echo "Configure LLM API Key"
echo "=========================================="
echo ""

if [ -n "$OPENAI_API_KEY" ]; then
    echo "  OPENAI_API_KEY is set: ${OPENAI_API_KEY:0:10}..."
else
    echo "  OPENAI_API_KEY not set."
    echo ""
    echo "Choose: 1) Env var (temporary)  2) .env file (persistent)"
    read -p "Choice (1/2): " choice
    if [ "$choice" == "1" ]; then
        read -p "OpenAI API Key (sk-...): " api_key
        export OPENAI_API_KEY="$api_key"
        echo "  Set for this session. Add to ~/.zshrc to persist: export OPENAI_API_KEY=\"$api_key\""
    elif [ "$choice" == "2" ]; then
        read -p "OpenAI API Key (sk-...): " api_key
        echo "OPENAI_API_KEY=$api_key" > .env
        echo "  Created .env. Run: pip install python-dotenv"
    fi
fi

echo ""
echo "=========================================="
echo "Test API connection"
echo "=========================================="
echo ""

python3 << 'PYTHON_EOF'
import os
from tools.llm_client import LLMClient

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("  OPENAI_API_KEY not set. Run: export OPENAI_API_KEY='sk-...'")
    exit(1)

print(f"  API Key set: {api_key[:10]}...")
print("")

client = LLMClient(model="gpt-5-nano", temperature=0.2)
if client.use_mock:
    print("  Still in MOCK mode. Check OPENAI_API_KEY and: pip install openai")
    exit(1)

print("  Real LLM mode enabled.")
print("")

print("  Testing API call...")
try:
    test_prompt = "Return JSON: {\"test\": true}"
    result = client.generate_json(test_prompt)
    print(f"  API call OK: {result}")
except Exception as e:
    print(f"  API call failed: {e}")
    print("  Check: API key, network, account balance.")
    exit(1)

print("")
print("==========================================")
print("  Setup complete. You can run experiments now.")
print("==========================================")
PYTHON_EOF

