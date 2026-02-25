# AIRTB Project

多智能体实时竞价（RTB）仿真框架，用于研究 **AI Agent 进入广告竞拍后，原有受众性别公平性调节方法是否仍有效**。

本文档说明如何在本机直接开始运行实验。

---

## 环境与依赖

- **Python**：建议 3.9–3.12。
- 在项目根目录创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS；Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

主要依赖：`numpy`、`pandas`、`scipy`、`scikit-learn`、`joblib`、`matplotlib`、`python-dotenv`、`pyyaml`；若跑含 LLM 的完整四组实验还需 `openai`，并在项目根目录 `.env` 中配置 `OPENAI_API_KEY`。

---

## 前置条件（需已就绪）

- **Impression 池**：`DATA/impression_pool_original.log.txt` 已存在（或通过 `IPINYOU_DATA_ROOT` 指定的数据根下同名文件）。
- **CTR 模型**：`models/` 下各广告主已有训练好的模型（如 `ctr.joblib`、`bidding.json`）。

若尚未准备，可参考 `scripts/create_impression_pool_original.py` 与 `scripts/train_ctr.py`。

---

## 运行实验

以下命令均在**项目根目录**执行。

**单次完整实验（4 组 × 2 机制，默认种子 42）：**

```bash
PYTHONPATH=. python main.py
```

结果写入 `logs/`（如 `experiment_report_YYYYMMDD_HHMMSS.json`）。

**指定种子复现（推荐）：**

```bash
PYTHONPATH=. python scripts/run_one_seed.py 2    # 种子 2
```

产出：`logs/run_seed2_terminal.log`、`logs/experiment_report_seed2_*.json`。

**多种子复现（例如 6 个种子）：**

```bash
for seed in 2 15 33 38 69 95; do PYTHONPATH=. python scripts/run_one_seed.py $seed; done
```

**仅跑 9 个 DataDriven + GSP vs Constrained（不跑 LLM，快速验证）：**

```bash
PYTHONPATH=. python run_gender_fairness_experiment.py
```

---

## 文档

- `FINAL_EXPERIMENT_DESIGN.md` — 实验设计、四组与机制说明。
- `GENDER_FAIRNESS_METRICS.md` — 公平性指标（slift、κ、dTV）。
- `ARCHITECTURE.md` — 系统架构。
- **跑含 LLM 的实验**：见 `README_LLM_SETUP.md`（API Key、验证与常见问题）。

---

## 数据与参考

数据预处理时参考了 [wnzhang/make-ipinyou-data](https://github.com/wnzhang/make-ipinyou-data)，将 iPinYou RTB 原始数据整理为统一格式。
