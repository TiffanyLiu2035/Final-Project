"""
Verify OpenAI API key with one call (OpenAI Developer quickstart style).

Official docs:
  - Create API key: https://platform.openai.com/api-keys
  - macOS/Linux: export OPENAI_API_KEY="your_api_key_here"
  - SDK reads key from env: client = OpenAI()

Run (use the same Python/env as your project, e.g. venv with pip install openai):
  cd /path/to/airtb_project
  PYTHONPATH=. python scripts/verify_openai_api.py
"""
import os
import sys

# Load .env from project root (optional; or export OPENAI_API_KEY in shell)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_root, ".env")
if os.path.isfile(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v:
                    os.environ[k] = v

key = os.getenv("OPENAI_API_KEY")
if not key:
    print("OPENAI_API_KEY not set. Either:")
    print("  1. Export in terminal: export OPENAI_API_KEY=\"your_api_key_here\"")
    print("  2. Or add to project root .env: OPENAI_API_KEY=your_api_key_here")
    sys.exit(1)
print(f"OPENAI_API_KEY set: {key[:12]}...{key[-4:] if len(key) > 16 else ''}")

# Quickstart: client = OpenAI() — reads OPENAI_API_KEY from env automatically
from openai import OpenAI
client = OpenAI()

MODEL = "gpt-4o-mini"

# 1) Basic connectivity
print("1) Calling API (gpt-4o-mini, one short request)...")
try:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=50,
        messages=[{"role": "user", "content": "Say exactly: API key works."}],
    )
    text = (response.choices[0].message.content or "").strip()
    print("   Response:", text)
    print("   OK — API key is valid.")
except Exception as e:
    print("   API call failed:", e)
    sys.exit(1)

# 2) Temperature: call with temperature=0 twice; same output => param works
print("\n2) Testing temperature (temperature=0, same prompt twice)...")
try:
    r1 = client.chat.completions.create(
        model=MODEL,
        max_tokens=20,
        temperature=0,
        messages=[{"role": "user", "content": "Reply with one number: 42"}],
    )
    r2 = client.chat.completions.create(
        model=MODEL,
        max_tokens=20,
        temperature=0,
        messages=[{"role": "user", "content": "Reply with one number: 42"}],
    )
    t1 = (r1.choices[0].message.content or "").strip()
    t2 = (r2.choices[0].message.content or "").strip()
    print("   First  reply:", t1)
    print("   Second reply:", t2)
    if t1 == t2:
        print("   OK — temperature=0 is supported and deterministic.")
    else:
        print("   (Responses differ; temperature may still be supported.)")
except Exception as e:
    print("   Temperature test failed:", e)
    sys.exit(1)
