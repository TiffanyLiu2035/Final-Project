"""
Test LLM API connection.
"""
import os
import sys

def test_llm_api():
    """Test that LLM API is working."""
    print("="*60)
    print("Test LLM API connection")
    print("="*60)
    print()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  Error: OPENAI_API_KEY not set")
        print()
        print("Set it with:")
        print("  export OPENAI_API_KEY='sk-your-key'")
        print()
        print("Or create .env (install python-dotenv first):")
        print("  pip install python-dotenv")
        print("  echo 'OPENAI_API_KEY=sk-your-key' > .env")
        return False

    print(f"  API Key set: {api_key[:10]}...{api_key[-4:]}")
    print()

    try:
        from tools.llm_client import LLMClient
        print("  LLMClient import OK")
    except Exception as e:
        print(f"  Import failed: {e}")
        return False

    print("  Creating LLMClient...")
    client = LLMClient(model="gpt-5-nano", temperature=0.2)

    if client.use_mock:
        print("  Still in MOCK mode")
        print()
        print("Possible causes:")
        print("  1. OPENAI_API_KEY not passed correctly")
        print("  2. openai library not installed")
        print("  3. API Key format invalid")
        return False

    print("  Real LLM mode enabled")
    print()

    print("  Testing API call...")
    test_prompt = """Return a simple JSON object:
{
    "test": true,
    "message": "API connection OK"
}"""

    try:
        result = client.generate_json(test_prompt)
        print("  API call OK")
        print(f"  Result: {result}")
        print()
        print("="*60)
        print("  All tests passed. LLM API ready.")
        print("="*60)
        return True
    except Exception as e:
        print(f"  API call failed: {e}")
        print()
        print("Check:")
        print("  1. API Key valid (format: sk-...)")
        print("  2. Network connection")
        print("  3. API balance")
        print("  4. Firewall / proxy")
        return False

if __name__ == "__main__":
    success = test_llm_api()
    sys.exit(0 if success else 1)
