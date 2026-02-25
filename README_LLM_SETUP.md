# LLM API 接入（跑含 AI Agent 的实验时用）

## API Key 配置

在**项目根目录**新建 `.env` 文件，写一行：

```bash
OPENAI_API_KEY=sk-你的密钥
```

`main.py` 与 `run_one_seed.py` 会自动加载项目根目录的 `.env`，无需再 `export`。

## 验证

```bash
PYTHONPATH=. python test_llm_api.py
```

若输出包含「API 调用成功」或已切换到真实 LLM 模式，即配置正确。未配置或 Key 无效时，LLM 会走 MOCK 模式（不发起真实请求）。

## 可选配置

- **模型**：在 `experiments/config.py` 中修改 `LLM_MODEL`（默认 `gpt-4o-mini`）。
- **仍为 Mock**：检查同终端下 `echo $OPENAI_API_KEY` 是否为空；若用 `.env`，确认在项目根目录运行、且文件名为 `.env`。

## 常见问题

- **API 报错**：检查 Key 是否有效、网络与代理、OpenAI 账户余额。
- **不要将 API Key 写在代码里或提交到仓库。**
