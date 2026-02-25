# AIRTB multi-agent simulation system — architecture

## System overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application entry                        │
│  main.py  →  experiments.experiment_runner.main()               │
│  run_gender_fairness_experiment.py  (optional: GSP vs Constrained only) │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Experiment layer                           │
│              experiments/experiment_runner.py                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ExperimentRunner                                          │  │
│  │  - Create agents by group (1–4), inject GSP or Constrained │  │
│  │  - Call SimulationEngine.run(), collect round_history     │  │
│  │  - Compute GenderFairnessMetrics, write logs and reports  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Config      │  │ Agent factory│  │ Simulation   │
│ experiments/ │  │ experiments/ │  │ engine/      │
│ config.py    │  │ agent_factory│  │ simulation.py│
│ agent_tuning │  │              │  │              │
│ .yaml (opt)  │  │ - Create     │  │ - Per round: │
│              │  │   three agent│  │   collect    │
│ - Advertiser/│  │   types by   │  │   bids→winner│
│   budget     │  │   strategy   │  │ - platform   │
│ - Rounds/LLM │  │ - Groups 1–4 │  │   swappable  │
└──────────────┘  └──────────────┘  │   GSP/Constr.│
                                    └──────┬───────┘
                    ┌──────────────────────┼───────────────────────┐
                    │                      │                       │
                    ▼                      ▼                       ▼
         ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
         │   Agent layer    │   │   Mechanisms     │   │   Tools          │
         │   agents/        │   │   mechanisms/    │   │   tools/          │
         │                  │   │                  │   │                   │
         │ - DataDrivenAgent│   │ - GSPMechanism   │   │ - CTRModel        │
         │   (Group 1 base) │   │ - Constrained    │   │ - LLMClient       │
         │ - AdaptiveProfit │   │   AuctionMechanism│   │ - ipinyou_loader  │
         │   Agent (Grp 2)  │   │   (audience      │   │ - impression_pool │
         │ - FairnessAware  │   │   gender bounds) │   │ - gender_*        │
         │   Agent (Grp 3)  │   │                  │   │   feature_mapper  │
         │ Group 4 = mix    │   │ (injected into   │   │   _pool           │
         └──────────────────┘   │  engine.platform)│   └──────────────────┘
                    │           └──────────────────┘
                    └───────────┬──────────┘
                                ▼
                    ┌──────────────────┐
                    │   Metrics        │
                    │   metrics/       │
                    │ GenderFairness   │
                    │ Metrics          │
                    │ (slift, κ, dTV)  │
                    └──────────────────┘
```

## Data flow

### 1. Training (offline)

```
iPinYou data
    │
    ▼
tools/ipinyou_loader.py  (parse YZX format)
    │
    ▼
scripts/train_ctr.py → tools/ctr_models.py
    │
    ▼
models/{adv_id}/
    ├── ctr.joblib
    └── (optional) bidding.json
```

### 2. Experiments (online simulation)

```
ExperimentConfig.get_experiment_group_configs(group_num)
    │
    ▼
AgentFactory.create_agents(configs)
    │ (DataDriven / AdaptiveProfit / FairnessAware)
    ▼
SimulationEngine(agents, ..., platform = GSP or Constrained)
    │
    ├── Per round:
    │   ├── ImpressionPool supplies current impression (incl. gender)
    │   ├── Agent.decide_bid()  (CTRModel / LLM)
    │   ├── platform.select_winner(bids[, agents][, impression])
    │   ├── Update agent budget and metrics
    │   └── Append to round_history
    │
    ▼
GenderFairnessMetrics computed from round_history
    │
    ▼
logs/ (CSV, JSON, reports)
```

## Core components

### 1. Agent layer (`agents/`)

```
BaseAgent (base.py)
    │
    ├── DataDrivenAgent (data_driven_agent.py)
    │   └── Group 1: CTR-based bids, no fairness awareness, no strategy updates
    │
    └── LLMBiddingAgent(DataDrivenAgent) (llm_bidding_agent.py)
            ├── AdaptiveProfitAgent   — Group 2: profit-seeking, update λ_male/λ_female per round
            └── FairnessAwareAgent   — Group 3: fairness-aware; suppress updates when slift below threshold
```

- Group 4: mix of the three types above (3 each).
- Responsibilities: `decide_bid()`, `update_metrics()`, optional `observe_other_bids()` / `set_round_info()`.

### 2. Auction mechanisms (`mechanisms/`)

- **GSPMechanism**: Second-price auction; optional filter of unknown gender by impression.
- **ConstrainedAuctionMechanism**: Audience gender constraints (target interval [ℓ, 1−ℓ]), state-dependent fairness adjustment.
- Created by `experiment_runner` and assigned to `engine.platform`, replacing the default simple highest-bid-wins `Platform` in `engine/platform.py`.

### 3. Simulation engine (`engine/`)

- **simulation.py**: Round loop; collect bids → `self.platform.select_winner(...)` → update agents and `round_history`.
- **platform.py**: Default `Platform` for simple winner selection when GSP/Constrained are not injected.

### 4. Tools (`tools/`)

- **ctr_models.py** — CTRModel
- **llm_client.py** — LLMClient
- **ipinyou_loader.py** — YZX data loading
- **impression_pool.py** — ImpressionPool
- **gender_feature_mapper.py** / **gender_filtered_pool.py** — gender feature and filtering
- **save_round_history.py** — round history persistence

### 5. Metrics (`metrics/`)

- **GenderFairnessMetrics**: slift (Selection Lift), κ (Revenue Ratio), dTV (Advertiser Displacement), etc., from `round_history` and audience gender.

## Experiment execution flow

1. **Init**: Load `.env`, `ExperimentConfig` (optional `agent_tuning.yaml`), get config by group → `AgentFactory.create_agents()`.
2. **Run**: For each group and mechanism, create `SimulationEngine`, set `engine.platform = GSPMechanism()` or `ConstrainedAuctionMechanism(...)` → `engine.run()` (rounds from `ExperimentConfig.TOTAL_ROUNDS`, default 1000).
3. **Results**: `GenderFairnessMetrics` → write to `logs/` (CSV, JSON, etc.).

## Data layout

```
project root/
├── models/{adv_id}/     # CTR models, etc.
├── logs/                # Experiment logs, fairness results
└── scripts/train_ctr.py
```

## Interface contract

### Agent

- `decide_bid() -> float`
- `update_budget(amount)` (called by engine on win)
- Optional: `set_round_info()`, `observe_other_bids()`, `update_metrics()`, `get_performance_metrics()`, `set_current_impression()`

### Winner selection (platform / mechanism)

- Default `Platform.select_winner(bids)` → `(name, payment)` or `None`.
- GSP / Constrained: `select_winner(bids, agents=None, impression=None)`; may return `List[(name, payment)]` for multi-slot. Engine uses `inspect.signature` for compatibility.

## Design patterns

- **Factory**: `AgentFactory` creates agents by strategy.
- **Pluggable strategy**: `SimulationEngine.platform` can be GSP or Constrained.
- **Template method**: `BaseAgent` defines interface; subclasses implement `decide_bid()` etc.
