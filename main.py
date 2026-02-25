"""
Entry point: load .env first (so OPENAI_API_KEY is set before any LLM client is created), then run experiments.
"""
import os

try:
    from dotenv import load_dotenv
    _root = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

def _load_env():
    """Load .env from project root. Values in .env override existing env vars so OPENAI_API_KEY etc. take effect."""
    # Try two paths: based on current file, and based on cwd (subprocess cwd is usually project root)
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    path = None
    for p in candidates:
        if os.path.isfile(p):
            path = p
            break
    if not path:
        print(f"[main] .env not found, tried: {candidates}")
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k:
                    os.environ[k] = v
    key = os.environ.get("OPENAI_API_KEY", "")
    print(f"[main] .env loaded: {path} | OPENAI_API_KEY: {'set, len %d' % len(key) if key else 'not set'}")

_load_env()

from experiments import experiment_runner


if __name__ == "__main__":
    experiment_runner.main()
