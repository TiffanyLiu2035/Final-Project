# LLM API setup (for experiments with AI agents)

## API key configuration

Create a `.env` file in the **project root** with one line:

```bash
OPENAI_API_KEY=sk-your-key
```

`main.py` and `run_one_seed.py` load `.env` from the project root automatically; no need to `export`.

## Verification

```bash
PYTHONPATH=. python test_llm_api.py
```

If the output shows "API call succeeded" or that it has switched to real LLM mode, configuration is correct. If unset or invalid, the LLM runs in MOCK mode (no real requests).

## Optional configuration

- **Model**: Change `LLM_MODEL` in `experiments/config.py` (default `gpt-4o-mini`).
- **Still in Mock**: Check `echo $OPENAI_API_KEY` in the same terminal; if using `.env`, ensure you run from the project root and the file is named `.env`.

## FAQ

- **API errors**: Check that the key is valid, network/proxy, and OpenAI account balance.
- **Do not put the API key in code or commit it to the repository.**
