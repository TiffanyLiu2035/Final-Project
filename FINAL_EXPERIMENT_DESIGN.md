# 实验设计与使用指南：AI Agent 进入后受众性别公平性调节是否仍有效

## 🎯 研究问题

**核心问题**：AI Agent 辅助广告主竞价是不可逆趋势。本试验模拟一个竞价广告平台，用 AI Agent 逐步替换历史数据训练出的 Agent，观察**受众性别公平性**指标变化，研究：**AI Agent 进入广告竞拍系统后，原本的公平性调节方法（平台机制 + 广告主自律）是否仍有效。**

- **研究主体**：受众公平性（性别公平），数据中有明确性别标签。
- **平台侧调节**：Constrained Auction Mechanism（约束拍卖，按受众性别施加公平约束）。
- **广告主侧调节**：公平感知型逐利 Agent（在收益目标下兼顾曝光分布与公平性目标，对应 Bid Reweighting 思路在 Agent 行为中的体现）。

---

## 📊 实验设计

### 测试的机制（2 种）

1. **GSP (Generalized Second Price)** — 第二价格拍卖，作为**基准**，无公平干预。
2. **Constrained Auction Mechanism** — 平台侧受众性别约束（目标区间 [ℓ, 1−ℓ] 等，见 `mechanisms/constrained_auction.py`）。

### 公平性指标（3 个）

1. **Selection Lift (slift)** — 公平改善：衡量公平约束是否提升了原本处于不利地位群体的曝光机会（性别比例公平性）。系统级有两种：**slift**（worst-case）与 **slift_weighted**（按曝光加权平均）。**实验与绘图统一以 slift_weighted 为核心指标。**
2. **Revenue Ratio κ (kappa)** — 效率代价：κ = rev_fair / rev_base，衡量在实现公平性的同时平台收入的损失程度。
3. **TV-distance (dTV, advertiser displacement)** — 系统稳定性：衡量公平干预对广告主分配结果造成的整体扰动大小。

- **slift_weighted（核心）**：越接近 1 表示各广告主在男女曝光比例上越公平；按曝光加权，避免小样本广告主拉低系统得分。
- **κ**：公平机制相对 GSP 的收入比，κ < 1 表示为公平付出收入代价。
- **dTV**：公平机制相对 GSP 的广告主份额变化（total variation distance）。

实现与完整说明见 `GENDER_FAIRNESS_METRICS.md` 与 `metrics/gender_fairness_metrics.py`。

### 三类 Agent（广告主）

1. **历史数据训练型**  
   仅根据用户标签（含性别等）评估价值并竞价，不更新策略、不感知公平性、不学习机制。对应现有 `DataDrivenAgent`。

2. **自适应逐利型**  
   模拟在 AI 辅助竞价背景下，高度适应但完全逐利的广告主。以收益最大化为唯一目标，根据拍卖反馈动态调整出价策略；通过对不同用户标签下的回报长期观察，调整在不同群体上的出价强度，在既定机制下实现收益优化。**已实现**：`agents/llm_bidding_agent.py` 中的 `AdaptiveProfitAgent`（Type 2），基于 DataDriven 的 base_bid × lambda_male/female，由 LLM 定期更新系数。

3. **公平感知型逐利**  
   研究广告主自律是否能在一定程度上缓解平台公平性调节压力，是否与平台机制叠加时产生过度调节。仍以收益为主要目标，但在评估策略时同时考虑竞价收益与受众曝光分布是否偏离预设公平目标；当某策略导致受众公平性显著恶化时，在后续更新中抑制该方向，从而在收益与公平之间权衡。**已实现**：`agents/llm_bidding_agent.py` 中的 `FairnessAwareAgent`（Type 3），prompt 中注入 slift 与合规阈值，LLM 输出 lambda 以兼顾公平与收益。

---

## 🔬 四组实验

每组均在 **GSP 或 Constrained Auction** 下运行 **1000 次**竞拍，并计算上述三个公平性指标（slift、κ、dTV）。

