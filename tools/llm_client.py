import os
import json
from typing import Optional, Dict, Any

_openai_import_error = None
try:
    from openai import OpenAI  # openai>=1.0.0
except Exception as e:  # pragma: no cover
    OpenAI = None  # type: ignore
    _openai_import_error = e

# OpenAI API valid temperature range [0, 2]
TEMPERATURE_MIN, TEMPERATURE_MAX = 0.0, 2.0


class LLMClient:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2, timeout: float = 20.0, use_mock: Optional[bool] = None, api_key: Optional[str] = None):
        self.model = model
        self.temperature = max(TEMPERATURE_MIN, min(TEMPERATURE_MAX, float(temperature)))
        if self.temperature != temperature:
            import warnings
            warnings.warn(f"temperature {temperature} clamped to [{TEMPERATURE_MIN}, {TEMPERATURE_MAX}] -> {self.temperature}")
        self.timeout = timeout
        key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if use_mock is None:
            self.use_mock = OpenAI is None or not key
        else:
            self.use_mock = use_mock
        if self.use_mock or OpenAI is None:
            self._client = None
        else:
            self._client = OpenAI(api_key=key) if key else None
            if not key:
                self.use_mock = True
        if self.use_mock:
            if OpenAI is None:
                print("[LLMClient] Mode: MOCK — OpenAI module not available. Install: pip install openai", _openai_import_error or "")
            else:
                print("[LLMClient] Mode: MOCK (no API calls). Set OPENAI_API_KEY in .env or export it to use real API.")
        else:
            print(f"[LLMClient] Mode: REAL API (model={self.model}). API key loaded.")

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        if self.use_mock:
            # Deterministic mock for reproducibility
            return {
                "bid": 10.0,
                "a_t": 0.0,
                "explore": False,
                "rationale": "mock decision",
                "risk_flags": []
            }
        # GPT-5 series does not support custom temperature; omit to avoid API error
        try:
            kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            }
            if self.model.startswith("gpt-5"):
                pass
            else:
                kwargs["temperature"] = self.temperature
            resp = self._client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:  # fallback
            print(f"[LLMClient] API call failed: {e}")
            return {
                "bid": 10.0,
                "a_t": 0.0,
                "explore": False,
                "rationale": f"fallback due to error: {e}",
                "risk_flags": ["llm_error"]
            }


