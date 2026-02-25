# AIRTB 多智能体仿真系统 - 整体架构

## 📐 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用入口层                                 │
│  main.py  →  experiments.experiment_runner.main()               │
│  run_gender_fairness_experiment.py  (可选，独立跑 GSP vs Constrained) │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      实验管理层                                   │
│              experiments/experiment_runner.py                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ExperimentRunner                                          │  │
│  │  - 按实验组 (1~4) 创建 Agent，注入 GSP 或 Constrained 机制   │  │
│  │  - 调用 SimulationEngine.run()，收集 round_history         │  │
│  │  - 计算 GenderFairnessMetrics，导出日志与报告               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  配置        │  │  Agent 工厂   │  │  仿真引擎     │
│ experiments/ │  │ experiments/ │  │ engine/      │
│ config.py     │  │ agent_factory│  │ simulation.py│
│ agent_tuning  │  │              │  │              │
│ .yaml(可选)  │  │ - 按 strategy │  │ - 每轮收集   │
│              │  │   创建三类    │  │   出价→选胜者 │
│ - 广告主/预算 │  │   Agent 实例 │  │ - platform   │
│ - 轮数/LLM   │  │ - 组 1~4 配置 │  │   可替换为   │
└──────────────┘  └──────────────┘  │   GSP/Constrained
                                    └──────┬───────┘
                    ┌──────────────────────┼───────────────────────┐
                    │                      │                       │
                    ▼                      ▼                       ▼
         ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
         │   Agent 层       │   │   拍卖机制        │   │   工具层          │
         │   agents/        │   │   mechanisms/     │   │   tools/          │
         │                  │   │                  │   │                   │
         │ - DataDrivenAgent│   │ - GSPMechanism    │   │ - CTRModel        │
         │   (组1 基线)     │   │ - Constrained     │   │ - LLMClient       │
         │ - AdaptiveProfit │   │   AuctionMechanism│   │ - ipinyou_loader  │
         │   Agent (组2)    │   │   (受众性别约束)   │   │ - impression_pool │
         │ - FairnessAware  │   │                  │   │ - gender_*       │
         │   Agent (组3)    │   │ (注入 engine.     │   │   feature_mapper  │
         │ 组4 为三类混合   │   │  platform)        │   │   _pool           │
         └──────────────────┘   └──────────────────┘   └──────────────────┘
                    │                      │
                    └───────────┬──────────┘
                                ▼
                    ┌──────────────────┐
                    │   指标层         │
                    │   metrics/       │
                    │ GenderFairness   │
                    │ Metrics          │
                    │ (slift, κ, dTV)  │
                    └──────────────────┘
```

## 🔄 数据流

### 1. 训练阶段（离线）

```
iPinYou 数据
    │
    ▼
tools/ipinyou_loader.py  (解析 YZX 格式)
    │
    ▼
scripts/train_ctr.py → tools/ctr_models.py
    │
    ▼
models/{adv_id}/
    ├── ctr.joblib
    └── (可选) bidding.json
```

### 2. 实验阶段（在线仿真）

```
ExperimentConfig.get_experiment_group_configs(group_num)
    │
    ▼
AgentFactory.create_agents(configs)
    │ (DataDriven / AdaptiveProfit / FairnessAware)
    ▼
SimulationEngine(agents, ..., platform 可被替换为 GSP/Constrained)
    │
    ├── 每轮：
    │   ├── ImpressionPool 提供当前 impression（含性别等）
    │   ├── Agent.decide_bid()  （CTRModel / LLM 决策）
    │   ├── platform.select_winner(bids[, agents][, impression])
    │   ├── 更新 Agent 预算与指标
    │   └── 写入 round_history
    │
    ▼
GenderFairnessMetrics 基于 round_history 计算
    │
    ▼
logs/（CSV、JSON、报告）
```

## 🏗️ 核心组件

### 1. Agent 层 (`agents/`)

```
BaseAgent (base.py)
    │
    ├── DataDrivenAgent (data_driven_agent.py)
    │   └── 组 1：CTR 模型出价，不感知公平、不更新策略
    │
    └── LLMBiddingAgent(DataDrivenAgent) (llm_bidding_agent.py)
            ├── AdaptiveProfitAgent   — 组 2：逐利，按轮更新 λ_male/λ_female
            └── FairnessAwareAgent   — 组 3：兼顾公平，slift 低于阈值时抑制更新
```

- 组 4：上述三类混合（各 3 个）。
- 职责：`decide_bid()`、`update_metrics()`、可选 `observe_other_bids()` / `set_round_info()` 等。

### 2. 拍卖机制 (`mechanisms/`)

- **GSPMechanism**：第二价格拍卖，可选按 impression 过滤未知性别。
- **ConstrainedAuctionMechanism**：受众性别约束（目标区间 [ℓ, 1−ℓ]），状态依赖公平调整。
- 由 `experiment_runner` 创建后赋给 `engine.platform`，替代默认的 `engine/platform.py` 中简单价高者得 `Platform`。

### 3. 仿真引擎 (`engine/`)

- **simulation.py**：轮次循环，收集出价 → 调用 `self.platform.select_winner(...)` → 更新 Agent 与 `round_history`。
- **platform.py**：默认 `Platform`，仅用于未注入 GSP/Constrained 时的简单选胜者。

### 4. 工具层 (`tools/`)

- **ctr_models.py** — CTRModel  
- **llm_client.py** — LLMClient  
- **ipinyou_loader.py** — YZX 数据加载  
- **impression_pool.py** — ImpressionPool（统一 impression 池）  
- **gender_feature_mapper.py** / **gender_filtered_pool.py** — 性别特征与过滤  
- **save_round_history.py** — 回合历史保存  

### 5. 指标层 (`metrics/`)

- **GenderFairnessMetrics**：slift（Selection Lift）、κ（Revenue Ratio）、dTV（Advertiser Displacement）等，基于 `round_history` 与受众性别。

## 🔀 实验执行流程

1. **初始化**：加载 `.env`、`ExperimentConfig`（含可选 `agent_tuning.yaml`）、按组号取配置 → `AgentFactory.create_agents()`。
2. **执行**：对每组、每种机制创建 `SimulationEngine`，设置 `engine.platform = GSPMechanism()` 或 `ConstrainedAuctionMechanism(...)` → `engine.run()`（轮数由 `ExperimentConfig.TOTAL_ROUNDS` 决定，默认 1000）。
3. **结果**：`GenderFairnessMetrics` 计算 → 写入 `logs/`（CSV、JSON、图表等）。

## 📊 数据存储

```
项目根目录/
├── models/{adv_id}/     # CTR 模型等
├── logs/                # 实验日志、公平性结果
└── scripts/train_ctr.py
```

## 🔌 接口约定

### Agent

- `decide_bid() -> float`
- `update_budget(amount)`（由引擎在胜出时调用）
- 可选：`set_round_info()`, `observe_other_bids()`, `update_metrics()`, `get_performance_metrics()`, `set_current_impression()`

### 选胜者（platform / mechanism）

- 默认 `Platform.select_winner(bids)` → `(name, payment)` 或 `None`。
- GSP / Constrained：`select_winner(bids, agents=None, impression=None)`，支持多 slot 时返回 `List[(name, payment)]`。引擎通过 `inspect.signature` 做兼容调用。

## 🎯 设计模式

- **工厂**：`AgentFactory` 按 strategy 创建 Agent。
- **策略可替换**：`SimulationEngine.platform` 可替换为 GSP 或 Constrained。
- **模板方法**：`BaseAgent` 定义接口，子类实现 `decide_bid()` 等。