| 组别 | Agent 配置 | 目的 |
|------|------------|------|
| **1. Baseline** | 9 个历史数据训练型 Agent | 无 AI、无公平感知，作为基准。 |
| **2. 逐利型** | 9 个自适应逐利型 AI Agent（可设不同逐利程度） | 观察纯逐利 AI 对公平性指标的影响。 |
| **3. 公平感知型** | 9 个公平感知型逐利 AI Agent（可设不同合规程度） | 观察广告主自律（Bid Reweighting 思路）是否缓解/叠加平台机制。 |
| **4. 混合** | 上述三类 Agent 各 3 个，共 9 个 | 观察 AI 逐步替代过程中，公平性指标与机制有效性的变化。 |

**实验组合**：2 种机制 × 4 组配置。每组配置可分别跑 GSP 与 Constrained，便于对比 baseline 与公平机制下的 slift、κ、dTV。

---

## 📈 预期分析

1. **机制有效性**：在四组 Agent 配置下，Constrained 相对 GSP 的 slift、κ、dTV 变化，判断平台公平机制在「数据训练型 → 逐利型 → 公平感知型 → 混合」环境下是否仍有效。
2. **广告主自律效果**：组 3（公平感知型）与组 2（纯逐利型）对比，看自律是否缓解公平性恶化、是否与 Constrained 叠加产生过度调节（如 dTV 过大）。
3. **系统稳定性**：通过 dTV 观察公平干预对广告主份额分布的扰动，结合 κ 评估效率–公平–稳定性三角。

---

## 🚀 运行实验

### 前置条件

1. **已训练 CTR 模型**
   ```bash
   PYTHONPATH=. python scripts/train_ctr.py DATA models
   ```

2. **（可选）设置 LLM API Key**（若使用逐利型/公平感知型 LLM Agent）
   ```bash
   export OPENAI_API_KEY="sk-你的API密钥"
   ```
   详见 `README_LLM_SETUP.md`。

### 主实验：4 组 × 2 机制（完整实验）

```bash
PYTHONPATH=. python main.py
# 或
PYTHONPATH=. python -m experiments.experiment_runner
```

对组 1–4 分别跑 GSP 与 Constrained（每组 1000 轮），使用受众性别公平指标（slift、κ、dTV）；报告与 fairness 明细见控制台及 `logs/`（如 `experiment_report_YYYYMMDD_HHMMSS.json`）。

### 多种子复现（建议至少 5 次）

```bash
PYTHONPATH=. python scripts/run_experiment_multiple_seeds.py
```

默认使用种子 42、43、44、45、46 各跑一轮完整实验，报告另存为 `logs/experiment_report_seed{N}_*.json`。

### 简化实验：仅 Baseline（9 个 DataDriven + GSP vs Constrained）

```bash
PYTHONPATH=. python run_gender_fairness_experiment.py
```

输出：Baseline (GSP) 与 Constrained 的 round_history 及 **slift、κ、dTV**（见控制台与 `logs/`）。不跑组 2–4、不调用 LLM。

---

## 🔧 自定义配置

- **实验轮数**：在 `experiments/config.py` 中修改 `TOTAL_ROUNDS`（当前设计为 1000）。
- **随机种子**：默认 42；多种子时由 `scripts/run_experiment_multiple_seeds.py` 设置，或通过环境变量 `EXPERIMENT_RANDOM_SEED` 覆盖。
- **Constrained 参数**：在 `experiments/config.py` 中见 `MAX_BID_RATIO`、`MIN_WIN_RATE`；`run_gender_fairness_experiment.py` 中可调 `fairness_strength`、`penalty_scale`（仅影响该脚本）。

---

## ✅ 与当前代码/文档对齐

- **机制**：GSP、Constrained Auction（实现见 `mechanisms/`）。
- **指标**：Selection Lift、Revenue Ratio κ、TV-distance（见 `GENDER_FAIRNESS_METRICS.md` 与 `metrics/gender_fairness_metrics.py`）。
- **入口**：完整 4 组 × 2 机制实验入口为 `main.py`；逐利型、公平感知型及混合组已在 `experiments/config.py` 与 `agents/llm_bidding_agent.py` 中实现，由 `experiments/agent_factory.py` 按配置创建。
